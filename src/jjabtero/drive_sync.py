"""서재 데이터베이스와 구글 드라이브의 동기화.

@doc: docs/design/DriveSync.md#5-동기화
@doc: docs/design/DriveSync.md#2-로컬-파일
@doc: docs/design/DriveSync.md#8-서버-환경
"""

import hashlib
import json
import os
import secrets
import sqlite3
import tempfile
import threading
from collections.abc import Callable
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal, Protocol

import httpx2
import platformdirs
from pydantic import BaseModel
from sqlalchemy import Engine, text

from jjabtero.db import upgrade_database
from jjabtero.drive import DriveApiError, DriveFiles, RemoteFile
from jjabtero.google_auth import (
    DriveAuthError,
    DriveNotConfiguredError,
    OAuthClient,
    Token,
    TokenStore,
    access_token,
    authorization_url,
    exchange_code,
    load_client,
    new_pkce_pair,
    write_private,
)

FOLDER_NAME = "Jjabtero"
FILE_NAME = "library.db"
PUSH_DELAY_SECONDS = 5.0


@dataclass(frozen=True)
class DrivePaths:
    """동기화가 쓰는 로컬 파일 경로.

    @doc: docs/design/DriveSync.md#2-로컬-파일
    """

    client_secret: Path
    token: Path
    state: Path
    backups: Path


def user_data_dir() -> Path:
    """사용자 데이터 폴더. 환경 변수 `JJABTERO_DATA_DIR`로 바꿀 수 있다.

    @doc: docs/design/DriveSync.md#2-로컬-파일
    """
    override = os.environ.get("JJABTERO_DATA_DIR")
    if override:
        return Path(override).expanduser()
    return platformdirs.user_data_path("Jjabtero", appauthor=False)


def default_drive_paths(db_path: Path) -> DrivePaths:
    """데이터베이스 경로에 맞춘 기본 경로를 만든다.

    @doc: docs/design/DriveSync.md#2-로컬-파일
    """
    data_dir = user_data_dir()
    client_override = os.environ.get("JJABTERO_GOOGLE_CLIENT_SECRET")
    return DrivePaths(
        client_secret=Path(client_override).expanduser()
        if client_override
        else data_dir / "google_client_secret.json",
        token=data_dir / "google_token.json",
        state=db_path.parent / "drive_sync.json",
        backups=db_path.parent / "backups",
    )


def seed_token_from_env(store: TokenStore) -> bool:
    """토큰 파일이 없고 `JJABTERO_GOOGLE_REFRESH_TOKEN`이 있으면 갱신 토큰만 든 토큰 파일을 만든다.

    @doc: docs/design/DriveSync.md#8-서버-환경
    """
    refresh = os.environ.get("JJABTERO_GOOGLE_REFRESH_TOKEN", "").strip()
    if not refresh or store.load() is not None:
        return False
    store.save(Token(access_token="", refresh_token=refresh, expires_at=0))
    return True


def snapshot_db(engine: Engine) -> bytes:
    """실행 중인 데이터베이스의 일관된 사본을 만든다.

    @doc: docs/design/DriveSync.md#5-동기화
    """
    with tempfile.TemporaryDirectory() as folder:
        copy_path = Path(folder) / "snapshot.db"
        raw = engine.raw_connection()
        try:
            copy = sqlite3.connect(copy_path)
            raw.driver_connection.backup(copy)
            copy.close()
        finally:
            raw.close()
        return copy_path.read_bytes()


def restore_db(engine: Engine, data: bytes) -> None:
    """받은 사본을 검사한 뒤 실행 중인 데이터베이스에 덮어쓴다.

    @doc: docs/design/DriveSync.md#5-동기화
    """
    with tempfile.TemporaryDirectory() as folder:
        copy_path = Path(folder) / "incoming.db"
        copy_path.write_bytes(data)
        try:
            source = sqlite3.connect(copy_path)
            result = source.execute("PRAGMA integrity_check").fetchone()
        except sqlite3.DatabaseError as error:
            raise ValueError(f"받은 서재 파일이 SQLite 데이터베이스가 아닙니다: {error}") from error
        if result != ("ok",):
            source.close()
            raise ValueError(f"받은 서재 파일이 깨졌습니다: {result}")
        raw = engine.raw_connection()
        try:
            source.backup(raw.driver_connection)
        finally:
            raw.close()
            source.close()
    engine.dispose()
    upgrade_database(engine)


def content_hash(engine: Engine) -> str:
    """데이터베이스 내용(SQL 덤프)의 해시를 만든다.

    @doc: docs/design/DriveSync.md#5-동기화
    """
    raw = engine.raw_connection()
    try:
        digest = hashlib.sha256()
        for line in raw.driver_connection.iterdump():
            digest.update(line.encode())
            digest.update(b"\n")
        return digest.hexdigest()
    finally:
        raw.close()


def _library_is_empty(engine: Engine) -> bool:
    with engine.connect() as connection:
        return connection.execute(text("SELECT COUNT(*) FROM papers")).scalar() == 0


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


