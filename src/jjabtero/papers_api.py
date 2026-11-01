"""논문 검색, 추가, 목록, 삭제 API.

@doc: docs/design/PaperSearch.md#3-api
@doc: docs/design/LibraryView.md#1-api
@doc: docs/design/ReadingStatus.md#2-저장-함수와-api
"""

from collections.abc import Iterator
from datetime import datetime
from typing import Annotated

import httpx2
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from jjabtero.library import (
    DuplicateDoiError,
    PaperData,
    PaperNotFoundError,
    ReadingUpdate,
    add_paper,
    delete_paper,
    list_papers,
    update_reading,
)
from jjabtero.models import Paper
from jjabtero.search import SOURCES, SearchResponse, search_papers

router = APIRouter(prefix="/api")


def _session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


def _http_client(request: Request) -> httpx2.Client:
    return request.app.state.http_client


class PaperOut(BaseModel):
    """논문 응답.

    @doc: docs/design/PaperSearch.md#3-api
    """

    id: int
    title: str
    authors: list[str]
    item_type: str
    year: int | None
    venue: str | None
    doi: str | None
    url: str | None
    tags: list[str]
    read_status: str
    note: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_paper(cls, paper: Paper) -> "PaperOut":
        """모델 객체를 응답으로 바꾼다.

        @doc: docs/design/PaperSearch.md#3-api
        """
        return cls(
            id=paper.id,
            title=paper.title,
            authors=paper.author_names,
            item_type=paper.item_type,
            year=paper.year,
            venue=paper.venue,
            doi=paper.doi,
            url=paper.url,
            tags=paper.tag_names,
            read_status=paper.read_status,
            note=paper.note,
            created_at=paper.created_at,
            updated_at=paper.updated_at,
        )


@router.get("/search")
def search(
    q: Annotated[str, Query()],
    session: Annotated[Session, Depends(_session)],
    client: Annotated[httpx2.Client, Depends(_http_client)],
    sources: Annotated[list[str] | None, Query()] = None,
    limit: Annotated[int, Query(ge=1, le=25)] = 10,
) -> SearchResponse:
    """`GET /api/search`를 처리한다.

    @doc: docs/design/PaperSearch.md#3-api
    """
    query = q.strip()
    if not query:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "검색어가 비어 있습니다")
    chosen = sources or list(SOURCES)
    unknown = [name for name in chosen if name not in SOURCES]
    if unknown:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, f"알 수 없는 검색원입니다: {', '.join(unknown)}"
        )
    response = search_papers(client, query, chosen, limit)
    dois = {result.doi for result in response.results if result.doi}
    rows = session.execute(select(Paper.doi, Paper.id).where(Paper.doi.in_(dois)))
    owners = {doi: paper_id for doi, paper_id in rows}
    for result in response.results:
        result.library_paper_id = owners.get(result.doi)
    return response


@router.post("/papers", status_code=status.HTTP_201_CREATED)
def create_paper(data: PaperData, session: Annotated[Session, Depends(_session)]) -> PaperOut:
    """`POST /api/papers`를 처리한다.

    @doc: docs/design/PaperSearch.md#3-api
    """
    try:
        paper = add_paper(session, data)
    except DuplicateDoiError as error:
        raise HTTPException(
            status.HTTP_409_CONFLICT, {"message": str(error), "paper_id": error.paper_id}
        ) from error
    return PaperOut.from_paper(paper)


@router.get("/papers")
def read_papers(session: Annotated[Session, Depends(_session)]) -> list[PaperOut]:
    """`GET /api/papers`를 처리한다.

    @doc: docs/design/LibraryView.md#1-api
    """
    return [PaperOut.from_paper(paper) for paper in list_papers(session)]


@router.delete("/papers/{paper_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_paper(paper_id: int, session: Annotated[Session, Depends(_session)]) -> Response:
    """`DELETE /api/papers/{paper_id}`를 처리한다.

    @doc: docs/design/LibraryView.md#1-api
    """
    try:
        delete_paper(session, paper_id)
    except PaperNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.patch("/papers/{paper_id}")
def change_reading(
    paper_id: int, update: ReadingUpdate, session: Annotated[Session, Depends(_session)]
) -> PaperOut:
    """`PATCH /api/papers/{paper_id}`를 처리한다.

    @doc: docs/design/ReadingStatus.md#2-저장-함수와-api
    """
    try:
        paper = update_reading(session, paper_id, update)
    except PaperNotFoundError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(error)) from error
    return PaperOut.from_paper(paper)

