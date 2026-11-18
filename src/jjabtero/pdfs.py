"""논문 PDF의 가져오기, 보관, 내려주기.

@doc: docs/design/Reader.md#2-pdf-가져오기
@doc: docs/design/Reader.md#3-보관
"""

import difflib
import hashlib
import os
import re
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path
from typing import Annotated, Protocol

import httpx2
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from jjabtero.citations import OPENALEX_WORKS_URL
from jjabtero.models import Paper, PaperPdf
from jjabtero.pdf_versions import available_versions
from jjabtero.titles import normalize

# @doc: docs/design/Reader.md#2-pdf-가져오기
MAX_PDF_BYTES = 100 * 1024 * 1024
PDF_FOLDER = "pdfs"
_PDF_MAGIC = b"%PDF-"
_ARXIV_DOI = re.compile(r"^10\.48550/arxiv\.(.+)$", re.IGNORECASE)
_ARXIV_ABS = re.compile(r"^https?://(?:www\.)?arxiv\.org/abs/(.+?)/?$", re.IGNORECASE)


class NotPdfError(ValueError):
    """받거나 올린 내용이 PDF가 아니다.

    @doc: docs/design/Reader.md#2-pdf-가져오기
    """


class PdfTooLargeError(ValueError):
    """PDF가 크기 제한(100MB)을 넘는다.

    @doc: docs/design/Reader.md#2-pdf-가져오기
    """


class DriveFilesLike(Protocol):
    """PDF 보관이 쓰는 드라이브 동기화의 모양.

    @doc: docs/design/Reader.md#3-보관
    """

    def put_file(self, subfolder: str, name: str, data: bytes) -> str | None: ...
    def download_file(self, file_id: str) -> bytes | None: ...
    def schedule_push(self) -> None: ...


def check_pdf(data: bytes) -> None:
    """PDF 내용인지와 크기를 확인한다.

    @doc: docs/design/Reader.md#2-pdf-가져오기
    """
    if len(data) > MAX_PDF_BYTES:
        raise PdfTooLargeError("PDF가 100MB를 넘습니다.")
    if not data.startswith(_PDF_MAGIC):
        raise NotPdfError("PDF 파일이 아닙니다.")


def _oa_pdf_url(work: dict) -> str | None:
    # 공개 PDF 주소. arXiv 소개 페이지는 PDF 주소로 바꾼다.
    url = (work.get("best_oa_location") or {}).get("pdf_url") or (work.get("open_access") or {}).get("oa_url")
    if not url:
        return None
    abstract = _ARXIV_ABS.match(url)
    return f"https://arxiv.org/pdf/{abstract.group(1)}" if abstract else url


def open_access_pdf_url(http: httpx2.Client, openalex_id: str | None, doi: str | None) -> tuple[str, str] | None:
    """OpenAlex ID와 DOI로 공개 PDF 주소와 출처(`openalex`, `arxiv`)를 찾는다. 없으면 `None`이다.

    @doc: docs/design/Reader.md#2-pdf-가져오기
    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """
    match = _ARXIV_DOI.match(doi or "")
    if match:
        # arXiv 논문은 arXiv PDF가 가장 확실하다. OpenAlex는 다른 저장소의 사본 주소를 주기도 한다.
        return f"https://arxiv.org/pdf/{match.group(1)}", "arxiv"
    if openalex_id:
        params = {"select": "best_oa_location,open_access"}
        api_key = os.environ.get("OPENALEX_API_KEY")
        if api_key:
            params["api_key"] = api_key
        response = http.get(f"{OPENALEX_WORKS_URL}/{openalex_id}", params=params)
        if response.status_code == 200:
            # OpenAlex가 arXiv 소개 페이지를 주는 경우가 있어 PDF 주소로 바꾼다.
            url = _oa_pdf_url(response.json())
            if url:
                return url, "openalex"
    return None


def open_pdf_url(http: httpx2.Client, paper: Paper) -> tuple[str, str] | None:
    """논문의 공개 PDF 주소와 출처(`openalex`, `arxiv`)를 찾는다. 없으면 `None`이다.

    @doc: docs/design/Reader.md#2-pdf-가져오기
    """
    return open_access_pdf_url(http, paper.openalex_id, paper.doi)


