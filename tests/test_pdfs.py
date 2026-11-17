"""논문 PDF의 가져오기, 보관, 내려주기를 검증한다.

@doc: docs/design/Reader.md#8-테스트
"""

import hashlib
from pathlib import Path

import httpx2
import pytest
from fastapi.testclient import TestClient

from fakes import FakeDrive, write_client_secret
from jjabtero.app import create_app
from jjabtero.drive_sync import DrivePaths
from jjabtero.google_auth import Token, TokenStore
from jjabtero.pdfs import MAX_PDF_BYTES, title_similarity

PDF = b"%PDF-1.7\n" + b"x" * 100
ARXIV_DOI = "10.48550/arxiv.1706.03762"


class FakeWeb:
    """OpenAlex와 PDF 주소에 답하는 가짜 웹.

    @doc: docs/design/Reader.md#8-테스트
    """

    def __init__(self, oa_url: str | None = "https://example.org/a.pdf", body: bytes = PDF) -> None:
        self.oa_url = oa_url
        self.body = body
        self.urls: list[str] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.urls.append(str(request.url))
        if request.url.host == "api.openalex.org":
            location = {"pdf_url": self.oa_url} if self.oa_url else None
            return httpx2.Response(200, json={"best_oa_location": location, "open_access": {"oa_url": None}})
        if request.url.path == "/redirect.pdf":
            return httpx2.Response(302, headers={"location": "https://example.org/a.pdf"})
        return httpx2.Response(200, content=self.body)


def make_app(tmp_path: Path, web: FakeWeb, drive: FakeDrive | None = None, connected: bool = True):
    """가짜 웹과 가짜 드라이브를 쓰는 앱. 드라이브는 연결된 상태로 둔다.

    @doc: docs/design/Reader.md#8-테스트
    """
    paths = DrivePaths(tmp_path / "client.json", tmp_path / "token.json", tmp_path / "state.json", tmp_path / "backups")
    if connected:
        write_client_secret(paths.client_secret)
        TokenStore(paths.token).save(Token("a", "r", 10**12))
    shared = drive or FakeDrive()
    app = create_app(
        frontend_dist=tmp_path / "missing",
        db_path=tmp_path / "data" / "library.db",
        http_client=httpx2.Client(transport=httpx2.MockTransport(web)),
        drive_paths=paths,
        drive_files=lambda http, token: shared,
    )
    app.state.drive.schedule_push = lambda: None
    return app, shared


def add_paper(client: TestClient, **fields) -> int:
    """서재에 논문을 넣고 ID를 돌려준다.

    @doc: docs/design/Reader.md#8-테스트
    """
    return client.post("/api/papers", json={"title": "T", **fields}).json()["id"]


def test_fetch_uses_openalex_pdf_and_stores_locally_and_in_drive(tmp_path: Path) -> None:
    """OpenAlex의 공개 PDF를 받아 로컬 사본과 드라이브 `Jjabtero/pdfs/`에 둔다.

    @doc: docs/design/Reader.md#8-테스트
    """
    web = FakeWeb()
    app, drive = make_app(tmp_path, web)
    client = TestClient(app)
    paper_id = add_paper(client, openalex_id="W1")

    response = client.post(f"/api/papers/{paper_id}/pdf/fetch")
    assert response.status_code == 200
    body = response.json()
    sha = hashlib.sha256(PDF).hexdigest()
    assert (body["source"], body["sha256"], body["stored_in_drive"]) == ("openalex", sha, True)
    assert (tmp_path / "data" / "pdfs" / f"{sha}.pdf").read_bytes() == PDF
    names = {item["name"]: item for item in drive.files.values()}
    assert names[f"{sha}.pdf"]["parent"] == next(k for k, v in drive.files.items() if v["name"] == "pdfs")
    assert client.get("/api/papers").json()[0]["has_pdf"] is True
    pdf = client.get(f"/api/papers/{paper_id}/pdf")
    assert pdf.headers["content-type"] == "application/pdf" and pdf.content == PDF


