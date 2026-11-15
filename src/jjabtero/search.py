"""외부 논문 검색.

@doc: docs/design/PaperSearch.md#2-검색-결과
"""

import os
import re
import xml.etree.ElementTree as ET
from collections.abc import Callable, Sequence
from typing import Any, Literal

import httpx2
from pydantic import BaseModel

from jjabtero.library import normalize_doi
from jjabtero.titles import normalize

# @doc: docs/design/PaperSearch.md#2-검색-결과
SearchMode = Literal["all", "title", "author"]
# 저자 검색어에서 여러 저자를 나누는 기호.
_AUTHOR_SPLIT = re.compile(r"\s*(?:[,;&]|\band\b)\s*", re.IGNORECASE)

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


def author_names(query: str) -> list[str]:
    """저자 검색어를 저자 이름들로 나눈다. 쉼표, 세미콜론, `&`, `and`로 나눈다.

    @doc: docs/design/PaperSearch.md#2-검색-결과
    """
    return [name for name in (_clean(part) for part in _AUTHOR_SPLIT.split(query)) if name]


def _openalex_filter_value(text: str) -> str:
    # OpenAlex 필터는 쉼표로 여러 필터를 나누므로 값 안의 쉼표와 콜론을 뗀다.
    return _clean(text.replace(",", " ").replace(":", " "))


def search_openalex(client: httpx2.Client, query: str, limit: int, mode: SearchMode = "all") -> list[SearchResult]:
    """OpenAlex에서 논문을 검색한다. 제목은 `title.search`, 저자는 `raw_author_name.search` 필터로 찾는다.

    @doc: docs/design/PaperSearch.md#2-검색-결과
    """
    params = {
        "per-page": str(limit),
        "select": "id,display_name,doi,publication_year,type,authorships,primary_location",
    }
    if mode == "title":
        params["filter"] = f"title.search:{_openalex_filter_value(query)}"
    elif mode == "author":
        names = author_names(query) or [query]
        params["filter"] = ",".join(f"raw_author_name.search:{_openalex_filter_value(name)}" for name in names)
    else:
        params["search"] = query
    api_key = os.environ.get("OPENALEX_API_KEY")
    if api_key:
        params["api_key"] = api_key
    response = client.get(OPENALEX_URL, params=params)
    response.raise_for_status()
    results = (_openalex_result(work) for work in response.json().get("results", []))
    return [result for result in results if result is not None]


def _arxiv_query(query: str, mode: SearchMode = "all") -> str:
    """arXiv 검색식을 만든다. 일반은 `all:`, 제목은 `ti:`, 저자는 `au:`를 AND로 잇는다.

    @doc: docs/design/PaperSearch.md#2-검색-결과
    """
    if mode == "author":
        names = author_names(query) or [query]
        return " AND ".join(f'au:"{name}"' if " " in name else f"au:{name}" for name in names)
    words = query.split()
    kept = [word for word in words if word.lower() not in _ARXIV_STOPWORDS] or words
    field = "ti" if mode == "title" else "all"
    return " AND ".join(f"{field}:{word}" for word in kept)


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


def search_arxiv(client: httpx2.Client, query: str, limit: int, mode: SearchMode = "all") -> list[SearchResult]:
    """arXiv에서 논문을 검색한다. 제목은 `ti:`, 저자는 `au:`로 찾는다.

    @doc: docs/design/PaperSearch.md#2-검색-결과
    """
    response = client.get(
        ARXIV_URL, params={"search_query": _arxiv_query(query, mode), "max_results": str(limit)}
    )
    response.raise_for_status()
    root = ET.fromstring(response.content)
    results = (_arxiv_result(entry) for entry in root.findall(f"{_ATOM}entry"))
    return [result for result in results if result is not None]


# @doc: docs/design/PaperSearch.md#2-검색-결과
SOURCES: dict[str, Callable[[httpx2.Client, str, int, SearchMode], list[SearchResult]]] = {
    "openalex": search_openalex,
    "arxiv": search_arxiv,
}


def _author_score(result: SearchResult, names: list[str]) -> float:
    authors = [set(normalize(author).split()) for author in result.authors]
    wanted = [set(normalize(name).split()) for name in names]
    wanted = [words for words in wanted if words]
    if not wanted:
        return 0.0
    return sum(any(words <= author for author in authors) for words in wanted) / len(wanted)


def relevance(result: SearchResult, query: str, mode: SearchMode = "all") -> float:
    """검색어와 결과가 얼마나 맞는지. 클수록 앞에 둔다.

    제목이 검색어와 같으면 3, 검색어가 제목 안에 그대로 있으면 2, 아니면 검색어 낱말이 제목에 있는 비율에
    제목 낱말 가운데 검색어 낱말의 비율 절반을 더한다. 저자 검색은 찾는 저자가 결과 저자에 있는 비율이다.
    일반 검색은 제목 점수에 검색어 낱말이 저자 이름에 있는 비율의 절반을 더한다.

    @doc: docs/design/PaperSearch.md#2-검색-결과
    """
    if mode == "author":
        return _author_score(result, author_names(query) or [query])
    wanted = normalize(query)
    title = normalize(result.title)
    words = set(wanted.split())
    title_words = set(title.split())
    if not words or not title_words:
        return 0.0
    if title == wanted:
        score = 3.0
    elif f" {wanted} " in f" {title} ":
        score = 2.0
    else:
        shared = len(words & title_words)
        score = shared / len(words) + 0.5 * shared / len(title_words)
    if mode == "all":
        author_words = set(normalize(" ".join(result.authors)).split())
        score += 0.5 * len(words & author_words) / len(words)
    return score


def search_papers(
    client: httpx2.Client, query: str, sources: Sequence[str], limit: int, mode: SearchMode = "all"
) -> SearchResponse:
    """고른 검색원에서 검색하고, DOI가 같은 결과를 빼고, 검색어와 맞는 정도로 다시 정렬한다.

    @doc: docs/design/PaperSearch.md#2-검색-결과
    """
    results: list[SearchResult] = []
    errors: list[SourceError] = []
    seen_dois: set[str] = set()
    for name in sources:
        try:
            found = SOURCES[name](client, query, limit, mode)
        except (httpx2.HTTPError, ValueError, KeyError, ET.ParseError) as error:
            errors.append(SourceError(source=name, message=str(error) or type(error).__name__))
            continue
        for result in found:
            if result.doi and result.doi in seen_dois:
                continue
            if result.doi:
                seen_dois.add(result.doi)
            results.append(result)
    # 검색원마다 순위 기준이 달라, 이어 붙이기만 하면 제목이 똑같은 결과도 뒤에 묻힌다. 같은 점수는 원래 순서다.
    # 저자 검색은 점수가 같은 결과가 많아 같은 점수끼리는 최신 논문을 앞에 둔다.
    newest = (lambda result: -(result.year or 0)) if mode == "author" else (lambda result: 0)
    results.sort(key=lambda result: (-relevance(result, query, mode), newest(result)))
    return SearchResponse(results=results, errors=errors)
