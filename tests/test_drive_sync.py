"""서재와 구글 드라이브의 동기화를 검증한다.

@doc: docs/design/DriveSync.md#9-테스트
"""

import time
from pathlib import Path

import pytest
from alembic import command
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session

from fakes import FakeDrive, write_client_secret
from jjabtero.db import _alembic_config, create_db_engine, upgrade_database
from jjabtero.drive_sync import (
    DrivePaths,
    DriveSync,
    content_hash,
    restore_db,
    seed_token_from_env,
    snapshot_db,
    upgrade_keeping_sync,
)
from jjabtero.google_auth import DriveAuthError, Token, TokenStore
from jjabtero.library import PaperData, add_paper, list_papers


def computer(
    tmp_path: Path, name: str, drive: FakeDrive, connected: bool = True, watch_interval: float = 0
) -> DriveSync:
    """임시 폴더에 서재 하나와 그 동기화를 만든다. 여러 개가 같은 가짜 드라이브를 쓸 수 있다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    folder = tmp_path / name
    engine = create_db_engine(folder / "library.db")
    upgrade_database(engine)
    paths = DrivePaths(folder / "client.json", folder / "token.json", folder / "drive_sync.json", folder / "backups")
    write_client_secret(paths.client_secret)
    if connected:
        TokenStore(paths.token).save(Token("a", "r", time.time() + 3600))
    return DriveSync(
        engine, paths, http=None, files_factory=lambda http, token: drive, push_delay=0.05, watch_interval=watch_interval
    )


def add(engine: Engine, title: str) -> None:
    """서재에 논문을 넣는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    with Session(engine) as session:
        add_paper(session, PaperData(title=title))


def clash(first: DriveSync, second: DriveSync) -> None:
    """두 서재에 자동으로 합칠 수 없는 변경(같은 설정을 다른 값으로)을 만든다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    for sync, value in ((first, "20"), (second, "50")):
        with sync.engine.begin() as connection:
            connection.execute(text("INSERT INTO settings (key, value) VALUES ('citing_limit', :value)"), {"value": value})


def titles(engine: Engine) -> list[str]:
    """서재 논문 제목을 이름순으로 돌려준다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    with Session(engine) as session:
        return sorted(paper.title for paper in list_papers(session))


@pytest.fixture
def drive() -> FakeDrive:
    """비어 있는 가짜 드라이브.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    return FakeDrive()


def test_first_sync_creates_folder_and_uploads(tmp_path: Path, drive: FakeDrive) -> None:
    """드라이브에 파일이 없으면 폴더를 만들고 로컬을 올린다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    add(a.engine, "A1")
    status = a.sync()
    assert status.state == "idle" and status.last_synced_at is not None
    assert drive.calls == ["create_folder", "create"]
    assert a.paths.state.exists()


def test_no_change_does_nothing(tmp_path: Path, drive: FakeDrive) -> None:
    """둘 다 안 바뀌었으면 올리거나 받지 않는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    drive.calls.clear()
    assert a.sync().state == "idle"
    assert drive.calls == []


def test_local_change_uploads(tmp_path: Path, drive: FakeDrive) -> None:
    """로컬만 바뀌면 올린다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    add(a.engine, "A1")
    drive.calls.clear()
    a.sync()
    assert drive.calls == ["update"]


def test_remote_change_downloads_on_other_computer(tmp_path: Path, drive: FakeDrive) -> None:
    """드라이브만 바뀌면 받아서 덮어쓰고 `data_version`을 올린다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    add(a.engine, "A1")
    a.sync()
    b = computer(tmp_path, "b", drive)
    assert b.sync().data_version == 1
    assert titles(b.engine) == ["A1"]
    add(b.engine, "B1")
    b.sync()
    status = a.sync()
    assert titles(a.engine) == ["A1", "B1"]
    assert status.state == "idle" and status.data_version == 1


def test_first_connect_with_local_papers_is_conflict(tmp_path: Path, drive: FakeDrive) -> None:
    """처음 연결하는 컴퓨터에 논문이 있고 드라이브에도 서재가 있으면 충돌이다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    add(a.engine, "A1")
    a.sync()
    b = computer(tmp_path, "b", drive)
    add(b.engine, "B1")
    assert b.sync().state == "conflict"
    assert titles(b.engine) == ["B1"]


