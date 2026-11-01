"""본인 전용 로그인.

@doc: docs/design/Auth.md#1-방식
"""

import os
import secrets
from collections.abc import Awaitable, Callable
from dataclasses import dataclass

import httpx2
from fastapi import APIRouter, HTTPException, Request, Response, status
from fastapi.responses import JSONResponse, RedirectResponse
from pydantic import BaseModel

from jjabtero.google_auth import (
    DriveAuthError,
    DriveNotConfiguredError,
    authorization_url,
    exchange_code_for_access,
    load_client,
    new_pkce_pair,
)

LOGIN_SCOPE = "openid email"
USERINFO_URL = "https://openidconnect.googleapis.com/v1/userinfo"
SESSION_COOKIE = "jjabtero_session"
SESSION_MAX_AGE = 30 * 24 * 60 * 60
_MIN_SECRET_LENGTH = 32
_PUBLIC_API_PREFIXES = ("/api/health", "/api/auth/")

router = APIRouter(prefix="/api/auth")


class AuthConfigError(Exception):
    """로그인 설정이 잘못되었다.

    @doc: docs/design/Auth.md#2-켜고-끄기
    """


@dataclass(frozen=True)
class AuthSettings:
    """로그인 설정.

    @doc: docs/design/Auth.md#2-켜고-끄기
    """

    allowed_email: str | None = None
    session_secret: str | None = None
    secure_cookie: bool = False

    @property
    def enabled(self) -> bool:
        """허용 이메일이 있으면 로그인이 켜진다.

        @doc: docs/design/Auth.md#2-켜고-끄기
        """
        return bool(self.allowed_email)

    def validate(self) -> None:
        """로그인이 켜졌는데 서명 키가 없거나 짧으면 `AuthConfigError`를 던진다.

        @doc: docs/design/Auth.md#2-켜고-끄기
        """
        if self.enabled and len(self.session_secret or "") < _MIN_SECRET_LENGTH:
            raise AuthConfigError(
                f"JJABTERO_SESSION_SECRET에 {_MIN_SECRET_LENGTH}자 이상의 값을 넣어야 로그인을 켤 수 있습니다."
            )


def auth_settings_from_env() -> AuthSettings:
    """환경 변수에서 로그인 설정을 읽는다.

    @doc: docs/design/Auth.md#2-켜고-끄기
    """
    email = os.environ.get("JJABTERO_ALLOWED_EMAIL", "").strip() or None
    return AuthSettings(
        allowed_email=email,
        session_secret=os.environ.get("JJABTERO_SESSION_SECRET") or None,
        secure_cookie=os.environ.get("JJABTERO_SECURE_COOKIE", "").lower() in ("1", "true", "yes"),
    )


class Me(BaseModel):
    """로그인 상태.

    @doc: docs/design/Auth.md#5-api
    """

    enabled: bool
    email: str | None = None


def _settings(request: Request) -> AuthSettings:
    return request.app.state.auth


def _logged_in_email(request: Request) -> str | None:
    if not _settings(request).enabled:
        return None
    return request.session.get("email")


async def require_login(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """로그인이 켜져 있으면 공개 예외 밖의 `/api` 요청을 로그인한 경우에만 통과시킨다.

    @doc: docs/design/Auth.md#4-막는-범위
    """
    path = request.url.path
    if (
        _settings(request).enabled
        and path.startswith("/api")
        and not path.startswith(_PUBLIC_API_PREFIXES)
        and _logged_in_email(request) is None
    ):
        return JSONResponse({"detail": "로그인이 필요합니다."}, status_code=status.HTTP_401_UNAUTHORIZED)
    return await call_next(request)


def _safe_path(value: str | None) -> str:
    if value and value.startswith("/") and not value.startswith(("//", "/\\")):
        return value
    return "/"


@router.get("/me")
def me(request: Request) -> Me:
    """`GET /api/auth/me`를 처리한다.

    @doc: docs/design/Auth.md#5-api
    """
    return Me(enabled=_settings(request).enabled, email=_logged_in_email(request))


@router.get("/login")
def login(request: Request, return_to: str | None = None) -> RedirectResponse:
    """`GET /api/auth/login`을 처리한다.

    @doc: docs/design/Auth.md#5-api
    """
    if not _settings(request).enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "로그인이 꺼져 있습니다.")
    try:
        client = load_client(request.app.state.drive.paths.client_secret)
    except DriveNotConfiguredError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    state = secrets.token_urlsafe(24)
    verifier, challenge = new_pkce_pair()
    request.session["login"] = {"state": state, "verifier": verifier, "return_to": _safe_path(return_to)}
    redirect_uri = f"{request.base_url}api/auth/callback"
    url = authorization_url(
        client, redirect_uri, state, challenge, scope=LOGIN_SCOPE, offline=False, prompt="select_account"
    )
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.get("/callback")
def callback(
    request: Request, state: str = "", code: str | None = None, error: str | None = None
) -> RedirectResponse:
    """`GET /api/auth/callback`을 처리한다.

    @doc: docs/design/Auth.md#5-api
    """
    settings = _settings(request)
    if not settings.enabled:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "로그인이 꺼져 있습니다.")
    pending = request.session.pop("login", None)
    if error or not code or pending is None or pending.get("state") != state:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "로그인 요청이 맞지 않습니다. 다시 로그인하세요.")
    http: httpx2.Client = request.app.state.http_client
    try:
        client = load_client(request.app.state.drive.paths.client_secret)
        redirect_uri = f"{request.base_url}api/auth/callback"
        token = exchange_code_for_access(http, client, code, redirect_uri, pending["verifier"])
        response = http.get(USERINFO_URL, headers={"Authorization": f"Bearer {token}"})
        response.raise_for_status()
        info = response.json()
    except (DriveAuthError, DriveNotConfiguredError, httpx2.HTTPError) as failure:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"로그인에 실패했습니다: {failure}") from failure
    email = str(info.get("email", ""))
    if not info.get("email_verified") or email.lower() != (settings.allowed_email or "").lower():
        raise HTTPException(status.HTTP_403_FORBIDDEN, "이 앱을 쓸 수 있는 계정이 아닙니다.")
    request.session["email"] = email
    return RedirectResponse(pending["return_to"], status_code=status.HTTP_302_FOUND)


@router.post("/logout")
def logout(request: Request) -> Me:
    """`POST /api/auth/logout`을 처리한다.

    @doc: docs/design/Auth.md#5-api
    """
    if _settings(request).enabled:
        request.session.clear()
    return Me(enabled=_settings(request).enabled)
