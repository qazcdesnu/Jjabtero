"""태그 붙이기·떼기, 이름 바꾸기·지우기.

@doc: docs/design/Tags.md#3-api
"""

import re
from collections.abc import Iterable, Iterator
from datetime import UTC, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from jjabtero.models import Paper, Tag, paper_tags
from jjabtero.papers_api import PaperOut

# @doc: docs/design/Tags.md#2-태그-이름-규칙
MAX_TAG_LENGTH = 50
_SPACES = re.compile(r"\s+")


class TagNameError(ValueError):
    """태그 이름이 규칙에 맞지 않는다.

    @doc: docs/design/Tags.md#2-태그-이름-규칙
    """


def clean_tags(names: Iterable[str]) -> list[str]:
    """태그 이름을 다듬는다. 빈칸을 정리하고, 빈 이름과 겹친 이름을 빼며, 50자를 넘으면 `TagNameError`다.

    @doc: docs/design/Tags.md#2-태그-이름-규칙
    """
    cleaned: list[str] = []
    for name in names:
        tidy = _SPACES.sub(" ", name).strip()
        if not tidy:
            continue
        if len(tidy) > MAX_TAG_LENGTH:
            raise TagNameError(f"태그 이름은 {MAX_TAG_LENGTH}자까지입니다: {tidy[:20]}…")
        if tidy not in cleaned:
            cleaned.append(tidy)
    return cleaned


def _tag(session: Session, name: str) -> Tag:
    return session.scalar(select(Tag).where(Tag.name == name)) or Tag(name=name)


def _touch(paper: Paper) -> None:
    # 드라이브 자동 합치기가 늦게 고친 쪽을 고를 수 있도록 고친 시각을 바꾼다.
    paper.updated_at = datetime.now(UTC)


def drop_unused_tags(session: Session) -> None:
    """어느 논문에도 붙지 않은 태그를 지운다.

    @doc: docs/design/Tags.md#2-태그-이름-규칙
    """
    session.flush()
    used = select(paper_tags.c.tag_id)
    for tag in session.scalars(select(Tag).where(Tag.id.not_in(used))):
        session.delete(tag)


def set_paper_tags(session: Session, paper: Paper, names: Iterable[str]) -> Paper:
    """논문의 태그를 이 목록으로 바꾼다.

    @doc: docs/design/Tags.md#3-api
    """
    wanted = clean_tags(names)
    if sorted(wanted) != paper.tag_names:
        paper.tags = [_tag(session, name) for name in wanted]
        _touch(paper)
        drop_unused_tags(session)
    session.commit()
    return paper


def apply_tags(session: Session, papers: list[Paper], add: Iterable[str], remove: Iterable[str]) -> int:
    """여러 논문에 태그를 붙이고 뗀다. 바뀐 논문 수를 돌려준다.

    @doc: docs/design/Tags.md#3-api
    """
    adding = clean_tags(add)
    removing = set(clean_tags(remove))
    tags = {name: _tag(session, name) for name in adding}
    changed = 0
    for paper in papers:
        before = set(paper.tag_names)
        kept = [tag for tag in paper.tags if tag.name not in removing]
        names = {tag.name for tag in kept}
        paper.tags = kept + [tags[name] for name in adding if name not in names and name not in removing]
        if set(paper.tag_names) != before:
            _touch(paper)
            changed += 1
    drop_unused_tags(session)
    session.commit()
    return changed


def rename_tag(session: Session, old: str, new: str) -> int:
    """태그 이름을 바꾼다. 새 이름의 태그가 이미 있으면 합친다. 바뀐 논문 수를 돌려준다.

    @doc: docs/design/Tags.md#3-api
    """
    tag = session.scalar(select(Tag).where(Tag.name == old))
    if tag is None:
        raise LookupError(old)
    [name] = clean_tags([new]) or [""]
    if not name:
        raise TagNameError("새 태그 이름이 비어 있습니다.")
    if name == old:
        return 0
    papers = [paper for paper in session.scalars(select(Paper)) if tag in paper.tags]
    target = session.scalar(select(Tag).where(Tag.name == name))
    if target is None:
        tag.name = name
    else:
        for paper in papers:
            paper.tags = [item for item in paper.tags if item is not tag] + ([] if target in paper.tags else [target])
        session.delete(tag)
    for paper in papers:
        _touch(paper)
    drop_unused_tags(session)
    session.commit()
    return len(papers)


