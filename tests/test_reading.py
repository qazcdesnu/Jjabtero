"""리더의 읽던 위치 API를 검증한다.

@doc: docs/design/Reader.md#8-테스트
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from jjabtero.app import create_app


@pytest.fixture
def client(tmp_path: Path) -> tuple[TestClient, list[str]]:
    """임시 서재를 쓰는 앱과 드라이브 올리기 예약 기록.

    @doc: docs/design/Reader.md#8-테스트
    """
    app = create_app(frontend_dist=tmp_path / "missing", db_path=tmp_path / "library.db")
    pushes: list[str] = []
    app.state.drive.schedule_push = lambda: pushes.append("push")
    return TestClient(app), pushes


def test_position_is_empty_then_saved_and_replaced(client: tuple[TestClient, list[str]]) -> None:
    """저장한 위치가 없으면 204이고, 저장하면 읽히며, 다시 저장하면 바뀐다. 저장마다 올리기를 예약한다.

    @doc: docs/design/Reader.md#8-테스트
    """
    test_client, pushes = client
    paper_id = test_client.post("/api/papers", json={"title": "T"}).json()["id"]
    pushes.clear()
    assert test_client.get(f"/api/papers/{paper_id}/position").status_code == 204
    saved = test_client.put(f"/api/papers/{paper_id}/position", json={"page": 3, "offset": 0.25, "zoom": 1.5})
    assert saved.status_code == 200
    assert test_client.get(f"/api/papers/{paper_id}/position").json()["page"] == 3
    test_client.put(f"/api/papers/{paper_id}/position", json={"page": 7, "offset": 0.5, "zoom": 1})
    body = test_client.get(f"/api/papers/{paper_id}/position").json()
    assert (body["page"], body["offset"], body["zoom"]) == (7, 0.5, 1)
    assert pushes == ["push", "push"]


@pytest.mark.parametrize(
    "body", [{"page": 0, "offset": 0, "zoom": 1}, {"page": 1, "offset": 1.5, "zoom": 1}, {"page": 1, "offset": 0, "zoom": 9}]
)
def test_position_rejects_out_of_range(client: tuple[TestClient, list[str]], body: dict) -> None:
    """쪽 0, 쪽 안 위치 1 초과, 확대 5 초과는 422다.

    @doc: docs/design/Reader.md#8-테스트
    """
    test_client, _ = client
    paper_id = test_client.post("/api/papers", json={"title": "T"}).json()["id"]
    assert test_client.put(f"/api/papers/{paper_id}/position", json=body).status_code == 422


def test_position_unknown_paper_and_delete(client: tuple[TestClient, list[str]]) -> None:
    """없는 논문은 404이고, 논문을 지우면 위치도 지운다.

    @doc: docs/design/Reader.md#8-테스트
    """
    test_client, _ = client
    assert test_client.get("/api/papers/9/position").status_code == 404
    paper_id = test_client.post("/api/papers", json={"title": "T"}).json()["id"]
    test_client.put(f"/api/papers/{paper_id}/position", json={"page": 2, "offset": 0, "zoom": 1})
    test_client.delete(f"/api/papers/{paper_id}")
    with test_client.app.state.engine.connect() as connection:
        assert connection.execute(text("select count(*) from reading_positions")).scalar() == 0
