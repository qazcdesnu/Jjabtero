"""인용 데이터의 연결, 가져오기, 저장, 갱신, API를 검증한다.

@doc: docs/design/Citations.md#7-테스트
"""

import sqlite3
from datetime import UTC, date, datetime, timedelta
from pathlib import Path

import httpx2
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from jjabtero.app import create_app
from jjabtero.citations import (
    CACHE_FILE,
    CACHE_VERSION,
    CitationStore,
    CitationSync,
    citing_window,
    fetch_citations,
)
from jjabtero.db import create_db_engine, upgrade_database
from jjabtero.library import PaperData, add_paper
from jjabtero.settings import update_settings

NOW = datetime(2026, 11, 15, tzinfo=UTC)
A = "W100"


def work(work_id: str, cited_by: int = 0, refs: list[str] | None = None, published: str = "2018-01-01") -> dict:
    """OpenAlex 작업 응답 하나.

    @doc: docs/design/Citations.md#7-테스트
    """
    return {
        "id": f"https://openalex.org/{work_id}",
        "doi": f"https://doi.org/10.1/{work_id.lower()}",
        "display_name": f"Paper {work_id}",
        "type": "article",
        "publication_year": int(published[:4]),
        "publication_date": published,
        "cited_by_count": cited_by,
        "authorships": [{"author": {"display_name": "Kim"}}],
        "primary_location": {"source": {"display_name": "Venue"}},
        "referenced_works": [f"https://openalex.org/{ref}" for ref in refs or []],
    }


class FakeOpenAlex:
    """참고문헌과 피인용을 고정해 답하는 가짜 OpenAlex. 받은 요청을 기록한다.

    @doc: docs/design/Citations.md#7-테스트
    """

    def __init__(self, citers: list[dict] | None = None, dois: dict[str, str] | None = None) -> None:
        self.base = {A: {"id": f"https://openalex.org/{A}", "publication_date": "2017-06-12", "referenced_works": ["https://openalex.org/W1", "https://openalex.org/W2"]}}
        self.citers = citers if citers is not None else [
            work("W10", 500, ["W1", "W2", "W50", A]),
            work("W11", 300, ["W1", "W50", "W60", A]),
            work("W12", 100, ["W60", A]),
        ]
        self.dois = dois or {"10.1/a": A}
        self.requests: list[httpx2.Request] = []
        self.budget_left: int | None = None

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        if request.url.host == "api.semanticscholar.org":
            return httpx2.Response(404, json={"error": "not found"})
        self.requests.append(request)
        if self.budget_left is not None:
            if self.budget_left <= 0:
                return httpx2.Response(429, json={})
            self.budget_left -= 1
        path = request.url.path
        params = request.url.params
        if path.startswith("/works/doi:"):
            work_id = self.dois.get(path.removeprefix("/works/doi:"))
            return httpx2.Response(200, json={"id": f"https://openalex.org/{work_id}"}) if work_id else httpx2.Response(404)
        if path.startswith("/works/W"):
            body = self.base.get(path.removeprefix("/works/"))
            return httpx2.Response(200, json=body) if body else httpx2.Response(404)
        flt = params["filter"]
        if flt.startswith("cites:"):
            per_page = int(params["per-page"])
            page = int(params["page"])
            chunk = self.citers[(page - 1) * per_page : page * per_page]
            return httpx2.Response(200, json={"meta": {"count": len(self.citers)}, "results": chunk})
        ids = flt.removeprefix("openalex_id:").split("|")
        return httpx2.Response(200, json={"meta": {"count": len(ids)}, "results": [work(i) for i in ids]})


class FakeDrive:
    """캐시 파일만 다루는 가짜 드라이브.

    @doc: docs/design/Citations.md#7-테스트
    """

    def __init__(self, connected: bool = True) -> None:
        self.connected = connected
        self.files: dict[str, bytes] = {}
        self.pushes = 0

    def is_connected(self) -> bool:
        return self.connected

    def put_cache(self, name: str, data: bytes) -> bool:
        self.files[name] = data
        return True

    def get_cache(self, name: str) -> bytes | None:
        return self.files.get(name)

    def schedule_push(self) -> None:
        self.pushes += 1


