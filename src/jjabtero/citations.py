"""인용 데이터의 OpenAlex 연결, 가져오기, 캐시 저장, 백그라운드 갱신, API.

@doc: docs/design/Citations.md#4-저장
@doc: docs/design/Citations.md#5-갱신
"""

import json
import os
import re
import tempfile
import threading
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Literal, Protocol

import httpx2
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy import (
    Column,
    Engine,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    insert,
    select,
    text,
    union,
    update,
)
from sqlalchemy.orm import Session

from jjabtero.library import normalize_doi
from jjabtero.models import Paper
from jjabtero.search import _openalex_item_type
from jjabtero.semantic_scholar import S2Store, refresh_references
from jjabtero.settings import read_settings

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
CACHE_FILE = "citations.db"
# @doc: docs/design/Citations.md#4-저장
CACHE_VERSION = 2
REFRESH_AFTER = timedelta(days=7)
MISS_RETRY_AFTER = timedelta(days=7)
RUN_INTERVAL_SECONDS = 3600
PAGE_SIZE = 200
LOOKUP_BATCH = 100
COCITATION_LIMIT = 100
MAX_AUTHORS = 10
_WORK_FIELDS = "id,doi,display_name,type,publication_year,publication_date,cited_by_count,authorships,primary_location"
_WORK_ID = re.compile(r"W\d+")

_metadata = MetaData()
_fetches = Table(
    "fetches",
    _metadata,
    Column("paper", String, primary_key=True),
    Column("fetched_at", String),
    Column("publication_date", String),
    Column("window_end", String),
    Column("citing_limit", Integer),
    Column("citing_total", Integer),
)
_references = Table(
    "references",
    _metadata,
    Column("paper", String, primary_key=True),
    Column("work", String, primary_key=True),
)
_citations = Table(
    "citations",
    _metadata,
    Column("paper", String, primary_key=True),
    Column("work", String, primary_key=True),
    Column("publication_date", String),
    Column("shared_refs", Integer),
)
_cocitations = Table(
    "cocitations",
    _metadata,
    Column("paper", String, primary_key=True),
    Column("work", String, primary_key=True),
    Column("count", Integer),
)
_works = Table(
    "works",
    _metadata,
    Column("id", String, primary_key=True),
    Column("title", String),
    Column("authors", String),
    Column("year", Integer),
    Column("publication_date", String),
    Column("venue", String),
    Column("doi", String),
    Column("cited_by_count", Integer),
    Column("item_type", String),
    Column("updated_at", String),
)
_link_misses = Table(
    "link_misses",
    _metadata,
    Column("doi", String, primary_key=True),
    Column("tried_at", String),
)


class OpenAlexBudgetError(Exception):
    """OpenAlex 하루 사용량을 다 썼다(응답 429).

    @doc: docs/design/Citations.md#5-갱신
    """


def short_id(value: str | None) -> str | None:
    """`https://openalex.org/W…` 꼴을 `W…`로 줄인다. 형식이 맞지 않으면 `None`이다.

    @doc: docs/design/Citations.md#2-서재-논문과-openalex-연결
    """
    if not value:
        return None
    work_id = value.strip().removeprefix("https://openalex.org/")
    return work_id if _WORK_ID.fullmatch(work_id) else None


def citing_window(published: date) -> tuple[date, date]:
    """공개일부터 1년 뒤까지의 피인용 기간을 돌려준다.

    @doc: docs/design/Citations.md#3-가져오는-범위
    """
    try:
        end = published.replace(year=published.year + 1)
    except ValueError:
        end = date(published.year + 1, 2, 28)
    return published, end


def _get(http: httpx2.Client, url: str, params: dict[str, Any]) -> dict | None:
    api_key = os.environ.get("OPENALEX_API_KEY")
    if api_key:
        params = {**params, "api_key": api_key}
    response = http.get(url, params=params)
    if response.status_code == 429:
        raise OpenAlexBudgetError("OpenAlex 하루 사용량을 다 썼습니다. 다음 갱신 때 이어서 받습니다.")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def _work_row(work: dict[str, Any], now: str) -> dict[str, Any]:
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    authors = [
        (authorship.get("author") or {}).get("display_name")
        for authorship in work.get("authorships") or []
    ]
    return {
        "id": short_id(work.get("id")),
        "title": work.get("display_name") or "",
        "authors": json.dumps([name for name in authors if name][:MAX_AUTHORS], ensure_ascii=False),
        "year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "venue": source.get("display_name"),
        "doi": work.get("doi"),
        "cited_by_count": work.get("cited_by_count"),
        "item_type": _openalex_item_type(work),
        "updated_at": now,
    }


def link_paper(http: httpx2.Client, doi: str) -> str | None:
    """DOI로 OpenAlex 작업 ID를 찾는다. 없으면 `None`이다.

    @doc: docs/design/Citations.md#2-서재-논문과-openalex-연결
    """
    body = _get(http, f"{OPENALEX_WORKS_URL}/doi:{doi}", {"select": "id"})
    return None if body is None else short_id(body.get("id"))