# @doc: docs/design/Reader.md#2-pdf-가져오기
ALTERNATIVE_MIN_SIMILARITY = 0.85
ALTERNATIVE_MIN_OVERLAP = 0.5
ALTERNATIVE_YEARS = 5
ALTERNATIVE_LIMIT = 3


class OpenVersion(BaseModel):
    """서재 논문과 비슷한 공개판 하나.

    @doc: docs/design/Reader.md#2-pdf-가져오기
    """

    openalex_id: str
    title: str
    authors: list[str]
    year: int | None
    venue: str | None
    pdf_url: str
    similarity: float


def _stems(title: str) -> set[str]:
    return {word[:5] for word in normalize(title).split() if len(word) > 2}


def title_similarity(a: str, b: str) -> float:
    """두 제목이 같은 논문의 다른 판으로 볼 만큼 비슷한 정도(0~1). 기준에 못 미치면 0이다.

    본제목(쌍점 앞) 글자 비슷함이 0.85 이상이고 두 낱말 이상이거나, 전체 제목 낱말(앞 5글자) 겹침이 0.5 이상이어야 한다.

    @doc: docs/design/Reader.md#2-pdf-가져오기
    """
    main_a, main_b = normalize(a.split(":")[0]), normalize(b.split(":")[0])
    ratio = difflib.SequenceMatcher(None, main_a, main_b).ratio()
    stems_a, stems_b = _stems(a), _stems(b)
    overlap = len(stems_a & stems_b) / len(stems_a | stems_b) if stems_a and stems_b else 0.0
    main_ok = ratio >= ALTERNATIVE_MIN_SIMILARITY and min(len(main_a.split()), len(main_b.split())) >= 2
    if not main_ok and overlap < ALTERNATIVE_MIN_OVERLAP:
        return 0.0
    return round(max(ratio if main_ok else 0.0, overlap), 3)


def _surname(name: str) -> str:
    words = normalize(name).split()
    return words[-1] if words else ""


def open_alternatives(http: httpx2.Client, paper: Paper) -> list[OpenVersion]:
    """같은 첫 저자의 공개 논문 가운데 제목이 비슷한 것을 비슷함 순으로 3건까지 찾는다.

    @doc: docs/design/Reader.md#2-pdf-가져오기
    """
    authors = paper.author_names
    surname = _surname(authors[0]) if authors else ""
    if not surname:
        return []
    params = {
        "search": paper.title,
        "filter": f"is_oa:true,raw_author_name.search:{surname}",
        "per-page": 10,
        "select": "id,doi,display_name,publication_year,authorships,primary_location,best_oa_location,open_access",
    }
    api_key = os.environ.get("OPENALEX_API_KEY")
    if api_key:
        params["api_key"] = api_key
    response = http.get(OPENALEX_WORKS_URL, params=params)
    response.raise_for_status()
    own_doi = (paper.doi or "").lower()
    found: list[OpenVersion] = []
    for work in response.json().get("results") or []:
        work_id = (work.get("id") or "").removeprefix("https://openalex.org/")
        doi = (work.get("doi") or "").removeprefix("https://doi.org/").lower()
        if not work_id or work_id == paper.openalex_id or (own_doi and doi == own_doi):
            continue
        names = [(item.get("author") or {}).get("display_name") or "" for item in work.get("authorships") or []]
        if surname not in {_surname(name) for name in names}:
            continue
        year = work.get("publication_year")
        if paper.year and year and abs(paper.year - year) > ALTERNATIVE_YEARS:
            continue
        pdf_url = _oa_pdf_url(work)
        similarity = title_similarity(paper.title, work.get("display_name") or "")
        if not pdf_url or not similarity:
            continue
        source = (work.get("primary_location") or {}).get("source") or {}
        found.append(
            OpenVersion(
                openalex_id=work_id,
                title=work.get("display_name") or work_id,
                authors=names[:3],
                year=year,
                venue=source.get("display_name"),
                pdf_url=pdf_url,
                similarity=similarity,
            )
        )
    found.sort(key=lambda item: -item.similarity)
    return found[:ALTERNATIVE_LIMIT]


def download_pdf(http: httpx2.Client, url: str) -> bytes:
    """주소에서 PDF를 받는다. 크기 제한을 넘으면 받다가 멈춘다.

    @doc: docs/design/Reader.md#2-pdf-가져오기
    """
    chunks: list[bytes] = []
    size = 0
    with http.stream("GET", url, follow_redirects=True, timeout=60) as response:
        response.raise_for_status()
        for chunk in response.iter_bytes():
            size += len(chunk)
            if size > MAX_PDF_BYTES:
                raise PdfTooLargeError("PDF가 100MB를 넘습니다.")
            chunks.append(chunk)
    data = b"".join(chunks)
    check_pdf(data)
    return data