def test_both_changed_is_conflict_and_nothing_overwritten(tmp_path: Path, drive: FakeDrive) -> None:
    """둘 다 바뀌었고 자동으로 합칠 수 없으면 충돌이고, 다시 동기화해도 덮어쓰지 않으며 자동 올리기도 하지 않는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    b = computer(tmp_path, "b", drive)
    b.sync()
    add(a.engine, "A1")
    add(b.engine, "B1")
    clash(a, b)
    b.sync()
    first = a.sync()
    assert first.state == "conflict" and "자동으로 합치지 못했습니다" in first.message
    drive.calls.clear()
    assert a.sync().state == "conflict"
    a.schedule_push()
    assert a.status().pending is False
    assert drive.calls == []
    assert titles(a.engine) == ["A1"]


def test_resolve_remote_backs_up_local(tmp_path: Path, drive: FakeDrive) -> None:
    """드라이브 것을 고르면 로컬을 백업하고 드라이브 것으로 바꾼다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    b = computer(tmp_path, "b", drive)
    b.sync()
    add(a.engine, "A1")
    add(b.engine, "B1")
    clash(a, b)
    b.sync()
    a.sync()
    status = a.resolve("remote")
    assert status.state == "idle"
    assert titles(a.engine) == ["B1"]
    backups = list(a.paths.backups.glob("library-*-local.db"))
    assert len(backups) == 1 and b"A1" in backups[0].read_bytes()
    assert a.sync().state == "idle"


def test_resolve_local_backs_up_remote(tmp_path: Path, drive: FakeDrive) -> None:
    """이 컴퓨터 것을 고르면 드라이브 사본을 백업하고 로컬을 올린다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    b = computer(tmp_path, "b", drive)
    b.sync()
    add(a.engine, "A1")
    add(b.engine, "B1")
    clash(a, b)
    b.sync()
    a.sync()
    assert a.resolve("local").state == "idle"
    assert list(a.paths.backups.glob("library-*-remote.db"))
    b.sync()
    assert titles(b.engine) == ["A1"]


def test_resolve_without_conflict_does_nothing(tmp_path: Path, drive: FakeDrive) -> None:
    """충돌이 아니면 아무것도 하지 않는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    drive.calls.clear()
    assert a.resolve("local").state == "idle"
    assert drive.calls == []


def test_remote_changed_just_before_upload_is_merged(tmp_path: Path, drive: FakeDrive) -> None:
    """올리기 직전에 다른 컴퓨터가 올렸으면 덮어쓰지 않고 합친다. 두 컴퓨터의 논문이 모두 남는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    b = computer(tmp_path, "b", drive)
    b.sync()
    add(a.engine, "A1")
    add(b.engine, "B1")
    original_get = drive.get
    calls = {"count": 0}

    def racing_get(file_id: str):
        calls["count"] += 1
        if calls["count"] == 3:
            drive.files[file_id]["data"] = snapshot_db(b.engine)
        return original_get(file_id)

    drive.get = racing_get  # type: ignore[method-assign]
    assert a.sync().state == "idle"
    drive.get = original_get  # type: ignore[method-assign]
    assert titles(a.engine) == ["A1", "B1"]
    c = computer(tmp_path, "c", drive)
    c.sync()
    assert titles(c.engine) == ["A1", "B1"]


def test_broken_remote_copy_is_conflict(tmp_path: Path, drive: FakeDrive) -> None:
    """둘 다 바뀌었는데 드라이브 사본이 깨져 합칠 수 없으면 충돌이고, 아무것도 올리지 않는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    add(a.engine, "A1")
    file_id = a._load_state().file_id
    drive.files[file_id]["data"] = b"not a database"
    drive.calls.clear()
    status = a.sync()
    assert status.state == "conflict" and "자동으로 합치지 못했습니다" in status.message
    assert "update" not in drive.calls
    assert titles(a.engine) == ["A1"]