@dataclass
class FetchResult:
    """논문 하나에서 가져온 인용 데이터.

    @doc: docs/design/Citations.md#3-가져오는-범위
    """

    publication_date: str | None
    window_end: str | None
    citing_total: int
    references: list[str]
    citations: list[tuple[str, str | None, int]]
    cocitations: list[tuple[str, int]]
    works: list[dict[str, Any]] = field(default_factory=list)


def lookup_works(http: httpx2.Client, work_ids: list[str], now: datetime) -> list[dict[str, Any]]:
    """OpenAlex에서 여러 논문의 서지 정보를 100건씩 받는다.

    @doc: docs/design/Citations.md#4-저장
    """
    stamp = now.isoformat()
    rows: list[dict[str, Any]] = []
    for index in range(0, len(work_ids), LOOKUP_BATCH):
        batch = work_ids[index : index + LOOKUP_BATCH]
        body = _get(
            http,
            OPENALEX_WORKS_URL,
            {"filter": "openalex_id:" + "|".join(batch), "per-page": LOOKUP_BATCH, "select": _WORK_FIELDS},
        ) or {}
        rows.extend(_work_row(work, stamp) for work in body.get("results") or [] if short_id(work.get("id")))
    return rows


# @doc: docs/design/Citations.md#6-api와-화면
DIRECT_WEIGHT = 0.5
# @doc: docs/design/Citations.md#6-api와-화면
RELATED_LIMIT = 30


@dataclass(frozen=True)
class Relation:
    """가까운 논문 하나의 점수와 까닭.

    @doc: docs/design/Citations.md#6-api와-화면
    """

    work: str
    score: float
    cites_paper: bool
    cited_by_paper: bool
    cocited: int
    shared_refs: int


def related_works(work_id: str, rows: dict[str, Any], citing_count: int) -> list[Relation]:
    """논문 하나와 인용으로 가까운 논문을 점수 순으로 돌려준다.

    점수 = 직접 인용이면 0.5 + 함께 인용된 비율(공동 인용 수 / 가져온 피인용 수)
    + 공유한 참고문헌 비율(공유 참고문헌 수 / 이 논문의 참고문헌 수).

    @doc: docs/design/Citations.md#6-api와-화면
    """
    references: set[str] = rows["references"]
    citations: dict[str, int] = rows["citations"]
    cocitations: dict[str, int] = rows["cocitations"]
    relations = []
    for work in (references | set(citations) | set(cocitations)) - {work_id}:
        cites_paper = work in citations
        cited_by_paper = work in references
        cocited = cocitations.get(work, 0)
        shared = citations.get(work) or 0
        score = (
            (DIRECT_WEIGHT if cites_paper or cited_by_paper else 0)
            + cocited / max(citing_count, 1)
            + shared / max(len(references), 1)
        )
        relations.append(Relation(work, round(score, 4), cites_paper, cited_by_paper, cocited, shared))
    return sorted(relations, key=lambda relation: (-relation.score, relation.work))


# @doc: docs/design/Citations.md#6-api와-화면
Direction = Literal["prior", "later"]
# @doc: docs/design/Citations.md#6-api와-화면
DirectionBasis = Literal["citation", "date"]


def when(publication_date: str | None, year: int | None) -> str | None:
    """공개일(`YYYY-MM-DD`)이 있으면 그것을, 없으면 연도(`YYYY`)를 돌려준다.

    @doc: docs/design/Citations.md#6-api와-화면
    """
    if publication_date:
        return publication_date
    return f"{year:04d}" if year else None


def work_direction(
    relation: Relation, paper_when: str | None, work_when: str | None
) -> tuple[Direction | None, DirectionBasis | None]:
    """가까운 논문이 기준 논문의 선행(`prior`)인지 후행(`later`)인지와 그 근거를 정한다.

    한쪽으로만 인용하면 인용 방향을 따른다. 그 밖에는 공개일을 비교하며, 한쪽이라도 연도뿐이면 연도로 비교한다.
    같거나 알 수 없으면 `(None, None)`이다.

    @doc: docs/design/Citations.md#6-api와-화면
    """
    if relation.cited_by_paper and not relation.cites_paper:
        return "prior", "citation"
    if relation.cites_paper and not relation.cited_by_paper:
        return "later", "citation"
    if not paper_when or not work_when:
        return None, None
    if len(paper_when) < 10 or len(work_when) < 10:
        paper_when, work_when = paper_when[:4], work_when[:4]
    if work_when < paper_when:
        return "prior", "date"
    if work_when > paper_when:
        return "later", "date"
    return None, None


