"""AI 대화의 마스터 키, API 키 암호화 저장, 모델 고르기를 검증한다.

@doc: docs/design/AiChat.md#7-테스트
"""

import json
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
from test_pdfs import add_paper, make_app

API_KEY = "AIzaTEST-secret-value-1234"
MODELS = {
    "models": [
        {"name": "models/gemini-2.5-pro", "displayName": "Gemini 2.5 Pro", "supportedGenerationMethods": ["generateContent"]},
        {"name": "models/gemini-2.5-flash", "displayName": "Gemini 2.5 Flash", "description": "빠름", "supportedGenerationMethods": ["generateContent", "countTokens"]},
        {"name": "models/text-embedding-004", "supportedGenerationMethods": ["embedContent"]},
        {"name": "models/gemini-embedding-001", "supportedGenerationMethods": ["embedContent"]},
    ]
}


PRICING = """
## Gemini 2.5 Pro {% id=&quot;gemini-2.5-pro&quot; %}
*[`gemini-2.5-pro`](/docs/models/gemini-2.5-pro)*
{% hr /%}
{% tabs %}
  {% tab title=&quot;Standard&quot; %}
  {% table %}
  * Feature
  * Free Tier
  * Paid Tier
  ---
  * Input price
  * Not available
  * $1.25
  {% /table %}
  {% /tab %}
{% /tabs %}

## Gemini 2.5 Flash {% id=&quot;gemini-2.5-flash&quot; %}
*[`gemini-2.5-flash`](/docs/models/gemini-2.5-flash)*
{% hr /%}
{% tabs %}
  {% tab title=&quot;Standard&quot; %}
  {% table %}
  * Feature
  * Free Tier
  * Paid Tier
  ---
  * Input price (text, image, video)
  * Free of charge
  * $0.30
  {% /table %}
  {% /tab %}
{% /tabs %}
"""


class GeminiWeb:
    """Gemini 모델 목록에 답하는 가짜 웹. 받은 요청을 모은다.

    @doc: docs/design/AiChat.md#7-테스트
    """

    def __init__(self, status: int = 200) -> None:
        self.status = status
        self.requests: list[httpx2.Request] = []

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        self.requests.append(request)
        if request.url.host == "ai.google.dev":
            return httpx2.Response(200, text=PRICING)
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
    request = next(r for r in web.requests if r.url.host == "generativelanguage.googleapis.com")
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
    listed = client.get("/api/ai/models").json()
    # 키로 쓸 수 있는 모델 가운데 가격표에서 무료 등급인 것만 나온다.
    assert [model["name"] for model in listed["models"]] == ["gemini-2.5-flash"]
    assert listed["stale"] is False
    assert client.put("/api/ai/model", json={"model": "gemini-2.5-pro"}).status_code == 422
    assert client.put("/api/ai/model", json={"model": "gemini-2.5-flash"}).json()["model"] == "gemini-2.5-flash"
    changed = client.put("/api/ai/key", json={"api_key": "AIzaOTHER-9876"}).json()
    assert changed["hint"] == "9876"
    assert changed["model"] == "gemini-2.5-flash"
    deleted = client.delete("/api/ai/key").json()
    assert deleted["registered"] is False
    assert deleted["model"] == "gemini-2.5-flash"
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


class ChatWeb(GeminiWeb):
    """모델 목록과 대화에 답하는 가짜 Gemini. 대화 응답은 `reply`로 정한다.

    @doc: docs/design/AiChat.md#7-테스트
    """

    def __init__(self, reply: dict | None = None, chat_status: int = 200) -> None:
        super().__init__()
        self.reply = reply if reply is not None else {
            "candidates": [{"content": {"parts": [{"text": "생각", "thought": True}, {"text": "요약입니다."}]}}]
        }
        self.chat_status = chat_status

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        if request.url.path.endswith(":generateContent"):
            self.requests.append(request)
            if self.chat_status != 200:
                return httpx2.Response(self.chat_status, json={"error": {"message": "quota"}})
            return httpx2.Response(200, json=self.reply)
        return super().__call__(request)


def _chat_client(tmp_path: Path, web: GeminiWeb) -> tuple[TestClient, int]:
    client, _ = _client(tmp_path, web)
    paper_id = add_paper(client)
    client.put("/api/ai/key", json={"api_key": API_KEY})
    return client, paper_id


CHAT = {
    "page": 3,
    "context": "We propose a self-improving agent.",
    "messages": [
        {"role": "user", "text": "번역해 줘"},
        {"role": "model", "text": "자기 개선 에이전트를 제안한다."},
        {"role": "user", "text": "요약해 줘"},
    ],
}


def test_chat_sends_context_and_history(tmp_path: Path) -> None:
    """고른 글과 쪽, 논문 제목은 시스템 지시로, 주고받은 말은 차례로 보내고 생각 부분은 뺀 답을 돌려준다.

    @doc: docs/design/AiChat.md#7-테스트
    """
    web = ChatWeb()
    client, paper_id = _chat_client(tmp_path, web)
    response = client.post("/api/ai/chat", json={"paper_id": paper_id, **CHAT})
    assert response.status_code == 200
    assert response.json() == {"text": "요약입니다.", "model": "gemini-2.5-flash"}
    request = web.requests[-1]
    assert request.url.path == "/v1beta/models/gemini-2.5-flash:generateContent"
    assert request.headers["x-goog-api-key"] == API_KEY
    body = json.loads(request.content)
    system = body["systemInstruction"]["parts"][0]["text"]
    assert "We propose a self-improving agent." in system
    assert "3쪽에서" in system
    assert [(c["role"], c["parts"][0]["text"]) for c in body["contents"]] == [
        ("user", "번역해 줘"), ("model", "자기 개선 에이전트를 제안한다."), ("user", "요약해 줘"),
    ]


def test_chat_errors(tmp_path: Path) -> None:
    """없는 논문은 404, 마지막 말이 사용자 것이 아니면 422, Gemini 실패와 빈 답은 502, 키가 없으면 409다.

    @doc: docs/design/AiChat.md#7-테스트
    """
    client, paper_id = _chat_client(tmp_path, ChatWeb(chat_status=429))
    assert client.post("/api/ai/chat", json={"paper_id": 9999, **CHAT}).status_code == 404
    last_model = {**CHAT, "messages": CHAT["messages"][:2]}
    assert client.post("/api/ai/chat", json={"paper_id": paper_id, **last_model}).status_code == 422
    failed = client.post("/api/ai/chat", json={"paper_id": paper_id, **CHAT})
    assert failed.status_code == 502
    assert "quota" in failed.json()["detail"]

    blocked, paper_id = _chat_client(tmp_path / "b", ChatWeb(reply={"promptFeedback": {"blockReason": "SAFETY"}}))
    response = blocked.post("/api/ai/chat", json={"paper_id": paper_id, **CHAT})
    assert response.status_code == 502
    assert "SAFETY" in response.json()["detail"]
    blocked.delete("/api/ai/key")
    assert blocked.post("/api/ai/chat", json={"paper_id": paper_id, **CHAT}).status_code == 409
