"""인용 데이터의 OpenAlex 연결, 가져오기, 캐시 저장, 백그라운드 갱신, API.

@doc: docs/design/Citations.md#4-저장
@doc: docs/design/Citations.md#5-갱신
"""

import json
import os
import re
import tempfile
import threading
from collections import Counter
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, timedelta
from pathlib import Path
from typing import Any, Protocol

import httpx2
from fastapi import APIRouter, Request
from pydantic import BaseModel
from sqlalchemy import (
    Column,
    Engine,
    Integer,
    MetaData,
    String,
    Table,
    create_engine,
    delete,
    insert,
    select,
    text,
    union,
    update,
)
from sqlalchemy.orm import Session

from jjabtero.models import Paper
from jjabtero.settings import read_settings

OPENALEX_WORKS_URL = "https://api.openalex.org/works"
CACHE_FILE = "citations.db"
# @doc: docs/design/Citations.md#4-저장
CACHE_VERSION = 1
REFRESH_AFTER = timedelta(days=7)
MISS_RETRY_AFTER = timedelta(days=7)
RUN_INTERVAL_SECONDS = 3600
PAGE_SIZE = 200
LOOKUP_BATCH = 100
COCITATION_LIMIT = 100
MAX_AUTHORS = 10
_WORK_FIELDS = "id,doi,display_name,publication_year,publication_date,cited_by_count,authorships,primary_location"
_WORK_ID = re.compile(r"W\d+")

_metadata = MetaData()
_fetches = Table(
    "fetches",
    _metadata,
    Column("paper", String, primary_key=True),
    Column("fetched_at", String),
    Column("publication_date", String),
    Column("window_end", String),
    Column("citing_limit", Integer),
    Column("citing_total", Integer),
)
_references = Table(
    "references",
    _metadata,
    Column("paper", String, primary_key=True),
    Column("work", String, primary_key=True),
)
_citations = Table(
    "citations",
    _metadata,
    Column("paper", String, primary_key=True),
    Column("work", String, primary_key=True),
    Column("publication_date", String),
    Column("shared_refs", Integer),
)
_cocitations = Table(
    "cocitations",
    _metadata,
    Column("paper", String, primary_key=True),
    Column("work", String, primary_key=True),
    Column("count", Integer),
)
_works = Table(
    "works",
    _metadata,
    Column("id", String, primary_key=True),
    Column("title", String),
    Column("authors", String),
    Column("year", Integer),
    Column("publication_date", String),
    Column("venue", String),
    Column("doi", String),
    Column("cited_by_count", Integer),
    Column("updated_at", String),
)
_link_misses = Table(
    "link_misses",
    _metadata,
    Column("doi", String, primary_key=True),
    Column("tried_at", String),
)


class OpenAlexBudgetError(Exception):
    """OpenAlex 하루 사용량을 다 썼다(응답 429).

    @doc: docs/design/Citations.md#5-갱신
    """


def short_id(value: str | None) -> str | None:
    """`https://openalex.org/W…` 꼴을 `W…`로 줄인다. 형식이 맞지 않으면 `None`이다.

    @doc: docs/design/Citations.md#2-서재-논문과-openalex-연결
    """
    if not value:
        return None
    work_id = value.strip().removeprefix("https://openalex.org/")
    return work_id if _WORK_ID.fullmatch(work_id) else None


def citing_window(published: date) -> tuple[date, date]:
    """공개일부터 1년 뒤까지의 피인용 기간을 돌려준다.

    @doc: docs/design/Citations.md#3-가져오는-범위
    """
    try:
        end = published.replace(year=published.year + 1)
    except ValueError:
        end = date(published.year + 1, 2, 28)
    return published, end


def _get(http: httpx2.Client, url: str, params: dict[str, Any]) -> dict | None:
    api_key = os.environ.get("OPENALEX_API_KEY")
    if api_key:
        params = {**params, "api_key": api_key}
    response = http.get(url, params=params)
    if response.status_code == 429:
        raise OpenAlexBudgetError("OpenAlex 하루 사용량을 다 썼습니다. 다음 갱신 때 이어서 받습니다.")
    if response.status_code == 404:
        return None
    response.raise_for_status()
    return response.json()


