"""리더의 읽던 위치와 주석 API.

@doc: docs/design/Reader.md#5-api
"""

import json
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, HTTPException, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from jjabtero.models import Annotation, Paper, ReadingPosition

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


# @doc: docs/design/Reader.md#4-데이터
ANNOTATION_KINDS = ("highlight", "note")
# @doc: docs/design/Reader.md#4-데이터
ANNOTATION_COLORS = ("yellow", "green", "blue", "pink", "purple")


class Rect(BaseModel):
    """쪽 크기에 대한 비율(0~1)로 나타낸 사각형.

    @doc: docs/design/Reader.md#4-데이터
    """

    x: float = Field(ge=0, le=1)
    y: float = Field(ge=0, le=1)
    w: float = Field(gt=0, le=1)
    h: float = Field(gt=0, le=1)


class AnnotationIn(BaseModel):
    """주석을 만들 때의 입력.

    @doc: docs/design/Reader.md#5-api
    """

    kind: Literal["highlight", "note"]
    page: int = Field(ge=1)
    rects: list[Rect] = Field(min_length=1, max_length=200)
    text: str | None = Field(default=None, max_length=10000)
    color: Literal["yellow", "green", "blue", "pink", "purple"] = "yellow"
    note: str | None = Field(default=None, max_length=20000)


class AnnotationUpdate(BaseModel):
    """주석을 고칠 때의 입력. 보낸 항목만 바꾼다.

    @doc: docs/design/Reader.md#5-api
    """

    color: Literal["yellow", "green", "blue", "pink", "purple"] | None = None
    note: str | None = Field(default=None, max_length=20000)


class AnnotationOut(BaseModel):
    """주석 응답.

    @doc: docs/design/Reader.md#5-api
    """

    id: int
    paper_id: int
    kind: str
    page: int
    rects: list[Rect]
    text: str | None
    color: str
    note: str | None
    created_at: datetime
    updated_at: datetime

    @classmethod
    def from_annotation(cls, annotation: Annotation) -> "AnnotationOut":
        """모델 객체를 응답으로 바꾼다.

        @doc: docs/design/Reader.md#5-api
        """
        return cls(
            id=annotation.id,
            paper_id=annotation.paper_id,
            kind=annotation.kind,
            page=annotation.page,
            rects=[Rect(**rect) for rect in json.loads(annotation.rects)],
            text=annotation.text,
            color=annotation.color,
            note=annotation.note,
            created_at=annotation.created_at,
            updated_at=annotation.updated_at,
        )


def _clean(value: str | None) -> str | None:
    return value.strip() or None if value is not None else None


@router.get("/{paper_id}/annotations")
def list_annotations(paper_id: int, session: Annotated[Session, Depends(_session)]) -> list[AnnotationOut]:
    """`GET /api/papers/{paper_id}/annotations`를 처리한다. 쪽 순서, 쪽 안에서는 위에서부터다.

    @doc: docs/design/Reader.md#5-api
    """
    paper = _paper(session, paper_id)
    items = [AnnotationOut.from_annotation(annotation) for annotation in paper.annotations]
    return sorted(items, key=lambda item: (item.page, item.rects[0].y, item.rects[0].x, item.id))


@router.post("/{paper_id}/annotations", status_code=status.HTTP_201_CREATED)
def create_annotation(
    paper_id: int, data: AnnotationIn, request: Request, session: Annotated[Session, Depends(_session)]
) -> AnnotationOut:
    """`POST /api/papers/{paper_id}/annotations`를 처리한다.

    @doc: docs/design/Reader.md#5-api
    """
    paper = _paper(session, paper_id)
    now = datetime.now(UTC)
    annotation = Annotation(
        kind=data.kind,
        page=data.page,
        rects=json.dumps([rect.model_dump() for rect in data.rects]),
        text=_clean(data.text),
        color=data.color,
        note=_clean(data.note),
        created_at=now,
        updated_at=now,
    )
    paper.annotations.append(annotation)
    session.commit()
    request.app.state.drive.schedule_push()
    return AnnotationOut.from_annotation(annotation)


def _annotation(session: Session, annotation_id: int) -> Annotation:
    annotation = session.get(Annotation, annotation_id)
    if annotation is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"주석이 없습니다: {annotation_id}")
    return annotation


# @doc: docs/design/Reader.md#5-api
annotations_router = APIRouter(prefix="/api/annotations")


@annotations_router.patch("/{annotation_id}")
def update_annotation(
    annotation_id: int, data: AnnotationUpdate, request: Request, session: Annotated[Session, Depends(_session)]
) -> AnnotationOut:
    """`PATCH /api/annotations/{annotation_id}`를 처리한다.

    @doc: docs/design/Reader.md#5-api
    """
    annotation = _annotation(session, annotation_id)
    if "color" in data.model_fields_set and data.color is not None:
        annotation.color = data.color
    if "note" in data.model_fields_set:
        annotation.note = _clean(data.note)
    annotation.updated_at = datetime.now(UTC)
    session.commit()
    request.app.state.drive.schedule_push()
    return AnnotationOut.from_annotation(annotation)


@annotations_router.delete("/{annotation_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_annotation(
    annotation_id: int, request: Request, session: Annotated[Session, Depends(_session)]
) -> Response:
    """`DELETE /api/annotations/{annotation_id}`를 처리한다.

    @doc: docs/design/Reader.md#5-api
    """
    session.delete(_annotation(session, annotation_id))
    session.commit()
    request.app.state.drive.schedule_push()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
