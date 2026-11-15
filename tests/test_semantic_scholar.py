"""Semantic Scholar 참고문헌으로 서재 논문 사이 인용을 확인하는 일을 검증한다.

@doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
"""

from datetime import UTC, datetime, timedelta
from pathlib import Path

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from jjabtero.app import create_app
from jjabtero.semantic_scholar import (
    PaperKeys,
    S2BudgetError,
    S2Store,
    arxiv_id,
    fetch_references,
    library_cites,
    paper_keys,
    refresh_references,
    same_paper,
)
from test_citations import FakeOpenAlex

NOW = datetime(2026, 11, 15, tzinfo=UTC)


def ref(title: str, doi: str | None = None, arxiv: str | None = None) -> dict:
    """Semantic Scholar 참고문헌 항목 하나.

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """
    ids = {key: value for key, value in (("DOI", doi), ("ArXiv", arxiv)) if value}
    return {"citedPaper": {"paperId": "x", "title": title, "externalIds": ids}}


class FakeS2:
    """DOI별 참고문헌과 제목 맞추기에 답하는 가짜 Semantic Scholar. 받은 요청을 기록한다.

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """

    def __init__(self, references: dict[str, list[dict]], titles: dict[str, str] | None = None) -> None:
        self.references = references
        self.titles = titles or {}
        self.paths: list[str] = []
        self.limited = False

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        path = request.url.path.removeprefix("/graph/v1/paper/")
        self.paths.append(path)
        if self.limited:
            return httpx2.Response(429, json={"message": "Too Many Requests"})
        if path == "search/match":
            query = request.url.params["query"]
            for paper_id, title in self.titles.items():
                if title.lower() == query.lower():
                    return httpx2.Response(200, json={"data": [{"paperId": paper_id, "title": title}]})
            return httpx2.Response(404, json={"error": "Title match not found"})
        key = path.removesuffix("/references")
        if key.lower() in {k.lower() for k in self.references}:
            data = next(v for k, v in self.references.items() if k.lower() == key.lower())
            return httpx2.Response(200, json={"data": data})
        return httpx2.Response(404, json={"error": "not found"})


def client_for(fake: FakeS2) -> httpx2.Client:
    """가짜 Semantic Scholar로 가는 HTTP 클라이언트.

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """
    return httpx2.Client(transport=httpx2.MockTransport(fake))


def test_identifiers() -> None:
    """arXiv ID는 버전과 머리를 떼고, arXiv DOI에서 arXiv ID를 얻으며, 짧은 제목은 쓰지 않는다.

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """
    assert arxiv_id("arXiv:1706.03762v5") == "1706.03762"
    keys = paper_keys("10.48550/arXiv.1706.03762", "Attention Is All You Need")
    assert keys == PaperKeys("10.48550/arxiv.1706.03762", "1706.03762", "attention is all you need")
    assert paper_keys(None, "Adam").title is None
    assert same_paper(keys, PaperKeys(None, "1706.03762", None))
    assert same_paper(keys, PaperKeys("10.5555/other", None, "attention is all you need"))
    assert not same_paper(keys, PaperKeys("10.5555/other", "1234.5678", "something else entirely"))


def test_fetch_references_by_doi_then_title() -> None:
    """DOI로 받고, DOI로 없으면 제목이 똑같은 논문으로 받으며, 제목이 다르면 없음이고, 429는 알린다.

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """
    fake = FakeS2(
        {"DOI:10.1/a": [ref("Long Short-Term Memory", doi="10.1162/NECO")], "P9": [ref("Deep Residual Learning for Image Recognition")]},
        {"P9": "Squeeze-and-Excitation Networks"},
    )
    http = client_for(fake)
    assert fetch_references(http, "10.1/a") == [PaperKeys("10.1162/neco", None, "long short term memory")]
    by_title = fetch_references(http, "10.1109/cvpr.2018.00745", "Squeeze-and-Excitation Networks")
    assert by_title == [PaperKeys(None, None, "deep residual learning for image recognition")]
    assert fetch_references(http, "10.1/none", "A Paper That Does Not Exist") is None
    assert fetch_references(http, "10.1/none") is None
    fake.limited = True
    with pytest.raises(S2BudgetError):
        fetch_references(http, "10.1/a")


