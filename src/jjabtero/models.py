"""서재 데이터 모델.

@doc: docs/design/Library.md#1-데이터-모델
@doc: docs/design/ReadingStatus.md#1-데이터
"""

from datetime import UTC, datetime

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Table, Text
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
    openalex_id: Mapped[str | None] = mapped_column(String)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)

    author_links: Mapped[list[PaperAuthor]] = relationship(
        back_populates="paper",
        order_by=PaperAuthor.position,
        cascade="all, delete-orphan",
    )
    tags: Mapped[list[Tag]] = relationship(secondary=paper_tags)
    pdf: Mapped["PaperPdf | None"] = relationship(cascade="all, delete-orphan", passive_deletes=True)
    position: Mapped["ReadingPosition | None"] = relationship(cascade="all, delete-orphan", passive_deletes=True)
    annotations: Mapped[list["Annotation"]] = relationship(cascade="all, delete-orphan", passive_deletes=True)

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


class Setting(Base):
    """사용자가 바꾼 설정 하나. 없는 키는 기본값을 쓴다.

    @doc: docs/design/Settings.md#2-저장
    """

    __tablename__ = "settings"

    key: Mapped[str] = mapped_column(String, primary_key=True)
    value: Mapped[str] = mapped_column(String)


class PaperPdf(Base):
    """논문의 PDF. 내용은 드라이브와 로컬 사본에 있고, 여기에는 연결만 둔다.

    @doc: docs/design/Reader.md#4-데이터
    @doc: docs/design/Library.md#1-데이터-모델
    """

    __tablename__ = "paper_pdfs"

    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    sha256: Mapped[str] = mapped_column(String)
    size: Mapped[int] = mapped_column(Integer)
    source: Mapped[str] = mapped_column(String)
    source_url: Mapped[str | None] = mapped_column(String)
    drive_file_id: Mapped[str | None] = mapped_column(String)
    page_count: Mapped[int | None] = mapped_column(Integer)
    added_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)



class ReadingPosition(Base):
    """논문을 읽던 위치. 쪽 번호와 그 쪽 안의 세로 비율, 확대 배율이다.

    @doc: docs/design/Reader.md#4-데이터
    @doc: docs/design/Library.md#1-데이터-모델
    """

    __tablename__ = "reading_positions"

    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), primary_key=True)
    page: Mapped[int] = mapped_column(Integer)
    offset: Mapped[float] = mapped_column(Float)
    zoom: Mapped[float] = mapped_column(Float)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)


class Annotation(Base):
    """PDF 위의 주석 하나. 하이라이트(`highlight`) 또는 영역 메모(`note`)다.

    @doc: docs/design/Reader.md#4-데이터
    @doc: docs/design/Library.md#1-데이터-모델
    """

    __tablename__ = "annotations"

    id: Mapped[int] = mapped_column(primary_key=True)
    paper_id: Mapped[int] = mapped_column(ForeignKey("papers.id", ondelete="CASCADE"), index=True)
    kind: Mapped[str] = mapped_column(String)
    page: Mapped[int] = mapped_column(Integer)
    rects: Mapped[str] = mapped_column(Text)
    text: Mapped[str | None] = mapped_column(Text)
    color: Mapped[str] = mapped_column(String)
    note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_now)
