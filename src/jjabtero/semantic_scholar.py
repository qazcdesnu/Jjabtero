"""Semantic Scholar의 참고문헌으로 서재 논문 사이의 인용을 확인한다.

OpenAlex의 참고문헌 목록은 빠진 것이 많아(예: 'Attention Is All You Need'는 40개 가운데 35개),
서재 논문 사이의 인용 선이 빠진다. Semantic Scholar의 참고문헌을 함께 받아 DOI, arXiv ID, 제목으로 맞춘다.

@doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
"""

import os
import re
import time
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Any

import httpx2
from sqlalchemy import Boolean, Column, Engine, MetaData, String, Table, delete, insert, select

from jjabtero.titles import normalize

# @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
S2_PAPER_URL = "https://api.semanticscholar.org/graph/v1/paper"
# @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
S2_REFRESH_AFTER = timedelta(days=7)
# @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
S2_REQUEST_GAP_SECONDS = 1.1
# @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
S2_REFERENCE_LIMIT = 1000
# @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
MIN_TITLE_WORDS = 3

_ARXIV_DOI = re.compile(r"^10\.48550/arxiv\.(.+)$", re.IGNORECASE)
_ARXIV_VERSION = re.compile(r"v\d+$")

_metadata = MetaData()
_s2_fetches = Table(
    "s2_fetches",
    _metadata,
    Column("paper", String, primary_key=True),
    Column("fetched_at", String),
    Column("found", Boolean),
)
_s2_references = Table(
    "s2_references",
    _metadata,
    Column("paper", String, index=True),
    Column("doi", String),
    Column("arxiv", String),
    Column("title", String),
)


class S2BudgetError(Exception):
    """Semantic Scholar가 요청을 잠시 막았다(응답 429).

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """


@dataclass(frozen=True)
class PaperKeys:
    """논문을 맞추는 데 쓰는 식별자. DOI와 arXiv ID는 소문자, 제목은 다듬은 글이다.

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """

    doi: str | None
    arxiv: str | None
    title: str | None


def arxiv_id(value: str | None) -> str | None:
    """arXiv ID를 소문자로, 버전(`v2` 등)과 `arXiv:` 머리를 떼고 돌려준다.

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """
    if not value:
        return None
    plain = value.strip().lower().removeprefix("arxiv:")
    return _ARXIV_VERSION.sub("", plain) or None


def paper_keys(doi: str | None, title: str | None, arxiv: str | None = None) -> PaperKeys:
    """DOI, 제목, arXiv ID로 맞추기용 식별자를 만든다. arXiv DOI면 arXiv ID도 얻는다.

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """
    plain_doi = doi.strip().lower() if doi else None
    match = _ARXIV_DOI.match(plain_doi or "")
    words = normalize(title or "")
    return PaperKeys(
        doi=plain_doi,
        arxiv=arxiv_id(arxiv) or (arxiv_id(match.group(1)) if match else None),
        title=words if len(words.split()) >= MIN_TITLE_WORDS else None,
    )


def same_paper(a: PaperKeys, b: PaperKeys) -> bool:
    """DOI, arXiv ID, 제목 가운데 하나라도 같으면 같은 논문이다.

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """
    return bool(
        (a.doi and a.doi == b.doi) or (a.arxiv and a.arxiv == b.arxiv) or (a.title and a.title == b.title)
    )


def _get(http: httpx2.Client, path: str, params: dict[str, str]) -> dict[str, Any] | None:
    headers = {}
    api_key = os.environ.get("SEMANTIC_SCHOLAR_API_KEY")
    if api_key:
        headers["x-api-key"] = api_key
    response = http.get(f"{S2_PAPER_URL}/{path}", params=params, headers=headers, timeout=30)
    if response.status_code == 429:
        raise S2BudgetError("Semantic Scholar가 요청을 잠시 막았습니다. 다음 갱신 때 이어서 확인합니다.")
    if response.status_code in (400, 404):
        return None
    response.raise_for_status()
    return response.json()


def fetch_references(http: httpx2.Client, doi: str, title: str | None = None) -> list[PaperKeys] | None:
    """DOI로 Semantic Scholar의 참고문헌을 받는다. DOI로 없으면 제목이 똑같은 논문을 찾아 받는다.

    둘 다 없으면 `None`이다. 학회판 DOI가 Semantic Scholar에 없는 경우가 있다(예: SE Networks의 CVPR DOI).

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """
    params = {"fields": "title,externalIds", "limit": str(S2_REFERENCE_LIMIT)}
    body = _get(http, f"DOI:{doi}/references", params)
    if body is None and title:
        match = _get(http, "search/match", {"query": title, "fields": "title"})
        best = ((match or {}).get("data") or [{}])[0]
        wanted = paper_keys(None, title).title
        if best.get("paperId") and wanted and paper_keys(None, best.get("title")).title == wanted:
            body = _get(http, f"{best['paperId']}/references", params)
    if body is None:
        return None
    keys = []
    for item in body.get("data") or []:
        cited: dict[str, Any] = item.get("citedPaper") or {}
        ids = cited.get("externalIds") or {}
        found = paper_keys(ids.get("DOI"), cited.get("title"), ids.get("ArXiv"))
        if found.doi or found.arxiv or found.title:
            keys.append(found)
    return keys