def _work_row(work: dict[str, Any], now: str) -> dict[str, Any]:
    location = work.get("primary_location") or {}
    source = location.get("source") or {}
    authors = [
        (authorship.get("author") or {}).get("display_name")
        for authorship in work.get("authorships") or []
    ]
    return {
        "id": short_id(work.get("id")),
        "title": work.get("display_name") or "",
        "authors": json.dumps([name for name in authors if name][:MAX_AUTHORS], ensure_ascii=False),
        "year": work.get("publication_year"),
        "publication_date": work.get("publication_date"),
        "venue": source.get("display_name"),
        "doi": work.get("doi"),
        "cited_by_count": work.get("cited_by_count"),
        "updated_at": now,
    }


def link_paper(http: httpx2.Client, doi: str) -> str | None:
    """DOI로 OpenAlex 작업 ID를 찾는다. 없으면 `None`이다.

    @doc: docs/design/Citations.md#2-서재-논문과-openalex-연결
    """
    body = _get(http, f"{OPENALEX_WORKS_URL}/doi:{doi}", {"select": "id"})
    return None if body is None else short_id(body.get("id"))


@dataclass
class FetchResult:
    """논문 하나에서 가져온 인용 데이터.

    @doc: docs/design/Citations.md#3-가져오는-범위
    """

    publication_date: str | None
    window_end: str | None
    citing_total: int
    references: list[str]
    citations: list[tuple[str, str | None, int]]
    cocitations: list[tuple[str, int]]
    works: list[dict[str, Any]] = field(default_factory=list)


def fetch_citations(http: httpx2.Client, work_id: str, limit: int, now: datetime) -> FetchResult:
    """참고문헌과 공개 후 1년 안의 피인용(피인용 많은 순 최대 `limit`건)을 가져온다.

    @doc: docs/design/Citations.md#3-가져오는-범위
    """
    stamp = now.isoformat()
    base = _get(http, f"{OPENALEX_WORKS_URL}/{work_id}", {"select": "id,publication_date,referenced_works"})
    if base is None:
        raise LookupError(f"OpenAlex에 없는 작업입니다: {work_id}")
    references = [ref for ref in map(short_id, base.get("referenced_works") or []) if ref]
    published = base.get("publication_date")
    citers: list[dict[str, Any]] = []
    total = 0
    window_end = None
    if published:
        start, end = citing_window(date.fromisoformat(published))
        window_end = end.isoformat()
        per_page = min(PAGE_SIZE, limit)
        page = 1
        while len(citers) < limit:
            body = _get(
                http,
                OPENALEX_WORKS_URL,
                {
                    "filter": f"cites:{work_id},from_publication_date:{start},to_publication_date:{end}",
                    "sort": "cited_by_count:desc",
                    "per-page": per_page,
                    "page": page,
                    "select": f"{_WORK_FIELDS},referenced_works",
                },
            ) or {}
            total = (body.get("meta") or {}).get("count", 0)
            results = body.get("results") or []
            citers.extend(results)
            if len(results) < per_page:
                break
            page += 1
        citers = citers[:limit]

    reference_set = set(references)
    citations: list[tuple[str, str | None, int]] = []
    together: Counter[str] = Counter()
    for citer in citers:
        citer_id = short_id(citer.get("id"))
        if citer_id is None:
            continue
        citer_refs = {ref for ref in map(short_id, citer.get("referenced_works") or []) if ref}
        citations.append((citer_id, citer.get("publication_date"), len(reference_set & citer_refs)))
        together.update(citer_refs - {work_id})
    # 같은 횟수는 ID 순으로 두어, 실행마다 같은 결과가 나오게 한다.
    ranked = sorted(together.items(), key=lambda item: (-item[1], item[0]))
    cocitations = [(work, count) for work, count in ranked if count >= 2][:COCITATION_LIMIT]

    works = [_work_row(citer, stamp) for citer in citers if short_id(citer.get("id"))]
    for index in range(0, len(references), LOOKUP_BATCH):
        batch = references[index : index + LOOKUP_BATCH]
        body = _get(
            http,
            OPENALEX_WORKS_URL,
            {"filter": "openalex_id:" + "|".join(batch), "per-page": LOOKUP_BATCH, "select": _WORK_FIELDS},
        ) or {}
        works.extend(_work_row(work, stamp) for work in body.get("results") or [] if short_id(work.get("id")))
    return FetchResult(published, window_end, total, references, citations, cocitations, works)


