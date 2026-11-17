"""서재 인용 그래프의 데이터와 API를 검증한다.

@doc: docs/design/CitationGraph.md#5-테스트
@doc: docs/design/Tags.md#6-테스트
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx2
from fastapi.testclient import TestClient

from jjabtero.app import create_app
from jjabtero.citation_graph import GraphEdge, library_edges, outside_edges, reference_edges
from jjabtero.citations import CitationStore, Recommendation, Relation
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


def test_reference_edges_add_cites_and_drop_related() -> None:
    """서재 밖 논문의 참고문헌으로 그래프 안의 점을 잇고, 같은 두 점의 가까움 선은 빼며, 겹치거나 밖의 논문은 잇지 않는다.

    @doc: docs/design/CitationGraph.md#5-테스트
    """
    edges = [
        GraphEdge(source="p1", target="W9", kind="cites"),
        GraphEdge(source="p2", target="W9", kind="related", shared_refs=2),
        GraphEdge(source="p2", target="W8", kind="related", shared_refs=2),
    ]
    node_ids = {"WA": "p1", "WB": "p2", "W8": "W8", "W9": "W9"}
    refs = {"W9": ["WB", "W8", "W9", "W404"], "W8": ["W9", "W9"], "WX": ["W9"]}
    got = {(e.source, e.target, e.kind) for e in reference_edges(refs, node_ids, edges)}
    assert got == {("p1", "W9", "cites"), ("W9", "p2", "cites"), ("W9", "W8", "cites"), ("W8", "W9", "cites"), ("p2", "W8", "related")}


def test_outside_references_refresh_after_a_week(tmp_path: Path) -> None:
    """서재 밖 논문의 참고문헌은 없거나 7일이 지난 것만 다시 받을 대상이다.

    @doc: docs/design/CitationGraph.md#5-테스트
    """
    store = CitationStore(tmp_path / "citations.db")
    now = datetime(2026, 11, 18, tzinfo=UTC)
    store.save_outside_references({"W1": ["W2"], "W3": []}, now)
    assert store.outside_references({"W1", "W3", "W9"}) == {"W1": ["W2"], "W3": []}
    assert store.stale_outside_references({"W1", "W9"}, now + timedelta(days=6)) == ["W9"]
    assert store.stale_outside_references({"W1", "W9"}, now + timedelta(days=8)) == ["W1", "W9"]


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
    app.state.fake_openalex = openalex
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


def test_graph_api_outside_references(tmp_path: Path) -> None:
    """서재 밖 논문의 참고문헌을 한 번 받아 두고 그 인용 선을 그린다. 받지 못해도 그래프는 나온다.

    @doc: docs/design/CitationGraph.md#5-테스트
    """
    client, app = make_client(tmp_path)
    openalex = app.state.fake_openalex
    client.post("/api/papers", json={"title": "Base", "openalex_id": A})
    app.state.citations.run_once()
    candidates = ["W1", "W2", "W50", "W60", "W10", "W11", "W12"]
    openalex.refs = {work_id: [A, *candidates] for work_id in candidates}

    def ref_requests() -> int:
        return sum(1 for request in openalex.requests if request.url.params.get("select") == "id,referenced_works")

    body = client.get("/api/citations/graph", params={"outside": 3}).json()
    outside = [node["id"] for node in body["nodes"] if node["paper_id"] is None]
    edges = {(edge["source"], edge["target"], edge["kind"]) for edge in body["edges"]}
    assert len(outside) == 3 and ref_requests() == 1
    assert all((a, b, "cites") in edges for a in outside for b in outside if a != b)
    assert not any(kind == "related" and source in outside or kind == "related" and target in outside for source, target, kind in edges)
    client.get("/api/citations/graph", params={"outside": 3})
    assert ref_requests() == 1

    with app.state.citations.store.engine.begin() as connection:
        connection.exec_driver_sql("DELETE FROM outside_references")
    openalex.budget_left = 0
    assert len(client.get("/api/citations/graph", params={"outside": 3}).json()["nodes"]) == 4


def test_graph_api_filters_by_tags(tmp_path: Path) -> None:
    """태그를 주면 그 태그를 모두 가진 서재 논문만 점이 되고, 서재 밖 추천은 그 논문들로 계산하되 서재의 다른 논문은 추천하지 않는다.

    @doc: docs/design/CitationGraph.md#5-테스트
    """
    client, app = make_client(tmp_path)
    base = client.post("/api/papers", json={"title": "Base", "openalex_id": A, "tags": ["nlp", "core"]}).json()["id"]
    later = client.post("/api/papers", json={"title": "Later", "openalex_id": "W10", "tags": ["nlp"]}).json()["id"]
    client.post("/api/papers", json={"title": "Other", "openalex_id": "W11", "tags": ["cv"]})
    app.state.citations.run_once()

    nlp = client.get("/api/citations/graph", params={"tags": ["nlp"]}).json()
    assert {node["id"] for node in nlp["nodes"]} == {f"p{base}", f"p{later}"}
    both = client.get("/api/citations/graph", params=[("tags", "nlp"), ("tags", "core")]).json()
    assert {node["id"] for node in both["nodes"]} == {f"p{base}"}
    assert client.get("/api/citations/graph", params={"tags": ["none"]}).json() == {"nodes": [], "edges": []}
    wide = client.get("/api/citations/graph", params={"tags": ["core"], "outside": 5}).json()
    outside_ids = {node["openalex_id"] for node in wide["nodes"] if node["paper_id"] is None}
    assert outside_ids and "W10" not in outside_ids and "W11" not in outside_ids


def test_publication_when_precision() -> None:
    """1월 1일은 날짜로 믿지 않고, arXiv 번호에서 연·월을 얻으며, 그 밖에는 연도만 안다.

    @doc: docs/design/CitationGraph.md#5-테스트
    """
    from jjabtero.citation_graph import publication_when

    assert publication_when("2017-06-12", 2017, None) == ("2017-06-12", "day")
    assert publication_when("2018-01-01", 2018, "10.18653/v1/n18-2074") == ("2018", "year")
    assert publication_when("2018-01-01", 2018, "10.48550/arxiv.1803.02155") == ("2018-03", "month")
    assert publication_when(None, None, "10.48550/arxiv.cs/0612001") == ("2006-12", "month")
    assert publication_when(None, 2014, None) == ("2014", "year")
    assert publication_when(None, None, None) == (None, None)


def test_graph_nodes_carry_dates(tmp_path: Path) -> None:
    """그래프의 서재 점은 인용 데이터의 공개일을, 서재 밖 점은 서지 정보의 공개일을 정밀도와 함께 가진다.

    @doc: docs/design/CitationGraph.md#5-테스트
    """
    client, app = make_client(tmp_path)
    base = client.post("/api/papers", json={"title": "Base", "openalex_id": A}).json()["id"]
    app.state.citations.run_once()
    body = client.get("/api/citations/graph", params={"outside": 3}).json()
    nodes = {node["id"]: node for node in body["nodes"]}
    assert (nodes[f"p{base}"]["date"], nodes[f"p{base}"]["date_precision"]) == ("2017-06-12", "day")
    outside = [node for node in body["nodes"] if node["paper_id"] is None]
    assert all(node["date_precision"] in ("day", "year") for node in outside)