@pytest.fixture
def engine(tmp_path: Path):
    """마이그레이션을 끝낸 임시 서재.

    @doc: docs/design/Citations.md#7-테스트
    """
    engine = create_db_engine(tmp_path / "library.db")
    upgrade_database(engine)
    return engine


def make_sync(engine, tmp_path: Path, openalex: FakeOpenAlex, drive: FakeDrive | None = None, now: list[datetime] | None = None) -> CitationSync:
    """가짜 OpenAlex와 드라이브를 쓰는 갱신 객체.

    @doc: docs/design/Citations.md#7-테스트
    """
    clock = now or [NOW]
    return CitationSync(
        engine,
        tmp_path / CACHE_FILE,
        httpx2.Client(transport=httpx2.MockTransport(openalex)),
        drive or FakeDrive(),
        clock=lambda: clock[0],
    )


def add(engine, **fields) -> int:
    """서재에 논문을 넣고 ID를 돌려준다.

    @doc: docs/design/Citations.md#7-테스트
    """
    with Session(engine) as session:
        return add_paper(session, PaperData(title="T", **fields)).id


def openalex_id(engine, paper_id: int) -> str | None:
    """서재 논문의 OpenAlex ID를 읽는다.

    @doc: docs/design/Citations.md#7-테스트
    """
    with Session(engine) as session:
        from jjabtero.models import Paper

        return session.get(Paper, paper_id).openalex_id


def test_citing_window_is_one_year_after_publication() -> None:
    """공개일부터 1년 뒤까지이고, 2월 29일은 다음 해 2월 28일까지다.

    @doc: docs/design/Citations.md#7-테스트
    """
    assert citing_window(date(2017, 6, 12)) == (date(2017, 6, 12), date(2018, 6, 12))
    assert citing_window(date(2020, 2, 29)) == (date(2020, 2, 29), date(2021, 2, 28))


def test_fetch_requests_window_sorted_by_citations() -> None:
    """피인용 요청은 공개 후 1년 기간, 피인용 많은 순, 한도만큼의 쪽 크기를 쓴다.

    @doc: docs/design/Citations.md#7-테스트
    """
    openalex = FakeOpenAlex()
    result = fetch_citations(httpx2.Client(transport=httpx2.MockTransport(openalex)), A, 10, NOW)
    cites = next(r for r in openalex.requests if r.url.params.get("filter", "").startswith("cites:"))
    assert cites.url.params["filter"] == f"cites:{A},from_publication_date:2017-06-12,to_publication_date:2018-06-12"
    assert cites.url.params["sort"] == "cited_by_count:desc"
    assert cites.url.params["per-page"] == "10"
    assert result.references == ["W1", "W2"]
    assert result.citations == [("W10", "2018-01-01", 2), ("W11", "2018-01-01", 1), ("W12", "2018-01-01", 0)]
    assert result.cocitations == [("W1", 2), ("W50", 2), ("W60", 2)]
    assert result.citing_total == 3
    assert {row["id"] for row in result.works} == {"W10", "W11", "W12", "W1", "W2"}


def test_fetch_limit_over_page_size_reads_several_pages() -> None:
    """한도가 200을 넘으면 여러 쪽을 받고 한도에서 자른다.

    @doc: docs/design/Citations.md#7-테스트
    """
    citers = [work(f"W{1000 + i}", 1000 - i, [A]) for i in range(450)]
    openalex = FakeOpenAlex(citers=citers)
    result = fetch_citations(httpx2.Client(transport=httpx2.MockTransport(openalex)), A, 250, NOW)
    pages = [r.url.params["page"] for r in openalex.requests if r.url.params.get("filter", "").startswith("cites:")]
    assert pages == ["1", "2"]
    assert len(result.citations) == 250


def test_run_links_by_doi_fetches_and_uploads(engine, tmp_path: Path) -> None:
    """DOI로 연결하고, 인용 데이터를 저장하고, 캐시를 드라이브에 올린다.

    @doc: docs/design/Citations.md#7-테스트
    """
    drive = FakeDrive()
    sync = make_sync(engine, tmp_path, FakeOpenAlex(), drive)
    paper_id = add(engine, doi="10.1/a")

    assert sync.run_once() == 1
    assert openalex_id(engine, paper_id) == A
    assert drive.pushes == 1
    assert {row["work"] for row in sync.store.rows("references")} == {"W1", "W2"}
    assert {(row["work"], row["shared_refs"]) for row in sync.store.rows("citations")} == {("W10", 2), ("W11", 1), ("W12", 0)}
    assert sync.store.rows("fetches")[0]["citing_limit"] == 10
    assert CACHE_FILE in drive.files
    copy = tmp_path / "copy.db"
    copy.write_bytes(drive.files[CACHE_FILE])
    assert sqlite3.connect(copy).execute("select count(*) from citations").fetchone() == (3,)


