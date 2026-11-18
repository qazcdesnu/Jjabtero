"""AI 대화: 마스터 키, Google AI API 키의 암호화 저장, Gemini 모델 목록, API.

@doc: docs/design/AiChat.md#2-키-암호화
"""

import os
from collections.abc import Iterator
from datetime import datetime
from pathlib import Path
from typing import Annotated, Literal

import httpx2
from cryptography.fernet import Fernet, InvalidToken
from fastapi import APIRouter, Depends, HTTPException, Request, status
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from jjabtero.ai_models import FreeModelsError
from jjabtero.models import Paper, Setting

# @doc: docs/design/AiChat.md#2-키-암호화
SECRET_ENV = "JJABTERO_SECRET_KEY"
# @doc: docs/design/AiChat.md#2-키-암호화
SECRET_FILE = "secret.key"
# @doc: docs/design/AiChat.md#3-데이터
KEY_SETTING = "ai.gemini_key"
# @doc: docs/design/AiChat.md#3-데이터
HINT_SETTING = "ai.gemini_key_hint"
# @doc: docs/design/AiChat.md#3-데이터
MODEL_SETTING = "ai.gemini_model"
# @doc: docs/design/AiChat.md#4-gemini-호출
GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta"
# @doc: docs/design/AiChat.md#4-gemini-호출
DEFAULT_MODEL = "gemini-2.5-flash"

_NO_MASTER = "암호화 키가 없어 API 키를 저장할 수 없습니다. 서버에 JJABTERO_SECRET_KEY를 넣어 주세요."
_NO_KEY = "Google AI API 키가 없습니다. 프로필에서 등록하세요."
_LOCKED = "등록된 API 키를 이곳의 암호화 키로 풀 수 없습니다. 키를 다시 등록하세요."
_REJECTED = "구글이 이 키를 받아들이지 않았습니다. 키를 확인하세요."


def master_key_text(data_dir: Path) -> str | None:
    """마스터 키 글자. 환경 변수가 먼저고, 없으면 서재 폴더의 파일이다. 둘 다 없으면 `None`.

    @doc: docs/design/AiChat.md#2-키-암호화
    """
    value = os.environ.get(SECRET_ENV, "").strip()
    if value:
        return value
    path = data_dir / SECRET_FILE
    if path.exists():
        return path.read_text().strip() or None
    return None


