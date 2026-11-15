"""서재 사본 세 개(기준, 이쪽, 드라이브)의 3방향 합치기.

드라이브 사본에서 출발해, 이쪽이 기준 이후 바꾼 것만 행·칸 단위로 적용한다. 합칠 수 없으면 `MergeConflict`다.

@doc: docs/design/DriveSync.md#10-자동-합치기
"""

import sqlite3
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError

from jjabtero.db import upgrade_database


class MergeConflict(Exception):
    """자동으로 합칠 수 없는 변경이 있다. 까닭을 담는다.

    @doc: docs/design/DriveSync.md#10-자동-합치기
    """


@dataclass(frozen=True)
class TableSpec:
    """표 하나를 합치는 규칙.

    `key`는 주 키 열, `natural`은 같은 것으로 볼 고유 열(이름, DOI), `renumber`는 겹치면 새 번호를 줄 수 있는
    정수 ID인지, `refs`는 다른 표의 ID를 가리키는 열, `clock`은 같은 칸을 양쪽이 고쳤을 때 늦은 쪽을 고를 시각 열이다.

    @doc: docs/design/DriveSync.md#10-자동-합치기
    """

    name: str
    key: tuple[str, ...]
    natural: str | None = None
    renumber: bool = False
    refs: dict[str, str] = field(default_factory=dict)
    clock: str | None = None


# 부모 표가 먼저 오도록 둔다. 자식 행의 ID를 바꿀 때 부모의 새 ID가 정해져 있어야 하기 때문이다.
# @doc: docs/design/DriveSync.md#10-자동-합치기
TABLES = (
    TableSpec("authors", ("id",), natural="name", renumber=True),
    TableSpec("tags", ("id",), natural="name", renumber=True),
    TableSpec("papers", ("id",), natural="doi", renumber=True, clock="updated_at"),
    TableSpec("paper_authors", ("paper_id", "position"), refs={"paper_id": "papers", "author_id": "authors"}),
    TableSpec("paper_tags", ("paper_id", "tag_id"), refs={"paper_id": "papers", "tag_id": "tags"}),
    TableSpec("settings", ("key",)),
    TableSpec("paper_pdfs", ("paper_id",), refs={"paper_id": "papers"}, clock="added_at"),
    TableSpec("reading_positions", ("paper_id",), refs={"paper_id": "papers"}, clock="updated_at"),
    TableSpec("annotations", ("id",), renumber=True, refs={"paper_id": "papers"}, clock="updated_at"),
)
_SKIP = {"alembic_version", "sqlite_sequence"}

Row = dict[str, Any]


def _rows(connection: sqlite3.Connection, spec: TableSpec) -> dict[tuple, Row]:
    cursor = connection.execute(f'SELECT * FROM "{spec.name}"')
    columns = [column[0] for column in cursor.description]
    rows = (dict(zip(columns, values, strict=True)) for values in cursor)
    return {tuple(row[key] for key in spec.key): row for row in rows}


def _tables(connection: sqlite3.Connection) -> set[str]:
    rows = connection.execute("SELECT name FROM sqlite_master WHERE type = 'table'")
    return {name for (name,) in rows if not name.startswith("sqlite_")}


def _quote(name: str) -> str:
    return f'"{name}"'


