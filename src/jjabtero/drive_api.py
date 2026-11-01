"""구글 드라이브 연결과 동기화 API.

@doc: docs/design/DriveSync.md#6-api
"""

from typing import Literal

import httpx2
from fastapi import APIRouter, HTTPException, Request, status
from fastapi.responses import RedirectResponse
from pydantic import BaseModel

from jjabtero.drive_sync import DriveSync, SyncStatus
from jjabtero.google_auth import DriveAuthError, DriveNotConfiguredError

router = APIRouter(prefix="/api/drive")

_LOCAL_ORIGINS = ("http://127.0.0.1", "http://localhost")


class ResolveRequest(BaseModel):
    """충돌 풀기 요청.

    @doc: docs/design/DriveSync.md#6-api
    """

    choice: Literal["remote", "local"]


def _drive(request: Request) -> DriveSync:
    return request.app.state.drive


def _safe_return_to(value: str | None) -> str:
    if value and any(value == origin or value.startswith((f"{origin}:", f"{origin}/")) for origin in _LOCAL_ORIGINS):
        return value
    return "/"


@router.get("/status")
def drive_status(request: Request) -> SyncStatus:
    """`GET /api/drive/status`를 처리한다.

    @doc: docs/design/DriveSync.md#6-api
    """
    return _drive(request).status()


@router.get("/connect")
def connect(request: Request, return_to: str | None = None) -> RedirectResponse:
    """`GET /api/drive/connect`를 처리한다.

    @doc: docs/design/DriveSync.md#6-api
    """
    redirect_uri = f"{request.base_url}api/drive/callback"
    try:
        url = _drive(request).connect_url(redirect_uri, _safe_return_to(return_to))
    except DriveNotConfiguredError as error:
        raise HTTPException(status.HTTP_409_CONFLICT, str(error)) from error
    return RedirectResponse(url, status_code=status.HTTP_302_FOUND)


@router.get("/callback")
def callback(
    request: Request, state: str = "", code: str | None = None, error: str | None = None
) -> RedirectResponse:
    """`GET /api/drive/callback`을 처리한다.

    @doc: docs/design/DriveSync.md#6-api
    """
    if error or not code:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"드라이브 연결이 취소되었습니다: {error}")
    drive = _drive(request)
    try:
        return_to = drive.finish_connect(state, code)
    except ValueError as failure:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, str(failure)) from failure
    except (DriveAuthError, DriveNotConfiguredError, httpx2.HTTPError) as failure:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"드라이브 연결에 실패했습니다: {failure}") from failure
    drive.sync()
    return RedirectResponse(return_to, status_code=status.HTTP_302_FOUND)


@router.post("/sync")
def sync_now(request: Request) -> SyncStatus:
    """`POST /api/drive/sync`를 처리한다.

    @doc: docs/design/DriveSync.md#6-api
    """
    return _drive(request).sync()


@router.post("/resolve")
def resolve(request: Request, body: ResolveRequest) -> SyncStatus:
    """`POST /api/drive/resolve`를 처리한다.

    @doc: docs/design/DriveSync.md#6-api
    """
    return _drive(request).resolve(body.choice)


@router.post("/disconnect")
def disconnect(request: Request) -> SyncStatus:
    """`POST /api/drive/disconnect`를 처리한다.

    @doc: docs/design/DriveSync.md#6-api
    """
    return _drive(request).disconnect()