def master_cipher(data_dir: Path, create: bool = False) -> Fernet | None:
    """마스터 키로 만든 암호기. 키가 없고 `create`이면 파일을 새로 만들어 본인만 읽게 둔다.

    @doc: docs/design/AiChat.md#2-키-암호화
    """
    text = master_key_text(data_dir)
    if text is None and create:
        data_dir.mkdir(parents=True, exist_ok=True)
        text = Fernet.generate_key().decode()
        descriptor = os.open(data_dir / SECRET_FILE, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w") as file:
            file.write(text + "\n")
    if text is None:
        return None
    return Fernet(text.encode())


class GeminiError(Exception):
    """Gemini 호출 실패. `rejected`는 구글이 키를 받아들이지 않았다는 뜻이다.

    @doc: docs/design/AiChat.md#4-gemini-호출
    """

    def __init__(self, message: str, rejected: bool = False) -> None:
        super().__init__(message)
        self.rejected = rejected


class ModelOut(BaseModel):
    """고를 수 있는 Gemini 모델 하나.

    @doc: docs/design/AiChat.md#5-api
    """

    name: str
    label: str
    description: str


def _gemini_error(response: httpx2.Response) -> GeminiError:
    try:
        message = response.json()["error"]["message"]
    except (ValueError, KeyError, TypeError):
        message = f"HTTP {response.status_code}"
    return GeminiError(f"Gemini가 요청을 거절했습니다: {message}", rejected=response.status_code in (400, 401, 403))


# 대화(글을 받아 글로 답하기)에 쓰지 않는 모델의 이름 조각. 이름을 `-`로 나눈 조각과 맞춰 본다.
# @doc: docs/design/AiChat.md#4-gemini-호출
NON_CHAT_PARTS = frozenset(
    {"tts", "embedding", "live", "audio", "transcribe", "translate", "image", "robotics", "decision", "aqa"}
)


def is_chat_model(name: str) -> bool:
    """대화에 쓰는 Gemini 언어 모델인지. 음성 합성·임베딩·실시간·음성·이미지·로봇·판정 모델은 뺀다.

    @doc: docs/design/AiChat.md#4-gemini-호출
    """
    parts = name.lower().split("-")
    return parts[0] == "gemini" and not NON_CHAT_PARTS.intersection(parts)


def gemini_models(http: httpx2.Client, api_key: str) -> list[ModelOut]:
    """그 키로 `generateContent`를 쓸 수 있는 Gemini 모델 목록. 키는 머리글로만 보낸다.

    @doc: docs/design/AiChat.md#4-gemini-호출
    """
    try:
        response = http.get(
            f"{GEMINI_URL}/models", params={"pageSize": 1000}, headers={"x-goog-api-key": api_key}, timeout=20
        )
    except httpx2.HTTPError as error:
        raise GeminiError("Gemini에 연결하지 못했습니다.") from error
    if response.status_code != 200:
        raise _gemini_error(response)
    models = []
    for item in response.json().get("models", []):
        name = str(item.get("name", "")).removeprefix("models/")
        if not is_chat_model(name) or "generateContent" not in item.get("supportedGenerationMethods", []):
            continue
        models.append(
            ModelOut(name=name, label=item.get("displayName") or name, description=item.get("description") or "")
        )
    return models


# @doc: docs/design/AiChat.md#4-gemini-호출
SYSTEM_PROMPT = (
    "당신은 논문을 읽는 사람을 돕는다. 논문 제목: {title}\n"
    "사용자가 {page}논문에서 고른 글은 아래와 같다.\n---\n{context}\n---\n"
    "이 글을 바탕으로 답한다. 따로 말하지 않으면 한국어로 답한다."
)


def gemini_chat(http: httpx2.Client, api_key: str, model: str, system: str, messages: list[tuple[str, str]]) -> str:
    """Gemini `generateContent`로 대화를 보내고 답의 글을 돌려준다. `messages`는 (역할, 글)이다.

    @doc: docs/design/AiChat.md#4-gemini-호출
    """
    body = {
        "systemInstruction": {"parts": [{"text": system}]},
        "contents": [{"role": role, "parts": [{"text": text}]} for role, text in messages],
    }
    try:
        response = http.post(
            f"{GEMINI_URL}/models/{model}:generateContent",
            json=body,
            headers={"x-goog-api-key": api_key},
            timeout=120,
        )
    except httpx2.HTTPError as error:
        raise GeminiError("Gemini에 연결하지 못했습니다.") from error
    if response.status_code != 200:
        raise _gemini_error(response)
    data = response.json()
    candidates = data.get("candidates") or []
    first = candidates[0] if candidates else {}
    parts = (first.get("content") or {}).get("parts") or []
    text = "".join(str(part.get("text", "")) for part in parts if not part.get("thought")).strip()
    if not text:
        reason = (data.get("promptFeedback") or {}).get("blockReason") or first.get("finishReason")
        raise GeminiError(f"Gemini가 답하지 않았습니다({reason or '이유 없음'}).")
    return text


def default_model(models: list[ModelOut]) -> str | None:
    """처음 쓸 모델. `DEFAULT_MODEL`이 있으면 그것, 없으면 목록의 첫 모델이다.

    @doc: docs/design/AiChat.md#4-gemini-호출
    """
    names = [model.name for model in models]
    if DEFAULT_MODEL in names:
        return DEFAULT_MODEL
    return names[0] if names else None


def _setting(session: Session, key: str) -> str | None:
    row = session.get(Setting, key)
    return row.value if row else None


def stored_api_key(session: Session, cipher: Fernet | None) -> str:
    """저장된 API 키를 풀어 돌려준다. 없거나 풀 수 없으면 HTTP 오류를 던진다.

    @doc: docs/design/AiChat.md#3-데이터
    """
    token = _setting(session, KEY_SETTING)
    if token is None:
        raise HTTPException(status.HTTP_409_CONFLICT, _NO_KEY)
    if cipher is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _NO_MASTER)
    try:
        return cipher.decrypt(token.encode()).decode()
    except InvalidToken as error:
        raise HTTPException(status.HTTP_409_CONFLICT, _LOCKED) from error


