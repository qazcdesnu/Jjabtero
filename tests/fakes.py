"""외부 API(검색, 구글 드라이브)를 대신하는 가짜.

@doc: docs/design/PaperSearch.md#5-테스트
@doc: docs/design/DriveSync.md#9-테스트
"""

import json
from collections.abc import Callable
from pathlib import Path

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


class FakeDrive:
    """메모리 안의 가짜 드라이브. `FilesLike`와 같은 모양이다.

    @doc: docs/design/DriveSync.md#9-테스트
    """

    def __init__(self) -> None:
        self.files: dict[str, dict] = {}
        self.calls: list[str] = []
        self._next = 0

    def _new_id(self) -> str:
        self._next += 1
        return f"f{self._next}"

    def _remote(self, file_id: str):
        from jjabtero.drive import RemoteFile

        import hashlib

        item = self.files[file_id]
        checksum = "" if item["folder"] else hashlib.md5(item["data"]).hexdigest()
        return RemoteFile(id=file_id, checksum=checksum)

    def find_folder(self, name: str):
        """이름이 같은 폴더를 찾는다.

        @doc: docs/design/DriveSync.md#9-테스트
        """
        for file_id, item in self.files.items():
            if item["folder"] and item["name"] == name and not item["trashed"]:
                return self._remote(file_id)
        return None

    def create_folder(self, name: str):
        """폴더를 만든다.

        @doc: docs/design/DriveSync.md#9-테스트
        """
        self.calls.append("create_folder")
        file_id = self._new_id()
        self.files[file_id] = {"name": name, "folder": True, "parent": None, "data": b"", "trashed": False}
        return self._remote(file_id)

    def find_file(self, folder_id: str, name: str):
        """폴더 안에서 파일을 찾는다.

        @doc: docs/design/DriveSync.md#9-테스트
        """
        for file_id, item in self.files.items():
            if not item["folder"] and item["parent"] == folder_id and item["name"] == name and not item["trashed"]:
                return self._remote(file_id)
        return None

    def get(self, file_id: str):
        """파일 정보를 돌려준다.

        @doc: docs/design/DriveSync.md#9-테스트
        """
        item = self.files.get(file_id)
        return None if item is None or item["trashed"] else self._remote(file_id)

    def download(self, file_id: str) -> bytes:
        """내용을 돌려준다.

        @doc: docs/design/DriveSync.md#9-테스트
        """
        self.calls.append("download")
        return self.files[file_id]["data"]

    def create(self, folder_id: str, name: str, data: bytes):
        """새 파일을 만든다.

        @doc: docs/design/DriveSync.md#9-테스트
        """
        self.calls.append("create")
        file_id = self._new_id()
        self.files[file_id] = {"name": name, "folder": False, "parent": folder_id, "data": data, "trashed": False}
        return self._remote(file_id)

    def update(self, file_id: str, data: bytes):
        """내용을 바꾼다.

        @doc: docs/design/DriveSync.md#9-테스트
        """
        self.calls.append("update")
        self.files[file_id]["data"] = data
        return self._remote(file_id)


def write_client_secret(path: Path) -> None:
    """가짜 웹 애플리케이션 클라이언트 JSON을 쓴다.

    @doc: docs/design/DriveSync.md#9-테스트
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(
            {
                "web": {
                    "client_id": "client-1",
                    "client_secret": "secret-1",
                    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                    "token_uri": "https://oauth2.googleapis.com/token",
                    "redirect_uris": ["http://127.0.0.1:8000/api/drive/callback"],
                }
            }
        )
    )
