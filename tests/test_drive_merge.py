"""서재 사본 세 개의 3방향 합치기를 검증한다.

@doc: docs/design/DriveSync.md#9-테스트
"""

from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from jjabtero.db import _alembic_config, create_db_engine, upgrade_database
from jjabtero.drive_merge import MergeConflict, merge_libraries
from jjabtero.drive_sync import snapshot_db
from jjabtero.library import PaperData, add_paper, delete_paper, list_papers


class Copies:
    """기준 사본에서 갈라진 이쪽(local)과 드라이브(remote) 서재.

    @doc: docs/design/DriveSync.md#9-테스트
    """

    def __init__(self, tmp_path: Path, base: Engine) -> None:
        self.tmp_path = tmp_path
        self.base = snapshot_db(base)
        self.local = self._open("local")
        self.remote = self._open("remote")

    def _open(self, name: str) -> Engine:
        path = self.tmp_path / f"{name}.db"
        path.write_bytes(self.base)
        return create_db_engine(path)

    def merge(self) -> Engine:
        """합친 사본을 열어 돌려준다.

        @doc: docs/design/DriveSync.md#9-테스트
        """
        path = self.tmp_path / "merged.db"
        path.write_bytes(merge_libraries(self.base, snapshot_db(self.local), snapshot_db(self.remote)))
        return create_db_engine(path)


def library(tmp_path: Path, *papers: PaperData) -> Engine:
    """논문들이 든 기준 서재.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    engine = create_db_engine(tmp_path / "base.db")
    upgrade_database(engine)
    with Session(engine) as session:
        for paper in papers:
            add_paper(session, paper)
    return engine


def add(engine: Engine, **fields) -> int:
    """논문을 넣고 ID를 돌려준다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    with Session(engine) as session:
        return add_paper(session, PaperData(**fields)).id


def sql(engine: Engine, statement: str, **params) -> list:
    """SQL을 실행하고 결과 행을 돌려준다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    with engine.begin() as connection:
        result = connection.execute(text(statement), params)
        return list(result) if result.returns_rows else []


def papers(engine: Engine) -> dict[str, tuple[list[str], list[str]]]:
    """제목마다 (저자, 태그).

    @doc: docs/design/DriveSync.md#9-테스트
    """
    with Session(engine) as session:
        return {paper.title: (paper.author_names, paper.tag_names) for paper in list_papers(session)}


def test_both_added_papers_with_same_ids_keep_both_with_links(tmp_path: Path) -> None:
    """양쪽이 같은 ID로 다른 논문을 넣으면 이쪽 논문에 새 ID를 주고 저자·태그 연결도 옮긴다. 같은 이름의 저자·태그는 잇는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    copies = Copies(tmp_path, library(tmp_path, PaperData(title="Base", authors=["Kim"])))
    add(copies.local, title="Local", authors=["Lee", "Kim"], tags=["nlp"])
    add(copies.remote, title="Remote", authors=["Park", "Lee"], tags=["nlp", "cv"])
    merged = copies.merge()
    assert papers(merged) == {
        "Base": (["Kim"], []),
        "Local": (["Lee", "Kim"], ["nlp"]),
        "Remote": (["Park", "Lee"], ["cv", "nlp"]),
    }
    assert sql(merged, "SELECT COUNT(*) FROM authors")[0][0] == 3
    assert sql(merged, "SELECT COUNT(*) FROM tags")[0][0] == 2


def test_same_doi_added_on_both_sides_is_one_paper(tmp_path: Path) -> None:
    """양쪽이 같은 DOI의 논문을 넣으면 하나로 잇고, 이쪽에서 단 태그와 주석도 그 논문에 붙인다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    copies = Copies(tmp_path, library(tmp_path))
    add(copies.remote, title="Paper", doi="10.1/x")
    local_id = add(copies.local, title="Paper", doi="10.1/x", tags=["mine"])
    sql(
        copies.local,
        "INSERT INTO annotations (paper_id, kind, page, rects, color, created_at, updated_at) "
        "VALUES (:paper, 'highlight', 1, '[]', 'yellow', '2026-01-01', '2026-01-01')",
        paper=local_id,
    )
    merged = copies.merge()
    assert papers(merged) == {"Paper": ([], ["mine"])}
    remote_id = sql(merged, "SELECT id FROM papers")[0][0]
    assert sql(merged, "SELECT paper_id FROM annotations") == [(remote_id,)]


def test_different_columns_merge_and_same_column_takes_newer(tmp_path: Path) -> None:
    """같은 논문의 다른 칸을 고치면 둘 다 남고, 같은 칸을 고치면 수정 시각이 늦은 쪽을 쓴다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    copies = Copies(tmp_path, library(tmp_path, PaperData(title="A"), PaperData(title="B")))
    sql(copies.local, "UPDATE papers SET note = 'local note', updated_at = '2026-11-15 10:00' WHERE title = 'A'")
    sql(copies.remote, "UPDATE papers SET read_status = 'read', updated_at = '2026-11-15 09:00' WHERE title = 'A'")
    sql(copies.local, "UPDATE papers SET note = 'older', updated_at = '2026-11-15 08:00' WHERE title = 'B'")
    sql(copies.remote, "UPDATE papers SET note = 'newer', updated_at = '2026-11-15 11:00' WHERE title = 'B'")
    merged = copies.merge()
    rows = dict((title, (note, status)) for title, note, status in sql(merged, "SELECT title, note, read_status FROM papers"))
    assert rows == {"A": ("local note", "read"), "B": ("newer", "to-read")}


