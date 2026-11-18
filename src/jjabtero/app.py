"""백엔드 FastAPI 앱.

@doc: docs/design/AppSkeleton.md#1-백엔드-앱
@doc: docs/design/PaperSearch.md#3-api
@doc: docs/design/DriveSync.md#6-api
@doc: docs/design/Auth.md#3-세션
@doc: docs/design/DriveSync.md#8-서버-환경
@doc: docs/design/PublicPages.md#1-제공-방식
"""

import os
from collections.abc import AsyncIterator, Awaitable, Callable
from contextlib import asynccontextmanager
from pathlib import Path

import httpx2
from fastapi import APIRouter, FastAPI, Request, Response
from fastapi.staticfiles import StaticFiles
from starlette.responses import Response
from starlette.types import Scope
from starlette.concurrency import run_in_threadpool
from starlette.middleware.sessions import SessionMiddleware
from pydantic import BaseModel

from jjabtero import __version__
from jjabtero.ai import router as ai_router
from jjabtero.auth import (
    SESSION_COOKIE,
    SESSION_MAX_AGE,
    AuthSettings,
    auth_settings_from_env,
    require_login,
)
from jjabtero.auth import router as auth_router
from jjabtero.citation_graph import router as citation_graph_router
from jjabtero.citations import CACHE_FILE, CitationSync
from jjabtero.citations import paper_router as paper_citations_router
from jjabtero.citations import router as citations_router
from jjabtero.db import create_db_engine, default_db_path
from jjabtero.drive_api import router as drive_router
from jjabtero.drive_sync import (
    DrivePaths,
    DriveSync,
    FilesLike,
    default_drive_paths,
    seed_token_from_env,
    upgrade_keeping_sync,
)
from jjabtero.papers_api import router as papers_router
from jjabtero.pdfs import PdfStore
from jjabtero.pdf_versions import router as pdf_versions_router
from jjabtero.pdfs import router as pdfs_router
from jjabtero.public_pages import router as public_pages_router
from jjabtero.reading import annotations_router
from jjabtero.references import router as references_router
from jjabtero.reading import router as reading_router
from jjabtero.settings import router as settings_router
from jjabtero.tags import router as tags_router

# @doc: docs/design/AppSkeleton.md#1-백엔드-앱
DEFAULT_FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"


class FrontendFiles(StaticFiles):
    """빌드된 프론트엔드 파일. 이름에 해시가 붙은 `assets/`는 오래 캐시하고, 그 밖(`index.html` 등)은 매번 확인하게 한다.

    @doc: docs/design/AppSkeleton.md#1-백엔드-앱
    """

    async def get_response(self, path: str, scope: Scope) -> Response:
        """파일 응답에 캐시 지시를 붙인다.

        @doc: docs/design/AppSkeleton.md#1-백엔드-앱
        """
        response = await super().get_response(path, scope)
        if response.status_code in (200, 304):
            hashed = path.replace("\\", "/").startswith("assets/")
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable" if hashed else "no-cache"
        return response

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


_WRITE_METHODS = {"POST", "PUT", "PATCH", "DELETE"}
_NO_FRESH_PREFIXES = ("/api/drive/", "/api/auth/")


async def _fresh_before_write(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
    """서재를 바꾸는 요청 앞에서, 마지막 확인이 30초보다 오래되었으면 드라이브를 먼저 확인한다.

    다른 곳이 올린 변경을 받지 않은 채 쓰면 둘 다 바뀌어 충돌이 되기 때문이다.

    @doc: docs/design/DriveSync.md#5-동기화
    """
    path = request.url.path
    if request.method in _WRITE_METHODS and path.startswith("/api/") and not path.startswith(_NO_FRESH_PREFIXES):
        await run_in_threadpool(request.app.state.drive.ensure_fresh)
    return await call_next(request)


def _default_http_client() -> httpx2.Client:
    return httpx2.Client(timeout=10, headers={"User-Agent": f"Jjabtero/{__version__}"})


def create_app(
    frontend_dist: Path = DEFAULT_FRONTEND_DIST,
    db_path: Path | None = None,
    http_client: httpx2.Client | None = None,
    drive_paths: DrivePaths | None = None,
    drive_files: Callable[[httpx2.Client, Callable[[], str]], FilesLike] | None = None,
    auth: AuthSettings | None = None,
    wait_initial_sync: bool | None = None,
    run_citations: bool = False,
) -> FastAPI:
    """FastAPI 앱을 만든다.

    @doc: docs/design/AppSkeleton.md#1-백엔드-앱
    @doc: docs/design/PaperSearch.md#3-api
    @doc: docs/design/DriveSync.md#6-api
    @doc: docs/design/Auth.md#3-세션
    @doc: docs/design/DriveSync.md#8-서버-환경
    @doc: docs/design/PublicPages.md#1-제공-방식
    @doc: docs/design/Citations.md#5-갱신
    @doc: docs/design/Reader.md#3-보관
    """
    settings = auth or auth_settings_from_env()
    settings.validate()

    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        yield
        app.state.citations.stop()
        app.state.drive.stop()
        app.state.drive.flush()

    app = FastAPI(title="Jjabtero", version=__version__, lifespan=lifespan)
    app.state.auth = settings
    # 로그인 검사보다 먼저 더해 안쪽에 둔다. 로그인한 요청만 드라이브를 확인한다.
    app.middleware("http")(_fresh_before_write)
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
    app.state.data_dir = path.parent
    paths = drive_paths or default_drive_paths(path)
    # 스키마만 올린 것을 이 컴퓨터의 변경으로 세지 않도록 동기화 상태를 이어받는다.
    upgrade_keeping_sync(app.state.engine, paths.state)
    app.state.http_client = http_client or _default_http_client()
    drive_options: dict = {"files_factory": drive_files} if drive_files else {}
    watch = os.environ.get("JJABTERO_DRIVE_WATCH_SECONDS")
    if watch is not None:
        drive_options["watch_interval"] = float(watch)
    app.state.drive = DriveSync(app.state.engine, paths, app.state.http_client, **drive_options)
    seed_token_from_env(app.state.drive.tokens)
    if wait_initial_sync is None:
        wait_initial_sync = os.environ.get("JJABTERO_INITIAL_SYNC") == "wait"
    app.state.drive.start(wait=wait_initial_sync)
    app.state.citations = CitationSync(
        app.state.engine, path.parent / CACHE_FILE, app.state.http_client, app.state.drive
    )
    if run_citations:
        app.state.citations.start()
    app.state.pdfs = PdfStore(path.parent / "pdfs", app.state.drive)
    app.include_router(_api)
    app.include_router(ai_router)
    app.include_router(papers_router)
    app.include_router(tags_router)
    app.include_router(drive_router)
    app.include_router(auth_router)
    app.include_router(public_pages_router)
    app.include_router(settings_router)
    app.include_router(citations_router)
    app.include_router(citation_graph_router)
    app.include_router(paper_citations_router)
    app.include_router(pdfs_router)
    app.include_router(pdf_versions_router)
    app.include_router(reading_router)
    app.include_router(annotations_router)
    app.include_router(references_router)
    # 정적 파일 마운트는 "/" 전체를 차지하므로 API 라우터 다음에 둔다.
    if frontend_dist.is_dir():
        app.mount("/", FrontendFiles(directory=frontend_dist, html=True), name="frontend")
    return app