def test_unfound_doi_is_not_retried_for_seven_days(engine, tmp_path: Path) -> None:
    """찾지 못한 DOI는 7일 동안 다시 찾지 않는다.

    @doc: docs/design/Citations.md#7-테스트
    """
    openalex = FakeOpenAlex()
    clock = [NOW]
    sync = make_sync(engine, tmp_path, openalex, now=clock)
    add(engine, doi="10.1/missing")
    sync.run_once()
    sync.run_once()
    lookups = [r for r in openalex.requests if r.url.path.startswith("/works/doi:")]
    assert len(lookups) == 1
    assert sync.status().not_found == 1
    clock[0] = NOW + timedelta(days=8)
    sync.run_once()
    assert len([r for r in openalex.requests if r.url.path.startswith("/works/doi:")]) == 2


def test_openalex_id_from_search_is_kept(engine, tmp_path: Path) -> None:
    """OpenAlex 검색에서 넣은 논문은 받은 ID를 쓰고 DOI로 찾지 않는다.

    @doc: docs/design/Citations.md#7-테스트
    """
    openalex = FakeOpenAlex()
    sync = make_sync(engine, tmp_path, openalex)
    paper_id = add(engine, openalex_id=f"https://openalex.org/{A}")
    assert openalex_id(engine, paper_id) == A
    sync.run_once()
    assert not [r for r in openalex.requests if r.url.path.startswith("/works/doi:")]


def test_paper_data_rejects_bad_openalex_id() -> None:
    """OpenAlex 작업 ID 형식이 아니면 검증 오류다.

    @doc: docs/design/Citations.md#7-테스트
    """
    with pytest.raises(ValueError):
        PaperData(title="T", openalex_id="A123")


def test_refetch_only_after_seven_days_and_replace(engine, tmp_path: Path) -> None:
    """7일 안에는 다시 가져오지 않고, 지나면 옛 데이터를 새 데이터로 바꾼다. 설정한 한도를 쓴다.

    @doc: docs/design/Citations.md#7-테스트
    """
    openalex = FakeOpenAlex()
    clock = [NOW]
    sync = make_sync(engine, tmp_path, openalex, now=clock)
    add(engine, openalex_id=A)
    assert sync.run_once() == 1
    assert sync.run_once() == 0
    openalex.citers = [work("W20", 9, [A])]
    with Session(engine) as session:
        update_settings(session, {"citing_limit": 5})
    clock[0] = NOW + timedelta(days=7, seconds=1)
    assert sync.run_once() == 1
    assert [row["work"] for row in sync.store.rows("citations")] == ["W20"]
    assert sync.store.rows("fetches")[0]["citing_limit"] == 5


def test_refresh_marks_everything_stale(engine, tmp_path: Path) -> None:
    """새로 받기는 7일이 지나지 않았어도 다시 가져오게 한다.

    @doc: docs/design/Citations.md#7-테스트
    """
    sync = make_sync(engine, tmp_path, FakeOpenAlex())
    add(engine, openalex_id=A)
    sync.run_once()
    sync.refresh()
    assert sync.run_once() == 1


def test_removed_paper_data_is_pruned(engine, tmp_path: Path) -> None:
    """서재에서 지운 논문의 인용 데이터와 쓰지 않는 works를 지운다.

    @doc: docs/design/Citations.md#7-테스트
    """
    from jjabtero.library import delete_paper

    sync = make_sync(engine, tmp_path, FakeOpenAlex())
    paper_id = add(engine, openalex_id=A)
    sync.run_once()
    with Session(engine) as session:
        delete_paper(session, paper_id)
    sync.run_once()
    for table in ("fetches", "references", "citations", "cocitations", "works"):
        assert sync.store.rows(table) == []