class _Result:
    """합친 결과(드라이브 사본에서 출발한 파일)에 쓰기."""

    def __init__(self, connection: sqlite3.Connection) -> None:
        self.connection = connection

    def get(self, spec: TableSpec, key: tuple) -> Row | None:
        where = " AND ".join(f"{_quote(column)} = ?" for column in spec.key)
        cursor = self.connection.execute(f"SELECT * FROM {_quote(spec.name)} WHERE {where}", key)
        values = cursor.fetchone()
        if values is None:
            return None
        return dict(zip([column[0] for column in cursor.description], values, strict=True))

    def find(self, spec: TableSpec, column: str, value: Any) -> Row | None:
        cursor = self.connection.execute(f"SELECT * FROM {_quote(spec.name)} WHERE {_quote(column)} = ?", (value,))
        values = cursor.fetchone()
        if values is None:
            return None
        return dict(zip([column[0] for column in cursor.description], values, strict=True))

    def put(self, spec: TableSpec, row: Row) -> None:
        # INSERT OR REPLACE는 기존 행을 지웠다 넣어, 외래 키의 ON DELETE CASCADE로 자식 행까지 지운다.
        # 그래서 있는 행은 UPDATE, 없는 행만 INSERT한다.
        key = tuple(row[column] for column in spec.key)
        try:
            if self.get(spec, key) is None:
                columns = ", ".join(_quote(column) for column in row)
                marks = ", ".join("?" for _ in row)
                self.connection.execute(f"INSERT INTO {_quote(spec.name)} ({columns}) VALUES ({marks})", list(row.values()))
            else:
                values = {column: value for column, value in row.items() if column not in spec.key}
                if not values:
                    return
                assignments = ", ".join(f"{_quote(column)} = ?" for column in values)
                where = " AND ".join(f"{_quote(column)} = ?" for column in spec.key)
                self.connection.execute(
                    f"UPDATE {_quote(spec.name)} SET {assignments} WHERE {where}", [*values.values(), *key]
                )
        except sqlite3.IntegrityError as error:
            raise MergeConflict(f"{spec.name}에 겹치는 값이 생깁니다: {error}") from error

    def delete(self, spec: TableSpec, key: tuple) -> None:
        where = " AND ".join(f"{_quote(column)} = ?" for column in spec.key)
        self.connection.execute(f"DELETE FROM {_quote(spec.name)} WHERE {where}", key)

    def max_id(self, spec: TableSpec) -> int:
        return self.connection.execute(f"SELECT COALESCE(MAX(id), 0) FROM {_quote(spec.name)}").fetchone()[0]


def _newer(left: Any, right: Any) -> bool:
    return str(left or "") > str(right or "")


def _merge_columns(spec: TableSpec, base: Row, local: Row, remote: Row) -> Row:
    """양쪽이 같은 행을 고쳤을 때 칸 단위로 합친다. 같은 칸을 다르게 고쳤으면 시각이 늦은 쪽을 쓴다."""
    merged = dict(remote)
    clashes = []
    for column, value in local.items():
        if value == base.get(column):
            continue
        if remote.get(column) == base.get(column) or remote.get(column) == value:
            merged[column] = value
        else:
            clashes.append(column)
    if clashes:
        if spec.clock is None:
            raise MergeConflict(f"{spec.name}의 같은 칸({', '.join(clashes)})을 양쪽에서 다르게 고쳤습니다.")
        if _newer(local.get(spec.clock), remote.get(spec.clock)):
            for column in clashes:
                merged[column] = local[column]
    return merged


def _merge_table(
    spec: TableSpec,
    base: dict[tuple, Row],
    local: dict[tuple, Row],
    remote: dict[tuple, Row],
    result: _Result,
    ids: dict[str, dict[Any, Any]],
) -> None:
    mapping = ids.setdefault(spec.name, {})

    def remap(row: Row) -> Row:
        mapped = dict(row)
        for column, parent in spec.refs.items():
            if mapped.get(column) is not None:
                mapped[column] = ids.get(parent, {}).get(mapped[column], mapped[column])
        return mapped

    next_id = 0
    if spec.renumber:
        used = [key[0] for key in (*base, *local, *remote) if isinstance(key[0], int)]
        next_id = max([result.max_id(spec), *used, 0]) + 1

    for key, row in local.items():
        if key in base:
            before = base[key]
            if row == before:
                continue
            current = remote.get(key)
            if current is None:
                raise MergeConflict(f"{spec.name}의 한 행을 이쪽은 고치고 드라이브는 지웠습니다.")
            changed = remap(row)
            result.put(spec, changed if current == before else _merge_columns(spec, before, changed, current))
            continue
        # 이쪽에서 새로 넣은 행
        changed = remap(row)
        if spec.natural and changed.get(spec.natural) is not None:
            same = result.find(spec, spec.natural, changed[spec.natural])
            if same is not None:
                # 드라이브에도 같은 이름·DOI가 있으면 그것과 잇는다.
                if spec.renumber:
                    mapping[row["id"]] = same["id"]
                if spec.clock and _newer(changed.get(spec.clock), same.get(spec.clock)):
                    result.put(spec, {**changed, **{column: same[column] for column in spec.key}})
                continue
        if spec.renumber:
            new_id = row["id"]
            if row["id"] in {key[0] for key in base} | {key[0] for key in remote}:
                new_id = next_id
                next_id += 1
            mapping[row["id"]] = new_id
            changed["id"] = new_id
            result.put(spec, changed)
            continue
        target = tuple(changed[column] for column in spec.key)
        existing = result.get(spec, target)
        if existing is None or existing == changed:
            result.put(spec, changed)
        elif target in remote and target not in base:
            # 양쪽이 같은 키로 새 행을 넣었다(예: 같은 논문의 읽던 위치).
            if spec.clock is None:
                raise MergeConflict(f"{spec.name}에 양쪽이 같은 키로 다른 행을 넣었습니다.")
            if _newer(changed.get(spec.clock), existing.get(spec.clock)):
                result.put(spec, changed)
        else:
            result.put(spec, changed)

    for key, before in base.items():
        if key in local:
            continue
        current = remote.get(key)
        if current is not None and current == before:
            result.delete(spec, key)
        # 드라이브가 고친 행은 이쪽이 지웠어도 남긴다. 지우는 쪽보다 고친 쪽을 지킨다.