class PdfStore:
    """PDF의 로컬 사본과 드라이브 보관.

    @doc: docs/design/Reader.md#3-보관
    """

    def __init__(self, local_dir: Path, drive: DriveFilesLike) -> None:
        self.local_dir = local_dir
        self.drive = drive

    def _local(self, sha256: str) -> Path:
        return self.local_dir / f"{sha256}.pdf"

    def save(
        self, session: Session, paper: Paper, data: bytes, source: str, source_url: str | None
    ) -> PaperPdf:
        """PDF를 로컬과 드라이브에 두고 논문의 판으로 더해 지금 판으로 고른다.

        같은 내용의 판이 이미 있으면 새로 더하지 않고 출처와 고른 시각만 바꾼다.

        @doc: docs/design/Reader.md#3-보관
        @doc: docs/design/PdfVersions.md#4-저장
        """
        check_pdf(data)
        sha256 = hashlib.sha256(data).hexdigest()
        path = self._local(sha256)
        if not path.exists():
            self.local_dir.mkdir(parents=True, exist_ok=True)
            temporary = path.with_suffix(".part")
            temporary.write_bytes(data)
            temporary.replace(path)
        drive_file_id = self.drive.put_file(PDF_FOLDER, f"{sha256}.pdf", data)
        now = datetime.now(UTC)
        pdf = paper.pdf_version(sha256)
        if pdf is None:
            pdf = PaperPdf(
                sha256=sha256,
                size=len(data),
                source=source,
                source_url=source_url,
                drive_file_id=drive_file_id,
                added_at=now,
                selected_at=now,
            )
            paper.pdfs.append(pdf)
        else:
            pdf.source = source
            pdf.source_url = source_url
            pdf.drive_file_id = drive_file_id or pdf.drive_file_id
            pdf.selected_at = now
        session.commit()
        self.drive.schedule_push()
        return pdf

    def read(self, pdf: PaperPdf) -> bytes | None:
        """PDF 내용을 돌려준다. 로컬 사본이 없으면 드라이브에서 받아 둔다.

        @doc: docs/design/Reader.md#3-보관
        """
        path = self._local(pdf.sha256)
        if path.exists():
            return path.read_bytes()
        if not pdf.drive_file_id:
            return None
        data = self.drive.download_file(pdf.drive_file_id)
        if data is None or hashlib.sha256(data).hexdigest() != pdf.sha256:
            return None
        self.local_dir.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        return data


class PdfOut(BaseModel):
    """논문 PDF 정보 응답.

    @doc: docs/design/Reader.md#5-api
    """

    paper_id: int
    sha256: str
    size: int
    source: str
    source_url: str | None
    stored_in_drive: bool

    @classmethod
    def from_pdf(cls, pdf: PaperPdf) -> "PdfOut":
        """모델 객체를 응답으로 바꾼다.

        @doc: docs/design/Reader.md#5-api
        """
        return cls(
            paper_id=pdf.paper_id,
            sha256=pdf.sha256,
            size=pdf.size,
            source=pdf.source,
            source_url=pdf.source_url,
            stored_in_drive=pdf.drive_file_id is not None,
        )


# @doc: docs/design/Reader.md#5-api
router = APIRouter(prefix="/api/papers")


def _session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


def _paper(session: Session, paper_id: int) -> Paper:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"논문이 없습니다: {paper_id}")
    return paper


# @doc: docs/design/PdfVersions.md#5-api
# @doc: docs/design/Reader.md#5-api
VERSION_PATTERN = r"^[0-9a-f]{64}$"


@router.get("/{paper_id}/pdf")
def read_pdf(
    paper_id: int,
    request: Request,
    session: Annotated[Session, Depends(_session)],
    version: Annotated[str | None, Query(pattern=VERSION_PATTERN)] = None,
) -> Response:
    """`GET /api/papers/{paper_id}/pdf`를 처리한다. `version`(SHA-256)을 주면 그 판, 없으면 지금 판이다.

    @doc: docs/design/Reader.md#5-api
    @doc: docs/design/PdfVersions.md#5-api
    """
    pdf = _paper(session, paper_id).pdf_version(version)
    data = request.app.state.pdfs.read(pdf) if pdf is not None else None
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "PDF가 없습니다.")
    # 판을 준 주소는 내용이 바뀌지 않지만, 지금 판 주소는 판을 고르면 내용이 바뀌므로 매번 확인하게 한다.
    cache = "private, max-age=3600" if version else "private, no-cache"
    return Response(data, media_type="application/pdf", headers={"Cache-Control": cache})