def test_budget_exhausted_stops_run(engine, tmp_path: Path) -> None:
    """429를 받으면 멈추고 상태에 오류를 남긴다. 다음 갱신 때 이어서 한다.

    @doc: docs/design/Citations.md#7-테스트
    """
    openalex = FakeOpenAlex()
    openalex.budget_left = 1
    sync = make_sync(engine, tmp_path, openalex)
    add(engine, openalex_id=A)
    assert sync.run_once() == 0
    assert "사용량" in sync.status().error
    openalex.budget_left = None
    assert sync.run_once() == 1
    assert sync.status().error == ""


def test_cache_version_mismatch_recreates(tmp_path: Path) -> None:
    """캐시 버전이 다르면 표를 지우고 다시 만든다.

    @doc: docs/design/Citations.md#7-테스트
    """
    path = tmp_path / CACHE_FILE
    connection = sqlite3.connect(path)
    connection.execute("create table works (old text)")
    connection.execute("pragma user_version = 99")
    connection.commit()
    connection.close()
    store = CitationStore(path)
    assert store.rows("works") == []
    assert sqlite3.connect(path).execute("pragma user_version").fetchone() == (CACHE_VERSION,)


def test_restore_from_drive_when_local_missing(engine, tmp_path: Path) -> None:
    """로컬 캐시가 없고 드라이브에 있으면 받는다.

    @doc: docs/design/Citations.md#7-테스트
    """
    drive = FakeDrive()
    first = make_sync(engine, tmp_path / "one", FakeOpenAlex(), drive)
    add(engine, openalex_id=A)
    first.run_once()
    second = make_sync(engine, tmp_path / "two", FakeOpenAlex(), drive)
    assert second.restore_from_drive() is True
    assert len(second.store.rows("citations")) == 3
    assert second.restore_from_drive() is False


def test_api_status_and_refresh(tmp_path: Path) -> None:
    """상태 API는 서재·연결·가져온 수를, 새로 받기는 상태를 돌려준다.

    @doc: docs/design/Citations.md#7-테스트
    """
    openalex = FakeOpenAlex()
    app = create_app(
        frontend_dist=tmp_path / "missing",
        db_path=tmp_path / "library.db",
        http_client=httpx2.Client(transport=httpx2.MockTransport(openalex)),
    )
    client = TestClient(app)
    client.post("/api/papers", json={"title": "T", "openalex_id": A})
    app.state.citations.run_once()
    status = client.get("/api/citations/status").json()
    assert (status["papers"], status["linked"], status["fetched"]) == (1, 1, 1)
    assert client.post("/api/citations/refresh").json()["fetched"] == 0


def test_paper_citations_api_lists_and_marks_library(tmp_path: Path) -> None:
    """논문의 인용 목록은 참고문헌과 피인용을 피인용 많은 순으로 주고, 서재에 있는 논문을 표시한다.

    @doc: docs/design/Citations.md#7-테스트
    """
    openalex = FakeOpenAlex()
    app = create_app(
        frontend_dist=tmp_path / "missing",
        db_path=tmp_path / "library.db",
        http_client=httpx2.Client(transport=httpx2.MockTransport(openalex)),
    )
    client = TestClient(app)
    paper_id = client.post("/api/papers", json={"title": "T", "openalex_id": A}).json()["id"]
    assert client.get(f"/api/papers/{paper_id}/citations").json()["state"] == "pending"
    app.state.citations.run_once()
    owned = client.post("/api/papers", json={"title": "Owned", "doi": "10.1/w11"}).json()["id"]

    body = client.get(f"/api/papers/{paper_id}/citations").json()
    assert body["state"] == "ready"
    assert (body["window_start"], body["window_end"], body["citing_total"], body["citing_limit"]) == ("2017-06-12", "2018-06-12", 3, 10)
    assert [item["openalex_id"] for item in body["citations"]] == ["W10", "W11", "W12"]
    first = body["citations"][0]
    assert (first["title"], first["authors"], first["doi"], first["shared_refs"], first["cited_by_count"]) == ("Paper W10", ["Kim"], "10.1/w10", 2, 500)
    assert body["citations"][1]["library_paper_id"] == owned
    assert {item["openalex_id"] for item in body["references"]} == {"W1", "W2"}


