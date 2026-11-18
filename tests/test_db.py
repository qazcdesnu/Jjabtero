"""데이터베이스 파일과 연결을 검증한다.

@doc: docs/design/Library.md#5-테스트
@doc: docs/design/ReadingStatus.md#4-테스트
"""

from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import inspect, text

from jjabtero.db import _alembic_config, create_db_engine, default_db_path, upgrade_database

LIBRARY_TABLES = {"papers", "authors", "paper_authors", "tags", "paper_tags"}


def test_default_db_path_uses_env(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """환경 변수 `JJABTERO_DB`가 있으면 그 경로를 쓴다.

    @doc: docs/design/Library.md#5-테스트
    """
    monkeypatch.setenv("JJABTERO_DB", str(tmp_path / "my.db"))
    assert default_db_path() == tmp_path / "my.db"


def test_default_db_path_without_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """환경 변수가 없으면 사용자 데이터 폴더의 `Jjabtero/library.db`다.

    @doc: docs/design/Library.md#5-테스트
    """
    monkeypatch.delenv("JJABTERO_DB", raising=False)
    path = default_db_path()
    assert path.name == "library.db"
    assert path.parent.name == "Jjabtero"


def test_create_db_engine_makes_parent_dir(tmp_path: Path) -> None:
    """상위 폴더가 없으면 만든다.

    @doc: docs/design/Library.md#5-테스트
    """
    path = tmp_path / "nested" / "library.db"
    create_db_engine(path)
    assert path.parent.is_dir()


def test_upgrade_creates_tables_and_downgrade_removes(tmp_path: Path) -> None:
    """빈 데이터베이스를 올리면 서재 테이블이 생기고, 되돌리면 사라진다.

    @doc: docs/design/Library.md#5-테스트
    """
    engine = create_db_engine(tmp_path / "library.db")
    upgrade_database(engine)
    assert LIBRARY_TABLES <= set(inspect(engine).get_table_names())

    with engine.begin() as connection:
        command.downgrade(_alembic_config(connection), "base")
    assert not LIBRARY_TABLES & set(inspect(engine).get_table_names())


def test_upgrade_is_idempotent(tmp_path: Path) -> None:
    """이미 최신이면 다시 올려도 바뀌지 않는다.

    @doc: docs/design/Library.md#5-테스트
    """
    engine = create_db_engine(tmp_path / "library.db")
    upgrade_database(engine)
    upgrade_database(engine)
    assert LIBRARY_TABLES <= set(inspect(engine).get_table_names())


def test_foreign_keys_are_enforced(tmp_path: Path) -> None:
    """없는 논문을 가리키는 저자 연결은 거부된다.

    @doc: docs/design/Library.md#5-테스트
    """
    engine = create_db_engine(tmp_path / "library.db")
    upgrade_database(engine)
    with engine.connect() as connection:
        assert connection.execute(text("PRAGMA foreign_keys")).scalar() == 1
        connection.execute(text("INSERT INTO authors (id, name) VALUES (1, 'A')"))
        with pytest.raises(Exception, match="FOREIGN KEY"):
            connection.execute(
                text("INSERT INTO paper_authors (paper_id, position, author_id) VALUES (99, 0, 1)")
            )


def test_upgrade_0002_keeps_papers_and_sets_defaults(tmp_path: Path) -> None:
    """0001 상태의 논문은 0002로 올린 뒤 읽을 것, 메모 없음이 된다.

    @doc: docs/design/ReadingStatus.md#4-테스트
    """
    engine = create_db_engine(tmp_path / "library.db")
    with engine.begin() as connection:
        command.upgrade(_alembic_config(connection), "0001")
        connection.execute(
            text(
                "INSERT INTO papers (id, title, item_type, created_at, updated_at) "
                "VALUES (1, 'Old', 'other', '2026-01-01', '2026-01-01')"
            )
        )
    upgrade_database(engine)
    with engine.connect() as connection:
        row = connection.execute(text("SELECT title, read_status, note FROM papers")).one()
    assert tuple(row) == ("Old", "to-read", None)



def test_upgrade_0008_links_positions_and_annotations_to_pdf_versions(tmp_path: Path) -> None:
    """0007 상태의 PDF는 지금 판이 되고, 위치와 주석은 그 판과 이어진다. PDF 없는 논문의 위치는 지운다. 되돌리면 지금 판만 남는다.

    @doc: docs/design/PdfVersions.md#7-테스트
    """
    engine = create_db_engine(tmp_path / "library.db")
    with engine.begin() as connection:
        command.upgrade(_alembic_config(connection), "0007")
        for statement in (
            "INSERT INTO papers (id, title, item_type, created_at, updated_at) VALUES (1, 'A', 'other', '2026-01-01', '2026-01-01')",
            "INSERT INTO papers (id, title, item_type, created_at, updated_at) VALUES (2, 'B', 'other', '2026-01-01', '2026-01-01')",
            "INSERT INTO paper_pdfs (paper_id, sha256, size, source, added_at) VALUES (1, 'aaa', 1, 'upload', '2026-01-02')",
            'INSERT INTO reading_positions (paper_id, page, "offset", zoom, updated_at) VALUES (1, 3, 0.5, 1, \'2026-01-03\')',
            'INSERT INTO reading_positions (paper_id, page, "offset", zoom, updated_at) VALUES (2, 4, 0.5, 1, \'2026-01-03\')',
            "INSERT INTO annotations (paper_id, kind, page, rects, color, created_at, updated_at) "
            "VALUES (1, 'note', 1, '[]', 'yellow', '2026-01-03', '2026-01-03')",
        ):
            connection.execute(text(statement))
    upgrade_database(engine)
    with engine.begin() as connection:
        assert connection.execute(text("SELECT sha256, selected_at FROM paper_pdfs")).all() == [("aaa", "2026-01-02")]
        assert connection.execute(text("SELECT paper_id, pdf_sha256, page FROM reading_positions")).all() == [(1, "aaa", 3)]
        assert connection.execute(text("SELECT pdf_sha256 FROM annotations")).all() == [("aaa",)]
        connection.execute(
            text(
                "INSERT INTO paper_pdfs (paper_id, sha256, size, source, added_at, selected_at) "
                "VALUES (1, 'bbb', 1, 'upload', '2026-01-04', '2026-01-04')"
            )
        )
        connection.execute(
            text(
                'INSERT INTO reading_positions (paper_id, pdf_sha256, page, "offset", zoom, updated_at) '
                "VALUES (1, 'bbb', 9, 0.5, 1, '2026-01-04')"
            )
        )
        command.downgrade(_alembic_config(connection), "0007")
    with engine.connect() as connection:
        assert connection.execute(text("SELECT paper_id, sha256 FROM paper_pdfs")).all() == [(1, "bbb")]
        assert connection.execute(text("SELECT paper_id, page FROM reading_positions")).all() == [(1, 9)]
        assert connection.execute(text("SELECT count(*) FROM annotations")).scalar() == 0
