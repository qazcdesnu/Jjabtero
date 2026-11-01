"""논문 저장 함수를 검증한다.

@doc: docs/design/Library.md#5-테스트
"""

from collections.abc import Iterator
from pathlib import Path

import pytest
from pydantic import ValidationError
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from jjabtero.db import create_db_engine, upgrade_database
from jjabtero.library import (
    DuplicateDoiError,
    PaperData,
    PaperNotFoundError,
    add_paper,
    delete_paper,
    get_paper,
    list_papers,
    normalize_doi,
    update_paper,
)
from jjabtero.models import Author, Tag


@pytest.fixture
def session(tmp_path: Path) -> Iterator[Session]:
    """마이그레이션으로 올린 새 데이터베이스의 세션.

    @doc: docs/design/Library.md#5-테스트
    """
    engine = create_db_engine(tmp_path / "library.db")
    upgrade_database(engine)
    with Session(engine) as session:
        yield session


def test_add_and_get_paper(session: Session) -> None:
    """논문을 만들면 모든 항목이 저장되고 ID로 찾을 수 있다.

    @doc: docs/design/Library.md#5-테스트
    """
    paper = add_paper(
        session,
        PaperData(
            title="Attention Is All You Need",
            authors=["Ashish Vaswani", "Noam Shazeer"],
            item_type="conference-paper",
            year=2017,
            venue="NeurIPS",
            doi="10.48550/arXiv.1706.03762",
            url="https://arxiv.org/abs/1706.03762",
            tags=["transformer"],
        ),
    )
    found = get_paper(session, paper.id)
    assert found is not None
    assert found.title == "Attention Is All You Need"
    assert found.author_names == ["Ashish Vaswani", "Noam Shazeer"]
    assert found.item_type == "conference-paper"
    assert (found.year, found.venue) == (2017, "NeurIPS")
    assert found.doi == "10.48550/arxiv.1706.03762"
    assert found.url == "https://arxiv.org/abs/1706.03762"
    assert found.tag_names == ["transformer"]
    assert found.created_at is not None and found.updated_at is not None


def test_add_paper_with_title_only_uses_defaults(session: Session) -> None:
    """제목만 있어도 만들 수 있고, 항목 종류는 `other`다.

    @doc: docs/design/Library.md#5-테스트
    """
    paper = add_paper(session, PaperData(title="메모"))
    assert paper.item_type == "other"
    assert paper.author_names == [] and paper.tag_names == []
    assert paper.doi is None


def test_get_paper_missing_returns_none(session: Session) -> None:
    """없는 ID는 `None`이다.

    @doc: docs/design/Library.md#5-테스트
    """
    assert get_paper(session, 999) is None


def test_author_order_and_shared_rows(session: Session) -> None:
    """저자 순서를 지키고, 같은 이름의 저자와 태그는 논문 사이에서 공유한다.

    @doc: docs/design/Library.md#5-테스트
    """
    first = add_paper(session, PaperData(title="A", authors=["Kim", "Lee"], tags=["nlp"]))
    second = add_paper(session, PaperData(title="B", authors=["Lee", "Kim", "Lee"], tags=["nlp"]))
    assert first.author_names == ["Kim", "Lee"]
    assert second.author_names == ["Lee", "Kim", "Lee"]
    assert session.scalar(select(func.count()).select_from(Author)) == 2
    assert session.scalar(select(func.count()).select_from(Tag)) == 1


def test_list_papers_newest_first(session: Session) -> None:
    """최근에 만든 논문부터 돌려준다.

    @doc: docs/design/Library.md#5-테스트
    """
    add_paper(session, PaperData(title="old"))
    add_paper(session, PaperData(title="new"))
    assert [paper.title for paper in list_papers(session)] == ["new", "old"]


def test_list_papers_empty(session: Session) -> None:
    """논문이 없으면 빈 목록이다.

    @doc: docs/design/Library.md#5-테스트
    """
    assert list_papers(session) == []


def test_update_paper_replaces_all_fields(session: Session) -> None:
    """고치면 저자와 태그를 포함한 모든 항목이 입력대로 바뀌고 `updated_at`이 바뀐다.

    @doc: docs/design/Library.md#5-테스트
    """
    paper = add_paper(
        session, PaperData(title="Draft", authors=["A", "B"], year=2020, tags=["x", "y"])
    )
    before = paper.updated_at
    update_paper(session, paper.id, PaperData(title="Final", authors=["B", "C"], tags=["y"]))
    paper = get_paper(session, paper.id)
    assert paper is not None
    assert paper.title == "Final"
    assert paper.author_names == ["B", "C"]
    assert paper.tag_names == ["y"]
    assert paper.year is None
    assert paper.updated_at > before


