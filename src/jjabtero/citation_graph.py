"""서재 인용 그래프의 데이터와 API.

@doc: docs/design/CitationGraph.md#2-그래프-데이터
@doc: docs/design/CitationGraph.md#3-api
"""

import json
import re
from typing import Annotated, Any, Literal

import httpx2
from fastapi import APIRouter, Query, Request
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from jjabtero.citations import (
    CitationSync,
    OpenAlexBudgetError,
    Recommendation,
    lookup_references,
    lookup_works,
    recommend_works,
)
from jjabtero.library import normalize_doi
from jjabtero.models import Paper
from jjabtero.semantic_scholar import PaperKeys, library_cites, paper_keys

# @doc: docs/design/CitationGraph.md#2-그래프-데이터
OUTSIDE_LIMIT = 30
# @doc: docs/design/CitationGraph.md#2-그래프-데이터
COUPLING_MIN = 2


class GraphNode(BaseModel):
    """그래프의 점 하나. 서재 논문이면 `paper_id`, 서재 밖 논문이면 `score`가 있다.

    @doc: docs/design/CitationGraph.md#2-그래프-데이터
    """

    id: str
    paper_id: int | None = None
    openalex_id: str | None = None
    title: str
    item_type: str = "other"
    authors: list[str] = []
    year: int | None = None
    venue: str | None = None
    doi: str | None = None
    cited_by_count: int | None = None
    # 공개일과 그 정밀도. 같은 연도 안에서 위아래 순서를 정하는 데 쓴다.
    date: str | None = None
    date_precision: Literal["day", "month", "year"] | None = None
    has_data: bool = True
    score: float | None = None


_ARXIV_NEW = re.compile(r"^10\.48550/arxiv\.(\d{2})(\d{2})\.\d{4,5}", re.IGNORECASE)
_ARXIV_OLD = re.compile(r"^10\.48550/arxiv\.[a-z\-.]+/(\d{2})(\d{2})\d{3}", re.IGNORECASE)


def publication_when(
    published: str | None, year: int | None, doi: str | None
) -> tuple[str | None, Literal["day", "month", "year"] | None]:
    """공개일과 정밀도를 정한다.

    OpenAlex는 연도만 알 때 공개일을 1월 1일로 채우므로, 1월 1일은 날짜로 믿지 않는다. 그때 arXiv 논문이면
    arXiv 번호(`YYMM.NNNNN`)에서 연·월을 얻고, 아니면 연도만 안다.

    @doc: docs/design/CitationGraph.md#4-화면
    """
    if published and len(published) >= 10 and not published.endswith("-01-01"):
        return published[:10], "day"
    match = _ARXIV_NEW.match(doi or "") or _ARXIV_OLD.match(doi or "")
    if match:
        short, month = int(match.group(1)), int(match.group(2))
        if 1 <= month <= 12:
            return f"{(2000 if short < 90 else 1900) + short}-{month:02d}", "month"
    known_year = year or (int(published[:4]) if published else None)
    return (str(known_year), "year") if known_year else (None, None)


class GraphEdge(BaseModel):
    """그래프의 선 하나. `cites`는 `source`가 `target`을 인용한다는 뜻이다.

    @doc: docs/design/CitationGraph.md#2-그래프-데이터
    """

    source: str
    target: str
    kind: Literal["cites", "related"]
    shared_refs: int = 0
    cocited: int = 0


class CitationGraph(BaseModel):
    """서재 인용 그래프.

    @doc: docs/design/CitationGraph.md#3-api
    """

    nodes: list[GraphNode]
    edges: list[GraphEdge]