class S2Store:
    """인용 캐시 파일 안의 Semantic Scholar 참고문헌 표. 서재 논문의 DOI로 묶는다.

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """

    def __init__(self, engine: Engine) -> None:
        self.engine = engine
        with engine.begin() as connection:
            _metadata.create_all(connection)

    def save(self, paper: str, references: list[PaperKeys] | None, now: datetime) -> None:
        """논문 하나의 참고문헌을 바꿔 저장한다. `None`은 Semantic Scholar에 없다는 뜻이다.

        @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
        """
        with self.engine.begin() as connection:
            connection.execute(delete(_s2_references).where(_s2_references.c.paper == paper))
            connection.execute(delete(_s2_fetches).where(_s2_fetches.c.paper == paper))
            connection.execute(
                insert(_s2_fetches).values(paper=paper, fetched_at=now.isoformat(), found=references is not None)
            )
            for key in references or []:
                connection.execute(insert(_s2_references).values(paper=paper, doi=key.doi, arxiv=key.arxiv, title=key.title))

    def stale(self, papers: list[str], now: datetime) -> list[str]:
        """확인한 적이 없거나 확인한 지 7일이 지난 논문을 오래된 것부터 돌려준다.

        @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
        """
        with self.engine.connect() as connection:
            fetched = dict(connection.execute(select(_s2_fetches.c.paper, _s2_fetches.c.fetched_at)).all())
        cutoff = (now - S2_REFRESH_AFTER).isoformat()
        due = [paper for paper in dict.fromkeys(papers) if not fetched.get(paper) or fetched[paper] <= cutoff]
        return sorted(due, key=lambda paper: fetched.get(paper) or "")

    def references(self) -> dict[str, list[PaperKeys]]:
        """논문마다의 참고문헌 식별자.

        @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
        """
        found: dict[str, list[PaperKeys]] = {}
        with self.engine.connect() as connection:
            for row in connection.execute(select(_s2_references)):
                found.setdefault(row.paper, []).append(PaperKeys(row.doi, row.arxiv, row.title))
        return found

    def checked_count(self, papers: set[str]) -> int:
        """이 논문들 가운데 Semantic Scholar에서 참고문헌을 받은 수.

        @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
        """
        with self.engine.connect() as connection:
            rows = connection.execute(select(_s2_fetches.c.paper).where(_s2_fetches.c.found.is_(True)))
            return len({row.paper for row in rows} & papers)

    def prune(self, keep: set[str]) -> None:
        """서재에 없는 논문의 기록을 지운다.

        @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
        """
        with self.engine.begin() as connection:
            connection.execute(delete(_s2_references).where(_s2_references.c.paper.not_in(keep)))
            connection.execute(delete(_s2_fetches).where(_s2_fetches.c.paper.not_in(keep)))


def refresh_references(
    http: httpx2.Client,
    store: S2Store,
    papers: list[tuple[str, str | None]],
    now: datetime,
    stopped: Callable[[], bool] = lambda: False,
    sleep: Callable[[float], None] = time.sleep,
) -> tuple[int, str]:
    """오래된 논문의 참고문헌을 받는다. `papers`는 (DOI, 제목)이다. 받은 수와 오류(없으면 빈 글)를 돌려준다.

    키 없이 쓰면 요청 속도 제한이 있으므로 요청 사이를 1.1초 띄우고, 429를 받으면 멈춘다.

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """
    titles = dict(papers)
    store.prune(set(titles))
    count = 0
    for index, doi in enumerate(store.stale(list(titles), now)):
        if stopped():
            break
        if index:
            sleep(S2_REQUEST_GAP_SECONDS)
        try:
            references = fetch_references(http, doi, titles[doi])
        except S2BudgetError as error:
            return count, str(error)
        except (httpx2.HTTPError, ValueError) as error:
            return count, f"Semantic Scholar 연결 실패: {error}"
        store.save(doi, references, now)
        count += 1
    return count, ""


def library_cites(papers: list[tuple[str, str | None, PaperKeys]], references: dict[str, list[PaperKeys]]) -> set[tuple[str, str]]:
    """서재 논문 사이의 인용(인용한 점 ID, 인용된 점 ID)을 Semantic Scholar 참고문헌으로 찾는다.

    `papers`는 (점 ID, 저장 열쇠인 DOI, 식별자)다.

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """
    found: set[tuple[str, str]] = set()
    for citing, key, _ in papers:
        refs = references.get(key or "")
        if not refs:
            continue
        for cited, _, keys in papers:
            if cited != citing and any(same_paper(keys, ref) for ref in refs):
                found.add((citing, cited))
    return found