def test_deletes_apply_only_when_other_side_kept_row(tmp_path: Path) -> None:
    """이쪽에서 지운 논문은 드라이브가 그대로일 때만 지우고, 드라이브가 고쳤으면 남긴다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    copies = Copies(tmp_path, library(tmp_path, PaperData(title="Gone", tags=["t"]), PaperData(title="Kept")))
    with Session(copies.local) as session:
        for paper in list_papers(session):
            delete_paper(session, paper.id)
    sql(copies.remote, "UPDATE papers SET note = 'edited' WHERE title = 'Kept'")
    merged = copies.merge()
    assert list(papers(merged)) == ["Kept"]
    assert sql(merged, "SELECT COUNT(*) FROM paper_tags")[0][0] == 0


def test_local_edit_of_remote_deleted_row_is_conflict(tmp_path: Path) -> None:
    """이쪽이 고친 논문을 드라이브가 지웠으면 합치지 않는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    copies = Copies(tmp_path, library(tmp_path, PaperData(title="A")))
    sql(copies.local, "UPDATE papers SET note = 'x'")
    with Session(copies.remote) as session:
        delete_paper(session, list_papers(session)[0].id)
    with pytest.raises(MergeConflict):
        copies.merge()


def test_reading_position_and_annotations_from_both_sides(tmp_path: Path) -> None:
    """같은 논문의 읽던 위치는 늦은 쪽을, 양쪽이 같은 ID로 넣은 주석은 둘 다 남긴다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    copies = Copies(tmp_path, library(tmp_path, PaperData(title="A")))
    for engine, page, at in ((copies.local, 3, "2026-11-15 10:00"), (copies.remote, 7, "2026-11-15 09:00")):
        sql(engine, "INSERT INTO reading_positions VALUES (1, :page, 0.1, 1.0, :at)", page=page, at=at)
        sql(
            engine,
            "INSERT INTO annotations (paper_id, kind, page, rects, color, note, created_at, updated_at) "
            "VALUES (1, 'note', :page, '[]', 'yellow', :note, :at, :at)",
            page=page,
            note=f"p{page}",
            at=at,
        )
    merged = copies.merge()
    assert sql(merged, "SELECT page FROM reading_positions") == [(3,)]
    assert sorted(note for (note,) in sql(merged, "SELECT note FROM annotations")) == ["p3", "p7"]


def test_same_setting_changed_differently_is_conflict(tmp_path: Path) -> None:
    """시각이 없는 설정을 양쪽이 다르게 바꾸면 합치지 않고, 같게 바꾸었거나 한쪽만 바꾸면 합친다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    copies = Copies(tmp_path, library(tmp_path))
    sql(copies.local, "INSERT INTO settings VALUES ('citing_limit', '20')")
    sql(copies.remote, "INSERT INTO settings VALUES ('citing_limit', '50')")
    with pytest.raises(MergeConflict):
        copies.merge()
    sql(copies.remote, "UPDATE settings SET value = '20'")
    assert sql(copies.merge(), "SELECT value FROM settings") == [("20",)]


def test_base_with_old_schema_is_upgraded_before_merge(tmp_path: Path) -> None:
    """기준 사본이 옛 스키마여도 올린 뒤 합친다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    old = create_db_engine(tmp_path / "old.db")
    with old.begin() as connection:
        command.upgrade(_alembic_config(connection), "0002")
        connection.execute(
            text("INSERT INTO papers (id, title, item_type, created_at, updated_at) VALUES (1, 'Old', 'other', '2026-01-01', '2026-01-01')")
        )
    copies = Copies(tmp_path, old)
    upgrade_database(copies.local)
    upgrade_database(copies.remote)
    add(copies.local, title="L")
    add(copies.remote, title="R")
    assert sorted(papers(copies.merge())) == ["L", "Old", "R"]