def library_edges(
    node_ids: dict[str, str],
    rows_by_paper: dict[str, dict[str, Any]],
    extra_cites: set[tuple[str, str]] | None = None,
) -> list[GraphEdge]:
    """서재 논문 사이의 인용 선과 가까움 선을 만든다.

    `node_ids`는 OpenAlex ID에서 점 ID로, `rows_by_paper`는 OpenAlex ID에서 `relation_rows` 결과로 간다.
    `extra_cites`는 다른 출처(Semantic Scholar)로 찾은 인용(인용한 점 ID, 인용된 점 ID)이다.

    @doc: docs/design/CitationGraph.md#2-그래프-데이터
    """
    cites: set[tuple[str, str]] = set(extra_cites or ())
    for work, rows in rows_by_paper.items():
        for ref in rows["references"]:
            if ref in node_ids and ref != work:
                cites.add((node_ids[work], node_ids[ref]))
        for citer in rows["citations"]:
            if citer in node_ids and citer != work:
                cites.add((node_ids[citer], node_ids[work]))
    edges = [GraphEdge(source=a, target=b, kind="cites") for a, b in sorted(cites)]
    linked = {frozenset(pair) for pair in cites}
    works = sorted(rows_by_paper)
    for i, a in enumerate(works):
        for b in works[i + 1 :]:
            if frozenset((node_ids[a], node_ids[b])) in linked:
                continue
            shared = len(rows_by_paper[a]["references"] & rows_by_paper[b]["references"])
            cocited = max(rows_by_paper[a]["cocitations"].get(b, 0), rows_by_paper[b]["cocitations"].get(a, 0))
            if shared >= COUPLING_MIN or cocited >= 2:
                edges.append(
                    GraphEdge(source=node_ids[a], target=node_ids[b], kind="related", shared_refs=shared, cocited=cocited)
                )
    return edges


def outside_edges(item: Recommendation, node_ids: dict[str, str]) -> list[GraphEdge]:
    """서재 밖 논문 하나와 이어진 서재 논문들 사이의 선을 만든다.

    @doc: docs/design/CitationGraph.md#2-그래프-데이터
    """
    edges = []
    for source, relation in zip(item.sources, item.relations, strict=True):
        library = node_ids[source]
        if relation.cited_by_paper:
            edges.append(GraphEdge(source=library, target=item.work, kind="cites"))
        elif relation.cites_paper:
            edges.append(GraphEdge(source=item.work, target=library, kind="cites"))
        else:
            edges.append(
                GraphEdge(
                    source=library,
                    target=item.work,
                    kind="related",
                    shared_refs=relation.shared_refs,
                    cocited=relation.cocited,
                )
            )
    return edges


def _doi(value: str | None) -> str | None:
    if not value:
        return None
    try:
        return normalize_doi(value)
    except ValueError:
        return None


def reference_edges(
    outside_refs: dict[str, list[str]], node_ids: dict[str, str], edges: list[GraphEdge]
) -> list[GraphEdge]:
    """서재 밖 논문의 참고문헌으로 인용 선을 더한다. 같은 두 점 사이의 가까움 선은 뺀다.

    `node_ids`는 OpenAlex ID → 점 ID다.

    @doc: docs/design/CitationGraph.md#2-그래프-데이터
    """
    cites = {(edge.source, edge.target) for edge in edges if edge.kind == "cites"}
    added: list[GraphEdge] = []
    for work, refs in sorted(outside_refs.items()):
        source = node_ids.get(work)
        if source is None:
            continue
        for ref in refs:
            target = node_ids.get(ref)
            if target is None or target == source or (source, target) in cites:
                continue
            cites.add((source, target))
            added.append(GraphEdge(source=source, target=target, kind="cites"))
    linked = {frozenset(pair) for pair in cites}
    kept = [edge for edge in edges if edge.kind == "cites" or frozenset((edge.source, edge.target)) not in linked]
    return kept + added