@dataclass
class _State:
    folder_id: str
    file_id: str
    remote_checksum: str
    local_hash: str
    synced_at: str


class FilesLike(Protocol):
    """`DriveFiles`와 같은 모양의 드라이브 접근.

    @doc: docs/design/DriveSync.md#4-드라이브-파일
    """

    def find_folder(self, name: str) -> RemoteFile | None: ...
    def create_folder(self, name: str) -> RemoteFile: ...
    def find_file(self, folder_id: str, name: str) -> RemoteFile | None: ...
    def get(self, file_id: str) -> RemoteFile | None: ...
    def download(self, file_id: str) -> bytes: ...
    def create(self, folder_id: str, name: str, data: bytes) -> RemoteFile: ...
    def update(self, file_id: str, data: bytes) -> RemoteFile: ...


class SyncStatus(BaseModel):
    """동기화 상태.

    @doc: docs/design/DriveSync.md#5-동기화
    """

    state: Literal["not_configured", "disconnected", "idle", "syncing", "conflict", "error"]
    message: str = ""
    last_synced_at: str | None = None
    pending: bool = False
    data_version: int = 0


class DriveSync:
    """앱 하나의 드라이브 동기화.

    @doc: docs/design/DriveSync.md#5-동기화
    """

    def __init__(
        self,
        engine: Engine,
        paths: DrivePaths,
        http: httpx2.Client,
        files_factory: Callable[[httpx2.Client, Callable[[], str]], FilesLike] = DriveFiles,
        push_delay: float = PUSH_DELAY_SECONDS,
    ) -> None:
        self.engine = engine
        self.paths = paths
        self.http = http
        self.files_factory = files_factory
        self.push_delay = push_delay
        self.tokens = TokenStore(paths.token)
        self._lock = threading.Lock()
        self._timer: threading.Timer | None = None
        self._flows: dict[str, tuple[str, str, str]] = {}
        self._conflict: tuple[str, RemoteFile] | None = None
        self._busy = False
        self._error = ""
        self._data_version = 0

    # 인증

    def _client(self) -> OAuthClient:
        return load_client(self.paths.client_secret)

    def connect_url(self, redirect_uri: str, return_to: str) -> str:
        """동의 화면 주소를 만들고 이 연결 시도를 기억한다.

        @doc: docs/design/DriveSync.md#6-api
        """
        client = self._client()
        state = secrets.token_urlsafe(24)
        verifier, challenge = new_pkce_pair()
        self._flows[state] = (verifier, redirect_uri, return_to)
        return authorization_url(client, redirect_uri, state, challenge)

    def finish_connect(self, state: str, code: str) -> str:
        """인증 코드를 토큰으로 바꿔 저장하고 돌아갈 주소를 돌려준다.

        @doc: docs/design/DriveSync.md#6-api
        """
        flow = self._flows.pop(state, None)
        if flow is None:
            raise ValueError("알 수 없는 연결 요청입니다. 다시 연결하세요.")
        verifier, redirect_uri, return_to = flow
        token = exchange_code(self.http, self._client(), code, redirect_uri, verifier)
        self.tokens.save(token)
        self._error = ""
        return return_to

    def disconnect(self) -> SyncStatus:
        """토큰을 지운다. 동기화 상태 파일은 남긴다.

        @doc: docs/design/DriveSync.md#6-api
        """
        self._cancel_timer()
        self.tokens.clear()
        self._conflict = None
        self._error = ""
        return self.status()

    # 상태

    def _load_state(self) -> _State | None:
        try:
            return _State(**json.loads(self.paths.state.read_text()))
        except (FileNotFoundError, TypeError, ValueError):
            return None

    def _save_state(self, folder_id: str, remote: RemoteFile) -> None:
        state = _State(folder_id, remote.id, remote.checksum, content_hash(self.engine), _now())
        write_private(self.paths.state, json.dumps(asdict(state)))

    def status(self) -> SyncStatus:
        """현재 상태를 돌려준다.

        @doc: docs/design/DriveSync.md#5-동기화
        """
        saved = self._load_state()
        common = {
            "last_synced_at": saved.synced_at if saved else None,
            "pending": self._timer is not None,
            "data_version": self._data_version,
        }
        if not self.paths.client_secret.exists():
            return SyncStatus(
                state="not_configured",
                message=f"OAuth 클라이언트 파일이 없습니다: {self.paths.client_secret}",
                **common,
            )
        if self.tokens.load() is None:
            return SyncStatus(state="disconnected", message=self._error, **common)
        if self._busy:
            return SyncStatus(state="syncing", **common)
        if self._conflict is not None:
            return SyncStatus(
                state="conflict",
                message="이 컴퓨터와 드라이브의 서재가 둘 다 바뀌었습니다. 쓸 쪽을 고르세요.",
                **common,
            )
        if self._error:
            return SyncStatus(state="error", message=self._error, **common)
        return SyncStatus(state="idle", **common)

    def is_connected(self) -> bool:
        """클라이언트 파일과 토큰이 모두 있으면 참이다.

        @doc: docs/design/DriveSync.md#5-동기화
        """
        return self.paths.client_secret.exists() and self.tokens.load() is not None

    # 동기화

    def _files(self) -> FilesLike:
        client = self._client()
        return self.files_factory(self.http, lambda: access_token(self.http, client, self.tokens))

    def _run(self, action: Callable[[FilesLike], None]) -> SyncStatus:
        if not self.is_connected():
            return self.status()
        with self._lock:
            self._busy = True
            try:
                action(self._files())
                self._error = ""
            except DriveAuthError as error:
                self.tokens.clear()
                self._error = str(error)
            except (DriveNotConfiguredError, DriveApiError, httpx2.HTTPError, ValueError) as error:
                self._error = str(error) or type(error).__name__
            finally:
                self._busy = False
        return self.status()

    def _folder(self, files: FilesLike, saved: _State | None) -> str:
        if saved is not None and files.get(saved.folder_id) is not None:
            return saved.folder_id
        folder = files.find_folder(FOLDER_NAME) or files.create_folder(FOLDER_NAME)
        return folder.id

    def _download(self, files: FilesLike, folder_id: str, remote: RemoteFile) -> None:
        restore_db(self.engine, files.download(remote.id))
        self._save_state(folder_id, remote)
        self._data_version += 1

    def _backup(self, data: bytes, side: str) -> None:
        self.paths.backups.mkdir(parents=True, exist_ok=True)
        stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
        (self.paths.backups / f"library-{stamp}-{side}.db").write_bytes(data)

    def _sync_with(self, files: FilesLike) -> None:
        saved = self._load_state()
        folder_id = self._folder(files, saved)
        remote = files.get(saved.file_id) if saved is not None else None
        if remote is None:
            remote = files.find_file(folder_id, FILE_NAME)
        if remote is None:
            self._save_state(folder_id, files.create(folder_id, FILE_NAME, snapshot_db(self.engine)))
            return
        if saved is None or saved.file_id != remote.id:
            if _library_is_empty(self.engine):
                self._download(files, folder_id, remote)
            else:
                self._conflict = (folder_id, remote)
            return
        local_changed = content_hash(self.engine) != saved.local_hash
        remote_changed = remote.checksum != saved.remote_checksum
        if local_changed and remote_changed:
            self._conflict = (folder_id, remote)
        elif local_changed:
            current = files.get(remote.id)
            if current is None or current.checksum != remote.checksum:
                self._conflict = (folder_id, current or remote)
                return
            self._save_state(folder_id, files.update(remote.id, snapshot_db(self.engine)))
        elif remote_changed:
            self._download(files, folder_id, remote)

    def sync(self) -> SyncStatus:
        """로컬과 드라이브를 맞춘다. 충돌 중이면 아무것도 하지 않는다.

        @doc: docs/design/DriveSync.md#5-동기화
        """
        self._cancel_timer()
        if self._conflict is not None:
            return self.status()
        return self._run(self._sync_with)

    def resolve(self, choice: Literal["remote", "local"]) -> SyncStatus:
        """충돌을 고른 쪽으로 푼다. 버린 쪽은 백업한다.

        @doc: docs/design/DriveSync.md#5-동기화
        """
        conflict = self._conflict
        if conflict is None:
            return self.status()
        folder_id, remote = conflict

        def apply(files: FilesLike) -> None:
            current = files.get(remote.id) or remote
            if choice == "remote":
                self._backup(snapshot_db(self.engine), "local")
                self._download(files, folder_id, current)
            else:
                self._backup(files.download(current.id), "remote")
                self._save_state(folder_id, files.update(current.id, snapshot_db(self.engine)))
            self._conflict = None

        return self._run(apply)

    # 백그라운드

    def _cancel_timer(self) -> None:
        if self._timer is not None:
            self._timer.cancel()
            self._timer = None

    def schedule_push(self) -> None:
        """잠시 뒤 백그라운드에서 동기화하도록 예약한다. 다시 부르면 예약을 미룬다.

        @doc: docs/design/DriveSync.md#5-동기화
        """
        if not self.is_connected() or self._conflict is not None:
            return
        self._cancel_timer()
        timer = threading.Timer(self.push_delay, self.sync)
        timer.daemon = True
        self._timer = timer
        timer.start()

    def start(self, wait: bool = False) -> None:
        """연결되어 있으면 한 번 동기화한다. `wait`이면 끝날 때까지 기다리고, 아니면 백그라운드에서 한다.

        @doc: docs/design/DriveSync.md#5-동기화
        @doc: docs/design/DriveSync.md#8-서버-환경
        """
        if not self.is_connected():
            return
        if wait:
            self.sync()
        else:
            threading.Thread(target=self.sync, daemon=True).start()

    def flush(self) -> None:
        """대기 중인 자동 올리기가 있으면 예약을 취소하고 바로 동기화한다.

        @doc: docs/design/DriveSync.md#8-서버-환경
        """
        if self._timer is not None:
            self.sync()