def test_fetch_falls_back_to_arxiv_doi(tmp_path: Path) -> None:
    """OpenAlex에 공개 PDF가 없어도 arXiv DOI면 arXiv PDF를 받는다.

    @doc: docs/design/Reader.md#8-테스트
    """
    web = FakeWeb(oa_url=None)
    app, _ = make_app(tmp_path, web)
    client = TestClient(app)
    paper_id = add_paper(client, doi=ARXIV_DOI)
    assert client.post(f"/api/papers/{paper_id}/pdf/fetch").json()["source"] == "arxiv"
    assert "https://arxiv.org/pdf/1706.03762" in web.urls


def test_fetch_without_open_pdf_is_404(tmp_path: Path) -> None:
    """공개 PDF가 없으면 404와 직접 올리라는 안내다.

    @doc: docs/design/Reader.md#8-테스트
    """
    app, _ = make_app(tmp_path, FakeWeb(oa_url=None))
    client = TestClient(app)
    paper_id = add_paper(client, openalex_id="W1")
    response = client.post(f"/api/papers/{paper_id}/pdf/fetch")
    assert response.status_code == 404 and "직접 올려" in response.json()["detail"]


def test_fetch_rejects_html(tmp_path: Path) -> None:
    """PDF가 아닌 내용을 받으면 502로 거절하고 저장하지 않는다.

    @doc: docs/design/Reader.md#8-테스트
    """
    app, _ = make_app(tmp_path, FakeWeb(body=b"<html>login</html>"))
    client = TestClient(app)
    paper_id = add_paper(client, openalex_id="W1")
    assert client.post(f"/api/papers/{paper_id}/pdf/fetch").status_code == 502
    assert client.get("/api/papers").json()[0]["has_pdf"] is False


def test_upload_replaces_and_validates(tmp_path: Path) -> None:
    """올린 PDF는 옛 PDF를 바꾸고, PDF가 아니면 415, 너무 크면 413이다.

    @doc: docs/design/Reader.md#8-테스트
    """
    app, _ = make_app(tmp_path, FakeWeb())
    client = TestClient(app)
    paper_id = add_paper(client, openalex_id="W1")
    client.post(f"/api/papers/{paper_id}/pdf/fetch")
    other = b"%PDF-1.4\nother"
    response = client.put(f"/api/papers/{paper_id}/pdf", content=other)
    assert response.status_code == 200 and response.json()["source"] == "upload"
    assert client.get(f"/api/papers/{paper_id}/pdf").content == other
    assert client.put(f"/api/papers/{paper_id}/pdf", content=b"not a pdf").status_code == 415
    big = client.put(
        f"/api/papers/{paper_id}/pdf", content=b"%PDF-", headers={"content-length": str(MAX_PDF_BYTES + 1)}
    )
    assert big.status_code == 413


def test_missing_local_copy_is_restored_from_drive(tmp_path: Path) -> None:
    """로컬 사본이 없으면(다른 컴퓨터나 재시작한 서버) 드라이브에서 받아 둔다.

    @doc: docs/design/Reader.md#8-테스트
    """
    app, _ = make_app(tmp_path, FakeWeb())
    client = TestClient(app)
    paper_id = add_paper(client, openalex_id="W1")
    sha = client.post(f"/api/papers/{paper_id}/pdf/fetch").json()["sha256"]
    local = tmp_path / "data" / "pdfs" / f"{sha}.pdf"
    local.unlink()
    assert client.get(f"/api/papers/{paper_id}/pdf").content == PDF
    assert local.exists()


def test_without_drive_keeps_local_only(tmp_path: Path) -> None:
    """드라이브에 연결되어 있지 않으면 로컬 사본만 둔다.

    @doc: docs/design/Reader.md#8-테스트
    """
    app, drive = make_app(tmp_path, FakeWeb(), connected=False)
    client = TestClient(app)
    paper_id = add_paper(client)
    body = client.put(f"/api/papers/{paper_id}/pdf", content=PDF).json()
    assert body["stored_in_drive"] is False
    assert drive.files == {}
    assert client.get(f"/api/papers/{paper_id}/pdf").content == PDF


