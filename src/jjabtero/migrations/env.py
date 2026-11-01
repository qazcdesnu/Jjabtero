"""Alembic 마이그레이션 환경.

@doc: docs/design/Library.md#3-스키마-변경
"""

from alembic import context

from jjabtero.db import create_db_engine, default_db_path
from jjabtero.models import Base

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """SQL 문을 출력하는 오프라인 모드로 마이그레이션한다.

    @doc: docs/design/Library.md#3-스키마-변경
    """
    context.configure(
        url=f"sqlite:///{default_db_path()}",
        target_metadata=target_metadata,
        literal_binds=True,
        render_as_batch=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """데이터베이스에 연결해 마이그레이션한다.

    @doc: docs/design/Library.md#3-스키마-변경
    """
    # upgrade_database가 연결을 넘기면 그것을 쓰고, Alembic 명령으로 실행하면 기본 경로에 연결한다.
    connection = context.config.attributes.get("connection")
    if connection is None:
        with create_db_engine(default_db_path()).connect() as own_connection:
            _run(own_connection)
            own_connection.commit()
    else:
        _run(connection)


def _run(connection) -> None:
    # SQLite는 ALTER TABLE이 약해 batch 모드로 테이블을 다시 만들어 바꾼다.
    context.configure(connection=connection, target_metadata=target_metadata, render_as_batch=True)
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
