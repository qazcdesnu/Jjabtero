"""외부 검색 API를 대신하는 가짜 응답.

@doc: docs/design/PaperSearch.md#5-테스트
"""

from collections.abc import Callable

import httpx2

OPENALEX_BODY = {
    "results": [
        {
            "id": "https://openalex.org/W1",
            "display_name": "Attention Is All You Need",
            "doi": "https://doi.org/10.48550/ARXIV.1706.03762",
            "publication_year": 2017,
            "type": "preprint",
            "authorships": [
                {"author": {"display_name": "Ashish Vaswani"}},
                {"author": {"display_name": "Noam Shazeer"}},
            ],
            "primary_location": {
                "landing_page_url": "https://arxiv.org/abs/1706.03762",
                "source": {"display_name": "arXiv", "type": "repository"},
            },
        },
        {
            "id": "https://openalex.org/W2",
            "display_name": "Speech Separation",
            "doi": None,
            "publication_year": 2021,
            "type": "article",
            "authorships": [],
            "primary_location": {"source": {"display_name": "ICASSP", "type": "conference"}},
        },
        {"id": "https://openalex.org/W3", "display_name": "", "type": "article"},
        {"id": "https://openalex.org/W4", "display_name": "Thesis", "type": "dissertation"},
    ]
}

ARXIV_BODY = """<?xml version="1.0" encoding="UTF-8"?>
<feed xmlns="http://www.w3.org/2005/Atom" xmlns:arxiv="http://arxiv.org/schemas/atom">
  <entry>
    <id>http://arxiv.org/abs/1706.03762v7</id>
    <title>Attention Is All
      You Need</title>
    <published>2017-06-12T17:57:34Z</published>
    <author><name>Ashish   Vaswani</name></author>
    <author><name>Noam Shazeer</name></author>
  </entry>
  <entry>
    <id>http://arxiv.org/abs/2001.00001v1</id>
    <title>Published Later</title>
    <published>2020-01-01T00:00:00Z</published>
    <arxiv:doi>10.1000/JOURNAL.1</arxiv:doi>
  </entry>
</feed>
"""


def make_client(handler: Callable[[httpx2.Request], httpx2.Response]) -> httpx2.Client:
    """고정된 응답을 돌려주는 가짜 전송의 클라이언트.

    @doc: docs/design/PaperSearch.md#5-테스트
    """
    return httpx2.Client(transport=httpx2.MockTransport(handler))


def fixed_responses(request: httpx2.Request) -> httpx2.Response:
    """검색원마다 고정된 응답을 돌려준다.

    @doc: docs/design/PaperSearch.md#5-테스트
    """
    if request.url.host == "api.openalex.org":
        return httpx2.Response(200, json=OPENALEX_BODY)
    return httpx2.Response(200, text=ARXIV_BODY)
