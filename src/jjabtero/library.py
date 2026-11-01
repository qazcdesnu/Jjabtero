"""논문 저장 함수.

@doc: docs/design/Library.md#4-저장-함수
@doc: docs/design/ReadingStatus.md#2-저장-함수와-api
"""

import re
from datetime import UTC, datetime

from pydantic import BaseModel, field_validator
from sqlalchemy import select
from sqlalchemy.orm import Session

from jjabtero.models import ITEM_TYPES, READ_STATUSES, Author, Paper, PaperAuthor, Tag

_DOI_PREFIX = re.compile(r"^(https?://(dx\.)?doi\.org/|doi:)", re.IGNORECASE)


class PaperNotFoundError(LookupError):
    """없는 논문 ID를 받았다.

    @doc: docs/design/Library.md#4-저장-함수
    """

    def __init__(self, paper_id: int) -> None:
        super().__init__(f"논문이 없습니다: {paper_id}")
        self.paper_id = paper_id


class DuplicateDoiError(ValueError):
    """다른 논문이 이미 같은 DOI를 쓴다.

    @doc: docs/design/Library.md#4-저장-함수
    """

    def __init__(self, doi: str, paper_id: int) -> None:
        super().__init__(f"DOI {doi}는 이미 논문 {paper_id}가 씁니다")
        self.doi = doi
        self.paper_id = paper_id


def normalize_doi(value: str) -> str:
    """DOI를 정규화한다.

    @doc: docs/design/Library.md#4-저장-함수
    """
    doi = _DOI_PREFIX.sub("", value.strip()).lower()
    if not doi.startswith("10."):
        raise ValueError(f"DOI가 아닙니다: {value}")
    return doi


def _strip_or_none(value: str | None) -> str | None:
    if value is None:
        return None
    return value.strip() or None


class PaperData(BaseModel):
    """논문을 만들거나 고칠 때의 입력.

    @doc: docs/design/Library.md#4-저장-함수
    """

    title: str
    authors: list[str] = []
    item_type: str = "other"
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    tags: list[str] = []

    @field_validator("title")
    @classmethod
    def _check_title(cls, value: str) -> str:
        title = value.strip()
        if not title:
            raise ValueError("제목이 비어 있습니다")
        return title

    @field_validator("authors")
    @classmethod
    def _clean_authors(cls, value: list[str]) -> list[str]:
        return [name.strip() for name in value if name.strip()]

    @field_validator("tags")
    @classmethod
    def _clean_tags(cls, value: list[str]) -> list[str]:
        return list(dict.fromkeys(name.strip() for name in value if name.strip()))

    @field_validator("item_type")
    @classmethod
    def _check_item_type(cls, value: str) -> str:
        if value not in ITEM_TYPES:
            raise ValueError(f"알 수 없는 항목 종류입니다: {value}")
        return value

    @field_validator("venue", "url")
    @classmethod
    def _clean_optional(cls, value: str | None) -> str | None:
        return _strip_or_none(value)

    @field_validator("doi")
    @classmethod
    def _clean_doi(cls, value: str | None) -> str | None:
        value = _strip_or_none(value)
        return None if value is None else normalize_doi(value)


def _check_doi_free(session: Session, doi: str | None, paper_id: int | None) -> None:
    if doi is None:
        return
    owner = session.scalar(select(Paper.id).where(Paper.doi == doi))
    if owner is not None and owner != paper_id:
        raise DuplicateDoiError(doi, owner)


def _apply(session: Session, paper: Paper, data: PaperData) -> None:
    paper.title = data.title
    paper.item_type = data.item_type
    paper.year = data.year
    paper.venue = data.venue
    paper.doi = data.doi
    paper.url = data.url
    # 같은 이름이 한 입력에 두 번 나와도 저자 행을 하나만 만들도록 이번 호출 안에서 기억한다.
    authors: dict[str, Author] = {}
    for name in data.authors:
        if name not in authors:
            authors[name] = session.scalar(select(Author).where(Author.name == name)) or Author(name=name)
    paper.author_links = [
        PaperAuthor(position=position, author=authors[name])
        for position, name in enumerate(data.authors)
    ]
    paper.tags = [
        session.scalar(select(Tag).where(Tag.name == name)) or Tag(name=name) for name in data.tags
    ]


def add_paper(session: Session, data: PaperData) -> Paper:
    """논문을 만든다.

    @doc: docs/design/Library.md#4-저장-함수
    """
    _check_doi_free(session, data.doi, None)
    paper = Paper()
    session.add(paper)
    _apply(session, paper, data)
    session.commit()
    return paper


def get_paper(session: Session, paper_id: int) -> Paper | None:
    """ID로 논문을 찾는다.

    @doc: docs/design/Library.md#4-저장-함수
    """
    return session.get(Paper, paper_id)


def list_papers(session: Session) -> list[Paper]:
    """모든 논문을 최근에 만든 것부터 돌려준다.

    @doc: docs/design/Library.md#4-저장-함수
    """
    return list(session.scalars(select(Paper).order_by(Paper.created_at.desc(), Paper.id.desc())))


def update_paper(session: Session, paper_id: int, data: PaperData) -> Paper:
    """논문의 모든 항목을 바꾼다.

    @doc: docs/design/Library.md#4-저장-함수
    """
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise PaperNotFoundError(paper_id)
    _check_doi_free(session, data.doi, paper_id)
    # 같은 위치의 새 저자 연결이 옛 연결과 기본 키가 겹치지 않도록 옛 연결을 먼저 지운다.
    paper.author_links.clear()
    session.flush()
    _apply(session, paper, data)
    paper.updated_at = datetime.now(UTC)
    session.commit()
    return paper


def delete_paper(session: Session, paper_id: int) -> None:
    """논문을 지운다.

    @doc: docs/design/Library.md#4-저장-함수
    """
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise PaperNotFoundError(paper_id)
    session.delete(paper)
    session.commit()


class ReadingUpdate(BaseModel):
    """읽기 상태와 메모를 바꾸는 입력. 보낸 항목만 바꾼다.

    @doc: docs/design/ReadingStatus.md#2-저장-함수와-api
    """

    read_status: str | None = None
    note: str | None = None

    @field_validator("read_status")
    @classmethod
    def _check_read_status(cls, value: str | None) -> str:
        if value not in READ_STATUSES:
            raise ValueError(f"알 수 없는 읽기 상태입니다: {value}")
        return value

    @field_validator("note")
    @classmethod
    def _clean_note(cls, value: str | None) -> str | None:
        return _strip_or_none(value)


def update_reading(session: Session, paper_id: int, update: ReadingUpdate) -> Paper:
    """논문의 읽기 상태와 메모를 바꾼다.

    @doc: docs/design/ReadingStatus.md#2-저장-함수와-api
    """
    paper = session.get(Paper, paper_id)
    if paper is None:
        raise PaperNotFoundError(paper_id)
    if "read_status" in update.model_fields_set:
        paper.read_status = update.read_status
    if "note" in update.model_fields_set:
        paper.note = update.note
    paper.updated_at = datetime.now(UTC)
    session.commit()
    return paper