class CitationStore:
    """인용 데이터 캐시 파일 `citations.db`.

    @doc: docs/design/Citations.md#4-저장
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self.engine: Engine = create_engine(f"sqlite:///{path}")
        with self.engine.begin() as connection:
            version = connection.execute(text("PRAGMA user_version")).scalar()
            if version != CACHE_VERSION:
                _metadata.drop_all(connection)
                connection.execute(text(f"PRAGMA user_version = {CACHE_VERSION}"))
            _metadata.create_all(connection)

    def save(self, work_id: str, result: FetchResult, limit: int, now: datetime) -> None:
        """논문 하나의 인용 데이터를 옛 데이터와 바꿔 저장한다.

        @doc: docs/design/Citations.md#4-저장
        """
        with self.engine.begin() as connection:
            for table in (_references, _citations, _cocitations):
                connection.execute(delete(table).where(table.c.paper == work_id))
            connection.execute(delete(_fetches).where(_fetches.c.paper == work_id))
            connection.execute(
                insert(_fetches).values(
                    paper=work_id,
                    fetched_at=now.isoformat(),
                    publication_date=result.publication_date,
                    window_end=result.window_end,
                    citing_limit=limit,
                    citing_total=result.citing_total,
                )
            )
            if result.references:
                connection.execute(
                    insert(_references), [{"paper": work_id, "work": ref} for ref in dict.fromkeys(result.references)]
                )
            if result.citations:
                connection.execute(
                    insert(_citations),
                    [
                        {"paper": work_id, "work": work, "publication_date": published, "shared_refs": shared}
                        for work, published, shared in result.citations
                    ],
                )
            if result.cocitations:
                connection.execute(
                    insert(_cocitations),
                    [{"paper": work_id, "work": work, "count": count} for work, count in result.cocitations],
                )
            for row in {row["id"]: row for row in result.works}.values():
                connection.execute(delete(_works).where(_works.c.id == row["id"]))
                connection.execute(insert(_works).values(**row))

    def stale(self, work_ids: list[str], now: datetime) -> list[str]:
        """가져온 적이 없거나 가져온 지 7일이 지난 논문을 오래된 것부터 돌려준다.

        @doc: docs/design/Citations.md#5-갱신
        """
        with self.engine.connect() as connection:
            fetched = dict(connection.execute(select(_fetches.c.paper, _fetches.c.fetched_at)).all())
        cutoff = (now - REFRESH_AFTER).isoformat()
        due = [work for work in dict.fromkeys(work_ids) if not fetched.get(work) or fetched[work] <= cutoff]
        return sorted(due, key=lambda work: fetched.get(work) or "")

    def mark_all_stale(self) -> None:
        """모든 논문을 가져올 대상으로 표시한다.

        @doc: docs/design/Citations.md#5-갱신
        """
        with self.engine.begin() as connection:
            connection.execute(update(_fetches).values(fetched_at=None))

    def prune(self, keep: set[str]) -> None:
        """서재에 없는 논문의 인용 데이터와 쓰지 않는 `works`를 지운다.

        @doc: docs/design/Citations.md#4-저장
        """
        with self.engine.begin() as connection:
            for table in (_fetches, _references, _citations, _cocitations):
                connection.execute(delete(table).where(table.c.paper.not_in(keep)))
            used = union(
                select(_references.c.work),
                select(_citations.c.work),
                select(_cocitations.c.work),
                select(_fetches.c.paper),
            )
            connection.execute(delete(_works).where(_works.c.id.not_in(used)))

    def missed_recently(self, doi: str, now: datetime) -> bool:
        """이 DOI를 7일 안에 찾다가 못 찾았으면 참이다.

        @doc: docs/design/Citations.md#2-서재-논문과-openalex-연결
        """
        with self.engine.connect() as connection:
            tried = connection.execute(select(_link_misses.c.tried_at).where(_link_misses.c.doi == doi)).scalar()
        return tried is not None and tried > (now - MISS_RETRY_AFTER).isoformat()

    def record_miss(self, doi: str, now: datetime) -> None:
        """찾지 못한 DOI와 시각을 기억한다.

        @doc: docs/design/Citations.md#2-서재-논문과-openalex-연결
        """
        with self.engine.begin() as connection:
            connection.execute(delete(_link_misses).where(_link_misses.c.doi == doi))
            connection.execute(insert(_link_misses).values(doi=doi, tried_at=now.isoformat()))

    def fetched_count(self, work_ids: set[str]) -> int:
        """이 논문들 가운데 인용 데이터를 가져온 수를 센다.

        @doc: docs/design/Citations.md#6-api와-화면
        """
        with self.engine.connect() as connection:
            rows = connection.execute(select(_fetches.c.paper).where(_fetches.c.fetched_at.is_not(None)))
            return len({row.paper for row in rows} & work_ids)

    def miss_count(self, dois: set[str]) -> int:
        """이 DOI들 가운데 찾지 못한 것으로 기억한 수를 센다.

        @doc: docs/design/Citations.md#6-api와-화면
        """
        with self.engine.connect() as connection:
            return len({row.doi for row in connection.execute(select(_link_misses.c.doi))} & dois)

    def rows(self, table: str) -> list[dict[str, Any]]:
        """표 하나의 모든 행. 테스트와 진단에 쓴다.

        @doc: docs/design/Citations.md#7-테스트
        """
        with self.engine.connect() as connection:
            return [dict(row._mapping) for row in connection.execute(select(_metadata.tables[table]))]

    def snapshot(self) -> bytes:
        """쓰는 중이 아닌 일관된 사본의 내용을 돌려준다.

        @doc: docs/design/Citations.md#4-저장
        """
        with tempfile.TemporaryDirectory() as folder:
            copy = Path(folder) / CACHE_FILE
            with self.engine.connect() as connection:
                connection.exec_driver_sql("VACUUM INTO ?", (str(copy),))
            return copy.read_bytes()


class CitationStatus(BaseModel):
    """인용 데이터 상태.

    @doc: docs/design/Citations.md#6-api와-화면
    """

    papers: int
    linked: int
    not_found: int
    fetched: int
    running: bool
    last_run: datetime | None
    error: str


class DriveLike(Protocol):
    """`CitationSync`가 쓰는 드라이브 동기화의 모양. 테스트는 같은 모양의 가짜를 넘긴다.

    @doc: docs/design/Citations.md#4-저장
    """

    def is_connected(self) -> bool: ...
    def put_cache(self, name: str, data: bytes) -> bool: ...
    def get_cache(self, name: str) -> bytes | None: ...
    def schedule_push(self) -> None: ...


class CitationSync:
    """인용 데이터의 백그라운드 갱신.

    @doc: docs/design/Citations.md#5-갱신
    """

    def __init__(
        self,
        library_engine: Engine,
        cache_path: Path,
        http: httpx2.Client,
        drive: DriveLike,
        clock: Callable[[], datetime] = lambda: datetime.now(UTC),
    ) -> None:
        self.library_engine = library_engine
        self.cache_path = cache_path
        self.http = http
        self.drive = drive
        self.clock = clock
        self._store: CitationStore | None = None
        self._store_lock = threading.Lock()
        self._run_lock = threading.Lock()
        self._wake = threading.Event()
        self._stopped = False
        self._thread: threading.Thread | None = None
        self.running = False
        self.last_run: datetime | None = None
        self.error = ""

    @property
    def store(self) -> CitationStore:
        """캐시 파일. 처음 쓸 때 연다.

        @doc: docs/design/Citations.md#4-저장
        """
        with self._store_lock:
            if self._store is None:
                self._store = CitationStore(self.cache_path)
            return self._store

    def restore_from_drive(self) -> bool:
        """로컬에 캐시 파일이 없고 드라이브에 있으면 받는다.

        @doc: docs/design/Citations.md#4-저장
        """
        with self._store_lock:
            if self._store is not None or self.cache_path.exists() or not self.drive.is_connected():
                return False
            data = self.drive.get_cache(CACHE_FILE)
            if data is None:
                return False
            self.cache_path.parent.mkdir(parents=True, exist_ok=True)
            self.cache_path.write_bytes(data)
            return True

    def run_once(self) -> int:
        """갱신을 한 번 하고 가져온 논문 수를 돌려준다.

        @doc: docs/design/Citations.md#5-갱신
        """
        with self._run_lock:
            self.running = True
            self.error = ""
            try:
                return self._run()
            finally:
                self.running = False
                self.last_run = self.clock()

    def _run(self) -> int:
        now = self.clock()
        store = self.store
        with Session(self.library_engine) as session:
            papers = list(session.scalars(select(Paper)))
            store.prune({paper.openalex_id for paper in papers if paper.openalex_id})
            linked = False
            try:
                for paper in papers:
                    if paper.openalex_id or not paper.doi or store.missed_recently(paper.doi, now):
                        continue
                    work_id = link_paper(self.http, paper.doi)
                    if work_id is None:
                        store.record_miss(paper.doi, now)
                    else:
                        paper.openalex_id = work_id
                        linked = True
            except OpenAlexBudgetError as error:
                self.error = str(error)
            except (httpx2.HTTPError, ValueError) as error:
                self.error = f"OpenAlex 연결 실패: {error}"
            finally:
                if linked:
                    session.commit()
                    self.drive.schedule_push()
            if self.error:
                return 0
            limit = read_settings(session)["citing_limit"]
            work_ids = [paper.openalex_id for paper in papers if paper.openalex_id]
        fetched = 0
        for work_id in store.stale(work_ids, now):
            if self._stopped:
                break
            try:
                result = fetch_citations(self.http, work_id, limit, now)
            except OpenAlexBudgetError as error:
                self.error = str(error)
                break
            except (httpx2.HTTPError, ValueError, KeyError, LookupError) as error:
                self.error = f"{work_id} 인용 데이터를 받지 못했습니다: {error}"
                continue
            store.save(work_id, result, limit, now)
            fetched += 1
        if fetched:
            self.drive.put_cache(CACHE_FILE, store.snapshot())
        return fetched

    def _loop(self) -> None:
        self.restore_from_drive()
        while not self._stopped:
            try:
                self.run_once()
            except Exception as error:  # noqa: BLE001 - 스레드가 죽지 않게 모든 오류를 상태에 남긴다.
                self.error = f"인용 데이터 갱신 실패: {error}"
            self._wake.wait(RUN_INTERVAL_SECONDS)
            self._wake.clear()

    def start(self) -> None:
        """백그라운드 갱신 스레드를 띄운다.

        @doc: docs/design/Citations.md#5-갱신
        """
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """갱신 스레드를 멈춘다.

        @doc: docs/design/Citations.md#5-갱신
        """
        self._stopped = True
        self._wake.set()

    def wake(self) -> None:
        """기다리는 갱신을 바로 깨운다.

        @doc: docs/design/Citations.md#5-갱신
        """
        self._wake.set()

    def refresh(self) -> None:
        """모든 논문을 가져올 대상으로 표시하고 깨운다.

        @doc: docs/design/Citations.md#5-갱신
        """
        self.store.mark_all_stale()
        self.wake()

    def status(self) -> CitationStatus:
        """지금 상태를 돌려준다.

        @doc: docs/design/Citations.md#6-api와-화면
        """
        with Session(self.library_engine) as session:
            papers = list(session.scalars(select(Paper)))
        work_ids = {paper.openalex_id for paper in papers if paper.openalex_id}
        unlinked_dois = {paper.doi for paper in papers if not paper.openalex_id and paper.doi}
        store = self.store
        return CitationStatus(
            papers=len(papers),
            linked=sum(1 for paper in papers if paper.openalex_id),
            not_found=store.miss_count(unlinked_dois),
            fetched=store.fetched_count(work_ids),
            running=self.running,
            last_run=self.last_run,
            error=self.error,
        )


# @doc: docs/design/Citations.md#6-api와-화면
router = APIRouter(prefix="/api/citations")


@router.get("/status")
def citation_status(request: Request) -> CitationStatus:
    """`GET /api/citations/status`를 처리한다.

    @doc: docs/design/Citations.md#6-api와-화면
    """
    return request.app.state.citations.status()


@router.post("/refresh")
def refresh_citations(request: Request) -> CitationStatus:
    """`POST /api/citations/refresh`를 처리한다.

    @doc: docs/design/Citations.md#6-api와-화면
    """
    request.app.state.citations.refresh()
    return request.app.state.citations.status()