def test_update_missing_paper_raises(session: Session) -> None:
    """없는 ID를 고치면 `PaperNotFoundError`다.

    @doc: docs/design/Library.md#5-테스트
    """
    with pytest.raises(PaperNotFoundError):
        update_paper(session, 999, PaperData(title="x"))


def test_delete_paper_keeps_authors_and_tags(session: Session) -> None:
    """지우면 논문은 사라지고 저자와 태그는 남는다.

    @doc: docs/design/Library.md#5-테스트
    """
    paper = add_paper(session, PaperData(title="A", authors=["Kim"], tags=["nlp"]))
    delete_paper(session, paper.id)
    assert get_paper(session, paper.id) is None
    assert session.scalar(select(func.count()).select_from(Author)) == 1
    assert session.scalar(select(func.count()).select_from(Tag)) == 1


def test_delete_missing_paper_raises(session: Session) -> None:
    """없는 ID를 지우면 `PaperNotFoundError`다.

    @doc: docs/design/Library.md#5-테스트
    """
    with pytest.raises(PaperNotFoundError):
        delete_paper(session, 999)


def test_duplicate_doi_is_rejected_on_add(session: Session) -> None:
    """표기만 다른 같은 DOI로 만들면 `DuplicateDoiError`이고 논문이 늘지 않는다.

    @doc: docs/design/Library.md#5-테스트
    """
    original = add_paper(session, PaperData(title="A", doi="10.1000/ABC"))
    with pytest.raises(DuplicateDoiError) as caught:
        add_paper(session, PaperData(title="B", doi="https://doi.org/10.1000/abc"))
    assert caught.value.paper_id == original.id
    assert len(list_papers(session)) == 1


def test_duplicate_doi_is_rejected_on_update(session: Session) -> None:
    """다른 논문의 DOI로 고치면 `DuplicateDoiError`이고, 자기 DOI는 그대로 둘 수 있다.

    @doc: docs/design/Library.md#5-테스트
    """
    add_paper(session, PaperData(title="A", doi="10.1000/a"))
    other = add_paper(session, PaperData(title="B", doi="10.1000/b"))
    with pytest.raises(DuplicateDoiError):
        update_paper(session, other.id, PaperData(title="B", doi="10.1000/a"))
    update_paper(session, other.id, PaperData(title="B2", doi="10.1000/b"))
    assert get_paper(session, other.id).doi == "10.1000/b"


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("10.1000/ABC", "10.1000/abc"),
        ("  https://doi.org/10.1000/x ", "10.1000/x"),
        ("http://dx.doi.org/10.1000/x", "10.1000/x"),
        ("doi:10.1000/x", "10.1000/x"),
    ],
)
def test_normalize_doi(raw: str, expected: str) -> None:
    """DOI의 앞부분과 대소문자를 정규화한다.

    @doc: docs/design/Library.md#5-테스트
    """
    assert normalize_doi(raw) == expected


def test_normalize_doi_rejects_non_doi() -> None:
    """`10.`으로 시작하지 않으면 오류다.

    @doc: docs/design/Library.md#5-테스트
    """
    with pytest.raises(ValueError):
        normalize_doi("https://example.com/paper")


def test_paper_data_cleans_input() -> None:
    """공백을 지우고, 빈 저자·태그를 버리고, 겹치는 태그는 하나만 남긴다.

    @doc: docs/design/Library.md#5-테스트
    """
    data = PaperData(
        title="  Title ",
        authors=[" Kim ", " ", "Lee"],
        tags=["nlp", " nlp ", ""],
        venue="  ",
        doi=" ",
    )
    assert data.title == "Title"
    assert data.authors == ["Kim", "Lee"]
    assert data.tags == ["nlp"]
    assert data.venue is None
    assert data.doi is None


@pytest.mark.parametrize(
    "fields",
    [{"title": "   "}, {"title": "x", "item_type": "blog"}, {"title": "x", "doi": "abc"}],
)
def test_paper_data_rejects_invalid(fields: dict[str, str]) -> None:
    """빈 제목, 알 수 없는 항목 종류, 잘못된 DOI는 검증 오류다.

    @doc: docs/design/Library.md#5-테스트
    """
    with pytest.raises(ValidationError):
        PaperData(**fields)
