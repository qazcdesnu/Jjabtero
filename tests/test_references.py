"""참고문헌 항목 글로 논문 찾기를 검증한다.

@doc: docs/design/ReaderCitations.md#4-논문-찾기
"""

from pathlib import Path

import httpx2
from fastapi.testclient import TestClient

from jjabtero.app import create_app
from jjabtero.references import match_reference, normalize, title_candidates

A = "W100"
TITLES = {
    "W1": ("Long Short-Term Memory", 1997, None),
    "W2": ("Neural Machine Translation by Jointly Learning to Align and Translate", 2014, "10.48550/arxiv.1409.0473"),
    "W3": ("Adam", 2014, None),
}
LSTM = "Sepp Hochreiter and Jürgen Schmidhuber. Long short-term memory. Neural computation, 9(8):1735–1780, 1997."
BAHDANAU = (
    "Dzmitry Bahdanau, Kyunghyun Cho, and Yoshua Bengio. Neural machine translation by jointly learning to align and "
    "translate. CoRR, abs/1409.0473, 2014."
)
GAN = "Ian Goodfellow et al. Generative adversarial nets. In NIPS, 2014."


def work(work_id: str) -> dict:
    """OpenAlex 작업 응답 하나.

    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """
    title, year, doi = TITLES[work_id]
    return {
        "id": f"https://openalex.org/{work_id}",
        "doi": f"https://doi.org/{doi}" if doi else None,
        "display_name": title,
        "type": "article",
        "publication_year": year,
        "publication_date": f"{year}-01-01",
        "cited_by_count": 10,
        "authorships": [],
        "primary_location": None,
    }


class FakeOpenAlex:
    """참고문헌, 검색, 공개 PDF 주소에 답하는 가짜 OpenAlex.

    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """

    def __init__(self) -> None:
        self.searches: list[str] = []
        self.oa = {"W1": "https://example.org/lstm.pdf"}

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        params = request.url.params
        path = request.url.path
        if path == f"/works/{A}":
            refs = [f"https://openalex.org/{w}" for w in ("W1", "W2", "W3")]
            return httpx2.Response(200, json={"id": f"https://openalex.org/{A}", "publication_date": "2017-06-12", "referenced_works": refs})
        if path.startswith("/works/W"):
            url = self.oa.get(path.removeprefix("/works/"))
            return httpx2.Response(200, json={"best_oa_location": {"pdf_url": url} if url else None, "open_access": {"oa_url": None}})
        if "search" in params:
            self.searches.append(params["search"])
            gan = {**work("W1"), "id": "https://openalex.org/W9", "display_name": "Generative Adversarial Nets", "publication_year": 2014}
            return httpx2.Response(200, json={"results": [gan]})
        flt = params.get("filter", "")
        if flt.startswith("cites:"):
            return httpx2.Response(200, json={"meta": {"count": 0}, "results": []})
        ids = flt.removeprefix("openalex_id:").split("|")
        return httpx2.Response(200, json={"meta": {"count": len(ids)}, "results": [work(i) for i in ids if i in TITLES]})


def test_normalize_drops_accents_and_symbols() -> None:
    """악센트를 떼고 글자·숫자가 아닌 것을 빈칸으로 바꾼다.

    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """
    assert normalize("Jürgen  Schmidhuber: Long short-term memory (1997).") == "jurgen schmidhuber long short term memory 1997"


def test_title_candidates_put_title_first() -> None:
    """번호 표시를 떼고 이름 머리글자에서 끊지 않으며, 저자와 게재처 조각보다 제목 조각을 앞에 둔다.

    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """
    assert title_candidates(f"[12] {LSTM}")[0] == "Long short-term memory"
    assert title_candidates("D. P. Kingma and J. Ba. Adam: A method for stochastic optimization. In ICLR, 2015.")[:2] == [
        "Adam: A method for stochastic optimization",
        "D. P. Kingma and J. Ba",
    ]
    vaswani = "Ashish Vaswani, Noam Shazeer, et al. Attention is all you need. In Advances in NeurIPS, pages 5998–6008, 2017."
    assert title_candidates(vaswani)[0] == "Attention is all you need"
    apa = "Zhang, Y., Li, X., & Wang, Z. (2025b). Scaling laws for retrieval augmented generation. In Proceedings of ICML 2025."
    assert title_candidates(apa)[0] == "Scaling laws for retrieval augmented generation"


