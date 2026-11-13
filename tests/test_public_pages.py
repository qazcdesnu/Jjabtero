"""로그인 없이 여는 공개 페이지를 검증한다.

@doc: docs/design/PublicPages.md#4-테스트
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fakes import FakeDrive, write_client_secret
from jjabtero.app import create_app
from jjabtero.auth import AuthSettings
from jjabtero.drive_sync import DrivePaths
from jjabtero.public_pages import CONTACT_URL, ROBOTS

PAGES = ["/about", "/privacy"]


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """로그인을 켜고 빌드된 화면을 둔 앱의 테스트 클라이언트.

    @doc: docs/design/PublicPages.md#4-테스트
    """
    dist = tmp_path / "dist"
    dist.mkdir()
    (dist / "index.html").write_text("<p>app</p>")
    paths = DrivePaths(tmp_path / "client.json", tmp_path / "token.json", tmp_path / "state.json", tmp_path / "backups")
    write_client_secret(paths.client_secret)
    app = create_app(
        frontend_dist=dist,
        db_path=tmp_path / "library.db",
        drive_paths=paths,
        drive_files=lambda http, token: FakeDrive(),
        auth=AuthSettings(allowed_email="me@example.com", session_secret="x" * 40),
    )
    return TestClient(app, follow_redirects=False)


@pytest.mark.parametrize("path", PAGES)
def test_page_is_public_html_and_noindex(client: TestClient, path: str) -> None:
    """로그인 없이 HTML과 noindex를 돌려주고, 빌드된 화면보다 먼저 잡힌다.

    @doc: docs/design/PublicPages.md#4-테스트
    """
    assert client.get("/api/papers").status_code == 401
    response = client.get(path)
    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert response.headers["x-robots-tag"] == ROBOTS
    assert f'<meta name="robots" content="{ROBOTS}">' in response.text
    assert "<p>app</p>" not in response.text


def test_about_links_privacy(client: TestClient) -> None:
    """소개 페이지가 개인정보처리방침을 링크한다.

    @doc: docs/design/PublicPages.md#4-테스트
    """
    text = client.get("/about").text
    assert 'href="/privacy"' in text


def test_privacy_covers_scopes_limited_use_and_contact(client: TestClient) -> None:
    """개인정보처리방침이 범위, 제한적 사용 문장, 연락처를 담는다.

    @doc: docs/design/PublicPages.md#4-테스트
    """
    text = client.get("/privacy").text
    assert "openid email" in text and "drive.file" in text
    assert "Limited Use" in text
    assert "api-services-user-data-policy" in text
    assert CONTACT_URL in text
