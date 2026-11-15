"""서재 인용 그래프의 데이터와 API를 검증한다.

@doc: docs/design/CitationGraph.md#5-테스트
"""

from pathlib import Path

import httpx2
from fastapi.testclient import TestClient

from jjabtero.app import create_app
from jjabtero.citation_graph import library_edges, outside_edges
from jjabtero.citations import Recommendation, Relation
from test_citations import A, FakeOpenAlex


def rows(references: set[str], citations: dict[str, int] | None = None, cocitations: dict[str, int] | None = None) -> dict:
    """`relation_rows`와 같은 모양.

    @doc: docs/design/CitationGraph.md#5-테스트
    """
    return {"references": references, "citations": citations or {}, "cocitations": cocitations or {}}


def test_library_edges_cites_from_references_and_citations() -> None:
    """참고문헌과 피인용 어느 쪽에서 알아도 인용 선 하나를 만들고, 자기 자신은 잇지 않는다.

    @doc: docs/design/CitationGraph.md#5-테스트
    """
    node_ids = {"WA": "p1", "WB": "p2", "WC": "p3"}
    by_paper = {
        "WA": rows({"WB", "WA"}),
        "WB": rows(set(), {"WA": 0, "WC": 0}),
    }
    edges = [(e.source, e.target, e.kind) for e in library_edges(node_ids, by_paper)]
    assert edges == [("p1", "p2", "cites"), ("p3", "p2", "cites")]


def test_library_edges_related_threshold_and_skip_when_cited() -> None:
    """참고문헌 2개 이상 공유나 2번 이상 함께 인용이면 가까움 선이고, 인용 선이 있으면 그리지 않는다.

    @doc: docs/design/CitationGraph.md#5-테스트
    """
    node_ids = {"WA": "p1", "WB": "p2", "WC": "p3", "WD": "p4"}
    by_paper = {
        "WA": rows({"X1", "X2", "WD"}),
        "WB": rows({"X1", "X2"}),
        "WC": rows({"X1"}, cocitations={"WA": 3}),
        "WD": rows({"X1", "X2"}),
    }
    edges = {(e.source, e.target): e for e in library_edges(node_ids, by_paper)}
    assert edges[("p1", "p4")].kind == "cites"
    assert (edges[("p1", "p2")].kind, edges[("p1", "p2")].shared_refs) == ("related", 2)
    assert (edges[("p1", "p3")].kind, edges[("p1", "p3")].cocited) == ("related", 3)
    assert ("p2", "p3") not in edges
    assert ("p2", "p4") in edges and ("p1", "p4") in edges and len([k for k in edges if set(k) == {"p1", "p4"}]) == 1


def test_outside_edges_follow_citation_direction() -> None:
    """서재 밖 논문은 서재 논문이 인용하면 서재 → 밖, 밖이 인용하면 밖 → 서재, 그 밖에는 가까움 선이다.

    @doc: docs/design/CitationGraph.md#5-테스트
    """
    item = Recommendation(
        "W9",
        sources=["WA", "WB", "WC"],
        relations=[
            Relation("W9", 0.5, False, True, 0, 0),
            Relation("W9", 0.5, True, False, 0, 1),
            Relation("W9", 0.3, False, False, 2, 0),
        ],
    )
    edges = [(e.source, e.target, e.kind, e.cocited) for e in outside_edges(item, {"WA": "p1", "WB": "p2", "WC": "p3"})]
    assert edges == [("p1", "W9", "cites", 0), ("W9", "p2", "cites", 0), ("p3", "W9", "related", 2)]


def make_client(tmp_path: Path) -> tuple[TestClient, object]:
    """가짜 OpenAlex를 쓰는 앱. 서재 논문 W10의 OpenAlex 응답을 더한다.

    @doc: docs/design/CitationGraph.md#5-테스트
    """
    openalex = FakeOpenAlex()
    openalex.base["W10"] = {
        "id": "https://openalex.org/W10",
        "publication_date": "2018-01-01",
        "referenced_works": ["https://openalex.org/W1", f"https://openalex.org/{A}"],
    }
    app = create_app(
        frontend_dist=tmp_path / "missing",
        db_path=tmp_path / "library.db",
        http_client=httpx2.Client(transport=httpx2.MockTransport(openalex)),
    )
    return TestClient(app), app


def test_graph_api_library_and_outside(tmp_path: Path) -> None:
    """그래프 API는 서재 논문을 모두 점으로, 서재 사이 인용을 선으로 주고, 고르면 서재 밖 논문을 더한다.

    @doc: docs/design/CitationGraph.md#5-테스트
    """
    client, app = make_client(tmp_path)
    base = client.post("/api/papers", json={"title": "Base", "openalex_id": A, "authors": ["Kim"]}).json()["id"]
    later = client.post("/api/papers", json={"title": "Later", "openalex_id": "W10"}).json()["id"]
    bare = client.post("/api/papers", json={"title": "No DOI"}).json()["id"]
    app.state.citations.run_once()

    body = client.get("/api/citations/graph").json()
    nodes = {node["id"]: node for node in body["nodes"]}
    assert set(nodes) == {f"p{base}", f"p{later}", f"p{bare}"}
    assert nodes[f"p{base}"]["year"] == 2017 and nodes[f"p{base}"]["authors"] == ["Kim"]
    assert nodes[f"p{bare}"]["has_data"] is False and nodes[f"p{base}"]["has_data"] is True
    assert {"source": f"p{later}", "target": f"p{base}", "kind": "cites", "shared_refs": 0, "cocited": 0} in body["edges"]

    wide = client.get("/api/citations/graph", params={"outside": 3}).json()
    outside = [node for node in wide["nodes"] if node["paper_id"] is None]
    assert len(outside) == 3 and all(node["score"] for node in outside)
    assert outside[0]["title"].startswith("Paper ")
    ids = {node["id"] for node in wide["nodes"]}
    assert all(edge["source"] in ids and edge["target"] in ids for edge in wide["edges"])
    assert client.get("/api/citations/graph", params={"outside": 31}).status_code == 422