@pytest.mark.parametrize("method,path", [("get", "/pdf"), ("post", "/pdf/fetch"), ("put", "/pdf")])
def test_unknown_paper_is_404(tmp_path: Path, method: str, path: str) -> None:
    """없는 논문은 404다.

    @doc: docs/design/Reader.md#8-테스트
    """
    app, _ = make_app(tmp_path, FakeWeb())
    client = TestClient(app)
    response = getattr(client, method)(f"/api/papers/99{path}", **({"content": PDF} if method == "put" else {}))
    assert response.status_code == 404


def test_deleting_paper_removes_pdf_link(tmp_path: Path) -> None:
    """논문을 지우면 PDF 연결도 지운다. 드라이브 파일은 남긴다.

    @doc: docs/design/Reader.md#8-테스트
    """
    app, drive = make_app(tmp_path, FakeWeb())
    client = TestClient(app)
    paper_id = add_paper(client)
    client.put(f"/api/papers/{paper_id}/pdf", content=PDF)
    assert client.delete(f"/api/papers/{paper_id}").status_code == 204
    from sqlalchemy import text

    with app.state.engine.connect() as connection:
        assert connection.execute(text("select count(*) from paper_pdfs")).scalar() == 0
    assert any(item["name"].endswith(".pdf") for item in drive.files.values())


def test_arxiv_abstract_page_becomes_pdf_url(tmp_path: Path) -> None:
    """OpenAlex가 arXiv 소개 페이지를 주면 PDF 주소로 바꿔 받는다.

    @doc: docs/design/Reader.md#8-테스트
    """
    web = FakeWeb(oa_url="https://arxiv.org/abs/1412.6980v5")
    app, _ = make_app(tmp_path, web)
    client = TestClient(app)
    paper_id = add_paper(client, openalex_id="W1")
    body = client.post(f"/api/papers/{paper_id}/pdf/fetch").json()
    assert body["source_url"] == "https://arxiv.org/pdf/1412.6980v5"


def test_title_similarity_accepts_other_editions_only() -> None:
    """표기가 다른 같은 논문의 판은 비슷하다고 보고, 같은 저자의 다른 논문은 0이다.

    @doc: docs/design/Reader.md#8-테스트
    """
    chapter = "Gödel Machines: Fully Self-referential Optimal Universal Self-improvers"
    preprint = "Goedel Machines: Self-Referential Universal Problem Solvers Making Provably Optimal Self-Improvements"
    assert title_similarity(chapter, preprint) > 0.9
    assert title_similarity(chapter, "Developmental robotics, optimal artificial curiosity, creativity, music") == 0
    assert title_similarity("Learning: a survey", "Learning: other things entirely") == 0
    assert title_similarity("Deep learning in neural networks", "Neural networks and deep learning, revisited") > 0


def work(work_id: str, title: str, authors: list[str], year: int = 2003, pdf: str | None = None, doi: str | None = None) -> dict:
    """OpenAlex 검색 결과 하나.

    @doc: docs/design/Reader.md#8-테스트
    """
    return {
        "id": f"https://openalex.org/{work_id}",
        "doi": f"https://doi.org/{doi}" if doi else None,
        "display_name": title,
        "publication_year": year,
        "authorships": [{"author": {"display_name": name}} for name in authors],
        "primary_location": {"source": {"display_name": "arXiv"}},
        "best_oa_location": {"pdf_url": pdf} if pdf else None,
        "open_access": {"oa_url": None},
    }


class AlternativesWeb(FakeWeb):
    """서재 논문은 공개 PDF가 없고, 검색에는 공개판 후보를 주는 가짜 웹.

    @doc: docs/design/Reader.md#8-테스트
    """

    def __init__(self, results: list[dict]) -> None:
        super().__init__(oa_url=None)
        self.results = results
        self.params: list[dict] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        if request.url.host == "api.openalex.org" and request.url.path == "/works":
            self.urls.append(str(request.url))
            self.params.append(dict(request.url.params))
            return httpx2.Response(200, json={"results": self.results})
        if request.url.host == "api.openalex.org" and request.url.path == "/works/W2":
            self.urls.append(str(request.url))
            return httpx2.Response(200, json={"best_oa_location": {"pdf_url": "https://arxiv.org/abs/cs/0309048"}})
        return super().__call__(request)


