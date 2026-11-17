"""태그 붙이기·떼기, 이름 바꾸기·지우기를 검증한다.

@doc: docs/design/Tags.md#6-테스트
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import text

from jjabtero.app import create_app
from jjabtero.tags import TagNameError, clean_tags


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """임시 서재를 쓰는 앱. 드라이브 자동 올리기 예약은 센다.

    @doc: docs/design/Tags.md#6-테스트
    """
    app = create_app(frontend_dist=tmp_path / "missing", db_path=tmp_path / "library.db")
    app.state.pushes = 0

    def count() -> None:
        app.state.pushes += 1

    app.state.drive.schedule_push = count
    return TestClient(app)


def add(client: TestClient, title: str, tags: list[str] | None = None) -> dict:
    """논문을 넣고 응답을 돌려준다.

    @doc: docs/design/Tags.md#6-테스트
    """
    return client.post("/api/papers", json={"title": title, "tags": tags or []}).json()


def tag_rows(client: TestClient) -> list[str]:
    """태그 표의 이름들.

    @doc: docs/design/Tags.md#6-테스트
    """
    with client.app.state.engine.connect() as connection:
        return sorted(name for (name,) in connection.execute(text("SELECT name FROM tags")))


def test_clean_tags_rules() -> None:
    """빈칸을 정리하고 빈 이름과 겹친 이름을 빼며, 50자를 넘으면 오류다.

    @doc: docs/design/Tags.md#6-테스트
    """
    assert clean_tags(["  deep   learning ", "", "NLP", "deep learning", "nlp"]) == ["deep learning", "NLP", "nlp"]
    with pytest.raises(TagNameError):
        clean_tags(["x" * 51])


def test_put_paper_tags_replaces_bumps_time_and_drops_unused(client: TestClient) -> None:
    """논문의 태그를 바꾸고, 고친 시각을 바꾸며, 쓰지 않게 된 태그는 지우고, 자동 올리기를 예약한다.

    @doc: docs/design/Tags.md#6-테스트
    """
    paper = add(client, "A", ["old", "keep"])
    client.app.state.pushes = 0
    response = client.put(f"/api/papers/{paper['id']}/tags", json={"tags": ["keep", " new "]})
    assert response.status_code == 200
    body = response.json()
    assert body["tags"] == ["keep", "new"]
    assert body["updated_at"] > paper["updated_at"]
    assert tag_rows(client) == ["keep", "new"]
    assert client.app.state.pushes == 1
    assert client.put("/api/papers/99/tags", json={"tags": []}).status_code == 404
    assert client.put(f"/api/papers/{paper['id']}/tags", json={"tags": ["x" * 51]}).status_code == 422


def test_apply_tags_to_many_papers(client: TestClient) -> None:
    """여러 논문에 태그를 붙이고 떼며, 바뀐 논문 수를 돌려준다. 없는 논문이 섞이면 아무것도 바꾸지 않는다.

    @doc: docs/design/Tags.md#6-테스트
    """
    a = add(client, "A", ["x"])
    b = add(client, "B")
    c = add(client, "C", ["survey"])
    response = client.post("/api/tags/apply", json={"paper_ids": [a["id"], b["id"], c["id"]], "add": ["survey"], "remove": ["x"]})
    assert response.json() == {"changed": 2}
    tags = {paper["title"]: paper["tags"] for paper in client.get("/api/papers").json()}
    assert tags == {"A": ["survey"], "B": ["survey"], "C": ["survey"]}
    assert tag_rows(client) == ["survey"]
    missing = client.post("/api/tags/apply", json={"paper_ids": [a["id"], 99], "add": ["y"]})
    assert missing.status_code == 404
    assert tag_rows(client) == ["survey"]
    assert client.post("/api/tags/apply", json={"paper_ids": [], "add": ["y"]}).status_code == 422


def test_rename_and_merge_tags(client: TestClient) -> None:
    """태그 이름을 바꾸고, 새 이름이 이미 있으면 합친다. 없는 태그는 404다.

    @doc: docs/design/Tags.md#6-테스트
    """
    add(client, "A", ["nlp"])
    add(client, "B", ["NLP", "nlp"])
    assert client.patch("/api/tags/nlp", json={"name": "language"}).json() == {"changed": 2}
    assert tag_rows(client) == ["NLP", "language"]
    assert client.patch("/api/tags/NLP", json={"name": "language"}).json() == {"changed": 1}
    tags = {paper["title"]: paper["tags"] for paper in client.get("/api/papers").json()}
    assert tags == {"A": ["language"], "B": ["language"]}
    assert tag_rows(client) == ["language"]
    assert client.patch("/api/tags/none", json={"name": "x"}).status_code == 404
    assert client.patch("/api/tags/language", json={"name": "  "}).status_code == 422


def test_delete_tag_keeps_papers(client: TestClient) -> None:
    """태그를 지우면 모든 논문에서 떼고, 논문은 남긴다.

    @doc: docs/design/Tags.md#6-테스트
    """
    add(client, "A", ["temp", "keep"])
    add(client, "B", ["temp"])
    assert client.delete("/api/tags/temp").json() == {"changed": 2}
    tags = {paper["title"]: paper["tags"] for paper in client.get("/api/papers").json()}
    assert tags == {"A": ["keep"], "B": []}
    assert client.delete("/api/tags/temp").status_code == 404
