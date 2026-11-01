"""본인 전용 로그인을 검증한다.

@doc: docs/design/Auth.md#7-테스트
"""

from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx2
import pytest
from fastapi.testclient import TestClient

from fakes import FakeDrive, write_client_secret
from jjabtero.app import create_app
from jjabtero.auth import AuthConfigError, AuthSettings, auth_settings_from_env
from jjabtero.drive_sync import DrivePaths

SECRET = "x" * 40


def google(userinfo: dict) -> httpx2.Client:
    """토큰 교환과 사용자 정보 요청에 답하는 가짜 구글.

    @doc: docs/design/Auth.md#7-테스트
    """

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.host == "oauth2.googleapis.com":
            return httpx2.Response(200, json={"access_token": "a1", "expires_in": 3600})
        assert request.headers["Authorization"] == "Bearer a1"
        return httpx2.Response(200, json=userinfo)

    return httpx2.Client(transport=httpx2.MockTransport(handler))


def make_client(tmp_path: Path, settings: AuthSettings, userinfo: dict | None = None) -> TestClient:
    """임시 경로, 가짜 드라이브, 가짜 구글을 쓰는 앱의 테스트 클라이언트.

    @doc: docs/design/Auth.md#7-테스트
    """
    paths = DrivePaths(tmp_path / "client.json", tmp_path / "token.json", tmp_path / "state.json", tmp_path / "backups")
    write_client_secret(paths.client_secret)
    app = create_app(
        frontend_dist=tmp_path / "missing",
        db_path=tmp_path / "library.db",
        http_client=google(userinfo or {"email": "Me@Example.com", "email_verified": True}),
        drive_paths=paths,
        drive_files=lambda http, token: FakeDrive(),
        auth=settings,
    )
    return TestClient(app, follow_redirects=False)


@pytest.fixture
def enabled() -> AuthSettings:
    """로그인을 켠 설정.

    @doc: docs/design/Auth.md#7-테스트
    """
    return AuthSettings(allowed_email="me@example.com", session_secret=SECRET)


def log_in(client: TestClient, return_to: str = "/") -> httpx2.Response:
    """로그인 흐름을 끝까지 밟고 콜백 응답을 돌려준다.

    @doc: docs/design/Auth.md#7-테스트
    """
    response = client.get("/api/auth/login", params={"return_to": return_to})
    assert response.status_code == 302
    query = parse_qs(urlparse(response.headers["location"]).query)
    assert query["scope"] == ["openid email"] and query["prompt"] == ["select_account"]
    assert "access_type" not in query
    assert query["redirect_uri"] == ["http://testserver/api/auth/callback"]
    return client.get("/api/auth/callback", params={"state": query["state"][0], "code": "c1"})


def test_settings_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """환경 변수에서 읽고, 허용 이메일이 없으면 꺼진다.

    @doc: docs/design/Auth.md#7-테스트
    """
    assert auth_settings_from_env().enabled is False
    monkeypatch.setenv("JJABTERO_ALLOWED_EMAIL", " me@example.com ")
    monkeypatch.setenv("JJABTERO_SESSION_SECRET", SECRET)
    monkeypatch.setenv("JJABTERO_SECURE_COOKIE", "1")
    settings = auth_settings_from_env()
    assert (settings.enabled, settings.allowed_email, settings.secure_cookie) == (True, "me@example.com", True)


@pytest.mark.parametrize("secret", [None, "short"])
def test_enabled_without_strong_secret_fails(tmp_path: Path, secret: str | None) -> None:
    """로그인이 켜졌는데 서명 키가 없거나 짧으면 앱을 만들지 않는다.

    @doc: docs/design/Auth.md#7-테스트
    """
    with pytest.raises(AuthConfigError):
        make_client(tmp_path, AuthSettings(allowed_email="me@example.com", session_secret=secret))


def test_disabled_allows_api_and_hides_login(tmp_path: Path) -> None:
    """로그인이 꺼져 있으면 API가 그대로 열리고 로그인 경로는 404다.

    @doc: docs/design/Auth.md#7-테스트
    """
    client = make_client(tmp_path, AuthSettings())
    assert client.get("/api/auth/me").json() == {"enabled": False, "email": None}
    assert client.get("/api/papers").status_code == 200
    assert client.get("/api/auth/login").status_code == 404


def test_enabled_blocks_api_except_public(tmp_path: Path, enabled: AuthSettings) -> None:
    """로그인이 켜져 있으면 공개 예외 밖의 API는 401이다.

    @doc: docs/design/Auth.md#7-테스트
    """
    client = make_client(tmp_path, enabled)
    for path in ("/api/papers", "/api/drive/status", "/api/drive/callback"):
        response = client.get(path)
        assert response.status_code == 401 and response.json()["detail"] == "로그인이 필요합니다."
    assert client.get("/api/health").status_code == 200
    assert client.get("/api/auth/me").json() == {"enabled": True, "email": None}


def test_login_flow_allows_matching_email(tmp_path: Path, enabled: AuthSettings) -> None:
    """허용 이메일로 로그인하면 돌아갈 주소로 보내고 API가 열린다.

    @doc: docs/design/Auth.md#7-테스트
    """
    client = make_client(tmp_path, enabled)
    response = log_in(client, "/library?x=1")
    assert response.status_code == 302 and response.headers["location"] == "/library?x=1"
    assert client.get("/api/auth/me").json() == {"enabled": True, "email": "Me@Example.com"}
    assert client.get("/api/papers").status_code == 200


@pytest.mark.parametrize(
    "userinfo",
    [{"email": "other@example.com", "email_verified": True}, {"email": "me@example.com", "email_verified": False}],
)
def test_login_rejects_other_or_unverified_email(tmp_path: Path, enabled: AuthSettings, userinfo: dict) -> None:
    """다른 계정이나 확인되지 않은 이메일은 403이고 로그인되지 않는다.

    @doc: docs/design/Auth.md#7-테스트
    """
    client = make_client(tmp_path, enabled, userinfo)
    assert log_in(client).status_code == 403
    assert client.get("/api/papers").status_code == 401


@pytest.mark.parametrize("params", [{"state": "wrong", "code": "c1"}, {"error": "access_denied"}])
def test_callback_rejects_bad_state_or_error(tmp_path: Path, enabled: AuthSettings, params: dict) -> None:
    """`state`가 맞지 않거나 거부 응답이면 400이다.

    @doc: docs/design/Auth.md#7-테스트
    """
    client = make_client(tmp_path, enabled)
    client.get("/api/auth/login")
    assert client.get("/api/auth/callback", params=params).status_code == 400


@pytest.mark.parametrize("return_to", ["https://evil.example/", "//evil.example/", "/\\evil.example"])
def test_login_return_to_must_be_local_path(tmp_path: Path, enabled: AuthSettings, return_to: str) -> None:
    """돌아갈 주소가 같은 사이트 경로가 아니면 `/`로 돌아간다.

    @doc: docs/design/Auth.md#7-테스트
    """
    client = make_client(tmp_path, enabled)
    assert log_in(client, return_to).headers["location"] == "/"


def test_logout_clears_session(tmp_path: Path, enabled: AuthSettings) -> None:
    """로그아웃하면 다시 401이다.

    @doc: docs/design/Auth.md#7-테스트
    """
    client = make_client(tmp_path, enabled)
    log_in(client)
    assert client.post("/api/auth/logout").json() == {"enabled": True, "email": None}
    assert client.get("/api/papers").status_code == 401
