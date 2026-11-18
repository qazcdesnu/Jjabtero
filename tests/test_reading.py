"""리더의 읽던 위치 API를 검증한다.

@doc: docs/design/Reader.md#8-테스트
"""

from datetime import UTC, datetime
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


def test_paper_last_read_at_follows_position(client: tuple[TestClient, list[str]]) -> None:
    """논문 응답의 마지막으로 읽은 시각은 연 적이 없으면 담은 시각이고, 위치를 저장할 때마다 그 시각으로 바뀐다.

    @doc: docs/design/Reader.md#8-테스트
    """
    test_client, _ = client
    paper_id = test_client.post("/api/papers", json={"title": "T"}).json()["id"]
    added = test_client.get("/api/papers").json()[0]
    assert added["last_read_at"] == added["created_at"]
    first = test_client.put(f"/api/papers/{paper_id}/position", json={"page": 1, "offset": 0, "zoom": 1}).json()
    listed = test_client.get("/api/papers").json()[0]["last_read_at"]
    assert datetime.fromisoformat(listed).replace(tzinfo=UTC) == datetime.fromisoformat(first["updated_at"])
    second = test_client.put(f"/api/papers/{paper_id}/position", json={"page": 1, "offset": 0, "zoom": 1}).json()
    assert second["updated_at"] > first["updated_at"]
    listed = test_client.get("/api/papers").json()[0]["last_read_at"]
    assert datetime.fromisoformat(listed).replace(tzinfo=UTC) == datetime.fromisoformat(second["updated_at"])


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


HIGHLIGHT = {
    "kind": "highlight",
    "page": 2,
    "rects": [{"x": 0.1, "y": 0.5, "w": 0.6, "h": 0.02}, {"x": 0.1, "y": 0.52, "w": 0.3, "h": 0.02}],
    "text": "  attention  ",
    "color": "green",
}


def test_annotations_create_list_update_delete(client: tuple[TestClient, list[str]]) -> None:
    """주석을 만들고, 쪽·위치 순으로 읽고, 색과 메모를 고치고, 지운다. 바꿀 때마다 올리기를 예약한다.

    @doc: docs/design/Reader.md#8-테스트
    """
    test_client, pushes = client
    paper_id = test_client.post("/api/papers", json={"title": "T"}).json()["id"]
    pushes.clear()
    created = test_client.post(f"/api/papers/{paper_id}/annotations", json=HIGHLIGHT)
    assert created.status_code == 201
    body = created.json()
    assert (body["kind"], body["page"], body["text"], body["color"], len(body["rects"])) == ("highlight", 2, "attention", "green", 2)
    first = {**HIGHLIGHT, "page": 1, "rects": [{"x": 0.2, "y": 0.9, "w": 0.1, "h": 0.02}]}
    test_client.post(f"/api/papers/{paper_id}/annotations", json=first)
    listed = test_client.get(f"/api/papers/{paper_id}/annotations").json()
    assert [item["page"] for item in listed] == [1, 2]

    changed = test_client.patch(f"/api/annotations/{body['id']}", json={"color": "pink", "note": " 핵심 "}).json()
    assert (changed["color"], changed["note"]) == ("pink", "핵심")
    cleared = test_client.patch(f"/api/annotations/{body['id']}", json={"note": ""}).json()
    assert (cleared["color"], cleared["note"]) == ("pink", None)

    assert test_client.delete(f"/api/annotations/{body['id']}").status_code == 204
    assert len(test_client.get(f"/api/papers/{paper_id}/annotations").json()) == 1
    assert pushes == ["push"] * 5


@pytest.mark.parametrize(
    "change",
    [
        {"kind": "underline"},
        {"page": 0},
        {"rects": []},
        {"rects": [{"x": 1.2, "y": 0, "w": 0.1, "h": 0.1}]},
        {"rects": [{"x": 0, "y": 0, "w": 0, "h": 0.1}]},
        {"color": "red"},
    ],
)
def test_annotation_rejects_invalid(client: tuple[TestClient, list[str]], change: dict) -> None:
    """모르는 종류, 쪽 0, 빈 사각형, 범위 밖 좌표, 넓이 0, 모르는 색은 422다.

    @doc: docs/design/Reader.md#8-테스트
    """
    test_client, _ = client
    paper_id = test_client.post("/api/papers", json={"title": "T"}).json()["id"]
    assert test_client.post(f"/api/papers/{paper_id}/annotations", json={**HIGHLIGHT, **change}).status_code == 422


def test_annotations_unknown_and_cascade(client: tuple[TestClient, list[str]]) -> None:
    """없는 논문·주석은 404이고, 논문을 지우면 주석도 지운다.

    @doc: docs/design/Reader.md#8-테스트
    """
    test_client, _ = client
    assert test_client.get("/api/papers/9/annotations").status_code == 404
    assert test_client.patch("/api/annotations/9", json={"color": "blue"}).status_code == 404
    assert test_client.delete("/api/annotations/9").status_code == 404
    paper_id = test_client.post("/api/papers", json={"title": "T"}).json()["id"]
    test_client.post(f"/api/papers/{paper_id}/annotations", json=HIGHLIGHT)
    test_client.delete(f"/api/papers/{paper_id}")
    with test_client.app.state.engine.connect() as connection:
        assert connection.execute(text("select count(*) from annotations")).scalar() == 0