# @doc: docs/design/AiChat.md#5-api
router = APIRouter(prefix="/api/ai")


class KeyStatusOut(BaseModel):
    """API 키 상태. 키 자체는 담지 않는다.

    @doc: docs/design/AiChat.md#5-api
    """

    registered: bool
    hint: str | None
    usable: bool
    master_key: bool
    model: str | None


class KeyIn(BaseModel):
    """등록하거나 바꿀 API 키.

    @doc: docs/design/AiChat.md#5-api
    """

    api_key: str = Field(min_length=1, max_length=200)


class ModelIn(BaseModel):
    """고를 모델 이름.

    @doc: docs/design/AiChat.md#5-api
    """

    model: str = Field(min_length=1, max_length=200)


def _session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


def _data_dir(request: Request) -> Path:
    return request.app.state.data_dir


def key_status(session: Session, data_dir: Path) -> KeyStatusOut:
    """지금 키 상태를 만든다.

    @doc: docs/design/AiChat.md#5-api
    """
    cipher = master_cipher(data_dir)
    token = _setting(session, KEY_SETTING)
    usable = False
    if token is not None and cipher is not None:
        try:
            cipher.decrypt(token.encode())
            usable = True
        except InvalidToken:
            usable = False
    return KeyStatusOut(
        registered=token is not None,
        hint=_setting(session, HINT_SETTING) if token is not None else None,
        usable=usable,
        master_key=cipher is not None,
        model=_setting(session, MODEL_SETTING),
    )


@router.get("/key")
def read_key_status(request: Request, session: Annotated[Session, Depends(_session)]) -> KeyStatusOut:
    """`GET /api/ai/key`를 처리한다.

    @doc: docs/design/AiChat.md#5-api
    """
    return key_status(session, _data_dir(request))


@router.put("/key")
def save_key(data: KeyIn, request: Request, session: Annotated[Session, Depends(_session)]) -> KeyStatusOut:
    """`PUT /api/ai/key`를 처리한다. 구글에 키를 확인한 뒤 암호화해 저장한다.

    @doc: docs/design/AiChat.md#5-api
    """
    api_key = data.api_key.strip()
    if not api_key:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "API 키를 적어 주세요.")
    cipher = master_cipher(_data_dir(request), create=not request.app.state.auth.enabled)
    if cipher is None:
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, _NO_MASTER)
    try:
        models = gemini_models(request.app.state.http_client, api_key)
    except GeminiError as error:
        if error.rejected:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, _REJECTED) from error
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    session.merge(Setting(key=KEY_SETTING, value=cipher.encrypt(api_key.encode()).decode()))
    session.merge(Setting(key=HINT_SETTING, value=api_key[-4:]))
    if _setting(session, MODEL_SETTING) is None:
        try:
            chosen = default_model(_only_free(request, models).models)
        except HTTPException:
            # 무료 목록을 못 읽어도 키는 저장한다. 모델은 프로필에서 나중에 고른다.
            chosen = None
        if chosen:
            session.merge(Setting(key=MODEL_SETTING, value=chosen))
    session.commit()
    request.app.state.drive.schedule_push()
    return key_status(session, _data_dir(request))


@router.delete("/key")
def delete_key(request: Request, session: Annotated[Session, Depends(_session)]) -> KeyStatusOut:
    """`DELETE /api/ai/key`를 처리한다. 고른 모델은 남긴다.

    @doc: docs/design/AiChat.md#5-api
    """
    for key in (KEY_SETTING, HINT_SETTING):
        row = session.get(Setting, key)
        if row is not None:
            session.delete(row)
    session.commit()
    request.app.state.drive.schedule_push()
    return key_status(session, _data_dir(request))


