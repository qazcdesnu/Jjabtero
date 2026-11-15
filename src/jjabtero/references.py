"""리더의 참고문헌 항목 글로 논문을 찾는다.

@doc: docs/design/ReaderCitations.md#4-논문-찾기
"""

import re
from collections import OrderedDict
from typing import Any, Literal

import httpx2
from fastapi import APIRouter, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from jjabtero.citations import (
    _WORK_FIELDS,
    OPENALEX_WORKS_URL,
    CitationSync,
    CitedWork,
    OpenAlexBudgetError,
    _cited_work,
    _get,
    _work_row,
)
from jjabtero.models import Paper
from jjabtero.pdfs import open_access_pdf_url
from jjabtero.titles import normalize

# @doc: docs/design/ReaderCitations.md#4-논문-찾기
MATCH_MIN = 0.85
# @doc: docs/design/ReaderCitations.md#4-논문-찾기
MIN_TITLE_WORDS = 3
# @doc: docs/design/ReaderCitations.md#4-논문-찾기
YEAR_BONUS = 0.05
# @doc: docs/design/ReaderCitations.md#4-논문-찾기
SEARCH_LIMIT = 5
# @doc: docs/design/ReaderCitations.md#4-논문-찾기
SEARCH_CHARS = 250
# @doc: docs/design/ReaderCitations.md#4-논문-찾기
SEARCH_TRIES = 2
# @doc: docs/design/ReaderCitations.md#4-논문-찾기
CACHE_SIZE = 1000

_MARKER = re.compile(r"^\s*(\[[^\]]{1,12}\]|\(?\d{1,4}[.)])\s*")
_SPLIT = re.compile(r"(?<=[.?!])\s+")
# 마침표로 끝나도 문장 끝이 아닌 것: 이름 머리글자(대문자 한 글자), 흔한 줄임말.
# `et al.`은 대개 저자 목록의 끝이므로 문장 끝으로 본다.
_INITIAL = re.compile(r"(?:^|[\s(])[A-Z]\.$")
_ABBREVIATION = re.compile(r"(?:^|\s)(?:vol|no|pp|proc|conf|int|eds?|inc|jr|st|dr)\.$", re.IGNORECASE)
_VENUE_WORDS = {
    "proceedings", "proc", "conference", "conf", "journal", "transactions", "arxiv", "preprint", "corr", "abs",
    "pages", "pp", "vol", "volume", "workshop", "symposium", "press", "springer", "ieee", "acm", "advances",
    "international", "annual", "meeting", "neurips", "nips", "icml", "iclr", "cvpr", "iccv", "eccv", "acl", "emnlp",
}


def title_candidates(text: str) -> list[str]:
    """항목 글에서 제목일 만한 부분을 그럴듯한 순서로 돌려준다.

    마침표로 나눈 조각 가운데 낱말이 3개 이상인 것을 고르고, 저자 목록(대문자 이름과 쉼표, `and`)과
    게재처(학회·학술지 낱말, 숫자)처럼 보이는 조각을 뒤로 보낸다.

    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """
    body = _MARKER.sub("", " ".join(text.split()))
    pieces: list[str] = []
    for piece in _SPLIT.split(body):
        if pieces and (_INITIAL.search(pieces[-1]) or _ABBREVIATION.search(pieces[-1])):
            pieces[-1] = f"{pieces[-1]} {piece}"
        else:
            pieces.append(piece)
    scored = []
    for index, piece in enumerate(pieces):
        words = normalize(piece).split()
        if len(words) < MIN_TITLE_WORDS:
            continue
        raw = piece.split()
        capitalized = sum(word[:1].isupper() for word in raw) / len(raw)
        authors = (piece.count(",") + normalize(piece).split().count("and")) / len(raw) + capitalized
        venue = sum(word in _VENUE_WORDS for word in words) / len(words)
        digits = sum(word.isdigit() for word in words) / len(words)
        # 첫 조각은 대개 저자다. 같은 점수면 앞 조각을 고른다.
        penalty = authors * (1.5 if index == 0 else 1) + 2 * venue + 2 * digits
        scored.append((penalty, index, piece.rstrip(".")))
    return [piece for _, _, piece in sorted(scored)]


def match_reference(text: str, candidates: list[dict[str, Any]]) -> tuple[dict[str, Any], float] | None:
    """항목 글과 가장 잘 맞는 후보(제목 `title`, 연도 `year`)와 점수를 돌려준다. 맞는 것이 없으면 `None`이다.

    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """
    entry = normalize(text)
    padded = f" {entry} "
    words = set(entry.split())
    best: tuple[dict[str, Any], float] | None = None
    for candidate in candidates:
        title = normalize(candidate.get("title") or "")
        title_words = title.split()
        if len(title_words) < MIN_TITLE_WORDS:
            continue
        if f" {title} " in padded:
            score = 1.0
        else:
            score = sum(word in words for word in title_words) / len(title_words)
            if score < MATCH_MIN:
                continue
        if candidate.get("year") and str(candidate["year"]) in words:
            score += YEAR_BONUS
        if best is None or score > best[1]:
            best = (candidate, round(score, 4))
    return best