def build_graph(
    papers: list[Paper],
    rows_by_paper: dict[str, dict[str, Any]],
    known: dict[str, dict[str, Any]],
    dates: dict[str, str | None],
    outside: list[Recommendation],
    s2_references: dict[str, list[PaperKeys]] | None = None,
    outside_refs: dict[str, list[str]] | None = None,
) -> CitationGraph:
    """서재 논문, 인용 데이터, 서지 정보, 서재 밖 추천으로 그래프를 만든다.

    @doc: docs/design/CitationGraph.md#2-그래프-데이터
    """
    nodes: list[GraphNode] = []
    node_ids: dict[str, str] = {}
    for paper in papers:
        node_id = f"p{paper.id}"
        if paper.openalex_id:
            node_ids[paper.openalex_id] = node_id
        row = known.get(paper.openalex_id or "", {})
        published = dates.get(paper.openalex_id or "") or row.get("publication_date")
        year = paper.year or (int(published[:4]) if published else None)
        date, precision = publication_when(published, year, paper.doi)
        nodes.append(
            GraphNode(
                id=node_id,
                paper_id=paper.id,
                openalex_id=paper.openalex_id,
                title=paper.title,
                item_type=paper.item_type,
                authors=paper.author_names,
                year=year,
                venue=paper.venue,
                doi=paper.doi,
                cited_by_count=row.get("cited_by_count"),
                date=date,
                date_precision=precision,
                has_data=paper.openalex_id in rows_by_paper,
            )
        )
    library = [(f"p{paper.id}", paper.doi, paper_keys(paper.doi, paper.title)) for paper in papers]
    edges = library_edges(node_ids, rows_by_paper, library_cites(library, s2_references or {}))
    for item in outside:
        row = known.get(item.work, {})
        date, precision = publication_when(row.get("publication_date"), row.get("year"), _doi(row.get("doi")))
        nodes.append(
            GraphNode(
                id=item.work,
                openalex_id=item.work,
                title=row.get("title") or item.work,
                item_type=row.get("item_type") or "other",
                authors=json.loads(row["authors"]) if row.get("authors") else [],
                year=row.get("year"),
                venue=row.get("venue"),
                doi=_doi(row.get("doi")),
                cited_by_count=row.get("cited_by_count"),
                date=date,
                date_precision=precision,
                score=item.score,
            )
        )
        edges.extend(outside_edges(item, node_ids))
    if outside_refs:
        ids = node_ids | {item.work: item.work for item in outside}
        edges = reference_edges(outside_refs, ids, edges)
    return CitationGraph(nodes=nodes, edges=edges)


# @doc: docs/design/CitationGraph.md#3-api
router = APIRouter(prefix="/api/citations")


@router.get("/graph")
def citation_graph(
    request: Request,
    outside: Annotated[int, Query(ge=0, le=OUTSIDE_LIMIT)] = 0,
    tags: Annotated[list[str] | None, Query()] = None,
) -> CitationGraph:
    """`GET /api/citations/graph`를 처리한다. `tags`를 주면 그 태그를 모두 가진 서재 논문만으로 그린다.

    @doc: docs/design/CitationGraph.md#3-api
    @doc: docs/design/Tags.md#5-태그별-그래프
    """
    sync: CitationSync = request.app.state.citations
    store = sync.store
    with Session(sync.library_engine) as session:
        library = list(session.scalars(select(Paper).order_by(Paper.id)))
        wanted_tags = set(tags or [])
        papers = [paper for paper in library if wanted_tags <= set(paper.tag_names)]
        by_work = {paper.openalex_id for paper in papers if paper.openalex_id}
        # 추천에서 빼는 것은 태그와 관계없이 서재 전체다. 이미 서재에 있는 논문을 추천하지 않기 위해서다.
        library_works = {paper.openalex_id for paper in library if paper.openalex_id}
        library_dois = {paper.doi for paper in library if paper.doi}
        rows_by_paper = {}
        for work_id in by_work:
            rows = store.relation_rows(work_id)
            if rows["references"] or rows["citations"]:
                rows_by_paper[work_id] = rows
        # 서재 DOI와 겹치는 추천을 빼고도 `outside`편이 남도록 넉넉히 고른다.
        ranked = recommend_works(rows_by_paper, library_works, limit=outside * 2) if outside else []
        wanted = by_work | {item.work for item in ranked}
        known = store.works_by_id(wanted)
        missing = sorted({item.work for item in ranked} - set(known))
        if missing:
            try:
                store.save_works(lookup_works(sync.http, missing, sync.clock()))
                known = store.works_by_id(wanted)
            except (OpenAlexBudgetError, httpx2.HTTPError, ValueError):
                pass
        chosen = [item for item in ranked if _doi(known.get(item.work, {}).get("doi")) not in library_dois][:outside]
        drawn = {item.work for item in chosen}
        stale = store.stale_outside_references(drawn, sync.clock())
        if stale:
            try:
                store.save_outside_references(lookup_references(sync.http, stale), sync.clock())
            except (OpenAlexBudgetError, httpx2.HTTPError, ValueError):
                pass
        return build_graph(
            papers,
            rows_by_paper,
            known,
            store.publication_dates(by_work),
            chosen,
            sync.s2_store.references(),
            store.outside_references(drawn),
        )
