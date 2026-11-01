"""데이터베이스 파일과 연결을 검증한다.

@doc: docs/design/Library.md#5-테스트
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