def test_refresh_saves_skips_fresh_and_stops_on_limit(tmp_path: Path) -> None:
    """오래된 논문만 받고, 7일 안에 받은 논문은 건너뛰며, 429에서 멈추고, 서재에 없는 논문은 지운다.

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """
    store = S2Store(create_engine(f"sqlite:///{tmp_path / 'cache.db'}"))
    fake = FakeS2({"DOI:10.1/a": [ref("Long Short-Term Memory")], "DOI:10.1/b": []})
    http = client_for(fake)
    papers = [("10.1/a", "A"), ("10.1/b", "B"), ("10.1/c", "C")]
    assert refresh_references(http, store, papers, NOW) == (3, "")
    assert store.references() == {"10.1/a": [PaperKeys(None, None, "long short term memory")]}
    assert store.checked_count({"10.1/a", "10.1/b", "10.1/c"}) == 2
    assert refresh_references(http, store, papers, NOW + timedelta(days=1)) == (0, "")
    fake.limited = True
    count, error = refresh_references(http, store, papers, NOW + timedelta(days=8))
    assert count == 0 and "잠시 막았습니다" in error
    refresh_references(http, store, [("10.1/b", "B")], NOW + timedelta(days=8))
    assert store.references() == {}


def test_library_cites_matches_by_doi_arxiv_and_title() -> None:
    """참고문헌을 서재 논문과 DOI, arXiv ID, 제목으로 맞추고, 자기 자신은 잇지 않는다.

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """
    papers = [
        ("p1", "10.48550/arxiv.1706.03762", paper_keys("10.48550/arxiv.1706.03762", "Attention Is All You Need")),
        ("p2", "10.1/bahdanau", paper_keys("10.1/bahdanau", "Neural Machine Translation by Jointly Learning")),
        ("p3", "10.1/bert", paper_keys("10.1/bert", "BERT: Pre-training of Deep Bidirectional Transformers")),
        ("p4", None, paper_keys(None, "Long Short-Term Memory")),
    ]
    references = {
        "10.48550/arxiv.1706.03762": [
            PaperKeys(None, None, "neural machine translation by jointly learning"),
            PaperKeys(None, None, "long short term memory"),
            PaperKeys(None, "1706.03762", None),
        ],
        "10.1/bert": [PaperKeys(None, "1706.03762", None)],
    }
    assert library_cites(papers, references) == {("p1", "p2"), ("p1", "p4"), ("p3", "p1")}


class FakeBoth(FakeOpenAlex):
    """OpenAlex와 Semantic Scholar 둘 다 답하는 가짜.

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """

    def __init__(self, s2: FakeS2) -> None:
        super().__init__()
        self.s2 = s2

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        if request.url.host == "api.semanticscholar.org":
            return self.s2(request)
        return super().__call__(request)


def test_graph_uses_semantic_scholar_cites_and_status(tmp_path: Path) -> None:
    """OpenAlex 참고문헌에 없는 서재 논문 사이 인용을 Semantic Scholar로 찾아 그래프에 긋고, 상태에 확인한 수를 보인다.

    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """
    s2 = FakeS2({"DOI:10.1/a": [ref("Gated Recurrent Units Explained Here", arxiv="1412.3555v1")]})
    app = create_app(
        frontend_dist=tmp_path / "missing",
        db_path=tmp_path / "library.db",
        http_client=httpx2.Client(transport=httpx2.MockTransport(FakeBoth(s2))),
    )
    client = TestClient(app)
    base = client.post("/api/papers", json={"title": "Base", "doi": "10.1/a"}).json()["id"]
    gru = client.post("/api/papers", json={"title": "GRU", "doi": "10.48550/arXiv.1412.3555"}).json()["id"]
    app.state.citations.run_once()

    edges = client.get("/api/citations/graph").json()["edges"]
    assert {"source": f"p{base}", "target": f"p{gru}", "kind": "cites", "shared_refs": 0, "cocited": 0} in edges
    status = client.get("/api/citations/status").json()
    assert status["s2_checked"] == 1
    assert any(path.startswith("DOI:10.1/a") for path in s2.paths)