def test_trashed_remote_file_is_uploaded_again(tmp_path: Path, drive: FakeDrive) -> None:
    """드라이브 파일이 휴지통으로 가면 새로 올린다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    for item in drive.files.values():
        if not item["folder"]:
            item["trashed"] = True
    drive.calls.clear()
    assert a.sync().state == "idle"
    assert drive.calls == ["create"]


def test_snapshot_and_restore_keep_content(tmp_path: Path) -> None:
    """사본을 되살리면 내용 해시가 같다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    source = create_db_engine(tmp_path / "s.db")
    upgrade_database(source)
    add(source, "X")
    target = create_db_engine(tmp_path / "t.db")
    upgrade_database(target)
    restore_db(target, snapshot_db(source))
    assert content_hash(target) == content_hash(source)
    assert titles(target) == ["X"]


def test_restore_rejects_broken_data(tmp_path: Path, drive: FakeDrive) -> None:
    """SQLite가 아닌 사본은 거부하고 로컬을 그대로 두며, 동기화는 오류가 된다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    add(a.engine, "A1")
    with pytest.raises(ValueError):
        restore_db(a.engine, b"not a database at all" * 100)
    assert titles(a.engine) == ["A1"]
    a.sync()
    b = computer(tmp_path, "b", drive)
    for item in drive.files.values():
        if not item["folder"]:
            item["data"] = b"garbage" * 100
    status = b.sync()
    assert status.state == "error" and status.message


def test_status_not_configured_and_disconnected(tmp_path: Path, drive: FakeDrive) -> None:
    """클라이언트 파일이 없으면 설정 안 됨, 토큰이 없으면 연결 안 됨이고, 동기화하지 않는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive, connected=False)
    assert a.sync().state == "disconnected"
    a.paths.client_secret.unlink()
    assert a.status().state == "not_configured"
    assert drive.calls == []


def test_auth_error_disconnects(tmp_path: Path) -> None:
    """인증 오류가 나면 토큰을 지우고 연결 안 됨으로 알린다.

    @doc: docs/design/DriveSync.md#9-테스트
    """

    class Revoked(FakeDrive):
        def find_folder(self, name: str):
            raise DriveAuthError("드라이브 연결이 만료되었거나 취소되었습니다. 다시 연결하세요.")

    a = computer(tmp_path, "a", Revoked())
    status = a.sync()
    assert status.state == "disconnected" and "다시 연결" in status.message
    assert not a.paths.token.exists()


def test_schedule_push_uploads_after_delay(tmp_path: Path, drive: FakeDrive) -> None:
    """예약하면 잠시 뒤 백그라운드에서 올린다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    add(a.engine, "A1")
    a.schedule_push()
    assert a.status().pending is True
    deadline = time.time() + 3
    while "update" not in drive.calls and time.time() < deadline:
        time.sleep(0.02)
    assert "update" in drive.calls
    assert a.status().pending is False


def test_disconnect_clears_token_keeps_state(tmp_path: Path, drive: FakeDrive) -> None:
    """연결을 끊으면 토큰만 지운다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    assert a.disconnect().state == "disconnected"
    assert a.paths.state.exists() and not a.paths.token.exists()


def test_remote_metadata_change_without_content_change_is_not_conflict(tmp_path: Path, drive: FakeDrive) -> None:
    """드라이브 내용이 그대로면(버전 번호만 바뀐 경우) 로컬 변경은 그냥 올린다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    add(a.engine, "A1")
    drive.calls.clear()
    assert a.sync().state == "idle"
    assert drive.calls == ["update"]


def test_seed_token_from_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """환경 변수의 갱신 토큰으로 토큰 파일을 만들되, 이미 있으면 건드리지 않는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    store = TokenStore(tmp_path / "token.json")
    assert seed_token_from_env(store) is False
    monkeypatch.setenv("JJABTERO_GOOGLE_REFRESH_TOKEN", " r-env ")
    assert seed_token_from_env(store) is True
    assert store.load() == Token("", "r-env", 0)
    store.save(Token("a", "r-file", 1))
    assert seed_token_from_env(store) is False
    assert store.load().refresh_token == "r-file"


