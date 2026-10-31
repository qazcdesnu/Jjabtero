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
    client = TestClient(create_app(frontend_dist=tmp_path / "missing"))
    response = client.get("/api/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok", "version": __version__}


def test_unknown_api_path_returns_404(tmp_path: Path) -> None:
    """없는 API 경로는 빌드된 화면이 있어도 404다.

    @doc: docs/design/AppSkeleton.md#4-테스트
    """
    (tmp_path / "index.html").write_text("<p>app</p>")
    client = TestClient(create_app(frontend_dist=tmp_path))
    assert client.get("/api/nope").status_code == 404


def test_root_serves_built_frontend(tmp_path: Path) -> None:
    """빌드된 화면이 있으면 `/`에서 `index.html`을 준다.

    @doc: docs/design/AppSkeleton.md#4-테스트
    """
    (tmp_path / "index.html").write_text("<p>app</p>")
    client = TestClient(create_app(frontend_dist=tmp_path))
    response = client.get("/")
    assert response.status_code == 200
    assert "<p>app</p>" in response.text


def test_root_is_404_without_built_frontend(tmp_path: Path) -> None:
    """빌드된 화면이 없으면 `/`는 404이고 API는 동작한다.

    @doc: docs/design/AppSkeleton.md#4-테스트
    """
    client = TestClient(create_app(frontend_dist=tmp_path / "missing"))
    assert client.get("/").status_code == 404
    assert client.get("/api/health").status_code == 200
