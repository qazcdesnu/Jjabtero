"""AI 대화의 마스터 키, API 키 암호화 저장, 모델 고르기를 검증한다.

@doc: docs/design/AiChat.md#7-테스트
"""

import os
from pathlib import Path

import httpx2
import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from jjabtero import cli
from jjabtero.ai import (
    HINT_SETTING,
    KEY_SETTING,
    MODEL_SETTING,
    SECRET_FILE,
    ModelOut,
    default_model,
    master_cipher,
)
from jjabtero.models import Setting
from test_pdfs import make_app

API_KEY = "AIzaTEST-secret-value-1234"
MODELS = {
    "models": [
        {"name": "models/gemini-2.5-pro", "displayName": "Gemini 2.5 Pro", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-2.5-flash", "displayName": "Gemini 2.5 Flash", "description": "빠름", "supportedGenerationMethods": ["generateContent", "countTokens"]},
        {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
        {"name": "models/gemini-embedding-001", "supportedGenerationMethods": ["embedContent"]},
    ]
}


class GeminiWeb:
    """Gemini 모델 목록에 답하는 가짜 웹. 받은 요청을 모은다.

    @doc: docs/design/AiChat.md#7-테스트
    """

    def __init__(self, status: int = 200) -> None:
        self.status = status
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        if request.url.host != "generativelanguage.googleapis.com":
            return httpx2.Response(404)
        if self.status != 200:
            return httpx2.Response(self.status, json={"error": {"message": "API key not valid."}})
        return httpx2.Response(200, json=MODELS)


def _client(tmp_path: Path, web: GeminiWeb) -> tuple[TestClient, Path]:
    app, _ = make_app(tmp_path, web)  # type: ignore[arg-type]
    return TestClient(app), tmp_path / "data"


def _rows(tmp_path: Path, client: TestClient) -> dict[str, str]:
    with Session(client.app.state.engine) as session:  # type: ignore[attr-defined]
        return {row.key: row.value for row in session.query(Setting)}


def test_master_key_prefers_env_then_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """환경 변수가 먼저고, 없으면 파일을 읽는다. 둘 다 없으면 만들라고 할 때만 만든다.

    @doc: docs/design/AiChat.md#7-테스트
    """
    assert master_cipher(tmp_path) is None
    assert not (tmp_path / SECRET_FILE).exists()
    created = master_cipher(tmp_path, create=True)
    assert created is not None
    path = tmp_path / SECRET_FILE
    assert oct(os.stat(path).st_mode & 0o777) == "0o600"
    token = created.encrypt(b"x")
    assert master_cipher(tmp_path).decrypt(token) == b"x"  # type: ignore[union-attr]
    other = Fernet.generate_key().decode()
    monkeypatch.setenv("JJABTERO_SECRET_KEY", other)
    assert Fernet(other.encode()).decrypt(master_cipher(tmp_path).encrypt(b"y")) == b"y"  # type: ignore[union-attr]


def test_default_model_prefers_flash() -> None:
    """`gemini-2.5-flash`가 있으면 그것을, 없으면 첫 모델을 고른다.

    @doc: docs/design/AiChat.md#7-테스트
    """
    flash = ModelOut(name="gemini-2.5-flash", label="", description="")
    pro = ModelOut(name="gemini-2.5-pro", label="", description="")
    assert default_model([pro, flash]) == "gemini-2.5-flash"
    assert default_model([pro]) == "gemini-2.5-pro"
    assert default_model([]) is None


def test_register_encrypts_key_and_never_returns_it(tmp_path: Path) -> None:
    """등록하면 구글에 머리글로 확인하고, 암호화한 값과 끝 네 글자만 저장하며 응답에 키가 없다.

    @doc: docs/design/AiChat.md#7-테스트
    """
    web = GeminiWeb()
    client, data_dir = _client(tmp_path, web)
    assert client.get("/api/ai/key").json() == {
        "registered": False, "hint": None, "usable": False, "master_key": False, "model": None,
    }
    response = client.put("/api/ai/key", json={"api_key": f"  {API_KEY} "})
    assert response.status_code == 200
    assert response.json() == {
        "registered": True, "hint": "1234", "usable": True, "master_key": True, "model": "gemini-2.5-flash",
    }
    assert API_KEY not in response.text
    request = web.requests[-1]
    assert request.headers["x-goog-api-key"] == API_KEY
    assert API_KEY not in str(request.url)
    rows = _rows(tmp_path, client)
    assert API_KEY not in rows[KEY_SETTING]
    assert master_cipher(data_dir).decrypt(rows[KEY_SETTING].encode()).decode() == API_KEY  # type: ignore[union-attr]
    assert rows[HINT_SETTING] == "1234"
    assert (data_dir / SECRET_FILE).exists()


def test_register_rejected_key_saves_nothing(tmp_path: Path) -> None:
    """구글이 키를 거절하면 400이고 아무것도 저장하지 않는다.

    @doc: docs/design/AiChat.md#7-테스트
    """
    client, _ = _client(tmp_path, GeminiWeb(status=400))
    response = client.put("/api/ai/key", json={"api_key": API_KEY})
    assert response.status_code == 400
    assert "받아들이지 않았습니다" in response.json()["detail"]
    assert KEY_SETTING not in _rows(tmp_path, client)


def test_change_delete_and_model(tmp_path: Path) -> None:
    """키를 바꿔도 고른 모델은 남고, 목록 밖 모델은 거절하며, 지우면 키만 사라진다.

    @doc: docs/design/AiChat.md#7-테스트
    """
    client, _ = _client(tmp_path, GeminiWeb())
    client.put("/api/ai/key", json={"api_key": API_KEY})
    models = client.get("/api/ai/models").json()
    assert [model["name"] for model in models] == ["gemini-2.5-pro", "gemini-2.5-flash"]
    assert client.put("/api/ai/model", json={"model": "gemini-2.5-pro"}).json()["model"] == "gemini-2.5-pro"
    assert client.put("/api/ai/model", json={"model": "text-embedding-004"}).status_code == 422
    changed = client.put("/api/ai/key", json={"api_key": "AIzaOTHER-9876"}).json()
    assert changed["hint"] == "9876"
    assert changed["model"] == "gemini-2.5-pro"
    deleted = client.delete("/api/ai/key").json()
    assert deleted["registered"] is False
    assert deleted["model"] == "gemini-2.5-pro"
    assert client.get("/api/ai/models").status_code == 409


def test_key_from_other_master_key_is_locked(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """다른 마스터 키로 암호화한 키는 등록됨이지만 쓸 수 없다고 보인다.

    @doc: docs/design/AiChat.md#7-테스트
    """
    client, _ = _client(tmp_path, GeminiWeb())
    client.put("/api/ai/key", json={"api_key": API_KEY})
    monkeypatch.setenv("JJABTERO_SECRET_KEY", Fernet.generate_key().decode())
    status_now = client.get("/api/ai/key").json()
    assert status_now["registered"] is True
    assert status_now["usable"] is False
    response = client.get("/api/ai/models")
    assert response.status_code == 409
    assert "풀 수 없습니다" in response.json()["detail"]


def test_server_without_master_key_refuses(tmp_path: Path) -> None:
    """로그인이 켜진 서버에서는 마스터 키 파일을 만들지 않고 503으로 거절한다.

    @doc: docs/design/AiChat.md#7-테스트
    """
    client, data_dir = _client(tmp_path, GeminiWeb())
    client.app.state.auth = type("Auth", (), {"enabled": True})()  # type: ignore[attr-defined]
    response = client.put("/api/ai/key", json={"api_key": API_KEY})
    assert response.status_code == 503
    assert not (data_dir / SECRET_FILE).exists()


def test_print_secret_key(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """`--print-secret-key`는 마스터 키를 출력하고, 없으면 오류로 끝난다.

    @doc: docs/design/AiChat.md#7-테스트
    """
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli.uvicorn, "run", lambda app, **kwargs: pytest.fail("서버를 띄우면 안 됩니다"))
    with pytest.raises(SystemExit):
        cli.main(["--print-secret-key"])
    data_dir = Path(os.environ["JJABTERO_DB"]).parent
    master_cipher(data_dir, create=True)
    cli.main(["--print-secret-key"])
    assert capsys.readouterr().out.strip() == (data_dir / SECRET_FILE).read_text().strip()
