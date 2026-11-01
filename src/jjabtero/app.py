"""백엔드 FastAPI 앱.

@doc: docs/design/AppSkeleton.md#1-백엔드-앱
"""

from pathlib import Path

from fastapi import APIRouter, FastAPI
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from jjabtero import __version__

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


def create_app(frontend_dist: Path = DEFAULT_FRONTEND_DIST) -> FastAPI:
    """FastAPI 앱을 만든다.

    @doc: docs/design/AppSkeleton.md#1-백엔드-앱
    """
    app = FastAPI(title="Jjabtero", version=__version__)
    app.include_router(_api)
    # 정적 파일 마운트는 "/" 전체를 차지하므로 API 라우터 다음에 둔다.
    if frontend_dist.is_dir():
        app.mount("/", StaticFiles(directory=frontend_dist, html=True), name="frontend")
    return app
