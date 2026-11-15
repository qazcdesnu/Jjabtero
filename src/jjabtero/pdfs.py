"""논문 PDF의 가져오기, 보관, 내려주기.

@doc: docs/design/Reader.md#2-pdf-가져오기
@doc: docs/design/Reader.md#3-보관
"""

import hashlib
import os
import re
from collections.abc import Iterator
from pathlib import Path
from typing import Annotated, Protocol

import httpx2
from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from jjabtero.citations import OPENALEX_WORKS_URL
from jjabtero.models import Paper, PaperPdf

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


def open_access_pdf_url(http: httpx2.Client, openalex_id: str | None, doi: str | None) -> tuple[str, str] | None:
    """OpenAlex ID와 DOI로 공개 PDF 주소와 출처(`openalex`, `arxiv`)를 찾는다. 없으면 `None`이다.

    @doc: docs/design/Reader.md#2-pdf-가져오기
    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """
    if openalex_id:
        params = {"select": "best_oa_location,open_access"}
        api_key = os.environ.get("OPENALEX_API_KEY")
        if api_key:
            params["api_key"] = api_key
        response = http.get(f"{OPENALEX_WORKS_URL}/{openalex_id}", params=params)
        if response.status_code == 200:
            body = response.json()
            url = (body.get("best_oa_location") or {}).get("pdf_url") or (body.get("open_access") or {}).get("oa_url")
            if url:
                # OpenAlex가 arXiv 소개 페이지를 주는 경우가 있어 PDF 주소로 바꾼다.
                abstract = _ARXIV_ABS.match(url)
                return (f"https://arxiv.org/pdf/{abstract.group(1)}" if abstract else url), "openalex"
    match = _ARXIV_DOI.match(doi or "")
    if match:
        return f"https://arxiv.org/pdf/{match.group(1)}", "arxiv"
    return None


def open_pdf_url(http: httpx2.Client, paper: Paper) -> tuple[str, str] | None:
    """논문의 공개 PDF 주소와 출처(`openalex`, `arxiv`)를 찾는다. 없으면 `None`이다.

    @doc: docs/design/Reader.md#2-pdf-가져오기
    """
    return open_access_pdf_url(http, paper.openalex_id, paper.doi)


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
        """PDF를 로컬과 드라이브에 두고 논문과 잇는다. 옛 연결은 바꾼다.

        @doc: docs/design/Reader.md#3-보관
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
        if paper.pdf is not None:
            session.delete(paper.pdf)
            session.flush()
        paper.pdf = PaperPdf(
            sha256=sha256, size=len(data), source=source, source_url=source_url, drive_file_id=drive_file_id
        )
        session.commit()
        self.drive.schedule_push()
        return paper.pdf

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


@router.get("/{paper_id}/pdf")
def read_pdf(paper_id: int, request: Request, session: Annotated[Session, Depends(_session)]) -> Response:
    """`GET /api/papers/{paper_id}/pdf`를 처리한다.

    @doc: docs/design/Reader.md#5-api
    """
    paper = _paper(session, paper_id)
    data = request.app.state.pdfs.read(paper.pdf) if paper.pdf is not None else None
    if data is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "PDF가 없습니다.")
    return Response(data, media_type="application/pdf", headers={"Cache-Control": "private, max-age=3600"})


@router.post("/{paper_id}/pdf/fetch")
def fetch_pdf(paper_id: int, request: Request, session: Annotated[Session, Depends(_session)]) -> PdfOut:
    """`POST /api/papers/{paper_id}/pdf/fetch`를 처리한다.

    @doc: docs/design/Reader.md#5-api
    """
    paper = _paper(session, paper_id)
    http = request.app.state.http_client
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
