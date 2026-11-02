"""모든 테스트를 실제 사용자 데이터에서 떼어 놓는다.

@doc: docs/design/DriveSync.md#9-테스트
"""

from pathlib import Path

import pytest


@pytest.fixture(autouse=True)
def isolated_user_data(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    """사용자 데이터 폴더와 데이터베이스, 클라이언트 경로를 임시 폴더로 바꾼다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    monkeypatch.setenv("JJABTERO_DATA_DIR", str(tmp_path / "user-data"))
    monkeypatch.setenv("JJABTERO_DB", str(tmp_path / "user-data" / "library.db"))
    monkeypatch.delenv("JJABTERO_GOOGLE_CLIENT_SECRET", raising=False)
    monkeypatch.delenv("OPENALEX_API_KEY", raising=False)
    for name in (
        "JJABTERO_ALLOWED_EMAIL",
        "JJABTERO_SESSION_SECRET",
        "JJABTERO_SECURE_COOKIE",
        "JJABTERO_GOOGLE_REFRESH_TOKEN",
        "JJABTERO_INITIAL_SYNC",
    ):
        monkeypatch.delenv(name, raising=False)
