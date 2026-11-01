"""논문 검색과 추가 API.

@doc: docs/design/PaperSearch.md#3-api
"""

from collections.abc import Iterator
from datetime import datetime
from typing import Annotated

import httpx2
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from jjabtero.library import DuplicateDoiError, PaperData, add_paper
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