def test_start_wait_downloads_into_empty_server(tmp_path: Path, drive: FakeDrive) -> None:
    """빈 서버가 기다려 동기화하면, 돌아올 때 이미 드라이브 서재를 받아 두었다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    laptop = computer(tmp_path, "laptop", drive)
    add(laptop.engine, "A1")
    laptop.sync()
    server = computer(tmp_path, "server", drive)
    server.start(wait=True)
    assert titles(server.engine) == ["A1"]
    assert server.status().state == "idle"


def test_flush_pushes_pending_change_now(tmp_path: Path, drive: FakeDrive) -> None:
    """대기 중인 올리기가 있으면 바로 올리고, 없으면 아무것도 하지 않는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    drive.calls.clear()
    a.flush()
    assert drive.calls == []
    a.push_delay = 60
    add(a.engine, "A1")
    a.schedule_push()
    a.flush()
    assert drive.calls == ["update"]
    assert a.status().pending is False


def old_computer(tmp_path: Path, name: str, drive: FakeDrive) -> DriveSync:
    """스키마 0002(옛 버전 앱)에 논문 하나가 든 서재와 그 동기화.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    folder = tmp_path / name
    engine = create_db_engine(folder / "library.db")
    with engine.begin() as connection:
        command.upgrade(_alembic_config(connection), "0002")
        connection.execute(
            text("INSERT INTO papers (id, title, item_type, created_at, updated_at) VALUES (1, 'Old', 'other', '2026-01-01', '2026-01-01')")
        )
    paths = DrivePaths(folder / "client.json", folder / "token.json", folder / "drive_sync.json", folder / "backups")
    write_client_secret(paths.client_secret)
    TokenStore(paths.token).save(Token("a", "r", time.time() + 3600))
    return DriveSync(engine, paths, http=None, files_factory=lambda http, token: drive, push_delay=0.05, watch_interval=0)


def test_schema_upgrade_is_not_counted_as_local_change(tmp_path: Path, drive: FakeDrive) -> None:
    """새 버전 앱이 스키마를 올려도 서재가 마지막 동기화 때와 같았으면 로컬 변경으로 세지 않아, 드라이브 변경을 받는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    old = old_computer(tmp_path, "old", drive)
    assert old.sync().state == "idle"
    web = computer(tmp_path, "web", drive)
    web.sync()
    add(web.engine, "Added on web")
    web.sync()

    assert upgrade_keeping_sync(old.engine, old.paths.state) is True
    status = old.sync()
    assert status.state == "idle"
    assert titles(old.engine) == ["Added on web", "Old"]


def test_plain_schema_upgrade_is_merged(tmp_path: Path, drive: FakeDrive) -> None:
    """상태를 이어받지 않고 스키마만 올려 둘 다 바뀐 것으로 보여도, 기준 사본으로 합쳐 충돌하지 않는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    old = old_computer(tmp_path, "old", drive)
    old.sync()
    web = computer(tmp_path, "web", drive)
    web.sync()
    add(web.engine, "Added on web")
    web.sync()
    upgrade_database(old.engine)
    assert old.sync().state == "idle"
    assert titles(old.engine) == ["Added on web", "Old"]


def test_upgrade_keeping_sync_leaves_real_local_change(tmp_path: Path, drive: FakeDrive) -> None:
    """스키마를 올리기 전에 이미 바뀐 서재는 그대로 로컬 변경으로 남는다. 상태 파일이 없어도 스키마는 올린다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    old = old_computer(tmp_path, "old", drive)
    old.sync()
    saved = old.paths.state.read_text()
    with old.engine.begin() as connection:
        connection.execute(text("UPDATE papers SET title = 'Edited' WHERE id = 1"))
    assert upgrade_keeping_sync(old.engine, old.paths.state) is False
    assert old.paths.state.read_text() == saved
    fresh = create_db_engine(tmp_path / "fresh" / "library.db")
    assert upgrade_keeping_sync(fresh, tmp_path / "fresh" / "drive_sync.json") is False
    with fresh.connect() as connection:
        assert connection.execute(text("SELECT COUNT(*) FROM papers")).scalar() == 0


