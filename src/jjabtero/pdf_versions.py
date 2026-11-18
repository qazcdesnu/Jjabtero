"""논문 PDF의 판: 받을 수 있는 판 찾기(arXiv 개정판, OpenAlex 위치), 받아 둔 판 목록과 고르기.

@doc: docs/design/PdfVersions.md#2-판을-찾는-곳
@doc: docs/design/PdfVersions.md#5-api
"""

import os
import re
import xml.etree.ElementTree as ElementTree
from collections.abc import Iterator
from datetime import UTC, datetime
from email.utils import parsedate_to_datetime
from typing import Annotated
from urllib.parse import urlparse

import httpx2
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from jjabtero.citations import OPENALEX_WORKS_URL
from jjabtero.models import Paper, PaperPdf

# @doc: docs/design/PdfVersions.md#2-판을-찾는-곳
ARXIV_OAI_URL = "https://export.arxiv.org/oai2"
_ARXIV_RAW = "{http://arxiv.org/OAI/arXivRaw/}"
_ARXIV_DOI = re.compile(r"^10\.48550/arxiv\.(.+)$", re.IGNORECASE)
_ARXIV_URL = re.compile(
    r"^https?://(?:www\.|export\.)?arxiv\.org/(?:abs|pdf)/([a-z\-.]+/\d{7}|\d{4}\.\d{4,5})(v\d+)?(?:\.pdf)?/?$", re.IGNORECASE
)
_KINDS = {"publishedVersion": "출판판", "acceptedVersion": "수락판", "submittedVersion": "제출판"}


class PdfVersionOut(BaseModel):
    """받을 수 있는 판 하나.

    `key`는 받기에 쓰는 이름(`arxiv:v3`, `url:<주소>`), `date`는 arXiv 판의 날짜(`YYYY-MM-DD`), `latest`는 가장 늦은
    arXiv 판인지, `saved_sha256`은 이미 받아 둔 판이면 그 판의 SHA-256이다.

    @doc: docs/design/PdfVersions.md#5-api
    """

    key: str
    label: str
    url: str
    date: str | None = None
    latest: bool = False
    saved_sha256: str | None = None


class SavedVersionOut(BaseModel):
    """받아 둔 판 하나.

    @doc: docs/design/PdfVersions.md#5-api
    """

    sha256: str
    label: str
    source: str
    source_url: str | None
    added_at: datetime
    selected: bool


def arxiv_id(url: str | None) -> tuple[str, str | None] | None:
    """arXiv 주소에서 (번호, 판)을 읽는다. 판이 없는 주소이면 판은 `None`이다. arXiv 주소가 아니면 `None`이다.

    @doc: docs/design/PdfVersions.md#2-판을-찾는-곳
    """
    match = _ARXIV_URL.match(url or "")
    if match is None:
        return None
    return match.group(1), match.group(2)


def parse_arxiv_versions(xml: str) -> list[tuple[str, str | None]]:
    """arXiv OAI-PMH `arXivRaw` 응답에서 (판, 날짜 `YYYY-MM-DD`)를 판 순서대로 읽는다. 기록이 없으면 빈 목록이다.

    @doc: docs/design/PdfVersions.md#2-판을-찾는-곳
    """
    try:
        root = ElementTree.fromstring(xml)
    except ElementTree.ParseError:
        return []
    found: list[tuple[str, str | None]] = []
    for element in root.iter(f"{_ARXIV_RAW}version"):
        name = element.get("version")
        if not name or not re.fullmatch(r"v\d+", name):
            continue
        text = element.findtext(f"{_ARXIV_RAW}date")
        try:
            date = parsedate_to_datetime(text).date().isoformat() if text else None
        except (TypeError, ValueError):
            date = None
        found.append((name, date))
    return sorted(found, key=lambda item: int(item[0][1:]))


def arxiv_versions(http: httpx2.Client, number: str) -> list[tuple[str, str | None]]:
    """arXiv 논문의 (판, 날짜) 목록을 arXiv의 공식 메타데이터 API(OAI-PMH)로 찾는다.

    @doc: docs/design/PdfVersions.md#2-판을-찾는-곳
    """
    params = {"verb": "GetRecord", "identifier": f"oai:arXiv.org:{number}", "metadataPrefix": "arXivRaw"}
    response = http.get(ARXIV_OAI_URL, params=params, follow_redirects=True, timeout=30)
    response.raise_for_status()
    return parse_arxiv_versions(response.text)


def _openalex_locations(http: httpx2.Client, openalex_id: str | None) -> list[dict]:
    if not openalex_id:
        return []
    params = {"select": "locations"}
    api_key = os.environ.get("OPENALEX_API_KEY")
    if api_key:
        params["api_key"] = api_key
    response = http.get(f"{OPENALEX_WORKS_URL}/{openalex_id}", params=params)
    if response.status_code == 404:
        return []
    response.raise_for_status()
    return [location for location in response.json().get("locations") or [] if isinstance(location, dict)]


def _paper_arxiv_number(paper: Paper, locations: list[dict]) -> str | None:
    match = _ARXIV_DOI.match(paper.doi or "")
    if match:
        return match.group(1)
    for location in locations:
        for url in (location.get("landing_page_url"), location.get("pdf_url")):
            found = arxiv_id(url)
            if found:
                return found[0]
    return None