def test_paper_citations_states_without_link(tmp_path: Path) -> None:
    """DOI가 없으면 no_doi, 찾지 못했으면 not_found, 없는 논문은 404다.

    @doc: docs/design/Citations.md#7-테스트
    """
    app = create_app(
        frontend_dist=tmp_path / "missing",
        db_path=tmp_path / "library.db",
        http_client=httpx2.Client(transport=httpx2.MockTransport(FakeOpenAlex())),
    )
    client = TestClient(app)
    no_doi = client.post("/api/papers", json={"title": "T"}).json()["id"]
    missing = client.post("/api/papers", json={"title": "M", "doi": "10.1/missing"}).json()["id"]
    app.state.citations.run_once()
    assert client.get(f"/api/papers/{no_doi}/citations").json()["state"] == "no_doi"
    assert client.get(f"/api/papers/{missing}/citations").json()["state"] == "not_found"
    assert client.get("/api/papers/99/citations").status_code == 404


def test_related_works_scores_direct_cocitation_and_coupling() -> None:
    """점수는 직접 인용 0.5 + 함께 인용된 비율 + 공유 참고문헌 비율이고, 논문 자신은 뺀다.

    @doc: docs/design/Citations.md#7-테스트
    """
    from jjabtero.citations import related_works

    rows = {
        "references": {"W1", "W2"},
        "citations": {"W10": 2, "W11": 1, "W12": 0},
        "cocitations": {"W1": 2, "W50": 2, "W60": 2, A: 3},
    }
    relations = {relation.work: relation for relation in related_works(A, rows, 3)}
    assert A not in relations
    assert relations["W10"].score == round(0.5 + 2 / 2, 4)
    assert relations["W1"].score == round(0.5 + 2 / 3, 4)
    assert relations["W50"].score == round(2 / 3, 4)
    assert relations["W12"].score == 0.5
    w1 = relations["W1"]
    assert (w1.cited_by_paper, w1.cites_paper, w1.cocited, w1.shared_refs) == (True, False, 2, 0)
    ordered = [relation.work for relation in related_works(A, rows, 3)]
    assert ordered[:2] == ["W10", "W1"]


def test_work_direction_prefers_citation_then_date() -> None:
    """한쪽 인용이면 인용 방향을, 아니면 공개일(한쪽이 연도뿐이면 연도)을 따르고, 같거나 모르면 표시하지 않는다.

    @doc: docs/design/Citations.md#7-테스트
    """
    from jjabtero.citations import Relation, when, work_direction

    def relation(cites: bool, cited: bool) -> Relation:
        return Relation("W1", 1.0, cites, cited, 0, 0)

    assert work_direction(relation(False, True), "2020-01-01", "2021-01-01") == ("prior", "citation")
    assert work_direction(relation(True, False), "2020-01-01", "2019-01-01") == ("later", "citation")
    assert work_direction(relation(False, False), "2020-05-01", "2020-03-01") == ("prior", "date")
    assert work_direction(relation(True, True), "2020-05-01", "2020-07-01") == ("later", "date")
    assert work_direction(relation(False, False), "2020", "2020-07-01") == (None, None)
    assert work_direction(relation(False, False), "2019", "2020-07-01") == ("later", "date")
    assert work_direction(relation(False, False), None, "2020-07-01") == (None, None)
    assert (when("2020-01-02", 2020), when(None, 2020), when(None, None)) == ("2020-01-02", "2020", None)


def test_overall_direction() -> None:
    """이어진 서재 논문마다의 방향이 같으면 그 방향, 다르면 `mixed`, 없으면 `None`이다.

    @doc: docs/design/Citations.md#7-테스트
    """
    from jjabtero.citations import overall_direction

    assert overall_direction(["prior", None, "prior"]) == "prior"
    assert overall_direction(["prior", "later"]) == "mixed"
    assert overall_direction([None]) is None


