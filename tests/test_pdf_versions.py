"""논문 PDF의 판: 판 찾기, 받아 둔 판, 고르기, 판마다의 위치와 주석을 검증한다.

@doc: docs/design/PdfVersions.md#7-테스트
"""

from pathlib import Path

import httpx2
from fastapi.testclient import TestClient

from jjabtero.models import PaperPdf
from jjabtero.pdf_versions import arxiv_id, location_versions, parse_arxiv_versions, saved_label
from test_pdfs import FakeWeb, add_paper, make_app

ARXIV_RAW = """<?xml version="1.0" encoding="UTF-8"?>
<OAI-PMH xmlns="http://www.openarchives.org/OAI/2.0/"><GetRecord><record><metadata>
<arXivRaw xmlns="http://arxiv.org/OAI/arXivRaw/">
  <id>2505.22954</id>
  <version version="v2"><date>Fri, 26 Sep 2025 16:36:03 GMT</date><size>2259kb</size></version>
  <version version="v1"><date>Thu, 29 May 2025 00:26:15 GMT</date><size>2230kb</size></version>
  <version version="v3"><date>Thu, 12 Mar 2026 23:47:40 GMT</date><size>2241kb</size></version>
</arXivRaw></metadata></record></GetRecord></OAI-PMH>"""

LOCATIONS = [
    {
        "source": {"display_name": "SuperIntelligence"},
        "version": "publishedVersion",
        "pdf_url": "https://s-rsa.com/download/15063.pdf",
        "landing_page_url": "https://doi.org/10.70777/si.v2i3.15063",
    },
    {"source": {"display_name": "NeurIPS"}, "version": "publishedVersion", "pdf_url": None},
    {
        "source": {"display_name": "arXiv (Cornell University)"},
        "version": "submittedVersion",
        "pdf_url": "https://arxiv.org/pdf/2505.22954",
        "landing_page_url": "http://arxiv.org/abs/2505.22954",
    },
    {"source": None, "version": None, "pdf_url": "https://s-rsa.com/download/15063.pdf"},
]


class VersionsWeb(FakeWeb):
    """OpenAlex 위치와 arXiv 메타데이터에 답하는 가짜 웹. PDF 주소마다 다른 내용을 준다.

    @doc: docs/design/PdfVersions.md#7-테스트
    """

    def __init__(self, locations: list[dict] | None = None, arxiv: str = ARXIV_RAW, arxiv_status: int = 200) -> None:
        super().__init__()
        self.locations = LOCATIONS if locations is None else locations
        self.arxiv = arxiv
        self.arxiv_status = arxiv_status

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.urls.append(str(request.url))
        if request.url.host == "api.openalex.org":
            return httpx2.Response(200, json={"locations": self.locations})
        if request.url.host == "export.arxiv.org":
            return httpx2.Response(self.arxiv_status, text=self.arxiv)
        return httpx2.Response(200, content=b"%PDF-1.7 " + str(request.url).encode())


def test_parse_arxiv_versions_orders_versions_with_dates() -> None:
    """arXiv 메타데이터의 판을 번호 순으로 날짜와 함께 읽고, 깨진 응답은 빈 목록이다.

    @doc: docs/design/PdfVersions.md#7-테스트
    """
    assert parse_arxiv_versions(ARXIV_RAW) == [("v1", "2025-05-29"), ("v2", "2025-09-26"), ("v3", "2026-03-12")]
    assert parse_arxiv_versions("<OAI-PMH><error code='idDoesNotExist'/></OAI-PMH>") == []
    assert parse_arxiv_versions("not xml") == []


def test_arxiv_id_reads_numbers_and_versions() -> None:
    """arXiv 소개·PDF 주소에서 번호와 판을 읽고, 다른 주소는 `None`이다.

    @doc: docs/design/PdfVersions.md#7-테스트
    """
    assert arxiv_id("https://arxiv.org/pdf/2505.22954v2") == ("2505.22954", "v2")
    assert arxiv_id("http://arxiv.org/abs/2505.22954") == ("2505.22954", None)
    assert arxiv_id("https://arxiv.org/abs/cs/0309048") == ("cs/0309048", None)
    assert arxiv_id("https://example.org/2505.22954.pdf") is None