def location_versions(locations: list[dict]) -> list[PdfVersionOut]:
    """OpenAlex 위치 가운데 공개 PDF 주소가 있고 arXiv가 아닌 것을 판으로 고른다. 같은 주소는 한 번만 쓴다.

    @doc: docs/design/PdfVersions.md#2-판을-찾는-곳
    """
    found: list[PdfVersionOut] = []
    seen: set[str] = set()
    for location in locations:
        url = location.get("pdf_url")
        if not isinstance(url, str) or not url.startswith(("http://", "https://")) or url in seen:
            continue
        if arxiv_id(url) or arxiv_id(location.get("landing_page_url")):
            continue
        seen.add(url)
        source = (location.get("source") or {}).get("display_name") or urlparse(url).hostname or url
        kind = _KINDS.get(location.get("version") or "")
        found.append(PdfVersionOut(key=f"url:{url}", label=f"{source} · {kind}" if kind else source, url=url))
    return found


def available_versions(http: httpx2.Client, paper: Paper) -> list[PdfVersionOut]:
    """논문을 받을 수 있는 판 목록. OpenAlex 위치(출판판 등) 다음에 arXiv 판을 최신부터 둔다.

    받아 둔 판과 주소가 같으면 `saved_sha256`을 채운다. 네트워크 오류는 `httpx2.HTTPError`로 낸다.

    @doc: docs/design/PdfVersions.md#2-판을-찾는-곳
    """
    locations = _openalex_locations(http, paper.openalex_id)
    found = location_versions(locations)
    number = _paper_arxiv_number(paper, locations)
    if number:
        versions = arxiv_versions(http, number)
        for index, (name, date) in reversed(list(enumerate(versions))):
            found.append(
                PdfVersionOut(
                    key=f"arxiv:{name}",
                    label=f"arXiv {name}",
                    url=f"https://arxiv.org/pdf/{number}{name}",
                    date=date,
                    latest=index == len(versions) - 1,
                )
            )
    saved = {pdf.source_url: pdf.sha256 for pdf in paper.pdfs if pdf.source_url}
    for version in found:
        version.saved_sha256 = saved.get(version.url)
    return found


def saved_label(pdf: PaperPdf) -> str:
    """받아 둔 판의 이름. 출처 주소와 출처로 정한다.

    @doc: docs/design/PdfVersions.md#2-판을-찾는-곳
    """
    found = arxiv_id(pdf.source_url)
    if found:
        return f"arXiv {found[1]}" if found[1] else "arXiv"
    if pdf.source == "upload":
        return "올린 PDF"
    if pdf.source == "alternate":
        return "비슷한 공개판"
    return urlparse(pdf.source_url or "").hostname or pdf.source


def saved_out(paper: Paper) -> list[SavedVersionOut]:
    """받아 둔 판 목록. 지금 판이 먼저다.

    @doc: docs/design/PdfVersions.md#5-api
    """
    current = paper.pdf
    return [
        SavedVersionOut(
            sha256=pdf.sha256,
            label=saved_label(pdf),
            source=pdf.source,
            source_url=pdf.source_url,
            added_at=pdf.added_at,
            selected=pdf is current,
        )
        for pdf in paper.pdfs
    ]


# @doc: docs/design/PdfVersions.md#5-api
router = APIRouter(prefix="/api/papers")


def _session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


def _paper(session: Session, paper_id: int) -> Paper:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"논문이 없습니다: {paper_id}")
    return paper


@router.get("/{paper_id}/pdf/versions")
def saved_versions(paper_id: int, session: Annotated[Session, Depends(_session)]) -> list[SavedVersionOut]:
    """`GET /api/papers/{paper_id}/pdf/versions`를 처리한다. 바깥 요청을 하지 않는다.

    @doc: docs/design/PdfVersions.md#5-api
    """
    return saved_out(_paper(session, paper_id))


@router.get("/{paper_id}/pdf/versions/available")
def remote_versions(
    paper_id: int, request: Request, session: Annotated[Session, Depends(_session)]
) -> list[PdfVersionOut]:
    """`GET /api/papers/{paper_id}/pdf/versions/available`를 처리한다. 찾기에 실패하면 502다.

    @doc: docs/design/PdfVersions.md#5-api
    """
    paper = _paper(session, paper_id)
    try:
        return available_versions(request.app.state.http_client, paper)
    except (httpx2.HTTPError, ValueError) as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"받을 수 있는 판을 찾지 못했습니다: {error}") from error


class SelectIn(BaseModel):
    """고를 판.

    @doc: docs/design/PdfVersions.md#5-api
    """

    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


@router.put("/{paper_id}/pdf/selected")
def select_version(
    paper_id: int, data: SelectIn, request: Request, session: Annotated[Session, Depends(_session)]
) -> list[SavedVersionOut]:
    """`PUT /api/papers/{paper_id}/pdf/selected`를 처리한다. 받아 둔 판을 지금 판으로 고른다.

    @doc: docs/design/PdfVersions.md#5-api
    """
    paper = _paper(session, paper_id)
    pdf = paper.pdf_version(data.sha256)
    if pdf is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "받아 두지 않은 판입니다.")
    pdf.selected_at = datetime.now(UTC)
    session.commit()
    session.expire(paper, ["pdfs"])
    request.app.state.drive.schedule_push()
    return saved_out(paper)