class ModelsOut(BaseModel):
    """고를 수 있는 모델(그 키로 쓸 수 있고 오늘 무료 등급인 것)과 무료 목록을 읽은 시각.

    `stale`이면 오늘 가격표를 읽지 못해 지난 목록을 쓰는 중이다.

    @doc: docs/design/AiChat.md#5-api
    """

    models: list[ModelOut]
    checked_at: datetime
    stale: bool


def _only_free(request: Request, models: list[ModelOut]) -> ModelsOut:
    try:
        free = request.app.state.free_models.current()
    except FreeModelsError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    return ModelsOut(
        models=[model for model in models if model.name in free.names],
        checked_at=free.checked_at,
        stale=free.stale,
    )


def _models(request: Request, session: Session) -> ModelsOut:
    api_key = stored_api_key(session, master_cipher(_data_dir(request)))
    try:
        models = gemini_models(request.app.state.http_client, api_key)
    except GeminiError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    return _only_free(request, models)


@router.get("/models")
def list_models(request: Request, session: Annotated[Session, Depends(_session)]) -> ModelsOut:
    """`GET /api/ai/models`를 처리한다.

    @doc: docs/design/AiChat.md#5-api
    """
    return _models(request, session)


@router.put("/model")
def choose_model(data: ModelIn, request: Request, session: Annotated[Session, Depends(_session)]) -> KeyStatusOut:
    """`PUT /api/ai/model`을 처리한다. 고를 수 있는 목록(오늘 무료 등급)에 있는 모델만 받는다.

    @doc: docs/design/AiChat.md#5-api
    """
    if data.model not in {model.name for model in _models(request, session).models}:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "고를 수 없는 모델입니다. 오늘 무료 등급인 모델만 고를 수 있습니다.")
    session.merge(Setting(key=MODEL_SETTING, value=data.model))
    session.commit()
    request.app.state.drive.schedule_push()
    return key_status(session, _data_dir(request))


class ChatMessage(BaseModel):
    """대화의 말 하나. `user`는 사용자, `model`은 Gemini다.

    @doc: docs/design/AiChat.md#5-api
    """

    role: Literal["user", "model"]
    text: str = Field(min_length=1, max_length=20000)


class ChatIn(BaseModel):
    """대화 요청: 논문, 고른 글과 쪽, 지금까지 주고받은 말(마지막은 사용자).

    @doc: docs/design/AiChat.md#5-api
    """

    paper_id: int
    page: int | None = None
    context: str = Field(min_length=1, max_length=20000)
    messages: list[ChatMessage] = Field(min_length=1, max_length=60)


class ChatOut(BaseModel):
    """Gemini의 답과 쓴 모델.

    @doc: docs/design/AiChat.md#5-api
    """

    text: str
    model: str


@router.post("/chat")
def chat(data: ChatIn, request: Request, session: Annotated[Session, Depends(_session)]) -> ChatOut:
    """`POST /api/ai/chat`을 처리한다. 고른 글을 시스템 지시에 넣어 Gemini에 묻는다.

    @doc: docs/design/AiChat.md#5-api
    """
    paper = session.get(Paper, data.paper_id)
    if paper is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "논문을 찾지 못했습니다.")
    if data.messages[-1].role != "user":
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, "마지막 말은 사용자의 것이어야 합니다.")
    api_key = stored_api_key(session, master_cipher(_data_dir(request)))
    model = _setting(session, MODEL_SETTING)
    if not model:
        raise HTTPException(status.HTTP_409_CONFLICT, "프로필에서 Gemini 모델을 고르세요.")
    page = f"{data.page}쪽에서 " if data.page else ""
    system = SYSTEM_PROMPT.format(title=paper.title, page=page, context=data.context)
    try:
        text = gemini_chat(
            request.app.state.http_client, api_key, model, system, [(m.role, m.text) for m in data.messages]
        )
    except GeminiError as error:
        raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(error)) from error
    return ChatOut(text=text, model=model)
