"""외부 논문 검색을 검증한다.

@doc: docs/design/PaperSearch.md#5-테스트
"""

import httpx2
import pytest

from fakes import ARXIV_BODY, fixed_responses, make_client
from jjabtero.search import search_arxiv, search_openalex, search_papers


def test_search_openalex_maps_fields() -> None:
    """OpenAlex 결과의 항목을 바꾸고, 제목 없는 결과는 버린다.

    @doc: docs/design/PaperSearch.md#5-테스트
    """
    results = search_openalex(make_client(fixed_responses), "attention", 10)
    assert [result.title for result in results] == [
        "Attention Is All You Need",
        "Speech Separation",
        "Thesis",
    ]
    first, second, third = results
    assert first.authors == ["Ashish Vaswani", "Noam Shazeer"]
    assert (first.item_type, first.year, first.venue) == ("preprint", 2017, "arXiv")
    assert first.doi == "10.48550/arxiv.1706.03762"
    assert first.url == "https://arxiv.org/abs/1706.03762"
    assert second.item_type == "conference-paper"
    assert second.doi is None and second.url == "https://openalex.org/W2"
    assert third.item_type == "thesis"


def test_search_openalex_sends_query_and_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    """검색어와 결과 수를 보내고, 환경 변수가 있으면 API 키를 붙인다.

    @doc: docs/design/PaperSearch.md#5-테스트
    """
    monkeypatch.setenv("OPENALEX_API_KEY", "secret")
    seen: list[httpx2.Request] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return httpx2.Response(200, json={"results": []})

    search_openalex(make_client(handler), "graph networks", 5)
    params = seen[0].url.params
    assert (params["search"], params["per-page"], params["api_key"]) == ("graph networks", "5", "secret")


def test_search_arxiv_maps_fields_and_doi() -> None:
    """arXiv 결과의 공백을 정리하고, DOI가 없으면 arXiv DOI를 만든다.

    @doc: docs/design/PaperSearch.md#5-테스트
    """
    first, second = search_arxiv(make_client(fixed_responses), "attention", 10)
    assert first.title == "Attention Is All You Need"
    assert first.authors == ["Ashish Vaswani", "Noam Shazeer"]
    assert (first.item_type, first.year, first.venue) == ("preprint", 2017, "arXiv")
    assert first.source_id == "1706.03762"
    assert first.doi == "10.48550/arxiv.1706.03762"
    assert first.url == "http://arxiv.org/abs/1706.03762v7"
    assert second.doi == "10.1000/journal.1"


def test_search_arxiv_drops_stopwords_from_query() -> None:
    """낱말을 AND로 잇고 불용어는 빼며, 모두 불용어면 그대로 쓴다.

    @doc: docs/design/PaperSearch.md#5-테스트
    """
    queries: list[str] = []

    def handler(request: httpx2.Request) -> httpx2.Response:
        queries.append(request.url.params["search_query"])
        return httpx2.Response(200, text="<feed xmlns='http://www.w3.org/2005/Atom'/>")

    client = make_client(handler)
    search_arxiv(client, "attention is all you need", 3)
    search_arxiv(client, "to be", 3)
    assert queries == [
        "all:attention AND all:all AND all:you AND all:need",
        "all:to AND all:be",
    ]


def test_search_papers_merges_and_removes_duplicate_doi() -> None:
    """검색원 순서대로 잇고, 앞 결과와 DOI가 같은 결과는 뺀다.

    @doc: docs/design/PaperSearch.md#5-테스트
    """
    response = search_papers(make_client(fixed_responses), "attention", ["openalex", "arxiv"], 10)
    assert [(result.source, result.title) for result in response.results] == [
        ("openalex", "Attention Is All You Need"),
        ("openalex", "Speech Separation"),
        ("openalex", "Thesis"),
        ("arxiv", "Published Later"),
    ]
    assert response.errors == []


def test_search_papers_reports_failed_source() -> None:
    """한 검색원이 실패해도 나머지 결과를 돌려주고 실패를 알린다.

    @doc: docs/design/PaperSearch.md#5-테스트
    """

    def handler(request: httpx2.Request) -> httpx2.Response:
        if request.url.host == "api.openalex.org":
            return httpx2.Response(503)
        return httpx2.Response(200, text=ARXIV_BODY)

    response = search_papers(make_client(handler), "attention", ["openalex", "arxiv"], 10)
    assert [result.source for result in response.results] == ["arxiv", "arxiv"]
    assert [error.source for error in response.errors] == ["openalex"]


def test_search_papers_reports_unparsable_response() -> None:
    """해석할 수 없는 응답도 실패로 알린다.

    @doc: docs/design/PaperSearch.md#5-테스트
    """
    client = make_client(lambda request: httpx2.Response(200, text="not xml"))
    response = search_papers(client, "attention", ["arxiv"], 10)
    assert response.results == []
    assert [error.source for error in response.errors] == ["arxiv"]