def delete_tag(session: Session, name: str) -> int:
    """모든 논문에서 태그를 떼고 지운다. 뗀 논문 수를 돌려준다.

    @doc: docs/design/Tags.md#3-api
    """
    tag = session.scalar(select(Tag).where(Tag.name == name))
    if tag is None:
        raise LookupError(name)
    papers = [paper for paper in session.scalars(select(Paper)) if tag in paper.tags]
    for paper in papers:
        paper.tags = [item for item in paper.tags if item is not tag]
        _touch(paper)
    session.delete(tag)
    session.commit()
    return len(papers)


class TagsIn(BaseModel):
    """논문 하나의 태그 목록.

    @doc: docs/design/Tags.md#3-api
    """

    tags: list[str]


class ApplyIn(BaseModel):
    """여러 논문에 붙이고 뗄 태그.

    @doc: docs/design/Tags.md#3-api
    """

    paper_ids: list[int] = Field(min_length=1)
    add: list[str] = []
    remove: list[str] = []


class RenameIn(BaseModel):
    """새 태그 이름.

    @doc: docs/design/Tags.md#3-api
    """

    name: str


class ChangedOut(BaseModel):
    """바뀐 논문 수.

    @doc: docs/design/Tags.md#3-api
    """

    changed: int


# @doc: docs/design/Tags.md#3-api
router = APIRouter(prefix="/api")


def _session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


def _bad_name(error: TagNameError) -> HTTPException:
    return HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error))


@router.put("/papers/{paper_id}/tags")
def put_paper_tags(
    paper_id: int, body: TagsIn, request: Request, session: Annotated[Session, Depends(_session)]
) -> PaperOut:
    """`PUT /api/papers/{paper_id}/tags`를 처리한다.

    @doc: docs/design/Tags.md#3-api
    """
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"논문이 없습니다: {paper_id}")
    try:
        set_paper_tags(session, paper, body.tags)
    except TagNameError as error:
        raise _bad_name(error) from error
    request.app.state.drive.schedule_push()
    return PaperOut.from_paper(paper)


@router.post("/tags/apply")
def post_apply_tags(body: ApplyIn, request: Request, session: Annotated[Session, Depends(_session)]) -> ChangedOut:
    """`POST /api/tags/apply`를 처리한다.

    @doc: docs/design/Tags.md#3-api
    """
    papers = [session.get(Paper, paper_id) for paper_id in dict.fromkeys(body.paper_ids)]
    missing = [paper_id for paper_id, paper in zip(dict.fromkeys(body.paper_ids), papers, strict=True) if paper is None]
    if missing:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"논문이 없습니다: {missing}")
    try:
        changed = apply_tags(session, [paper for paper in papers if paper is not None], body.add, body.remove)
    except TagNameError as error:
        raise _bad_name(error) from error
    if changed:
        request.app.state.drive.schedule_push()
    return ChangedOut(changed=changed)


@router.patch("/tags/{name}")
def patch_tag(name: str, body: RenameIn, request: Request, session: Annotated[Session, Depends(_session)]) -> ChangedOut:
    """`PATCH /api/tags/{name}`을 처리한다.

    @doc: docs/design/Tags.md#3-api
    """
    try:
        changed = rename_tag(session, name, body.name)
    except LookupError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"태그가 없습니다: {name}") from error
    except TagNameError as error:
        raise _bad_name(error) from error
    request.app.state.drive.schedule_push()
    return ChangedOut(changed=changed)


@router.delete("/tags/{name}")
def remove_tag(name: str, request: Request, session: Annotated[Session, Depends(_session)]) -> ChangedOut:
    """`DELETE /api/tags/{name}`을 처리한다.

    @doc: docs/design/Tags.md#3-api
    """
    try:
        changed = delete_tag(session, name)
    except LookupError as error:
        raise HTTPException(status.HTTP_404_NOT_FOUND, f"태그가 없습니다: {name}") from error
    request.app.state.drive.schedule_push()
    return ChangedOut(changed=changed)