def test_paper_related_api_fills_missing_works(tmp_path: Path) -> None:
    """가까운 논문 API는 점수 순 목록을 주고, 서지 정보가 없는 공동 인용 논문은 OpenAlex에서 받아 둔다.

    @doc: docs/design/Citations.md#7-테스트
    """
    openalex = FakeOpenAlex()
    app = create_app(
        frontend_dist=tmp_path / "missing",
        db_path=tmp_path / "library.db",
        http_client=httpx2.Client(transport=httpx2.MockTransport(openalex)),
    )
    client = TestClient(app)
    paper_id = client.post("/api/papers", json={"title": "T", "openalex_id": A}).json()["id"]
    assert client.get(f"/api/papers/{paper_id}/related").json()["state"] == "pending"
    app.state.citations.run_once()
    body = client.get(f"/api/papers/{paper_id}/related").json()
    assert (body["state"], body["citing_count"], body["reference_count"]) == ("ready", 3, 2)
    works = {item["openalex_id"]: item for item in body["works"]}
    assert body["works"][0]["openalex_id"] == "W10"
    assert works["W50"]["title"] == "Paper W50"
    assert works["W50"]["cocited"] == 2 and works["W50"]["cites_paper"] is False
    assert (works["W10"]["direction"], works["W10"]["direction_basis"]) == ("later", "citation")
    assert (works["W1"]["direction"], works["W1"]["direction_basis"]) == ("prior", "citation")
    assert (works["W50"]["direction"], works["W50"]["direction_basis"]) == ("later", "date")
    lookups = [r for r in openalex.requests if r.url.params.get("filter", "").startswith("openalex_id:") and "W50" in r.url.params["filter"]]
    assert len(lookups) == 1
    client.get(f"/api/papers/{paper_id}/related")
    lookups = [r for r in openalex.requests if r.url.params.get("filter", "").startswith("openalex_id:") and "W50" in r.url.params["filter"]]
    assert len(lookups) == 1


def test_recommend_works_sums_scores_and_excludes_library() -> None:
    """여러 서재 논문과 이어진 논문의 점수를 더하고, 서재 논문은 빼며, 이어진 서재 논문을 기억한다.

    @doc: docs/design/Citations.md#7-테스트
    """
    from jjabtero.citations import recommend_works

    rows_by_paper = {
        "WA": {"references": {"W1", "WB"}, "citations": {}, "cocitations": {}},
        "WB": {"references": {"W1", "W2"}, "citations": {}, "cocitations": {}},
    }
    ranked = recommend_works(rows_by_paper, {"WA", "WB"})
    assert [item.work for item in ranked] == ["W1", "W2"]
    assert ranked[0].score == 1.0 and ranked[0].sources == ["WA", "WB"]
    assert ranked[1].score == 0.5 and ranked[1].sources == ["WB"]
    assert len(recommend_works(rows_by_paper, {"WA", "WB"}, limit=1)) == 1


def test_recommendations_api(tmp_path: Path) -> None:
    """추천 API는 서재 밖 논문을 점수 순으로 주고, 이어진 서재 논문과 서지 정보를 담으며, 서재 DOI는 뺀다.

    @doc: docs/design/Citations.md#7-테스트
    """
    app = create_app(
        frontend_dist=tmp_path / "missing",
        db_path=tmp_path / "library.db",
        http_client=httpx2.Client(transport=httpx2.MockTransport(FakeOpenAlex())),
    )
    client = TestClient(app)
    empty = client.get("/api/citations/recommendations").json()
    assert (empty["papers"], empty["papers_used"], empty["works"]) == (0, 0, [])
    paper_id = client.post("/api/papers", json={"title": "Base", "openalex_id": A}).json()["id"]
    app.state.citations.run_once()
    client.post("/api/papers", json={"title": "Owned", "doi": "10.1/w11"})
    body = client.get("/api/citations/recommendations").json()
    assert (body["papers"], body["papers_used"]) == (2, 1)
    ids = [item["openalex_id"] for item in body["works"]]
    assert ids[0] == "W10" and "W11" not in ids and A not in ids
    assert body["works"][0]["sources"] == [
        {"paper_id": paper_id, "title": "Base", "direction": "later", "direction_basis": "citation"}
    ]
    assert body["works"][0]["direction"] == "later"
    w1 = next(item for item in body["works"] if item["openalex_id"] == "W1")
    assert (w1["direction"], w1["sources"][0]["direction_basis"]) == ("prior", "citation")
    assert next(item for item in body["works"] if item["openalex_id"] == "W50")["title"] == "Paper W50"
