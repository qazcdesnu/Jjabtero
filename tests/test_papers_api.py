"""논문 검색과 추가 API를 검증한다.

@doc: docs/design/PaperSearch.md#5-테스트
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from fakes import fixed_responses, make_client
from jjabtero.app import create_app


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    """임시 데이터베이스와 가짜 검색 응답을 쓰는 앱의 테스트 클라이언트.

    @doc: docs/design/PaperSearch.md#5-테스트
    """
    app = create_app(
        frontend_dist=tmp_path / "missing",
        db_path=tmp_path / "library.db",
        http_client=make_client(fixed_responses),
    )
    return TestClient(app)


def test_search_returns_results_from_all_sources(client: TestClient) -> None:
    """검색원을 고르지 않으면 모든 검색원의 결과를 합쳐 돌려준다.

    @doc: docs/design/PaperSearch.md#5-테스트
    """
    response = client.get("/api/search", params={"q": " attention "})
    assert response.status_code == 200
    body = response.json()
    assert [result["source"] for result in body["results"]] == [
        "openalex",
        "openalex",
        "openalex",
        "arxiv",
    ]
    assert all(result["library_paper_id"] is None for result in body["results"])
    assert body["errors"] == []


def test_search_marks_papers_in_library(client: TestClient) -> None:
    """서재에 같은 DOI의 논문이 있으면 그 ID를 채운다.

    @doc: docs/design/PaperSearch.md#5-테스트
    """
    created = client.post(
        "/api/papers", json={"title": "Attention", "doi": "10.48550/arXiv.1706.03762"}
    ).json()
    results = client.get("/api/search", params={"q": "attention", "sources": "openalex"}).json()
    assert results["results"][0]["library_paper_id"] == created["id"]
    assert results["results"][1]["library_paper_id"] is None


@pytest.mark.parametrize(
    "params", [{"q": "   "}, {"q": "x", "sources": "scholar"}, {"q": "x", "limit": 0}]
)
def test_search_rejects_invalid_query(client: TestClient, params: dict[str, str]) -> None:
    """빈 검색어, 모르는 검색원, 범위 밖 결과 수는 422다.

    @doc: docs/design/PaperSearch.md#5-테스트
    """
    assert client.get("/api/search", params=params).status_code == 422


def test_create_paper_returns_201(client: TestClient) -> None:
    """논문을 만들면 201과 저장된 논문을 돌려준다.

    @doc: docs/design/PaperSearch.md#5-테스트
    """
    response = client.post(
        "/api/papers",
        json={
            "title": "Attention Is All You Need",
            "authors": ["Ashish Vaswani"],
            "item_type": "preprint",
            "year": 2017,
            "doi": "https://doi.org/10.48550/arXiv.1706.03762",
            "tags": ["transformer"],
        },
    )
    assert response.status_code == 201
    body = response.json()
    assert body["id"] > 0
    assert body["authors"] == ["Ashish Vaswani"]
    assert body["doi"] == "10.48550/arxiv.1706.03762"
    assert body["tags"] == ["transformer"]


def test_create_paper_duplicate_doi_returns_409(client: TestClient) -> None:
    """DOI가 겹치면 409와 이미 있는 논문 ID를 돌려준다.

    @doc: docs/design/PaperSearch.md#5-테스트
    """
    first = client.post("/api/papers", json={"title": "A", "doi": "10.1000/x"}).json()
    response = client.post("/api/papers", json={"title": "B", "doi": "10.1000/X"})
    assert response.status_code == 409
    assert response.json()["detail"]["paper_id"] == first["id"]


def test_create_paper_invalid_returns_422(client: TestClient) -> None:
    """검증 오류는 422다.

    @doc: docs/design/PaperSearch.md#5-테스트
    """
    assert client.post("/api/papers", json={"title": " "}).status_code == 422