def fetch_citations(http: httpx2.Client, work_id: str, limit: int, now: datetime) -> FetchResult:
    """참고문헌과 공개 후 1년 안의 피인용(피인용 많은 순 최대 `limit`건)을 가져온다.

    @doc: docs/design/Citations.md#3-가져오는-범위
    """
    stamp = now.isoformat()
    base = _get(http, f"{OPENALEX_WORKS_URL}/{work_id}", {"select": "id,publication_date,referenced_works"})
    if base is None:
        raise LookupError(f"OpenAlex에 없는 작업입니다: {work_id}")
    references = [ref for ref in map(short_id, base.get("referenced_works") or []) if ref]
    published = base.get("publication_date")
    citers: list[dict[str, Any]] = []
    total = 0
    window_end = None
    if published:
        start, end = citing_window(date.fromisoformat(published))
        window_end = end.isoformat()
        per_page = min(PAGE_SIZE, limit)
        page = 1
        while len(citers) < limit:
            body = _get(
                http,
                OPENALEX_WORKS_URL,
                {
                    "filter": f"cites:{work_id},from_publication_date:{start},to_publication_date:{end}",
                    "sort": "cited_by_count:desc",
                    "per-page": per_page,
                    "page": page,
                    "select": f"{_WORK_FIELDS},referenced_works",
                },
            ) or {}
            total = (body.get("meta") or {}).get("count", 0)
            results = body.get("results") or []
            citers.extend(results)
            if len(results) < per_page:
                break
            page += 1
        citers = citers[:limit]

    reference_set = set(references)
    citations: list[tuple[str, str | None, int]] = []
    together: Counter[str] = Counter()
    for citer in citers:
        citer_id = short_id(citer.get("id"))
        if citer_id is None:
            continue
        citer_refs = {ref for ref in map(short_id, citer.get("referenced_works") or []) if ref}
        citations.append((citer_id, citer.get("publication_date"), len(reference_set & citer_refs)))
        together.update(citer_refs - {work_id})
    # 같은 횟수는 ID 순으로 두어, 실행마다 같은 결과가 나오게 한다.
    ranked = sorted(together.items(), key=lambda item: (-item[1], item[0]))
    cocitations = [(work, count) for work, count in ranked if count >= 2][:COCITATION_LIMIT]

    works = [_work_row(citer, stamp) for citer in citers if short_id(citer.get("id"))]
    works.extend(lookup_works(http, references, now))
    return FetchResult(published, window_end, total, references, citations, cocitations, works)