def test_location_versions_skip_missing_pdf_arxiv_and_repeats() -> None:
    """공개 PDF가 없는 위치, arXiv 위치, 같은 주소는 빼고 출처와 판 종류로 이름을 붙인다.

    @doc: docs/design/PdfVersions.md#7-테스트
    """
    found = location_versions(LOCATIONS)
    assert [(item.key, item.label) for item in found] == [
        ("url:https://s-rsa.com/download/15063.pdf", "SuperIntelligence · 출판판")
    ]


def test_saved_label_by_source() -> None:
    """받아 둔 판의 이름은 arXiv 판, 올린 파일, 비슷한 공개판, 호스트 이름 순으로 정한다.

    @doc: docs/design/PdfVersions.md#7-테스트
    """

    def pdf(source: str, url: str | None) -> PaperPdf:
        return PaperPdf(sha256="a", size=1, source=source, source_url=url)

    assert saved_label(pdf("arxiv", "https://arxiv.org/pdf/2505.22954v1")) == "arXiv v1"
    assert saved_label(pdf("arxiv", "https://arxiv.org/pdf/2505.22954")) == "arXiv"
    assert saved_label(pdf("upload", None)) == "올린 PDF"
    assert saved_label(pdf("alternate", "https://x.org/a.pdf")) == "비슷한 공개판"
    assert saved_label(pdf("openalex", "https://s-rsa.com/a.pdf")) == "s-rsa.com"


def test_available_versions_from_openalex_and_arxiv(tmp_path: Path) -> None:
    """받을 수 있는 판은 OpenAlex 위치 다음에 arXiv 판을 최신부터 두고, 받아 둔 판은 표시한다.

    @doc: docs/design/PdfVersions.md#7-테스트
    """
    app, _ = make_app(tmp_path, VersionsWeb())
    client = TestClient(app)
    paper_id = add_paper(client, openalex_id="W1")
    found = client.get(f"/api/papers/{paper_id}/pdf/versions/available").json()
    assert [(item["key"], item["date"], item["latest"]) for item in found] == [
        ("url:https://s-rsa.com/download/15063.pdf", None, False),
        ("arxiv:v3", "2026-03-12", True),
        ("arxiv:v2", "2025-09-26", False),
        ("arxiv:v1", "2025-05-29", False),
    ]
    assert found[1]["url"] == "https://arxiv.org/pdf/2505.22954v3"
    assert client.post(f"/api/papers/{paper_id}/pdf/fetch", json={"version": "arxiv:v1"}).status_code == 200
    again = client.get(f"/api/papers/{paper_id}/pdf/versions/available").json()
    assert [item["saved_sha256"] is not None for item in again] == [False, False, False, True]


def test_available_versions_without_openalex_uses_arxiv_doi_and_reports_failure(tmp_path: Path) -> None:
    """OpenAlex에 연결되지 않은 arXiv 논문은 DOI로 arXiv 판을 찾고, 찾기에 실패하면 502다.

    @doc: docs/design/PdfVersions.md#7-테스트
    """
    web = VersionsWeb()
    app, _ = make_app(tmp_path, web)
    client = TestClient(app)
    paper_id = add_paper(client, doi="10.48550/arxiv.2505.22954")
    found = client.get(f"/api/papers/{paper_id}/pdf/versions/available").json()
    assert [item["key"] for item in found] == ["arxiv:v3", "arxiv:v2", "arxiv:v1"]
    assert not any("openalex" in url for url in web.urls)
    web.arxiv_status = 503
    assert client.get(f"/api/papers/{paper_id}/pdf/versions/available").status_code == 502


