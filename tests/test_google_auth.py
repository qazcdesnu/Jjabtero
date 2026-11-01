"""구글 OAuth 인증을 검증한다.

@doc: docs/design/DriveSync.md#8-테스트
"""

import stat
import time
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import httpx2
import pytest

from fakes import write_client_secret
from jjabtero.google_auth import (
    DRIVE_SCOPE,
    DriveAuthError,
    DriveNotConfiguredError,
    Token,
    TokenStore,
    access_token,
    authorization_url,
    exchange_code,
    load_client,
    new_pkce_pair,
    refresh_token,
)


def token_server(responses: list[httpx2.Response], seen: list[dict] | None = None) -> httpx2.Client:
    """토큰 요청에 차례로 응답하는 가짜 서버의 클라이언트.

    @doc: docs/design/DriveSync.md#8-테스트
    """

    def handler(request: httpx2.Request) -> httpx2.Response:
        if seen is not None:
            seen.append({key: values[0] for key, values in parse_qs(request.content.decode()).items()})
        return responses.pop(0)

    return httpx2.Client(transport=httpx2.MockTransport(handler))


@pytest.fixture
def client(tmp_path: Path):
    """가짜 클라이언트 JSON에서 읽은 OAuth 클라이언트.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    write_client_secret(tmp_path / "client.json")
    return load_client(tmp_path / "client.json")


def test_load_client_reads_web_entry(client) -> None:
    """`web` 항목을 읽는다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    assert (client.client_id, client.client_secret) == ("client-1", "secret-1")
    assert client.token_uri == "https://oauth2.googleapis.com/token"


@pytest.mark.parametrize("content", [None, "{}", "not json", '{"installed": {}}'])
def test_load_client_rejects_missing_or_invalid(tmp_path: Path, content: str | None) -> None:
    """파일이 없거나 웹 애플리케이션 JSON이 아니면 `DriveNotConfiguredError`다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    path = tmp_path / "client.json"
    if content is not None:
        path.write_text(content)
    with pytest.raises(DriveNotConfiguredError):
        load_client(path)


def test_authorization_url_has_required_params(client) -> None:
    """동의 주소에 범위, 오프라인 접근, 상태, PKCE가 들어간다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    verifier, challenge = new_pkce_pair()
    assert verifier != challenge and len(verifier) >= 43
    url = urlparse(authorization_url(client, "http://127.0.0.1:8000/api/drive/callback", "st", challenge))
    params = {key: values[0] for key, values in parse_qs(url.query).items()}
    assert url.netloc == "accounts.google.com"
    assert params["scope"] == DRIVE_SCOPE
    assert params["access_type"] == "offline" and params["prompt"] == "consent"
    assert params["state"] == "st"
    assert params["code_challenge"] == challenge and params["code_challenge_method"] == "S256"
    assert params["redirect_uri"] == "http://127.0.0.1:8000/api/drive/callback"


def test_exchange_code_returns_token(client) -> None:
    """인증 코드를 보내 토큰을 받는다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    seen: list[dict] = []
    http = token_server(
        [httpx2.Response(200, json={"access_token": "a1", "refresh_token": "r1", "expires_in": 3600})], seen
    )
    token = exchange_code(http, client, "code-1", "http://x/cb", "verifier-1")
    assert (token.access_token, token.refresh_token) == ("a1", "r1")
    assert token.expires_at > time.time() + 3000
    assert seen[0]["grant_type"] == "authorization_code"
    assert seen[0]["code_verifier"] == "verifier-1"


def test_exchange_code_without_refresh_token_fails(client) -> None:
    """갱신 토큰이 없으면 `DriveAuthError`다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    http = token_server([httpx2.Response(200, json={"access_token": "a1", "expires_in": 3600})])
    with pytest.raises(DriveAuthError):
        exchange_code(http, client, "code-1", "http://x/cb", "v")


def test_refresh_keeps_old_refresh_token(client) -> None:
    """갱신 응답에 갱신 토큰이 없으면 전의 것을 쓴다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    http = token_server([httpx2.Response(200, json={"access_token": "a2", "expires_in": 3600})])
    token = refresh_token(http, client, Token("a1", "r1", 0))
    assert (token.access_token, token.refresh_token) == ("a2", "r1")


def test_token_store_saves_private_file(tmp_path: Path) -> None:
    """토큰 파일은 소유자만 읽고 쓰며, 지우면 없어진다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    store = TokenStore(tmp_path / "data" / "token.json")
    assert store.load() is None
    store.save(Token("a", "r", 1.0))
    assert store.load() == Token("a", "r", 1.0)
    assert stat.S_IMODE(store.path.stat().st_mode) == 0o600
    store.clear()
    assert store.load() is None


def test_access_token_uses_valid_token_without_request(client, tmp_path: Path) -> None:
    """만료가 멀면 요청 없이 저장된 토큰을 쓴다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    store = TokenStore(tmp_path / "token.json")
    store.save(Token("a1", "r1", time.time() + 3600))
    assert access_token(token_server([]), client, store) == "a1"


def test_access_token_refreshes_near_expiry(client, tmp_path: Path) -> None:
    """만료 60초 전부터는 갱신해 저장한다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    store = TokenStore(tmp_path / "token.json")
    store.save(Token("a1", "r1", time.time() + 30))
    http = token_server([httpx2.Response(200, json={"access_token": "a2", "expires_in": 3600})])
    assert access_token(http, client, store) == "a2"
    assert store.load().access_token == "a2"


def test_access_token_invalid_grant_clears_token(client, tmp_path: Path) -> None:
    """갱신이 `invalid_grant`면 토큰을 지우고 `DriveAuthError`다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    store = TokenStore(tmp_path / "token.json")
    store.save(Token("a1", "r1", 0))
    http = token_server([httpx2.Response(400, json={"error": "invalid_grant"})])
    with pytest.raises(DriveAuthError):
        access_token(http, client, store)
    assert store.load() is None


def test_access_token_without_token_fails(client, tmp_path: Path) -> None:
    """토큰이 없으면 `DriveAuthError`다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    with pytest.raises(DriveAuthError):
        access_token(token_server([]), client, TokenStore(tmp_path / "none.json"))
