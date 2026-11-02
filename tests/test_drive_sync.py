"""서재와 구글 드라이브의 동기화를 검증한다.

@doc: docs/design/DriveSync.md#9-테스트
"""

import time
from pathlib import Path

import pytest
from sqlalchemy import Engine
from sqlalchemy.orm import Session

from fakes import FakeDrive, write_client_secret
from jjabtero.db import create_db_engine, upgrade_database
from jjabtero.drive_sync import (
    DrivePaths,
    DriveSync,
    content_hash,
    restore_db,
    seed_token_from_env,
    snapshot_db,
)
from jjabtero.google_auth import DriveAuthError, Token, TokenStore
from jjabtero.library import PaperData, add_paper, list_papers


def computer(tmp_path: Path, name: str, drive: FakeDrive, connected: bool = True) -> DriveSync:
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
    return DriveSync(engine, paths, http=None, files_factory=lambda http, token: drive, push_delay=0.05)


def add(engine: Engine, title: str) -> None:
    """서재에 논문을 넣는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    with Session(engine) as session:
        add_paper(session, PaperData(title=title))


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
    """둘 다 바뀌면 충돌이고, 다시 동기화해도 덮어쓰지 않으며 자동 올리기도 하지 않는다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    b = computer(tmp_path, "b", drive)
    b.sync()
    add(a.engine, "A1")
    add(b.engine, "B1")
    b.sync()
    drive.calls.clear()
    assert a.sync().state == "conflict"
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


def test_remote_changed_just_before_upload_is_conflict(tmp_path: Path, drive: FakeDrive) -> None:
    """올리기 직전에 드라이브 내용이 바뀌었으면 올리지 않고 충돌로 바꾼다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    a = computer(tmp_path, "a", drive)
    a.sync()
    add(a.engine, "A1")
    original_get = drive.get
    calls = {"count": 0}

    def racing_get(file_id: str):
        calls["count"] += 1
        if calls["count"] == 3:
            drive.files[file_id]["data"] += b"changed elsewhere"
        return original_get(file_id)

    drive.get = racing_get
    assert a.sync().state == "conflict"
    assert "update" not in drive.calls


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

