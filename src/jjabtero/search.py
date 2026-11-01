"""외부 논문 검색.

@doc: docs/design/PaperSearch.md#2-검색-결과
"""

import os
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable, Sequence
from typing import Any

import httpx2
from pydantic import BaseModel

from jjabtero.library import normalize_doi

OPENALEX_URL = "https://api.openalex.org/works"
ARXIV_URL = "https://export.arxiv.org/api/query"

_OPENALEX_TYPES = {
    "conference-paper": "conference-paper",
    "review": "journal-article",
    "preprint": "preprint",
    "book": "book",
    "book-chapter": "book-chapter",
    "report": "report",
    "dissertation": "thesis",
}
_ATOM = "{http://www.w3.org/2005/Atom}"
_ARXIV = "{http://arxiv.org/schemas/atom}"
_ARXIV_VERSION = re.compile(r"v\d+$")
_SPACES = re.compile(r"\s+")
# arXiv 검색은 이 낱말들을 색인하지 않아, AND로 이으면 결과가 비게 된다(Lucene 영어 불용어).
_ARXIV_STOPWORDS = frozenset(
    "a an and are as at be but by for if in into is it no not of on or such "
    "that the their then there these they this to was will with".split()
)


class SearchResult(BaseModel):
    """검색 결과 하나.

    @doc: docs/design/PaperSearch.md#2-검색-결과
    """

    source: str
    source_id: str
    title: str
    authors: list[str]
    item_type: str
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    url: str | None = None
    library_paper_id: int | None = None


class SourceError(BaseModel):
    """검색원 하나의 실패.

    @doc: docs/design/PaperSearch.md#2-검색-결과
    """

    source: str
    message: str


class SearchResponse(BaseModel):
    """검색원들의 결과를 합친 응답.

    @doc: docs/design/PaperSearch.md#2-검색-결과
    """

    results: list[SearchResult]
    errors: list[SourceError]


def _clean(text: str | None) -> str:
    return _SPACES.sub(" ", text or "").strip()


def _safe_doi(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return normalize_doi(value)
    except ValueError:
        return None


def _openalex_item_type(work: dict[str, Any]) -> str:
    work_type = work.get("type")
    if work_type == "article":
        source = (work.get("primary_location") or {}).get("source") or {}
        return "conference-paper" if source.get("type") == "conference" else "journal-article"
    return _OPENALEX_TYPES.get(work_type, "other")


def _openalex_result(work: dict[str, Any]) -> SearchResult | None:
    title = _clean(work.get("display_name"))
    if not title:
        return None
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    return SearchResult(
        source="openalex",
        source_id=work["id"],
        title=title,
        authors=[
            _clean(authorship["author"]["display_name"])
            for authorship in work.get("authorships") or []
            if (authorship.get("author") or {}).get("display_name")
        ],
        item_type=_openalex_item_type(work),
        year=work.get("publication_year"),
        venue=_clean(source.get("display_name")) or None,
        doi=_safe_doi(work.get("doi")),
        url=location.get("landing_page_url") or work.get("doi") or work["id"],
    )


def search_openalex(client: httpx2.Client, query: str, limit: int) -> list[SearchResult]:
    """OpenAlex에서 논문을 검색한다.

    @doc: docs/design/PaperSearch.md#2-검색-결과
    """
    params = {
        "search": query,
        "per-page": str(limit),
        "select": "id,display_name,doi,publication_year,type,authorships,primary_location",
    }
    api_key = os.environ.get("OPENALEX_API_KEY")
    if api_key:
        params["api_key"] = api_key
    response = client.get(OPENALEX_URL, params=params)
    response.raise_for_status()
    results = (_openalex_result(work) for work in response.json().get("results", []))
    return [result for result in results if result is not None]


def _arxiv_query(query: str) -> str:
    words = query.split()
    kept = [word for word in words if word.lower() not in _ARXIV_STOPWORDS] or words
    return " AND ".join(f"all:{word}" for word in kept)


def _arxiv_result(entry: ET.Element) -> SearchResult | None:
    title = _clean(entry.findtext(f"{_ATOM}title"))
    if not title:
        return None
    abs_url = _clean(entry.findtext(f"{_ATOM}id"))
    arxiv_id = _ARXIV_VERSION.sub("", abs_url.rsplit("/abs/", 1)[-1])
    published = _clean(entry.findtext(f"{_ATOM}published"))
    journal_doi = _safe_doi(entry.findtext(f"{_ARXIV}doi"))
    return SearchResult(
        source="arxiv",
        source_id=arxiv_id,
        title=title,
        authors=[
            _clean(author.findtext(f"{_ATOM}name"))
            for author in entry.findall(f"{_ATOM}author")
            if _clean(author.findtext(f"{_ATOM}name"))
        ],
        item_type="preprint",
        year=int(published[:4]) if published[:4].isdigit() else None,
        venue="arXiv",
        doi=journal_doi or normalize_doi(f"10.48550/arXiv.{arxiv_id}"),
        url=abs_url,
    )


def search_arxiv(client: httpx2.Client, query: str, limit: int) -> list[SearchResult]:
    """arXiv에서 논문을 검색한다.

    @doc: docs/design/PaperSearch.md#2-검색-결과
    """
    response = client.get(
        ARXIV_URL, params={"search_query": _arxiv_query(query), "max_results": str(limit)}
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)
    results = (_arxiv_result(entry) for entry in root.findall(f"{_ATOM}entry"))
    return [result for result in results if result is not None]


# @doc: docs/design/PaperSearch.md#2-검색-결과
SOURCES: dict[str, Callable[[httpx2.Client, str, int], list[SearchResult]]] = {
    "openalex": search_openalex,
    "arxiv": search_arxiv,
}


def search_papers(
    client: httpx2.Client, query: str, sources: Sequence[str], limit: int
) -> SearchResponse:
    """고른 검색원에서 검색하고 결과를 합친다.

    @doc: docs/design/PaperSearch.md#2-검색-결과
    """
    results: list[SearchResult] = []
    errors: list[SourceError] = []
    seen_dois: set[str] = set()
    for name in sources:
        try:
            found = SOURCES[name](client, query, limit)
        except (httpx2.HTTPError, ValueError, KeyError, ET.ParseError) as error:
            errors.append(SourceError(source=name, message=str(error) or type(error).__name__))
            continue
        for result in found:
            if result.doi and result.doi in seen_dois:
                continue
            if result.doi:
                seen_dois.add(result.doi)
            results.append(result)
    return SearchResponse(results=results, errors=errors)
