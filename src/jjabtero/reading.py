"""리더의 읽던 위치 API.

@doc: docs/design/Reader.md#5-api
"""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from jjabtero.models import Paper, ReadingPosition

# @doc: docs/design/Reader.md#5-api
router = APIRouter(prefix="/api/papers")


class PositionIn(BaseModel):
    """읽던 위치 입력. 쪽은 1부터, 쪽 안 위치는 0~1, 확대 배율은 0.25~5다.

    @doc: docs/design/Reader.md#4-데이터
    """

    page: int = Field(ge=1)
    offset: float = Field(ge=0, le=1)
    zoom: float = Field(ge=0.25, le=5)


class PositionOut(PositionIn):
    """읽던 위치 응답.

    @doc: docs/design/Reader.md#5-api
    """

    updated_at: datetime


def _session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


def _paper(session: Session, paper_id: int) -> Paper:
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"논문이 없습니다: {paper_id}")
    return paper


@router.get("/{paper_id}/position", response_model=None)
def read_position(paper_id: int, session: Annotated[Session, Depends(_session)]) -> PositionOut | Response:
    """`GET /api/papers/{paper_id}/position`을 처리한다. 저장한 위치가 없으면 204다.

    @doc: docs/design/Reader.md#5-api
    """
    position = _paper(session, paper_id).position
    if position is None:
        return Response(status_code=status.HTTP_204_NO_CONTENT)
    return PositionOut(page=position.page, offset=position.offset, zoom=position.zoom, updated_at=position.updated_at)


@router.put("/{paper_id}/position")
def save_position(
    paper_id: int, data: PositionIn, request: Request, session: Annotated[Session, Depends(_session)]
) -> PositionOut:
    """`PUT /api/papers/{paper_id}/position`을 처리한다. 저장하면 드라이브 자동 올리기를 예약한다.

    @doc: docs/design/Reader.md#5-api
    """
    paper = _paper(session, paper_id)
    now = datetime.now(UTC)
    if paper.position is None:
        paper.position = ReadingPosition(page=data.page, offset=data.offset, zoom=data.zoom, updated_at=now)
    else:
        paper.position.page = data.page
        paper.position.offset = data.offset
        paper.position.zoom = data.zoom
        paper.position.updated_at = now
    session.commit()
    request.app.state.drive.schedule_push()
    return PositionOut(page=data.page, offset=data.offset, zoom=data.zoom, updated_at=now)
