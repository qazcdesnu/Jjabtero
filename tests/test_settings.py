"""사용자 설정의 저장과 API를 검증한다.

@doc: docs/design/Settings.md#5-테스트
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from jjabtero.app import create_app
from jjabtero.db import create_db_engine, upgrade_database
from jjabtero.models import Setting
from jjabtero.settings import SETTINGS, SettingError, read_settings, update_settings


@pytest.fixture
def session(tmp_path: Path) -> Session:
    """마이그레이션을 끝낸 임시 데이터베이스의 세션.

    @doc: docs/design/Settings.md#5-테스트
    """
    engine = create_db_engine(tmp_path / "library.db")
    upgrade_database(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def client(tmp_path: Path) -> tuple[TestClient, list[str]]:
    """임시 데이터베이스를 쓰는 앱의 테스트 클라이언트와 드라이브 올리기 예약 기록.

    @doc: docs/design/Settings.md#5-테스트
    """
    app = create_app(frontend_dist=tmp_path / "missing", db_path=tmp_path / "library.db")
    pushes: list[str] = []
    app.state.drive.schedule_push = lambda: pushes.append("push")
    return TestClient(app), pushes


def test_defaults_when_nothing_saved(session: Session) -> None:
    """저장한 것이 없으면 기본값이다. `citing_limit` 기본값은 10이다.

    @doc: docs/design/Settings.md#5-테스트
    """
    assert read_settings(session) == {"citing_limit": 10}
    assert {spec.key: spec.default for spec in SETTINGS} == {"citing_limit": 10}


def test_update_saves_and_reads_back(session: Session) -> None:
    """바꾼 값을 저장하고 다시 읽는다.

    @doc: docs/design/Settings.md#5-테스트
    """
    assert update_settings(session, {"citing_limit": 50}) == {"citing_limit": 50}
    assert read_settings(session) == {"citing_limit": 50}
    assert session.get(Setting, "citing_limit").value == "50"


@pytest.mark.parametrize(
    "changes",
    [{"citing_limit": 30, "unknown": 1}, {"citing_limit": 0}, {"citing_limit": 1001}, {"citing_limit": "20"}, {"citing_limit": True}]
)
def test_update_rejects_invalid_and_saves_nothing(session: Session, changes: dict) -> None:
    """모르는 키, 범위 밖, 정수가 아닌 값은 거절하고 아무것도 저장하지 않는다.

    @doc: docs/design/Settings.md#5-테스트
    """
    with pytest.raises(SettingError):
        update_settings(session, changes)
    assert session.query(Setting).count() == 0


def test_broken_stored_value_falls_back_to_default(session: Session) -> None:
    """저장된 값이 정수가 아니거나 범위를 벗어나면 기본값을 쓴다.

    @doc: docs/design/Settings.md#5-테스트
    """
    session.add(Setting(key="citing_limit", value="many"))
    session.commit()
    assert read_settings(session) == {"citing_limit": 10}
    session.merge(Setting(key="citing_limit", value="5000"))
    session.commit()
    assert read_settings(session) == {"citing_limit": 10}


def test_api_lists_settings_with_metadata(client: tuple[TestClient, list[str]]) -> None:
    """`GET /api/settings`는 항목마다 이름, 설명, 값, 기본값, 범위를 돌려준다.

    @doc: docs/design/Settings.md#5-테스트
    """
    test_client, _ = client
    response = test_client.get("/api/settings")
    assert response.status_code == 200
    [item] = response.json()
    assert item["key"] == "citing_limit"
    assert (item["value"], item["default"], item["minimum"], item["maximum"]) == (10, 10, 1, 1000)
    assert item["label"] and item["description"]


def test_api_update_saves_and_schedules_push(client: tuple[TestClient, list[str]]) -> None:
    """`PUT /api/settings`는 저장하고 바뀐 목록을 돌려주며 드라이브 올리기를 예약한다.

    @doc: docs/design/Settings.md#5-테스트
    """
    test_client, pushes = client
    response = test_client.put("/api/settings", json={"citing_limit": 25})
    assert response.status_code == 200
    assert response.json()[0]["value"] == 25
    assert test_client.get("/api/settings").json()[0]["value"] == 25
    assert pushes == ["push"]


def test_api_rejects_invalid_with_422(client: tuple[TestClient, list[str]]) -> None:
    """잘못된 값은 422와 이유로 거절하고 드라이브 올리기를 예약하지 않는다.

    @doc: docs/design/Settings.md#5-테스트
    """
    test_client, pushes = client
    response = test_client.put("/api/settings", json={"citing_limit": 0})
    assert response.status_code == 422
    assert "1~1000" in response.json()["detail"]
    assert pushes == []
