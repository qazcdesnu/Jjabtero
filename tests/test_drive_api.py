"""드라이브 연결과 동기화 API를 검증한다.

@doc: docs/design/DriveSync.md#9-테스트
"""

import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx2
import pytest
from fastapi.testclient import TestClient

from fakes import FakeDrive, write_client_secret
from jjabtero.app import create_app
from jjabtero.drive_sync import DrivePaths
from jjabtero.google_auth import Token, TokenStore


def token_endpoint(request: httpx2.Request) -> httpx2.Response:
    """가짜 토큰 서버. 코드를 받으면 토큰을 준다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    return httpx2.Response(200, json={"access_token": "a1", "refresh_token": "r1", "expires_in": 3600})


def make_app(tmp_path: Path, drive: FakeDrive, configured: bool = True, connected: bool = False):
    """임시 경로와 가짜 드라이브를 쓰는 앱과 그 경로.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    paths = DrivePaths(tmp_path / "client.json", tmp_path / "token.json", tmp_path / "drive_sync.json", tmp_path / "backups")
    if configured:
        write_client_secret(paths.client_secret)
    if connected:
        TokenStore(paths.token).save(Token("a", "r", time.time() + 3600))
    app = create_app(
        frontend_dist=tmp_path / "missing",
        db_path=tmp_path / "library.db",
        http_client=httpx2.Client(transport=httpx2.MockTransport(token_endpoint)),
        drive_paths=paths,
        drive_files=lambda http, token: drive,
    )
    return TestClient(app, follow_redirects=False), paths


def start_connect(client: TestClient, return_to: str | None) -> str:
    """연결을 시작하고 동의 주소의 `state`를 돌려준다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    params = {"return_to": return_to} if return_to else {}
    response = client.get("/api/drive/connect", params=params)
    assert response.status_code == 302
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["redirect_uri"] == ["http://testserver/api/drive/callback"]
    return query["state"][0]


def test_status_not_configured_without_client(tmp_path: Path) -> None:
    """클라이언트 파일이 없으면 설정 안 됨이고 연결은 409다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    client, _ = make_app(tmp_path, FakeDrive(), configured=False)
    assert client.get("/api/drive/status").json()["state"] == "not_configured"
    assert client.get("/api/drive/connect").status_code == 409


def test_connect_and_callback_saves_token_syncs_and_returns(tmp_path: Path) -> None:
    """콜백이 토큰을 저장하고 동기화한 뒤 돌아갈 주소로 보낸다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    drive = FakeDrive()
    client, paths = make_app(tmp_path, drive)
    assert client.get("/api/drive/status").json()["state"] == "disconnected"
    state = start_connect(client, "http://localhost:5173/")
    response = client.get("/api/drive/callback", params={"state": state, "code": "c1"})
    assert response.status_code == 302 and response.headers["location"] == "http://localhost:5173/"
    assert TokenStore(paths.token).load().refresh_token == "r1"
    assert "create" in drive.calls
    assert client.get("/api/drive/status").json()["state"] == "idle"


@pytest.mark.parametrize("return_to", [None, "https://evil.example/", "http://localhost.evil.example/"])
def test_connect_rejects_non_local_return_to(tmp_path: Path, return_to: str | None) -> None:
    """돌아갈 주소가 로컬이 아니면 `/`로 돌아간다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    client, _ = make_app(tmp_path, FakeDrive())
    state = start_connect(client, return_to)
    response = client.get("/api/drive/callback", params={"state": state, "code": "c1"})
    assert response.headers["location"] == "/"


@pytest.mark.parametrize("params", [{"state": "unknown", "code": "c1"}, {"state": "x", "error": "access_denied"}])
def test_callback_rejects_unknown_state_or_error(tmp_path: Path, params: dict[str, str]) -> None:
    """모르는 `state`나 거부 응답은 400이다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    client, paths = make_app(tmp_path, FakeDrive())
    assert client.get("/api/drive/callback", params=params).status_code == 400
    assert TokenStore(paths.token).load() is None


def test_sync_resolve_and_disconnect(tmp_path: Path) -> None:
    """동기화, 충돌 풀기, 연결 해제가 상태를 돌려준다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    client, paths = make_app(tmp_path, FakeDrive(), connected=True)
    assert client.post("/api/drive/sync").json()["state"] == "idle"
    assert client.post("/api/drive/resolve", json={"choice": "remote"}).json()["state"] == "idle"
    assert client.post("/api/drive/resolve", json={"choice": "both"}).status_code == 422
    assert client.post("/api/drive/disconnect").json()["state"] == "disconnected"
    assert not paths.token.exists()


def test_paper_changes_schedule_push(tmp_path: Path) -> None:
    """논문을 넣고, 고치고, 지우면 자동 올리기를 예약한다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    client, _ = make_app(tmp_path, FakeDrive(), connected=True)
    client.post("/api/drive/sync")
    paper = client.post("/api/papers", json={"title": "A"}).json()
    assert client.get("/api/drive/status").json()["pending"] is True
    client.post("/api/drive/sync")
    assert client.get("/api/drive/status").json()["pending"] is False
    client.patch(f"/api/papers/{paper['id']}", json={"read_status": "read"})
    assert client.get("/api/drive/status").json()["pending"] is True
    client.post("/api/drive/sync")
    client.delete(f"/api/papers/{paper['id']}")
    assert client.get("/api/drive/status").json()["pending"] is True
    client.post("/api/drive/disconnect")


def test_create_app_waits_for_initial_sync_and_flushes_on_shutdown(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """서버 설정이면 시작할 때 드라이브 서재를 받아 두고, 끝날 때 대기 중인 변경을 올린다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    drive = FakeDrive()
    laptop_client, _ = make_app(tmp_path / "laptop", drive, connected=True)
    laptop_client.post("/api/drive/sync")
    laptop_client.post("/api/papers", json={"title": "from laptop"})
    laptop_client.post("/api/drive/sync")
    laptop_client.post("/api/drive/disconnect")

    monkeypatch.setenv("JJABTERO_GOOGLE_REFRESH_TOKEN", "r-env")
    monkeypatch.setenv("JJABTERO_INITIAL_SYNC", "wait")
    server_client, paths = make_app(tmp_path / "server", drive)
    assert TokenStore(paths.token).load().refresh_token == "r-env"
    with server_client:
        assert [paper["title"] for paper in server_client.get("/api/papers").json()] == ["from laptop"]
        server_client.post("/api/papers", json={"title": "from server"})
        assert server_client.get("/api/drive/status").json()["pending"] is True
        drive.calls.clear()
    assert drive.calls == ["update"]