class FetchIn(BaseModel):
    """공개 PDF 받기의 선택 입력. `openalex_id`를 주면 그 공개판의 PDF를, `version`을 주면 받을 수 있는 판 가운데
    그 이름(`arxiv:v3`, `url:<주소>`)의 판을 받는다.

    @doc: docs/design/Reader.md#5-api
    @doc: docs/design/PdfVersions.md#5-api
    """

    openalex_id: str | None = Field(default=None, pattern=r"^W\d+$")
    version: str | None = Field(default=None, max_length=2000)


@router.get("/{paper_id}/pdf/alternatives")
def pdf_alternatives(
    paper_id: int, request: Request, session: Annotated[Session, Depends(_session)]
) -> list[OpenVersion]:
    """`GET /api/papers/{paper_id}/pdf/alternatives`를 처리한다.

    @doc: docs/design/Reader.md#5-api
    """
    paper = _paper(session, paper_id)
    try:
        return open_alternatives(request.app.state.http_client, paper)
    except (httpx2.HTTPError, ValueError) as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"비슷한 공개판을 찾지 못했습니다: {error}") from error


@router.post("/{paper_id}/pdf/fetch")
def fetch_pdf(
    paper_id: int,
    request: Request,
    session: Annotated[Session, Depends(_session)],
    body: FetchIn | None = None,
) -> PdfOut:
    """`POST /api/papers/{paper_id}/pdf/fetch`를 처리한다.

    @doc: docs/design/Reader.md#5-api
    """
    paper = _paper(session, paper_id)
    http = request.app.state.http_client
    if body is not None and body.version:
        # 서버가 판 목록을 다시 찾아 그 이름의 주소만 받는다. 사용자가 준 주소를 그대로 받지 않기 위해서다.
        try:
            versions = available_versions(http, paper)
        except httpx2.HTTPError as error:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"받을 수 있는 판을 찾지 못했습니다: {error}") from error
        chosen = next((item for item in versions if item.key == body.version), None)
        if chosen is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "그 판을 찾지 못했습니다.")
        found = (chosen.url, "arxiv" if chosen.key.startswith("arxiv:") else "openalex")
    elif body is not None and body.openalex_id:
        alternate = open_access_pdf_url(http, body.openalex_id, None)
        found = (alternate[0], "alternate") if alternate else None
    else:
        found = open_pdf_url(http, paper)
    if found is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "공개된 PDF를 찾지 못했습니다. PDF를 직접 올려 주세요.")
    url, source = found
    try:
        data = download_pdf(http, url)
    except NotPdfError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"{url}에서 PDF가 아닌 내용을 받았습니다. PDF를 직접 올려 주세요.") from error
    except PdfTooLargeError as error:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(error)) from error
    except httpx2.HTTPError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"PDF를 받지 못했습니다: {error}") from error
    return PdfOut.from_pdf(request.app.state.pdfs.save(session, paper, data, source, url))


@router.put("/{paper_id}/pdf")
async def upload_pdf(paper_id: int, request: Request) -> PdfOut:
    """`PUT /api/papers/{paper_id}/pdf`를 처리한다. 본문이 PDF 내용이다.

    @doc: docs/design/Reader.md#5-api
    """
    declared = request.headers.get("content-length")
    if declared and declared.isdigit() and int(declared) > MAX_PDF_BYTES:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, "PDF가 100MB를 넘습니다.")
    data = await request.body()

    def store() -> PdfOut:
        with Session(request.app.state.engine) as session:
            paper = _paper(session, paper_id)
            return PdfOut.from_pdf(request.app.state.pdfs.save(session, paper, data, "upload", None))

    try:
        return await run_in_threadpool(store)
    except PdfTooLargeError as error:
        raise HTTPException(status.HTTP_413_CONTENT_TOO_LARGE, str(error)) from error
    except NotPdfError as error:
        raise HTTPException(status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, str(error)) from error