def _open_upgraded(folder: Path, name: str, data: bytes) -> sqlite3.Connection:
    path = folder / name
    path.write_bytes(data)
    engine = create_engine(f"sqlite:///{path}")
    try:
        upgrade_database(engine)
    finally:
        engine.dispose()
    return sqlite3.connect(path)


def merge_libraries(base: bytes, local: bytes, remote: bytes) -> bytes:
    """기준, 이쪽, 드라이브 서재 사본을 합친 사본을 돌려준다. 합칠 수 없으면 `MergeConflict`를 낸다.

    사본이 깨져 열거나 읽을 수 없어도 `MergeConflict`다.

    @doc: docs/design/DriveSync.md#10-자동-합치기
    """
    try:
        return _merge(base, local, remote)
    except (sqlite3.DatabaseError, SQLAlchemyError) as error:
        raise MergeConflict(f"서재 사본을 열 수 없습니다: {error}") from error


def _merge(base: bytes, local: bytes, remote: bytes) -> bytes:
    """`merge_libraries`의 본체. 세 사본 모두 먼저 최신 스키마로 올린다. 기준 사본은 마지막 동기화 때의 것이라 스키마가 옛것일 수 있다.

    @doc: docs/design/DriveSync.md#10-자동-합치기
    """
    with tempfile.TemporaryDirectory() as folder_name:
        folder = Path(folder_name)
        base_db = _open_upgraded(folder, "base.db", base)
        local_db = _open_upgraded(folder, "local.db", local)
        remote_db = _open_upgraded(folder, "result.db", remote)
        try:
            known = {spec.name for spec in TABLES} | _SKIP
            for name in (_tables(base_db) | _tables(local_db)) - known:
                # 규칙이 없는 표는 이쪽이 바꾸지 않았을 때만 합친다.
                if name not in _tables(base_db) or name not in _tables(local_db):
                    raise MergeConflict(f"합치는 규칙이 없는 표({name})가 한쪽에만 있습니다.")
                query = f"SELECT * FROM {_quote(name)} ORDER BY 1"
                if list(base_db.execute(query)) != list(local_db.execute(query)):
                    raise MergeConflict(f"합치는 규칙이 없는 표({name})를 이쪽에서 바꿨습니다.")
            remote_db.execute("PRAGMA foreign_keys = ON")
            result = _Result(remote_db)
            ids: dict[str, dict[Any, Any]] = {}
            for spec in TABLES:
                if spec.name not in _tables(remote_db):
                    continue
                _merge_table(spec, _rows(base_db, spec), _rows(local_db, spec), _rows(remote_db, spec), result, ids)
            problems = remote_db.execute("PRAGMA foreign_key_check").fetchall()
            if problems:
                raise MergeConflict(f"합친 서재의 연결이 맞지 않습니다: {problems[:3]}")
            remote_db.commit()
            if remote_db.execute("PRAGMA integrity_check").fetchone() != ("ok",):
                raise MergeConflict("합친 서재가 깨졌습니다.")
        finally:
            base_db.close()
            local_db.close()
            remote_db.close()
        return (folder / "result.db").read_bytes()