def test_check_reads_only_metadata_and_downloads_remote_change(tmp_path: Path, drive: FakeDrive) -> None:
    """확인은 드라이브가 그대로면 아무것도 하지 않고, 바뀌었으면 받는다. 이쪽 변경은 올리지 않는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    add(a.engine, "A1")
    a.sync()
    b = computer(tmp_path, "b", drive)
    b.sync()
    before = b.status().data_version
    assert b.check().data_version == before
    add(a.engine, "A2")
    a.sync()
    assert b.check().data_version == before + 1
    assert titles(b.engine) == ["A1", "A2"]
    add(b.engine, "B1")
    remote = drive.files[b._load_state().file_id]["data"]
    b.check()
    assert drive.files[b._load_state().file_id]["data"] == remote


def test_ensure_fresh_checks_at_most_every_30_seconds(tmp_path: Path, drive: FakeDrive) -> None:
    """쓰기 앞의 확인은 마지막 확인이 30초보다 오래되었을 때만 한다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    now = [1000.0]
    a = computer(tmp_path, "a", drive)
    a.sync()
    a.clock = lambda: now[0]
    a._checked_at = None
    calls = []
    original = a.check
    a.check = lambda: calls.append(now[0]) or original()  # type: ignore[method-assign]
    a.ensure_fresh()
    now[0] += 10
    a.ensure_fresh()
    now[0] += 25
    a.ensure_fresh()
    assert calls == [1000.0, 1035.0]


def test_write_after_ensure_fresh_does_not_conflict(tmp_path: Path, drive: FakeDrive) -> None:
    """다른 곳이 올린 변경을 쓰기 전에 받으면, 이쪽 쓰기를 올려도 충돌이 아니다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    computer_a = computer(tmp_path, "a", drive)
    add(computer_a.engine, "First")
    computer_a.sync()
    server = computer(tmp_path, "server", drive)
    server.sync()
    add(server.engine, "Added on web")
    server.sync()
    computer_a._checked_at = None
    computer_a.ensure_fresh()
    add(computer_a.engine, "Added here")
    assert computer_a.sync().state == "idle"
    assert server.check().state == "idle"
    assert titles(server.engine) == ["Added here", "Added on web", "First"]


def test_watcher_downloads_remote_change_without_action(tmp_path: Path, drive: FakeDrive) -> None:
    """확인 스레드가 주기적으로 드라이브를 보아, 아무것도 하지 않아도 다른 곳의 변경을 받는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    add(a.engine, "A1")
    a.sync()
    b = computer(tmp_path, "b", drive, watch_interval=0.05)
    b.start(wait=True)
    add(a.engine, "A2")
    a.sync()
    deadline = time.time() + 3
    while titles(b.engine) != ["A1", "A2"] and time.time() < deadline:
        time.sleep(0.05)
    b.stop()
    assert titles(b.engine) == ["A1", "A2"]