class ResolveIn(BaseModel):
    """참고문헌 항목 글.

    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """

    text: str = Field(min_length=1, max_length=2000)


class ReferenceMatch(BaseModel):
    """항목 글로 찾은 논문. 서재 상태와 공개 PDF 주소를 함께 가진다.

    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """

    state: Literal["found", "not_found"]
    source: Literal["references", "search"] | None = None
    work: CitedWork | None = None
    has_pdf: bool = False
    pdf_url: str | None = None


def _search(sync: CitationSync, query: str) -> list[dict[str, Any]]:
    body = _get(
        sync.http,
        OPENALEX_WORKS_URL,
        {"search": normalize(query)[:SEARCH_CHARS], "per-page": str(SEARCH_LIMIT), "select": _WORK_FIELDS},
    )
    stamp = sync.clock().isoformat()
    rows = [_work_row(work, stamp) for work in (body or {}).get("results", [])]
    rows = [row for row in rows if row["id"]]
    if rows:
        sync.store.save_works(rows)
    return rows


# 찾은 논문의 서지 정보, 찾은 경로, 공개 PDF 주소. 서재 상태는 바뀌므로 기억하지 않는다.
_Found = tuple[dict[str, Any], Literal["references", "search"], str | None] | None


def _cache(request: Request) -> OrderedDict[tuple[int, str], _Found]:
    cache = getattr(request.app.state, "reference_matches", None)
    if cache is None:
        cache = OrderedDict()
        request.app.state.reference_matches = cache
    return cache


# @doc: docs/design/ReaderCitations.md#4-논문-찾기
router = APIRouter(prefix="/api/papers")


@router.post("/{paper_id}/references/resolve")
def resolve_reference(paper_id: int, body: ResolveIn, request: Request) -> ReferenceMatch:
    """`POST /api/papers/{paper_id}/references/resolve`를 처리한다.

    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """
    sync: CitationSync = request.app.state.citations
    text = " ".join(body.text.split())
    with Session(sync.library_engine) as session:
        paper = session.get(Paper, paper_id)
        if paper is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, f"논문이 없습니다: {paper_id}")
        work_id = paper.openalex_id
        owners: dict[str, Paper] = {}
        for other in session.scalars(select(Paper)):
            if other.openalex_id:
                owners[other.openalex_id] = other
            if other.doi:
                owners[other.doi] = other
        pdf_owners = {key: (other.id, other.pdf is not None) for key, other in owners.items()}

    cache = _cache(request)
    key = (paper_id, text)
    if key in cache:
        cache.move_to_end(key)
        found = cache[key]
    else:
        found = _find(sync, work_id, text)
        cache[key] = found
        while len(cache) > CACHE_SIZE:
            cache.popitem(last=False)
    if found is None:
        return ReferenceMatch(state="not_found")
    row, source, pdf_url = found
    work = _cited_work({**row, "work": row["id"]}, {key: owner[0] for key, owner in pdf_owners.items()})
    owner = pdf_owners.get(work.openalex_id) or (pdf_owners.get(work.doi) if work.doi else None)
    return ReferenceMatch(
        state="found", source=source, work=work, has_pdf=bool(owner and owner[1]), pdf_url=pdf_url
    )


def _find(sync: CitationSync, work_id: str | None, text: str) -> _Found:
    """이 논문의 참고문헌에서, 없으면 OpenAlex 검색에서 찾고 공개 PDF 주소를 붙인다.

    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """
    found = None
    source: Literal["references", "search"] = "references"
    if work_id:
        _, references, _ = sync.store.paper_lists(work_id)
        found = match_reference(text, [{**row, "id": row["work"]} for row in references])
    if found is None:
        source = "search"
        # 글 전체로 검색하면 저자·게재처 낱말 때문에 엉뚱한 결과가 나오므로 제목일 만한 조각으로 검색한다.
        for query in title_candidates(text)[:SEARCH_TRIES]:
            try:
                found = match_reference(text, _search(sync, query))
            except (OpenAlexBudgetError, httpx2.HTTPError) as error:
                raise HTTPException(status.HTTP_502_BAD_GATEWAY, f"OpenAlex에서 찾지 못했습니다: {error}") from error
            if found:
                break
    if found is None:
        return None
    row = found[0]
    doi = _cited_work({**row, "work": row["id"]}, {}).doi
    try:
        located = open_access_pdf_url(sync.http, row["id"], doi)
    except httpx2.HTTPError:
        located = None
    return row, source, located[0] if located else None