def test_fetch_versions_keeps_each_and_select_switches(tmp_path: Path) -> None:
    """판을 받을 때마다 판이 늘고 지금 판이 되며, 같은 내용은 늘지 않고, 받아 둔 판을 골라 바꾼다. 모르는 판은 404다.

    @doc: docs/design/PdfVersions.md#7-테스트
    """
    app, _ = make_app(tmp_path, VersionsWeb())
    client = TestClient(app)
    paper_id = add_paper(client, openalex_id="W1")
    assert client.post(f"/api/papers/{paper_id}/pdf/fetch", json={"version": "arxiv:v9"}).status_code == 404
    first = client.post(f"/api/papers/{paper_id}/pdf/fetch", json={"version": "arxiv:v1"}).json()
    second = client.post(f"/api/papers/{paper_id}/pdf/fetch", json={"version": "url:https://s-rsa.com/download/15063.pdf"}).json()
    client.post(f"/api/papers/{paper_id}/pdf/fetch", json={"version": "arxiv:v1"})
    saved = client.get(f"/api/papers/{paper_id}/pdf/versions").json()
    assert [(item["sha256"], item["label"], item["selected"]) for item in saved] == [
        (first["sha256"], "arXiv v1", True),
        (second["sha256"], "s-rsa.com", False),
    ]
    selected = client.put(f"/api/papers/{paper_id}/pdf/selected", json={"sha256": second["sha256"]}).json()
    assert [item["selected"] for item in selected] == [True, False]
    assert selected[0]["sha256"] == second["sha256"]
    assert client.get(f"/api/papers/{paper_id}/pdf").content.endswith(b"15063.pdf")
    assert client.get(f"/api/papers/{paper_id}/pdf", params={"version": first["sha256"]}).content.endswith(b"v1")
    paper = client.get("/api/papers").json()[0]
    assert (paper["has_pdf"], paper["pdf_source"]) == (True, "openalex")
    assert client.put(f"/api/papers/{paper_id}/pdf/selected", json={"sha256": "0" * 64}).status_code == 404
    assert client.get(f"/api/papers/{paper_id}/pdf", params={"version": "0" * 64}).status_code == 404


def test_positions_and_annotations_are_per_version(tmp_path: Path) -> None:
    """읽던 위치와 주석은 판마다 따로이고, 판을 주지 않으면 지금 판이다. 마지막으로 읽은 시각은 판 가운데 가장 늦은 것이다.

    @doc: docs/design/PdfVersions.md#7-테스트
    """
    app, _ = make_app(tmp_path, VersionsWeb())
    client = TestClient(app)
    paper_id = add_paper(client, openalex_id="W1")
    note = {"kind": "note", "page": 1, "rects": [{"x": 0.1, "y": 0.1, "w": 0.2, "h": 0.2}], "note": "v1"}
    assert client.post(f"/api/papers/{paper_id}/annotations", json=note).status_code == 404
    assert client.get(f"/api/papers/{paper_id}/annotations").json() == []
    old = client.post(f"/api/papers/{paper_id}/pdf/fetch", json={"version": "arxiv:v1"}).json()["sha256"]
    client.put(f"/api/papers/{paper_id}/position", json={"page": 5, "offset": 0, "zoom": 1})
    client.post(f"/api/papers/{paper_id}/annotations", json=note)
    new = client.post(f"/api/papers/{paper_id}/pdf/fetch", json={"version": "arxiv:v3"}).json()["sha256"]
    assert client.get(f"/api/papers/{paper_id}/position").status_code == 204
    assert client.get(f"/api/papers/{paper_id}/annotations").json() == []
    saved = client.put(f"/api/papers/{paper_id}/position", json={"page": 2, "offset": 0, "zoom": 1}).json()
    client.post(f"/api/papers/{paper_id}/annotations", params={"version": old}, json={**note, "note": "v1 again"})
    assert client.get(f"/api/papers/{paper_id}/position", params={"version": old}).json()["page"] == 5
    assert client.get(f"/api/papers/{paper_id}/position", params={"version": new}).json()["page"] == 2
    notes = client.get(f"/api/papers/{paper_id}/annotations", params={"version": old}).json()
    assert [item["note"] for item in notes] == ["v1", "v1 again"]
    assert client.get(f"/api/papers/{paper_id}/position", params={"version": "0" * 64}).status_code == 404
    assert client.get(f"/api/papers/{paper_id}/annotations", params={"version": "0" * 64}).status_code == 404
    assert client.put(f"/api/papers/{paper_id}/position", params={"version": "x"}, json=saved).status_code == 422
    listed = client.get("/api/papers").json()[0]["last_read_at"]
    assert listed.startswith(saved["updated_at"][:19])
