"""구글 OAuth 2.0 인증.

@doc: docs/design/DriveSync.md#3-인증
"""

import base64
import hashlib
import json
import os
import secrets
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import urlencode

import httpx2

DRIVE_SCOPE = "https://www.googleapis.com/auth/drive.file"
_REFRESH_MARGIN_SECONDS = 60


class DriveNotConfiguredError(Exception):
    """OAuth 클라이언트 파일이 없거나 형식이 맞지 않는다.

    @doc: docs/design/DriveSync.md#3-인증
    """


class DriveAuthError(Exception):
    """드라이브에 연결되어 있지 않거나 연결이 취소되었다.

    @doc: docs/design/DriveSync.md#3-인증
    """


@dataclass(frozen=True)
class OAuthClient:
    """OAuth 웹 애플리케이션 클라이언트.

    @doc: docs/design/DriveSync.md#3-인증
    """

    client_id: str
    client_secret: str
    auth_uri: str
    token_uri: str
    redirect_uris: tuple[str, ...]


@dataclass(frozen=True)
class Token:
    """접근 토큰과 갱신 토큰.

    @doc: docs/design/DriveSync.md#3-인증
    """

    access_token: str
    refresh_token: str
    expires_at: float


def load_client(path: Path) -> OAuthClient:
    """클라이언트 JSON을 읽는다.

    @doc: docs/design/DriveSync.md#3-인증
    """
    try:
        web = json.loads(path.read_text())["web"]
        return OAuthClient(
            client_id=web["client_id"],
            client_secret=web["client_secret"],
            auth_uri=web["auth_uri"],
            token_uri=web["token_uri"],
            redirect_uris=tuple(web.get("redirect_uris", [])),
        )
    except FileNotFoundError as error:
        raise DriveNotConfiguredError(f"OAuth 클라이언트 파일이 없습니다: {path}") from error
    except (KeyError, TypeError, ValueError) as error:
        raise DriveNotConfiguredError(f"웹 애플리케이션 클라이언트 JSON이 아닙니다: {path}") from error


def new_pkce_pair() -> tuple[str, str]:
    """PKCE 검증 값과 그 S256 도전 값을 만든다.

    @doc: docs/design/DriveSync.md#3-인증
    """
    verifier = secrets.token_urlsafe(64)
    digest = hashlib.sha256(verifier.encode()).digest()
    challenge = base64.urlsafe_b64encode(digest).rstrip(b"=").decode()
    return verifier, challenge


def authorization_url(client: OAuthClient, redirect_uri: str, state: str, code_challenge: str) -> str:
    """동의 화면 주소를 만든다.

    @doc: docs/design/DriveSync.md#3-인증
    """
    params = {
        "client_id": client.client_id,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": DRIVE_SCOPE,
        "access_type": "offline",
        "prompt": "consent",
        "state": state,
        "code_challenge": code_challenge,
        "code_challenge_method": "S256",
    }
    return f"{client.auth_uri}?{urlencode(params)}"


def _token_request(http: httpx2.Client, client: OAuthClient, data: dict[str, str]) -> dict:
    response = http.post(
        client.token_uri,
        data={"client_id": client.client_id, "client_secret": client.client_secret, **data},
    )
    body = response.json() if response.content else {}
    if response.status_code == 400 and body.get("error") == "invalid_grant":
        raise DriveAuthError("드라이브 연결이 만료되었거나 취소되었습니다. 다시 연결하세요.")
    response.raise_for_status()
    return body


def exchange_code(
    http: httpx2.Client, client: OAuthClient, code: str, redirect_uri: str, code_verifier: str
) -> Token:
    """인증 코드를 토큰으로 바꾼다.

    @doc: docs/design/DriveSync.md#3-인증
    """
    body = _token_request(
        http,
        client,
        {
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": redirect_uri,
            "code_verifier": code_verifier,
        },
    )
    if "refresh_token" not in body:
        raise DriveAuthError("갱신 토큰을 받지 못했습니다. 다시 연결하세요.")
    return Token(body["access_token"], body["refresh_token"], time.time() + body["expires_in"])


def refresh_token(http: httpx2.Client, client: OAuthClient, token: Token) -> Token:
    """갱신 토큰으로 새 접근 토큰을 받는다.

    @doc: docs/design/DriveSync.md#3-인증
    """
    body = _token_request(
        http, client, {"grant_type": "refresh_token", "refresh_token": token.refresh_token}
    )
    return Token(
        body["access_token"],
        body.get("refresh_token", token.refresh_token),
        time.time() + body["expires_in"],
    )


class TokenStore:
    """토큰 파일.

    @doc: docs/design/DriveSync.md#3-인증
    """

    def __init__(self, path: Path) -> None:
        self.path = path

    def load(self) -> Token | None:
        """저장된 토큰을 읽는다. 없거나 깨졌으면 `None`이다.

        @doc: docs/design/DriveSync.md#3-인증
        """
        try:
            return Token(**json.loads(self.path.read_text()))
        except (FileNotFoundError, TypeError, ValueError):
            return None

    def save(self, token: Token) -> None:
        """토큰을 소유자만 읽고 쓰게 저장한다.

        @doc: docs/design/DriveSync.md#3-인증
        """
        write_private(self.path, json.dumps(asdict(token)))

    def clear(self) -> None:
        """토큰을 지운다.

        @doc: docs/design/DriveSync.md#3-인증
        """
        self.path.unlink(missing_ok=True)


def write_private(path: Path, text: str) -> None:
    """소유자만 읽고 쓰는 파일로 쓴다.

    @doc: docs/design/DriveSync.md#2-로컬-파일
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    # 처음부터 600으로 만들어, 쓰는 동안에도 다른 사용자가 읽을 수 없게 한다.
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(descriptor, "w") as file:
        file.write(text)
    os.chmod(path, 0o600)


def access_token(http: httpx2.Client, client: OAuthClient, store: TokenStore) -> str:
    """쓸 수 있는 접근 토큰을 돌려준다. 만료가 가까우면 갱신한다.

    @doc: docs/design/DriveSync.md#3-인증
    """
    token = store.load()
    if token is None:
        raise DriveAuthError("드라이브에 연결되어 있지 않습니다.")
    if token.expires_at - time.time() > _REFRESH_MARGIN_SECONDS:
        return token.access_token
    try:
        token = refresh_token(http, client, token)
    except DriveAuthError:
        store.clear()
        raise
    store.save(token)
    return token.access_token
