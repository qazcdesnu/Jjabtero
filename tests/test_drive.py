"""드라이브 파일 요청을 검증한다.

@doc: docs/design/DriveSync.md#8-테스트
"""

import httpx2
import pytest

from jjabtero.drive import DriveApiError, DriveFiles, RemoteFile


def files_with(handler, seen: list[httpx2.Request]) -> DriveFiles:
    """요청을 모으고 가짜로 응답하는 `DriveFiles`.

    @doc: docs/design/DriveSync.md#8-테스트
    """

    def recording(request: httpx2.Request) -> httpx2.Response:
        seen.append(request)
        return handler(request)

    return DriveFiles(httpx2.Client(transport=httpx2.MockTransport(recording)), lambda: "tok")


def test_find_folder_queries_root_folder() -> None:
    """맨 위 폴더를 이름과 종류로 찾고 접근 토큰을 붙인다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    seen: list[httpx2.Request] = []
    files = files_with(lambda r: httpx2.Response(200, json={"files": [{"id": "d1", "version": "3"}]}), seen)
    assert files.find_folder("Jjabtero") == RemoteFile("d1", "3")
    query = seen[0].url.params["q"]
    assert "name = 'Jjabtero'" in query and "'root' in parents" in query and "trashed = false" in query
    assert "application/vnd.google-apps.folder" in query
    assert seen[0].headers["Authorization"] == "Bearer tok"


def test_find_file_returns_none_when_empty() -> None:
    """찾는 파일이 없으면 `None`이다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    seen: list[httpx2.Request] = []
    files = files_with(lambda r: httpx2.Response(200, json={"files": []}), seen)
    assert files.find_file("d1", "library.db") is None
    assert "'d1' in parents" in seen[0].url.params["q"]


def test_get_handles_missing_and_trashed() -> None:
    """없거나(404) 휴지통에 있으면 `None`이다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    seen: list[httpx2.Request] = []
    responses = [
        httpx2.Response(200, json={"id": "f1", "version": 5, "trashed": False}),
        httpx2.Response(200, json={"id": "f1", "version": 5, "trashed": True}),
        httpx2.Response(404, json={}),
    ]
    files = files_with(lambda r: responses.pop(0), seen)
    assert files.get("f1") == RemoteFile("f1", "5")
    assert files.get("f1") is None
    assert files.get("f1") is None


def test_create_uploads_multipart_and_update_uploads_media() -> None:
    """새 파일은 multipart로, 내용 바꾸기는 media로 올린다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    seen: list[httpx2.Request] = []
    files = files_with(lambda r: httpx2.Response(200, json={"id": "f1", "version": "7"}), seen)
    assert files.create("d1", "library.db", b"DATA") == RemoteFile("f1", "7")
    assert files.update("f1", b"NEW") == RemoteFile("f1", "7")
    create, update = seen
    assert create.url.params["uploadType"] == "multipart"
    assert create.headers["Content-Type"].startswith("multipart/related; boundary=")
    assert b'"parents": ["d1"]' in create.content and b"DATA" in create.content
    assert update.method == "PATCH" and update.url.path.endswith("/upload/drive/v3/files/f1")
    assert update.url.params["uploadType"] == "media" and update.content == b"NEW"


def test_download_returns_bytes() -> None:
    """`alt=media`로 내용을 받는다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    seen: list[httpx2.Request] = []
    files = files_with(lambda r: httpx2.Response(200, content=b"BYTES"), seen)
    assert files.download("f1") == b"BYTES"
    assert seen[0].url.params["alt"] == "media"


def test_api_error_carries_status() -> None:
    """4xx·5xx 응답은 상태 코드를 담은 `DriveApiError`다.

    @doc: docs/design/DriveSync.md#8-테스트
    """
    files = files_with(lambda r: httpx2.Response(403, text="forbidden"), [])
    with pytest.raises(DriveApiError) as caught:
        files.download("f1")
    assert caught.value.status_code == 403
