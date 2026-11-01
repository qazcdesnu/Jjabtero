"""구글 드라이브 파일 요청.

@doc: docs/design/DriveSync.md#4-드라이브-파일
"""

import json
import uuid
from collections.abc import Callable
from dataclasses import dataclass

import httpx2

FILES_URL = "https://www.googleapis.com/drive/v3/files"
UPLOAD_URL = "https://www.googleapis.com/upload/drive/v3/files"
FOLDER_MIME = "application/vnd.google-apps.folder"
DB_MIME = "application/x-sqlite3"
_FIELDS = "id,md5Checksum,trashed"


class DriveApiError(Exception):
    """드라이브 API가 오류로 응답했다.

    @doc: docs/design/DriveSync.md#4-드라이브-파일
    """

    def __init__(self, status_code: int, detail: str) -> None:
        super().__init__(f"드라이브 API 오류 {status_code}: {detail}")
        self.status_code = status_code


@dataclass(frozen=True)
class RemoteFile:
    """드라이브 파일 정보.

    @doc: docs/design/DriveSync.md#4-드라이브-파일
    """

    id: str
    checksum: str


def _remote(body: dict) -> RemoteFile:
    return RemoteFile(id=body["id"], checksum=body.get("md5Checksum", ""))


def _quote(value: str) -> str:
    return value.replace("\\", "\\\\").replace("'", "\\'")


class DriveFiles:
    """드라이브 파일 요청. 요청마다 접근 토큰을 얻는 함수를 부른다.

    @doc: docs/design/DriveSync.md#4-드라이브-파일
    """

    def __init__(self, http: httpx2.Client, token: Callable[[], str]) -> None:
        self.http = http
        self.token = token

    def _request(self, method: str, url: str, **kwargs) -> httpx2.Response:
        headers = {"Authorization": f"Bearer {self.token()}", **kwargs.pop("headers", {})}
        response = self.http.request(method, url, headers=headers, **kwargs)
        if response.status_code >= 400:
            raise DriveApiError(response.status_code, response.text[:200])
        return response

    def _find(self, query: str) -> RemoteFile | None:
        response = self._request(
            "GET",
            FILES_URL,
            params={"q": query, "fields": f"files({_FIELDS})", "pageSize": "1", "spaces": "drive"},
        )
        files = response.json().get("files", [])
        return _remote(files[0]) if files else None

    def find_folder(self, name: str) -> RemoteFile | None:
        """내 드라이브 맨 위에서 폴더를 찾는다.

        @doc: docs/design/DriveSync.md#4-드라이브-파일
        """
        return self._find(
            f"name = '{_quote(name)}' and mimeType = '{FOLDER_MIME}' "
            "and 'root' in parents and trashed = false"
        )

    def create_folder(self, name: str) -> RemoteFile:
        """내 드라이브 맨 위에 폴더를 만든다.

        @doc: docs/design/DriveSync.md#4-드라이브-파일
        """
        response = self._request(
            "POST",
            FILES_URL,
            params={"fields": _FIELDS},
            json={"name": name, "mimeType": FOLDER_MIME, "parents": ["root"]},
        )
        return _remote(response.json())

    def find_file(self, folder_id: str, name: str) -> RemoteFile | None:
        """폴더 안에서 파일을 찾는다.

        @doc: docs/design/DriveSync.md#4-드라이브-파일
        """
        return self._find(f"name = '{_quote(name)}' and '{_quote(folder_id)}' in parents and trashed = false")

    def get(self, file_id: str) -> RemoteFile | None:
        """파일 정보를 돌려준다. 없거나 휴지통에 있으면 `None`이다.

        @doc: docs/design/DriveSync.md#4-드라이브-파일
        """
        try:
            body = self._request("GET", f"{FILES_URL}/{file_id}", params={"fields": _FIELDS}).json()
        except DriveApiError as error:
            if error.status_code == 404:
                return None
            raise
        return None if body.get("trashed") else _remote(body)

    def download(self, file_id: str) -> bytes:
        """파일 내용을 받는다.

        @doc: docs/design/DriveSync.md#4-드라이브-파일
        """
        return self._request("GET", f"{FILES_URL}/{file_id}", params={"alt": "media"}).content

    def create(self, folder_id: str, name: str, data: bytes) -> RemoteFile:
        """폴더에 새 파일을 올린다.

        @doc: docs/design/DriveSync.md#4-드라이브-파일
        """
        boundary = uuid.uuid4().hex
        metadata = json.dumps({"name": name, "parents": [folder_id], "mimeType": DB_MIME})
        body = (
            f"--{boundary}\r\nContent-Type: application/json; charset=UTF-8\r\n\r\n{metadata}\r\n"
            f"--{boundary}\r\nContent-Type: {DB_MIME}\r\n\r\n"
        ).encode() + data + f"\r\n--{boundary}--\r\n".encode()
        response = self._request(
            "POST",
            UPLOAD_URL,
            params={"uploadType": "multipart", "fields": _FIELDS},
            headers={"Content-Type": f"multipart/related; boundary={boundary}"},
            content=body,
        )
        return _remote(response.json())

    def update(self, file_id: str, data: bytes) -> RemoteFile:
        """파일 내용을 바꾼다.

        @doc: docs/design/DriveSync.md#4-드라이브-파일
        """
        response = self._request(
            "PATCH",
            f"{UPLOAD_URL}/{file_id}",
            params={"uploadType": "media", "fields": _FIELDS},
            headers={"Content-Type": DB_MIME},
            content=data,
        )
        return _remote(response.json())
