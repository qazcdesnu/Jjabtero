"""데이터베이스 파일과 연결.

@doc: docs/design/Library.md#2-데이터베이스-파일과-연결
"""

import os
from pathlib import Path
from typing import Any

import platformdirs
from alembic import command
from alembic.config import Config
from sqlalchemy import Connection, Engine, URL, create_engine, event

_MIGRATIONS_DIR = Path(__file__).resolve().parent / "migrations"


def default_db_path() -> Path:
    """데이터베이스 파일 경로를 돌려준다.

    @doc: docs/design/Library.md#2-데이터베이스-파일과-연결
    """
    override = os.environ.get("JJABTERO_DB")
    if override:
        return Path(override).expanduser()
    return platformdirs.user_data_path("Jjabtero", appauthor=False) / "library.db"


def _enable_foreign_keys(dbapi_connection: Any, _record: Any) -> None:
    cursor = dbapi_connection.cursor()
    cursor.execute("PRAGMA foreign_keys=ON")
    cursor.close()


def create_db_engine(path: Path) -> Engine:
    """SQLite 엔진을 만든다.

    @doc: docs/design/Library.md#2-데이터베이스-파일과-연결
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    engine = create_engine(URL.create("sqlite", database=str(path)))
    event.listen(engine, "connect", _enable_foreign_keys)
    return engine


def _alembic_config(connection: Connection) -> Config:
    config = Config()
    config.set_main_option("script_location", str(_MIGRATIONS_DIR))
    config.attributes["connection"] = connection
    return config


def upgrade_database(engine: Engine) -> None:
    """데이터베이스를 최신 스키마로 올린다.

    @doc: docs/design/Library.md#2-데이터베이스-파일과-연결
    """
    with engine.begin() as connection:
        command.upgrade(_alembic_config(connection), "head")
