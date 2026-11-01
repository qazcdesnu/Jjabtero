"""서재 데이터 모델.

@doc: docs/design/Library.md#1-데이터-모델
@doc: docs/design/ReadingStatus.md#1-데이터
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, Table, Text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

# @doc: docs/design/Library.md#1-데이터-모델
ITEM_TYPES = (
    "journal-article",
    "conference-paper",
    "preprint",
    "book",
    "book-chapter",
    "thesis",
    "report",
    "other",
)

# @doc: docs/design/ReadingStatus.md#1-데이터
READ_STATUSES = ("to-read", "reading", "read")


def _now() -> datetime:
    return datetime.now(UTC)


class Base(DeclarativeBase):
    """모든 모델의 바탕 클래스.

    @doc: docs/design/Library.md#1-데이터-모델
    """


paper_tags = Table(
    "paper_tags",
    Base.metadata,
    Column("paper_id", ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True),
    Column("tag_id", ForeignKey("tags.id", ondelete="CASCADE"), primary_key=True),
)


class Author(Base):
    """저자.

    @doc: docs/design/Library.md#1-데이터-모델
    """

    __tablename__ = "authors"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)


class Tag(Base):
    """사용자가 붙이는 태그.

    @doc: docs/design/Library.md#1-데이터-모델
    """

    __tablename__ = "tags"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String, unique=True)


class PaperAuthor(Base):
    """논문과 저자의 연결. 저자 순서를 가진다.

    @doc: docs/design/Library.md#1-데이터-모델
    """

    __tablename__ = "paper_authors"

    paper_id: Mapped[int] = mapped_column(
        ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True
    )
    position: Mapped[int] = mapped_column(Integer, primary_key=True)
    author_id: Mapped[int] = mapped_column(ForeignKey("authors.id"))

    paper: Mapped["Paper"] = relationship(back_populates="author_links")
    author: Mapped[Author] = relationship()


class Paper(Base):
    """논문 하나의 서지 정보.

    @doc: docs/design/Library.md#1-데이터-모델
    """

    __tablename__ = "papers"

    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String)
    item_type: Mapped[str] = mapped_column(String, default="other")
    year: Mapped[int | None] = mapped_column(Integer)
    venue: Mapped[str | None] = mapped_column(String)
    doi: Mapped[str | None] = mapped_column(String, unique=True)
    url: Mapped[str | None] = mapped_column(String)
    read_status: Mapped[str] = mapped_column(String, default="to-read", server_default="to-read")
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    author_links: Mapped[list[PaperAuthor]] = relationship(
        back_populates="paper",
        order_by=PaperAuthor.position,
        cascade="all, delete-orphan",
    )
    tags: Mapped[list[Tag]] = relationship(secondary=paper_tags)

    @property
    def author_names(self) -> list[str]:
        """저자 이름을 순서대로 돌려준다.

        @doc: docs/design/Library.md#1-데이터-모델
        """
        return [link.author.name for link in self.author_links]

    @property
    def tag_names(self) -> list[str]:
        """태그 이름을 가나다순으로 돌려준다.

        @doc: docs/design/Library.md#1-데이터-모델
        """
        return sorted(tag.name for tag in self.tags)