CHAPTER = "Gödel Machines: Fully Self-referential Optimal Universal Self-improvers"
PREPRINT = "Goedel Machines: Self-Referential Universal Problem Solvers Making Provably Optimal Self-Improvements"


def test_alternatives_pick_same_author_similar_title_with_pdf(tmp_path: Path) -> None:
    """같은 첫 저자, 비슷한 제목, 5년 안, 공개 PDF가 있는 것만 비슷함 순으로 고르고, 자기 자신은 뺀다.

    @doc: docs/design/Reader.md#8-테스트
    """
    web = AlternativesWeb(
        [
            work("W9", "Developmental robotics, optimal artificial curiosity", ["Jürgen Schmidhuber"], pdf="https://x/a.pdf"),
            work("W2", PREPRINT, ["Jürgen Schmidhuber"], pdf="https://arxiv.org/abs/cs/0309048"),
            work("W3", PREPRINT, ["Jürgen Schmidhuber"]),
            work("W4", "Gödel Agent: a self-referential agent", ["Xunjian Yin"], pdf="https://x/b.pdf"),
            work("W5", PREPRINT, ["Jürgen Schmidhuber"], year=1990, pdf="https://x/c.pdf"),
            work("W1", CHAPTER, ["Jürgen Schmidhuber"], year=2007, pdf="https://x/self.pdf"),
            work("W6", CHAPTER, ["J. Schmidhuber"], year=2007, pdf="https://x/d.pdf", doi="10.1007/978-3-540-68677-4_7"),
        ]
    )
    app, _ = make_app(tmp_path, web)
    client = TestClient(app)
    paper_id = add_paper(
        client, title=CHAPTER, authors=["Jürgen Schmidhuber"], year=2007, openalex_id="W1", doi="10.1007/978-3-540-68677-4_7"
    )
    found = client.get(f"/api/papers/{paper_id}/pdf/alternatives").json()
    assert [item["openalex_id"] for item in found] == ["W2"]
    assert found[0]["pdf_url"] == "https://arxiv.org/pdf/cs/0309048" and found[0]["authors"] == ["Jürgen Schmidhuber"]
    assert web.params[0]["filter"] == "is_oa:true,raw_author_name.search:schmidhuber"

    no_author = add_paper(client, title="Anonymous", doi="10.1/x")
    assert client.get(f"/api/papers/{no_author}/pdf/alternatives").json() == []
    assert client.get("/api/papers/999/pdf/alternatives").status_code == 404


def test_fetch_alternate_version_stores_its_pdf(tmp_path: Path) -> None:
    """공개판 ID를 주면 그 공개판의 PDF를 받아 출처 `alternate`로 두고, 논문 응답에 출처를 보인다.

    @doc: docs/design/Reader.md#8-테스트
    """
    web = AlternativesWeb([])
    app, _ = make_app(tmp_path, web)
    client = TestClient(app)
    paper_id = add_paper(client, title=CHAPTER, openalex_id="W1")
    assert client.post(f"/api/papers/{paper_id}/pdf/fetch").status_code == 404
    response = client.post(f"/api/papers/{paper_id}/pdf/fetch", json={"openalex_id": "W2"})
    assert response.status_code == 200
    assert (response.json()["source"], response.json()["source_url"]) == ("alternate", "https://arxiv.org/pdf/cs/0309048")
    paper = client.get("/api/papers").json()[0]
    assert (paper["pdf_source"], paper["pdf_source_url"]) == ("alternate", "https://arxiv.org/pdf/cs/0309048")
    assert client.post(f"/api/papers/{paper_id}/pdf/fetch", json={"openalex_id": "x"}).status_code == 422
