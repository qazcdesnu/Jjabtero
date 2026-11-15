"""백엔드 앱을 검증한다.

@doc: docs/design/AppSkeleton.md#4-테스트
"""

from pathlib import Path

from fastapi.testclient import TestClient

from jjabtero import __version__
from jjabtero.app import create_app


def test_health_returns_ok_and_version(tmp_path: Path) -> None:
    """상태 확인 API가 `ok`와 패키지 버전을 돌려준다.

    @doc: docs/design/AppSkeleton.md#4-테스트
    """
    client = TestClient(create_app(frontend_dist=tmp_path / "missing", db_path=tmp_path / "library.db"))
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_unknown_api_path_returns_404(tmp_path: Path) -> None:
    """없는 API 경로는 빌드된 화면이 있어도 404다.

    @doc: docs/design/AppSkeleton.md#4-테스트
    """
    (tmp_path / "index.html").write_text("<p>app</p>")
    client = TestClient(create_app(frontend_dist=tmp_path, db_path=tmp_path / "library.db"))
    assert client.get("/api/nope").status_code == 404


def test_root_serves_built_frontend(tmp_path: Path) -> None:
    """빌드된 화면이 있으면 `/`에서 `index.html`을 준다.

    @doc: docs/design/AppSkeleton.md#4-테스트
    """
    (tmp_path / "index.html").write_text("<p>app</p>")
    client = TestClient(create_app(frontend_dist=tmp_path, db_path=tmp_path / "library.db"))
    response = client.get("/")
    assert response.status_code == 200
    assert "<p>app</p>" in response.text


def test_root_is_404_without_built_frontend(tmp_path: Path) -> None:
    """빌드된 화면이 없으면 `/`는 404이고 API는 동작한다.

    @doc: docs/design/AppSkeleton.md#4-테스트
    """
    client = TestClient(create_app(frontend_dist=tmp_path / "missing", db_path=tmp_path / "library.db"))
    assert client.get("/").status_code == 404
    assert client.get("/api/health").status_code == 200


def test_frontend_cache_headers(tmp_path: Path) -> None:
    """해시가 붙은 `assets/` 파일은 오래 캐시하고, `index.html`은 매번 확인하게 한다.

    @doc: docs/design/AppSkeleton.md#4-테스트
    """
    (tmp_path / "index.html").write_text("<html></html>", encoding="utf-8")
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "app-abc123.js").write_text("export {}", encoding="utf-8")
    client = TestClient(create_app(frontend_dist=tmp_path, db_path=tmp_path / "library.db"))
    assert client.get("/").headers["cache-control"] == "no-cache"
    assert client.get("/assets/app-abc123.js").headers["cache-control"] == "public, max-age=31536000, immutable"
    assert "cache-control" not in client.get("/assets/missing.js").headers
