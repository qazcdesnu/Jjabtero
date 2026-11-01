"""백엔드 FastAPI 앱.

@doc: docs/design/AppSkeleton.md#1-백엔드-앱
@doc: docs/design/PaperSearch.md#3-api
@doc: docs/design/DriveSync.md#6-api
@doc: docs/design/Auth.md#3-세션
"""

from collections.abc import Callable
from pathlib import Path

import httpx2
from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel

from jjabtero import __version__
from jjabtero.auth import (
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    AuthSettings,
    auth_settings_from_env,
    require_login,
)
from jjabtero.auth import router as auth_router
from jjabtero.db import create_db_engine, default_db_path, upgrade_database
from jjabtero.drive_api import router as drive_router
from jjabtero.drive_sync import DrivePaths, DriveSync, FilesLike, default_drive_paths
from jjabtero.papers_api import router as papers_router

# @doc: docs/design/AppSkeleton.md#1-백엔드-앱
DEFAULT_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

_api = APIRouter(prefix="/api")


class Health(BaseModel):
    """상태 확인 응답.

    @doc: docs/design/AppSkeleton.md#1-백엔드-앱
    """

    status: str
    version: str


@_api.get("/health")
def health() -> Health:
    """`GET /api/health`를 처리한다.

    @doc: docs/design/AppSkeleton.md#1-백엔드-앱
    """
    return Health(status="ok", version=__version__)


def _default_http_client() -> httpx2.Client:
    return httpx2.Client(timeout=10, headers={"User-Agent": f"Jjabtero/{__version__}"})


def create_app(
    frontend_dist: Path = DEFAULT_FRONTEND_DIST,
    db_path: Path | None = None,
    http_client: httpx2.Client | None = None,
    drive_paths: DrivePaths | None = None,
    drive_files: Callable[[httpx2.Client, Callable[[], str]], FilesLike] | None = None,
    auth: AuthSettings | None = None,
) -> FastAPI:
    """FastAPI 앱을 만든다.

    @doc: docs/design/AppSkeleton.md#1-백엔드-앱
    @doc: docs/design/PaperSearch.md#3-api
    @doc: docs/design/DriveSync.md#6-api
    @doc: docs/design/Auth.md#3-세션
    """
    settings = auth or auth_settings_from_env()
    settings.validate()
    app = FastAPI(title="Jjabtero", version=__version__)
    app.state.auth = settings
    if settings.enabled:
        # 나중에 더한 미들웨어가 바깥을 감싸므로, 세션을 로그인 검사보다 뒤에 더해 먼저 풀리게 한다.
        app.middleware("http")(require_login)
        app.add_middleware(
            SessionMiddleware,
            secret_key=settings.session_secret,
            session_cookie=SESSION_COOKIE,
            max_age=SESSION_MAX_AGE,
            same_site="lax",
            https_only=settings.secure_cookie,
        )
    path = db_path or default_db_path()
    app.state.engine = create_db_engine(path)
    upgrade_database(app.state.engine)
    app.state.http_client = http_client or _default_http_client()
    drive_options = {"files_factory": drive_files} if drive_files else {}
    app.state.drive = DriveSync(
        app.state.engine,
        drive_paths or default_drive_paths(path),
        app.state.http_client,
        **drive_options,
    )
    app.state.drive.start_background_sync()
    app.include_router(_api)
    app.include_router(papers_router)
    app.include_router(drive_router)
    app.include_router(auth_router)
    # 정적 파일 마운트는 "/" 전체를 차지하므로 API 라우터 다음에 둔다.
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    return app