def test_write_during_upload_is_pushed_next_time(tmp_path: Path, drive: FakeDrive) -> None:
    """올리는 도중에 들어온 쓰기는 올린 것으로 적지 않아, 다음 동기화 때 올라간다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    add(a.engine, "A1")
    a.sync()
    original = drive.update

    def slow_update(file_id: str, data: bytes):
        add(a.engine, "During upload")
        return original(file_id, data)

    drive.update = slow_update  # type: ignore[method-assign]
    add(a.engine, "A2")
    a.sync()
    drive.update = original  # type: ignore[method-assign]
    assert a.sync().state == "idle"
    b = computer(tmp_path, "b", drive)
    b.sync()
    assert titles(b.engine) == ["A1", "A2", "During upload"]


def test_download_records_hash_of_restored_copy(tmp_path: Path, drive: FakeDrive) -> None:
    """받은 뒤 적는 해시는 덮어쓴 서재와 같아, 바로 다음 동기화에서 로컬 변경이 아니다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    add(a.engine, "A1")
    a.sync()
    b = computer(tmp_path, "b", drive)
    b.sync()
    assert content_hash(b.engine) == b._load_state().local_hash


def test_both_changed_is_merged_with_backups(tmp_path: Path, drive: FakeDrive) -> None:
    """두 컴퓨터가 각자 논문을 넣으면 자동으로 합쳐 둘 다 남기고, 합치기 전 양쪽 사본을 백업하며 기준 사본을 바꾼다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    add(a.engine, "Base")
    a.sync()
    b = computer(tmp_path, "b", drive)
    b.sync()
    add(a.engine, "A1")
    add(b.engine, "B1")
    b.sync()
    before = a.status().data_version
    status = a.sync()
    assert status.state == "idle" and status.data_version == before + 1
    assert titles(a.engine) == ["A1", "B1", "Base"]
    assert {path.name.rsplit("-", 2)[-2] + "-" + path.name.rsplit("-", 1)[-1] for path in a.paths.backups.glob("*.db")} == {
        "merge-local.db",
        "merge-remote.db",
    }
    assert a.paths.base.read_bytes() == drive.files[a._load_state().file_id]["data"]
    assert b.check().state == "idle"
    assert titles(b.engine) == ["A1", "B1", "Base"]


def test_without_base_copy_is_conflict(tmp_path: Path, drive: FakeDrive) -> None:
    """기준 사본이 없으면(예: 이 기능 이전의 동기화) 합치지 않고 충돌로 둔다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    b = computer(tmp_path, "b", drive)
    b.sync()
    add(a.engine, "A1")
    add(b.engine, "B1")
    b.sync()
    a.paths.base.unlink()
    status = a.sync()
    assert status.state == "conflict" and "기준 사본이 없어" in status.message


def test_local_write_during_merge_is_not_overwritten(tmp_path: Path, drive: FakeDrive) -> None:
    """합치는 사이 이쪽에 쓰기가 들어오면 덮어쓰지 않고, 다음 동기화에서 그것까지 합친다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    b = computer(tmp_path, "b", drive)
    b.sync()
    add(a.engine, "A1")
    add(b.engine, "B1")
    b.sync()
    original = drive.download
    state = {"done": False}

    def download_with_write(file_id: str) -> bytes:
        data = original(file_id)
        if not state["done"]:
            state["done"] = True
            add(a.engine, "During merge")
        return data

    drive.download = download_with_write  # type: ignore[method-assign]
    assert a.sync().state == "idle"
    assert titles(a.engine) == ["A1", "During merge"]
    drive.download = original  # type: ignore[method-assign]
    assert a.sync().state == "idle"
    assert titles(a.engine) == ["A1", "B1", "During merge"]


def test_merge_backups_are_pruned(tmp_path: Path, drive: FakeDrive) -> None:
    """합치기 백업은 가장 최근 20개만 남긴다. 충돌 풀기 백업은 지우지 않는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.paths.backups.mkdir(parents=True)
    for index in range(25):
        (a.paths.backups / f"library-20260101-{index:06d}-merge-local.db").write_bytes(b"x")
    (a.paths.backups / "library-20250101-000000-local.db").write_bytes(b"x")
    a._prune_merge_backups()
    kept = sorted(path.name for path in a.paths.backups.glob("*merge*"))
    assert len(kept) == 20 and kept[0] == "library-20260101-000005-merge-local.db"
    assert (a.paths.backups / "library-20250101-000000-local.db").exists()