class CitationStore:
    """인용 데이터 캐시 파일 `citations.db`.

    @doc: docs/design/Citations.md#4-저장
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_engine(f"sqlite:///{path}")
        with self.engine.begin() as connection:
            version = connection.execute(text("PRAGMA user_version")).scalar()
            if version != CACHE_VERSION:
                _metadata.drop_all(connection)
                connection.execute(text(f"PRAGMA user_version = {CACHE_VERSION}"))
            _metadata.create_all(connection)

    def save(self, work_id: str, result: FetchResult, limit: int, now: datetime) -> None:
        """논문 하나의 인용 데이터를 옛 데이터와 바꿔 저장한다.

        @doc: docs/design/Citations.md#4-저장
        """
        with self.engine.begin() as connection:
            for table in (_references, _citations, _cocitations):
                connection.execute(delete(table).where(table.c.paper == work_id))
            connection.execute(delete(_fetches).where(_fetches.c.paper == work_id))
            connection.execute(
                insert(_fetches).values(
                    paper=work_id,
                    fetched_at=now.isoformat(),
                    publication_date=result.publication_date,
                    window_end=result.window_end,
                    citing_limit=limit,
                    citing_total=result.citing_total,
                )
            )
            if result.references:
                connection.execute(
                    insert(_references), [{"paper": work_id, "work": ref} for ref in dict.fromkeys(result.references)]
                )
            if result.citations:
                connection.execute(
                    insert(_citations),
                    [
                        {"paper": work_id, "work": work, "publication_date": published, "shared_refs": shared}
                        for work, published, shared in result.citations
                    ],
                )
            if result.cocitations:
                connection.execute(
                    insert(_cocitations),
                    [{"paper": work_id, "work": work, "count": count} for work, count in result.cocitations],
                )
            for row in {row["id"]: row for row in result.works}.values():
                connection.execute(delete(_works).where(_works.c.id == row["id"]))
                connection.execute(insert(_works).values(**row))

    def stale(self, work_ids: list[str], now: datetime) -> list[str]:
        """가져온 적이 없거나 가져온 지 7일이 지난 논문을 오래된 것부터 돌려준다.

        @doc: docs/design/Citations.md#5-갱신
        """
        with self.engine.connect() as connection:
            fetched = dict(connection.execute(select(_fetches.c.paper, _fetches.c.fetched_at)).all())
        cutoff = (now - REFRESH_AFTER).isoformat()
        due = [work for work in dict.fromkeys(work_ids) if not fetched.get(work) or fetched[work] <= cutoff]
        return sorted(due, key=lambda work: fetched.get(work) or "")

    def mark_all_stale(self) -> None:
        """모든 논문을 가져올 대상으로 표시한다.

        @doc: docs/design/Citations.md#5-갱신
        """
        with self.engine.begin() as connection:
            connection.execute(update(_fetches).values(fetched_at=None))

    def prune(self, keep: set[str]) -> None:
        """서재에 없는 논문의 인용 데이터와 쓰지 않는 `works`를 지운다.

        @doc: docs/design/Citations.md#4-저장
        """
        with self.engine.begin() as connection:
            for table in (_fetches, _references, _citations, _cocitations):
                connection.execute(delete(table).where(table.c.paper.not_in(keep)))
            used = union(
                select(_references.c.work),
                select(_citations.c.work),
                select(_cocitations.c.work),
                select(_fetches.c.paper),
            )
            connection.execute(delete(_works).where(_works.c.id.not_in(used)))

    def missed_recently(self, doi: str, now: datetime) -> bool:
        """이 DOI를 7일 안에 찾다가 못 찾았으면 참이다.

        @doc: docs/design/Citations.md#2-서재-논문과-openalex-연결
        """
        with self.engine.connect() as connection:
            tried = connection.execute(select(_link_misses.c.tried_at).where(_link_misses.c.doi == doi)).scalar()
        return tried is not None and tried > (now - MISS_RETRY_AFTER).isoformat()

    def record_miss(self, doi: str, now: datetime) -> None:
        """찾지 못한 DOI와 시각을 기억한다.

        @doc: docs/design/Citations.md#2-서재-논문과-openalex-연결
        """
        with self.engine.begin() as connection:
            connection.execute(delete(_link_misses).where(_link_misses.c.doi == doi))
            connection.execute(insert(_link_misses).values(doi=doi, tried_at=now.isoformat()))

    def publication_dates(self, work_ids: set[str]) -> dict[str, str | None]:
        """인용 데이터를 가져온 논문들의 공개일을 돌려준다.

        @doc: docs/design/Citations.md#6-api와-화면
        """
        if not work_ids:
            return {}
        with self.engine.connect() as connection:
            rows = connection.execute(
                select(_fetches.c.paper, _fetches.c.publication_date).where(_fetches.c.paper.in_(work_ids))
            ).all()
        return {row.paper: row.publication_date for row in rows}

    def fetched_count(self, work_ids: set[str]) -> int:
        """이 논문들 가운데 인용 데이터를 가져온 수를 센다.

        @doc: docs/design/Citations.md#6-api와-화면
        """
        with self.engine.connect() as connection:
            rows = connection.execute(select(_fetches.c.paper).where(_fetches.c.fetched_at.is_not(None)))
            return len({row.paper for row in rows} & work_ids)

    def miss_count(self, dois: set[str]) -> int:
        """이 DOI들 가운데 찾지 못한 것으로 기억한 수를 센다.

        @doc: docs/design/Citations.md#6-api와-화면
        """
        with self.engine.connect() as connection:
            return len({row.doi for row in connection.execute(select(_link_misses.c.doi))} & dois)

    def paper_lists(self, work_id: str) -> tuple[dict[str, Any] | None, list[dict[str, Any]], list[dict[str, Any]]]:
        """논문 하나의 가져온 정보, 참고문헌, 피인용(피인용 많은 순)을 서지 정보와 함께 돌려준다.

        @doc: docs/design/Citations.md#6-api와-화면
        """
        with self.engine.connect() as connection:
            fetch = connection.execute(select(_fetches).where(_fetches.c.paper == work_id)).first()
            references = connection.execute(
                select(_references.c.work, _works)
                .select_from(_references.outerjoin(_works, _works.c.id == _references.c.work))
                .where(_references.c.paper == work_id)
            ).all()
            citations = connection.execute(
                select(_citations.c.work, _citations.c.shared_refs, _works)
                .select_from(_citations.outerjoin(_works, _works.c.id == _citations.c.work))
                .where(_citations.c.paper == work_id)
            ).all()
        refs = [dict(row._mapping) for row in references]
        cites = [dict(row._mapping) for row in citations]
        refs.sort(key=lambda row: (-(row["cited_by_count"] or 0), row["work"]))
        cites.sort(key=lambda row: (-(row["cited_by_count"] or 0), row["work"]))
        return (dict(fetch._mapping) if fetch else None), refs, cites

    def relation_rows(self, work_id: str) -> dict[str, Any]:
        """가까운 논문 계산에 쓸 참고문헌, 피인용(공유 참고문헌 수), 공동 인용 수를 돌려준다.

        @doc: docs/design/Citations.md#6-api와-화면
        """
        with self.engine.connect() as connection:
            references = {row.work for row in connection.execute(select(_references.c.work).where(_references.c.paper == work_id))}
            citations = dict(
                connection.execute(select(_citations.c.work, _citations.c.shared_refs).where(_citations.c.paper == work_id)).all()
            )
            cocitations = dict(
                connection.execute(select(_cocitations.c.work, _cocitations.c.count).where(_cocitations.c.paper == work_id)).all()
            )
        return {"references": references, "citations": citations, "cocitations": cocitations}

    def works_by_id(self, work_ids: set[str]) -> dict[str, dict[str, Any]]:
        """`works`에 있는 서지 정보를 ID로 돌려준다.

        @doc: docs/design/Citations.md#6-api와-화면
        """
        if not work_ids:
            return {}
        with self.engine.connect() as connection:
            rows = connection.execute(select(_works).where(_works.c.id.in_(work_ids))).all()
        return {row.id: dict(row._mapping) for row in rows}

    def save_works(self, rows: list[dict[str, Any]]) -> None:
        """서지 정보를 저장한다. 같은 ID는 바꾼다.

        @doc: docs/design/Citations.md#4-저장
        @doc: docs/design/ReaderCitations.md#4-논문-찾기
        """
        with self.engine.begin() as connection:
            for row in {row["id"]: row for row in rows}.values():
                connection.execute(delete(_works).where(_works.c.id == row["id"]))
                connection.execute(insert(_works).values(**row))

    def rows(self, table: str) -> list[dict[str, Any]]:
        """표 하나의 모든 행. 테스트와 진단에 쓴다.

        @doc: docs/design/Citations.md#7-테스트
        """
        with self.engine.connect() as connection:
            return [dict(row._mapping) for row in connection.execute(select(_metadata.tables[table]))]

    def snapshot(self) -> bytes:
        """쓰는 중이 아닌 일관된 사본의 내용을 돌려준다.

        @doc: docs/design/Citations.md#4-저장
        """
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / CACHE_FILE
            with self.engine.connect() as connection:
                connection.exec_driver_sql("VACUUM INTO ?", (str(copy),))
            return copy.read_bytes()


class CitationStatus(BaseModel):
    """인용 데이터 상태.

    @doc: docs/design/Citations.md#6-api와-화면
    """

    papers: int
    linked: int
    not_found: int
    fetched: int
    s2_checked: int = 0
    running: bool
    last_run: datetime | None
    error: str


class DriveLike(Protocol):
    """`CitationSync`가 쓰는 드라이브 동기화의 모양. 테스트는 같은 모양의 가짜를 넘긴다.

    @doc: docs/design/Citations.md#4-저장
    """

    def is_connected(self) -> bool: ...
    def put_cache(self, name: str, data: bytes) -> bool: ...
    def get_cache(self, name: str) -> bytes | None: ...
    def schedule_push(self) -> None: ...


class CitationSync:
    """인용 데이터의 백그라운드 갱신.

    @doc: docs/design/Citations.md#5-갱신
    """

    def __init__(
        self,
        library_engine: Engine,
        cache_path: Path,
        http: httpx2.Client,
        drive: DriveLike,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.library_engine = library_engine
        self.cache_path = cache_path
        self.http = http
        self.drive = drive
        self.clock = clock
        self._store: CitationStore | None = None
        self._s2_store: S2Store | None = None
        self._store_lock = threading.Lock()
        self._run_lock = threading.Lock()
        self._wake = threading.Event()
        self._stopped = False
        self._thread: threading.Thread | None = None
        self.running = False
        self.last_run: datetime | None = None
        self.error = ""

    @property
    def s2_store(self) -> S2Store:
        """인용 캐시 파일 안의 Semantic Scholar 참고문헌 표.

        @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
        """
        if self._s2_store is None or self._s2_store.engine is not self.store.engine:
            self._s2_store = S2Store(self.store.engine)
        return self._s2_store

    @property
    def store(self) -> CitationStore:
        """캐시 파일. 처음 쓸 때 연다.

        @doc: docs/design/Citations.md#4-저장
        """
        with self._store_lock:
            if self._store is None:
                self._store = CitationStore(self.cache_path)
            return self._store

    def restore_from_drive(self) -> bool:
        """로컬에 캐시 파일이 없고 드라이브에 있으면 받는다.

        @doc: docs/design/Citations.md#4-저장
        """
        with self._store_lock:
            if self._store is not None or self.cache_path.exists() or not self.drive.is_connected():
                return False
            data = self.drive.get_cache(CACHE_FILE)
            if data is None:
                return False
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_bytes(data)
            return True

    def run_once(self) -> int:
        """갱신을 한 번 하고 가져온 논문 수를 돌려준다.

        @doc: docs/design/Citations.md#5-갱신
        """
        with self._run_lock:
            self.running = True
            self.error = ""
            try:
                return self._run()
            finally:
                self.running = False
                self.last_run = self.clock()

    def _run(self) -> int:
        now = self.clock()
        store = self.store
        with Session(self.library_engine) as session:
            papers = list(session.scalars(select(Paper)))
            store.prune({paper.openalex_id for paper in papers if paper.openalex_id})
            linked = False
            try:
                for paper in papers:
                    if paper.openalex_id or not paper.doi or store.missed_recently(paper.doi, now):
                        continue
                    work_id = link_paper(self.http, paper.doi)
                    if work_id is None:
                        store.record_miss(paper.doi, now)
                    else:
                        paper.openalex_id = work_id
                        linked = True
            except OpenAlexBudgetError as error:
                self.error = str(error)
            except (httpx2.HTTPError, ValueError) as error:
                self.error = f"OpenAlex 연결 실패: {error}"
            finally:
                if linked:
                    session.commit()
                    self.drive.schedule_push()
            if self.error:
                return 0
            limit = read_settings(session)["citing_limit"]
            work_ids = [paper.openalex_id for paper in papers if paper.openalex_id]
            s2_papers = [(paper.doi, paper.title) for paper in papers if paper.doi]
        fetched = 0
        for work_id in store.stale(work_ids, now):
            if self._stopped:
                break
            try:
                result = fetch_citations(self.http, work_id, limit, now)
            except OpenAlexBudgetError as error:
                self.error = str(error)
                break
            except (httpx2.HTTPError, ValueError, KeyError, LookupError) as error:
                self.error = f"{work_id} 인용 데이터를 받지 못했습니다: {error}"
                continue
            store.save(work_id, result, limit, now)
            fetched += 1
        # OpenAlex 참고문헌에 빠진 것이 많아 Semantic Scholar 참고문헌도 받아 둔다.
        checked, s2_error = refresh_references(self.http, self.s2_store, s2_papers, now, stopped=lambda: self._stopped)
        if s2_error and not self.error:
            self.error = s2_error
        if fetched or checked:
            self.drive.put_cache(CACHE_FILE, store.snapshot())
        return fetched

    def _loop(self) -> None:
        self.restore_from_drive()
        while not self._stopped:
            try:
                self.run_once()
            except Exception as error:  # noqa: BLE001 - 스레드가 죽지 않게 모든 오류를 상태에 남긴다.
                self.error = f"인용 데이터 갱신 실패: {error}"
            self._wake.wait(RUN_INTERVAL_SECONDS)
            self._wake.clear()

    def start(self) -> None:
        """백그라운드 갱신 스레드를 띄운다.

        @doc: docs/design/Citations.md#5-갱신
        """
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """갱신 스레드를 멈춘다.

        @doc: docs/design/Citations.md#5-갱신
        """
        self._stopped = True
        self._wake.set()

    def wake(self) -> None:
        """기다리는 갱신을 바로 깨운다.

        @doc: docs/design/Citations.md#5-갱신
        """
        self._wake.set()

    def refresh(self) -> None:
        """모든 논문을 가져올 대상으로 표시하고 깨운다.

        @doc: docs/design/Citations.md#5-갱신
        """
        self.store.mark_all_stale()
        self.wake()

    def status(self) -> CitationStatus:
        """지금 상태를 돌려준다.

        @doc: docs/design/Citations.md#6-api와-화면
        """
        with Session(self.library_engine) as session:
            papers = list(session.scalars(select(Paper)))
        work_ids = {paper.openalex_id for paper in papers if paper.openalex_id}
        unlinked_dois = {paper.doi for paper in papers if not paper.openalex_id and paper.doi}
        store = self.store
        return CitationStatus(
            papers=len(papers),
            linked=sum(1 for paper in papers if paper.openalex_id),
            not_found=store.miss_count(unlinked_dois),
            fetched=store.fetched_count(work_ids),
            s2_checked=self.s2_store.checked_count({paper.doi for paper in papers if paper.doi}),
            running=self.running,
            last_run=self.last_run,
            error=self.error,
        )


# @doc: docs/design/Citations.md#6-api와-화면
router = APIRouter(prefix="/api/citations")


@router.get("/status")
def citation_status(request: Request) -> CitationStatus:
    """`GET /api/citations/status`를 처리한다.

    @doc: docs/design/Citations.md#6-api와-화면
    """
    return request.app.state.citations.status()


@router.post("/refresh")
def refresh_citations(request: Request) -> CitationStatus:
    """`POST /api/citations/refresh`를 처리한다.

    @doc: docs/design/Citations.md#6-api와-화면
    """
    request.app.state.citations.refresh()
    return request.app.state.citations.status()


class CitedWork(BaseModel):
    """인용 목록에 보일 논문 하나. 서재에 있으면 그 논문 ID를 가진다.

    @doc: docs/design/Citations.md#6-api와-화면
    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """

    openalex_id: str
    title: str | None
    authors: list[str]
    item_type: str
    year: int | None
    venue: str | None
    doi: str | None
    cited_by_count: int | None
    shared_refs: int | None = None
    library_paper_id: int | None = None


class PaperCitations(BaseModel):
    """논문 하나의 인용 목록.

    @doc: docs/design/Citations.md#6-api와-화면
    """

    state: Literal["no_doi", "not_found", "pending", "ready"]
    openalex_id: str | None
    fetched_at: datetime | None = None
    window_start: str | None = None
    window_end: str | None = None
    citing_total: int = 0
    citing_limit: int | None = None
    references: list[CitedWork] = []
    citations: list[CitedWork] = []


def _cited_work(row: dict[str, Any], owners: dict[str, int]) -> CitedWork:
    doi = None
    if row.get("doi"):
        try:
            doi = normalize_doi(row["doi"])
        except ValueError:
            doi = None
    return CitedWork(
        openalex_id=row["work"],
        title=row.get("title") or None,
        authors=json.loads(row["authors"]) if row.get("authors") else [],
        item_type=row.get("item_type") or "other",
        year=row.get("year"),
        venue=row.get("venue"),
        doi=doi,
        cited_by_count=row.get("cited_by_count"),
        shared_refs=row.get("shared_refs"),
        library_paper_id=owners.get(row["work"]) or (owners.get(doi) if doi else None),
    )


# @doc: docs/design/Citations.md#6-api와-화면
paper_router = APIRouter(prefix="/api/papers")


@paper_router.get("/{paper_id}/citations")
def paper_citations(paper_id: int, request: Request) -> PaperCitations:
    """`GET /api/papers/{paper_id}/citations`를 처리한다.

    @doc: docs/design/Citations.md#6-api와-화면
    """
    sync: CitationSync = request.app.state.citations
    with Session(sync.library_engine) as session:
        paper = session.get(Paper, paper_id)
        if paper is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"논문이 없습니다: {paper_id}")
        owners: dict[str, int] = {}
        for other in session.scalars(select(Paper)):
            if other.openalex_id:
                owners[other.openalex_id] = other.id
            if other.doi:
                owners[other.doi] = other.id
        work_id, doi = paper.openalex_id, paper.doi
    if work_id is None:
        if not doi:
            return PaperCitations(state="no_doi", openalex_id=None)
        state = "not_found" if sync.store.missed_recently(doi, sync.clock()) else "pending"
        return PaperCitations(state=state, openalex_id=None)
    fetch, references, citations = sync.store.paper_lists(work_id)
    if fetch is None:
        return PaperCitations(state="pending", openalex_id=work_id)
    return PaperCitations(
        state="ready",
        openalex_id=work_id,
        fetched_at=datetime.fromisoformat(fetch["fetched_at"]) if fetch["fetched_at"] else None,
        window_start=fetch["publication_date"],
        window_end=fetch["window_end"],
        citing_total=fetch["citing_total"] or 0,
        citing_limit=fetch["citing_limit"],
        references=[_cited_work(row, owners) for row in references],
        citations=[_cited_work(row, owners) for row in citations],
    )


class RelatedWork(CitedWork):
    """가까운 논문 하나. 점수와 까닭을 함께 가진다.

    @doc: docs/design/Citations.md#6-api와-화면
    """

    score: float
    cites_paper: bool
    cited_by_paper: bool
    cocited: int
    direction: Direction | None = None
    direction_basis: DirectionBasis | None = None


class PaperRelated(BaseModel):
    """논문 하나의 가까운 논문 목록.

    @doc: docs/design/Citations.md#6-api와-화면
    """

    state: Literal["no_doi", "not_found", "pending", "ready"]
    citing_count: int = 0
    reference_count: int = 0
    works: list[RelatedWork] = []


@paper_router.get("/{paper_id}/related")
def paper_related(paper_id: int, request: Request) -> PaperRelated:
    """`GET /api/papers/{paper_id}/related`를 처리한다. 서지 정보가 없는 논문은 OpenAlex에서 받아 둔다.

    @doc: docs/design/Citations.md#6-api와-화면
    """
    listed = paper_citations(paper_id, request)
    if listed.state != "ready" or listed.openalex_id is None:
        return PaperRelated(state=listed.state)
    sync: CitationSync = request.app.state.citations
    rows = sync.store.relation_rows(listed.openalex_id)
    relations = related_works(listed.openalex_id, rows, len(rows["citations"]))[:RELATED_LIMIT]
    wanted = {relation.work for relation in relations}
    known = sync.store.works_by_id(wanted)
    missing = sorted(wanted - set(known))
    if missing:
        try:
            sync.store.save_works(lookup_works(sync.http, missing, sync.clock()))
            known = sync.store.works_by_id(wanted)
        except (OpenAlexBudgetError, httpx2.HTTPError, ValueError):
            pass
    owners = {
        item.openalex_id: item.library_paper_id
        for item in listed.references + listed.citations
        if item.library_paper_id
    }
    with Session(sync.library_engine) as session:
        for other in session.scalars(select(Paper)):
            if other.openalex_id:
                owners[other.openalex_id] = other.id
            if other.doi:
                owners[other.doi] = other.id
        paper = session.get(Paper, paper_id)
        paper_when = when(listed.window_start, paper.year if paper else None)
    works = []
    for relation in relations:
        row = known.get(relation.work, {})
        base = _cited_work({"work": relation.work, **row}, owners)
        direction, basis = work_direction(relation, paper_when, when(row.get("publication_date"), row.get("year")))
        works.append(
            RelatedWork(
                **base.model_dump(exclude={"shared_refs"}),
                shared_refs=relation.shared_refs,
                score=relation.score,
                cites_paper=relation.cites_paper,
                cited_by_paper=relation.cited_by_paper,
                cocited=relation.cocited,
                direction=direction,
                direction_basis=basis,
            )
        )
    return PaperRelated(
        state="ready", citing_count=len(rows["citations"]), reference_count=len(rows["references"]), works=works
    )



# @doc: docs/design/Citations.md#6-api와-화면
RECOMMEND_LIMIT = 50


@dataclass
class Recommendation:
    """서재 밖 추천 하나. 서재 논문마다의 가까운 점수를 더한 값과 이어진 서재 논문들이다.

    @doc: docs/design/Citations.md#6-api와-화면
    """

    work: str
    score: float = 0.0
    sources: list[str] = field(default_factory=list)
    relations: list[Relation] = field(default_factory=list)


def recommend_works(
    rows_by_paper: dict[str, dict[str, Any]], exclude: set[str], limit: int = RECOMMEND_LIMIT
) -> list[Recommendation]:
    """서재 논문들과 인용으로 가까운 서재 밖 논문을 점수 순으로 돌려준다.

    서재 논문 A마다 `related_works`의 점수를 구해 같은 논문끼리 더한다. 여러 서재 논문과 이어질수록 위로 온다.

    @doc: docs/design/Citations.md#6-api와-화면
    @doc: docs/design/CitationGraph.md#2-그래프-데이터
    """
    found: dict[str, Recommendation] = {}
    for paper, rows in rows_by_paper.items():
        for relation in related_works(paper, rows, len(rows["citations"])):
            if relation.work in exclude:
                continue
            item = found.setdefault(relation.work, Recommendation(relation.work))
            item.score += relation.score
            item.sources.append(paper)
            item.relations.append(relation)
    ranked = sorted(found.values(), key=lambda item: (-item.score, -len(item.sources), item.work))
    for item in ranked:
        item.score = round(item.score, 4)
    return ranked[:limit]


def overall_direction(directions: list[Direction | None]) -> Literal["prior", "later", "mixed"] | None:
    """이어진 서재 논문마다의 방향을 하나로 모은다. 서로 다르면 `mixed`, 하나도 없으면 `None`이다.

    @doc: docs/design/Citations.md#6-api와-화면
    """
    found = {direction for direction in directions if direction}
    if len(found) > 1:
        return "mixed"
    return found.pop() if found else None


class RecommendationSource(BaseModel):
    """추천과 이어진 서재 논문.

    @doc: docs/design/Citations.md#6-api와-화면
    """

    paper_id: int
    title: str
    direction: Direction | None = None
    direction_basis: DirectionBasis | None = None


class RecommendedWork(CitedWork):
    """서재 밖 추천 논문 하나.

    @doc: docs/design/Citations.md#6-api와-화면
    """

    score: float
    sources: list[RecommendationSource]
    direction: Literal["prior", "later", "mixed"] | None = None


class Recommendations(BaseModel):
    """서재 밖 추천 목록.

    @doc: docs/design/Citations.md#6-api와-화면
    """

    papers: int
    papers_used: int
    works: list[RecommendedWork]


@router.get("/recommendations")
def recommendations(request: Request) -> Recommendations:
    """`GET /api/citations/recommendations`를 처리한다.

    @doc: docs/design/Citations.md#6-api와-화면
    """
    sync: CitationSync = request.app.state.citations
    with Session(sync.library_engine) as session:
        papers = list(session.scalars(select(Paper)))
    by_work = {paper.openalex_id: paper for paper in papers if paper.openalex_id}
    library_dois = {paper.doi for paper in papers if paper.doi}
    store = sync.store
    rows_by_paper = {}
    for work_id in by_work:
        rows = store.relation_rows(work_id)
        if rows["references"] or rows["citations"]:
            rows_by_paper[work_id] = rows
    ranked = recommend_works(rows_by_paper, set(by_work))
    wanted = {item.work for item in ranked}
    known = store.works_by_id(wanted)
    missing = sorted(wanted - set(known))
    if missing:
        try:
            store.save_works(lookup_works(sync.http, missing, sync.clock()))
            known = store.works_by_id(wanted)
        except (OpenAlexBudgetError, httpx2.HTTPError, ValueError):
            pass
    dates = store.publication_dates(set(rows_by_paper))
    paper_whens = {work_id: when(dates.get(work_id), by_work[work_id].year) for work_id in rows_by_paper}
    works = []
    for item in ranked:
        row = known.get(item.work, {})
        base = _cited_work({"work": item.work, **row}, {})
        if base.doi and base.doi in library_dois:
            continue
        work_when = when(row.get("publication_date"), row.get("year"))
        sources = []
        for source, relation in zip(item.sources, item.relations, strict=True):
            direction, basis = work_direction(relation, paper_whens[source], work_when)
            paper = by_work[source]
            sources.append(
                RecommendationSource(paper_id=paper.id, title=paper.title, direction=direction, direction_basis=basis)
            )
        works.append(
            RecommendedWork(
                **base.model_dump(),
                score=item.score,
                sources=sources,
                direction=overall_direction([source.direction for source in sources]),
            )
        )
    return Recommendations(papers=len(papers), papers_used=len(rows_by_paper), works=works)