def test_match_reference_rules() -> None:
    """제목이 그대로 있거나 낱말이 85% 이상 있으면 맞고, 짧은 제목은 맞추지 않으며, 연도가 맞는 후보를 고른다.

    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """
    candidates = [{"id": key, "title": title, "year": year} for key, (title, year, _) in TITLES.items()]
    found, score = match_reference(LSTM, candidates)
    assert (found["id"], score) == ("W1", 1.05)
    assert match_reference(BAHDANAU, candidates)[0]["id"] == "W2"
    assert match_reference("D. Kingma and J. Ba. Adam: a method for stochastic optimization. 2014", candidates) is None
    near = "Hochreiter. Long short-term memories. 1997"
    assert match_reference(near, candidates) is None
    twins = [{"id": "old", "title": "Deep Residual Learning", "year": 2015}, {"id": "new", "title": "Deep Residual Learning", "year": 2016}]
    assert match_reference("He et al. Deep residual learning. CVPR 2016.", twins)[0]["id"] == "new"


def make_client(tmp_path: Path, openalex: FakeOpenAlex) -> tuple[TestClient, object]:
    """가짜 OpenAlex를 쓰는 앱.

    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """
    app = create_app(
        frontend_dist=tmp_path / "missing",
        db_path=tmp_path / "library.db",
        http_client=httpx2.Client(transport=httpx2.MockTransport(openalex)),
    )
    return TestClient(app), app


def test_resolve_from_references_with_pdf_url_and_library_state(tmp_path: Path) -> None:
    """참고문헌에서 찾고 공개 PDF 주소를 주며, 서재에 담은 뒤에는 서재 논문 ID를 준다.

    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """
    openalex = FakeOpenAlex()
    client, app = make_client(tmp_path, openalex)
    paper_id = client.post("/api/papers", json={"title": "Base", "openalex_id": A}).json()["id"]
    app.state.citations.run_once()

    body = client.post(f"/api/papers/{paper_id}/references/resolve", json={"text": LSTM}).json()
    assert (body["state"], body["source"], body["work"]["openalex_id"]) == ("found", "references", "W1")
    assert body["pdf_url"] == "https://example.org/lstm.pdf" and body["work"]["library_paper_id"] is None
    assert openalex.searches == []

    arxiv = client.post(f"/api/papers/{paper_id}/references/resolve", json={"text": BAHDANAU}).json()
    assert arxiv["pdf_url"] == "https://arxiv.org/pdf/1409.0473"

    added = client.post("/api/papers", json={"title": "Long Short-Term Memory", "openalex_id": "W1"}).json()["id"]
    again = client.post(f"/api/papers/{paper_id}/references/resolve", json={"text": LSTM}).json()
    assert again["work"]["library_paper_id"] == added and again["has_pdf"] is False


def test_resolve_falls_back_to_search_and_reports_misses(tmp_path: Path) -> None:
    """참고문헌에 없으면 OpenAlex를 검색하고, 그래도 맞지 않으면 찾지 못함이며, 같은 글은 다시 검색하지 않는다.

    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    """
    openalex = FakeOpenAlex()
    client, _ = make_client(tmp_path, openalex)
    paper_id = client.post("/api/papers", json={"title": "No OpenAlex"}).json()["id"]

    body = client.post(f"/api/papers/{paper_id}/references/resolve", json={"text": GAN}).json()
    assert (body["state"], body["source"], body["work"]["title"]) == ("found", "search", "Generative Adversarial Nets")
    assert openalex.searches == ["generative adversarial nets"]
    client.post(f"/api/papers/{paper_id}/references/resolve", json={"text": GAN})
    assert len(openalex.searches) == 1

    # 낱말이 3개 이상인 조각만 제목 후보다. 이 글에서는 하나뿐이라 한 번만 검색한다.
    miss = client.post(f"/api/papers/{paper_id}/references/resolve", json={"text": "Someone. Unknown title here. 2020."}).json()
    assert miss == {"state": "not_found", "source": None, "work": None, "has_pdf": False, "pdf_url": None}
    assert openalex.searches[1:] == ["unknown title here"]
    assert client.post("/api/papers/99/references/resolve", json={"text": GAN}).status_code == 404
    assert client.post(f"/api/papers/{paper_id}/references/resolve", json={"text": ""}).status_code == 422
