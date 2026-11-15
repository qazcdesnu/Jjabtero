"""서재 인용 그래프의 데이터와 API.

@doc: docs/design/CitationGraph.md#2-그래프-데이터
@doc: docs/design/CitationGraph.md#3-api
"""

import json
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
    lookup_works,
    recommend_works,
)
from jjabtero.library import normalize_doi
from jjabtero.models import Paper

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
    has_data: bool = True
    score: float | None = None


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


def library_edges(node_ids: dict[str, str], rows_by_paper: dict[str, dict[str, Any]]) -> list[GraphEdge]:
    """서재 논문 사이의 인용 선과 가까움 선을 만든다.

    `node_ids`는 OpenAlex ID에서 점 ID로, `rows_by_paper`는 OpenAlex ID에서 `relation_rows` 결과로 간다.

    @doc: docs/design/CitationGraph.md#2-그래프-데이터
    """
    cites: set[tuple[str, str]] = set()
    for work, rows in rows_by_paper.items():
        for ref in rows["references"]:
            if ref in node_ids and ref != work:
                cites.add((work, ref))
        for citer in rows["citations"]:
            if citer in node_ids and citer != work:
                cites.add((citer, work))
    edges = [GraphEdge(source=node_ids[a], target=node_ids[b], kind="cites") for a, b in sorted(cites)]
    linked = {frozenset(pair) for pair in cites}
    works = sorted(rows_by_paper)
    for i, a in enumerate(works):
        for b in works[i + 1 :]:
            if frozenset((a, b)) in linked:
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


def build_graph(
    papers: list[Paper],
    rows_by_paper: dict[str, dict[str, Any]],
    known: dict[str, dict[str, Any]],
    dates: dict[str, str | None],
    outside: list[Recommendation],
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
        published = dates.get(paper.openalex_id or "")
        year = paper.year or (int(published[:4]) if published else None)
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
                has_data=paper.openalex_id in rows_by_paper,
            )
        )
    edges = library_edges(node_ids, rows_by_paper)
    for item in outside:
        row = known.get(item.work, {})
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
                score=item.score,
            )
        )
        edges.extend(outside_edges(item, node_ids))
    return CitationGraph(nodes=nodes, edges=edges)


# @doc: docs/design/CitationGraph.md#3-api
router = APIRouter(prefix="/api/citations")


@router.get("/graph")
def citation_graph(
    request: Request, outside: Annotated[int, Query(ge=0, le=OUTSIDE_LIMIT)] = 0
) -> CitationGraph:
    """`GET /api/citations/graph`를 처리한다.

    @doc: docs/design/CitationGraph.md#3-api
    """
    sync: CitationSync = request.app.state.citations
    store = sync.store
    with Session(sync.library_engine) as session:
        papers = list(session.scalars(select(Paper).order_by(Paper.id)))
        by_work = {paper.openalex_id for paper in papers if paper.openalex_id}
        library_dois = {paper.doi for paper in papers if paper.doi}
        rows_by_paper = {}
        for work_id in by_work:
            rows = store.relation_rows(work_id)
            if rows["references"] or rows["citations"]:
                rows_by_paper[work_id] = rows
        # 서재 DOI와 겹치는 추천을 빼고도 `outside`편이 남도록 넉넉히 고른다.
        ranked = recommend_works(rows_by_paper, by_work, limit=outside * 2) if outside else []
        wanted = by_work | {item.work for item in ranked}
        known = store.works_by_id(wanted)
        missing = sorted({item.work for item in ranked} - set(known))
        if missing:
            try:
                store.save_works(lookup_works(sync.http, missing, sync.clock()))
                known = store.works_by_id(wanted)
            except (OpenAlexBudgetError, httpx2.HTTPError, ValueError):
                pass
        chosen = [item for item in ranked if _doi(known.get(item.work, {}).get("doi")) not in library_dois]
        return build_graph(papers, rows_by_paper, known, store.publication_dates(by_work), chosen[:outside])
