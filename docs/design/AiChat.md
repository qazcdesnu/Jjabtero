# AI 대화 설계

이 문서는 리더에서 고른 글이나 하이라이트를 바탕으로 Gemini와 대화하는 기능과, 그 기능에 쓰는 Google AI API 키와 모델을 관리하는 프로필 창을 정한다. 사용자가 요청했다([로드맵의 M8](../Roadmap.md#m8-ai-대화)). 하이라이트와 리더 화면은 [PDF 리더 설계](Reader.md)에, 로그인은 [로그인 설계](Auth.md)에 있다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 정한 것

- 대화 상대는 Google의 Gemini다. 사용자가 정했다. 사용자가 프로필에 등록한 Google AI API 키(Google AI Studio에서 만드는 키)로 부른다.
- 머리줄의 계정 표시를 누르면 프로필 창이 열린다. 프로필 창에서 API 키를 등록·변경·삭제하고, 키가 있으면 쓸 Gemini 모델을 고른다. 사용자가 정했다.
- API 키는 암호화해서 저장한다. 사용자가 정했다. 화면과 API 응답에는 키를 다시 보내지 않고, 끝 네 글자만 보인다.
- 리더에서 글을 고르면 뜨는 하이라이트 색 옆과, 이미 있는 하이라이트를 눌렀을 때 뜨는 상자에 "AI 대화" 버튼을 둔다. 누르면 그 글을 바탕으로 질문, 번역, 요약 등을 Gemini와 주고받는다. 사용자가 정했다.
- 브라우저는 Gemini를 직접 부르지 않는다. 서버가 키를 풀어 부르고 답만 돌려준다. 풀린 키가 브라우저로 나가지 않게 하기 위해서다.

## 2. 키 암호화

- 키는 [Fernet](https://cryptography.io/en/latest/fernet/)(AES-128-CBC와 HMAC-SHA256)으로 암호화한다. Python `cryptography` 패키지를 의존성으로 더한다. 검증된 구현을 쓰고 암호를 직접 만들지 않기 위해서다.
- 암호화 키(마스터 키)는 서재 파일 밖에 둔다. 서재 파일은 드라이브로 동기화되므로, 같은 곳에 두면 암호화하는 뜻이 없기 때문이다.
  - 환경 변수 `JJABTERO_SECRET_KEY`가 있으면 그 값을 쓴다. 서버(Render)는 이것을 쓴다.
  - 없으면 서재 파일과 같은 폴더의 `secret.key`를 쓴다. 파일이 없고 로그인이 꺼져 있으면(내 컴퓨터) 새로 만들어 본인만 읽게(권한 600) 저장한다. 로그인이 켜진 서버에서는 만들지 않는다. Render는 재시작하면 파일이 지워져, 만든 키로 암호화한 API 키를 다시 풀 수 없게 되기 때문이다.
  - [master_key_text](../../src/jjabtero/ai.py#master_key_text)가 마스터 키 글자를 찾고([SECRET_ENV](../../src/jjabtero/ai.py#SECRET_ENV), [SECRET_FILE](../../src/jjabtero/ai.py#SECRET_FILE)), [master_cipher](../../src/jjabtero/ai.py#master_cipher)가 암호기를 만든다. 서재 폴더는 앱이 `app.state.data_dir`로 가진다.
  - 마스터 키가 없으면 AI 기능은 "암호화 키가 없어 API 키를 저장할 수 없습니다"로 막는다.
- 로컬과 서버가 같은 API 키를 쓰려면 두 곳의 마스터 키가 같아야 한다. 사용자가 로컬에서 `jjabtero --print-secret-key`([main](../../src/jjabtero/cli.py#main))로 값을 꺼내 Render 환경 변수 `JJABTERO_SECRET_KEY`에 넣는다([이슈 I33](../Issue.md)). 값은 사용자만 꺼내고 넣는다. 드라이브 갱신 토큰과 같은 방식이다([배포 설계](Deployment.md#3-데이터와-비밀-값)).
- 마스터 키가 달라 풀 수 없으면 키는 "등록됨, 이곳에서 풀 수 없음"으로 보이고, 다시 등록하거나 삭제할 수 있다.

## 3. 데이터

- 암호화한 키와 고른 모델은 [사용자 설정](Settings.md#2-저장)과 같은 `settings` 표에 둔다. 서재와 함께 드라이브로 동기화되어, 로컬과 서버가 같은 값을 보게 하기 위해서다. 사용자가 숫자 칸으로 바꾸는 설정 항목(`SETTINGS`)은 아니므로 설정 화면에는 나오지 않는다. 표 모양이 그대로라 마이그레이션은 없다.

| 키 | 값 |
| --- | --- |
| `ai.gemini_key` ([KEY_SETTING](../../src/jjabtero/ai.py#KEY_SETTING)) | 암호화한 API 키(Fernet 토큰) |
| `ai.gemini_key_hint` ([HINT_SETTING](../../src/jjabtero/ai.py#HINT_SETTING)) | API 키의 끝 네 글자. 어떤 키를 등록했는지 알아보는 데 쓴다. |
| `ai.gemini_model` ([MODEL_SETTING](../../src/jjabtero/ai.py#MODEL_SETTING)) | 고른 모델 이름(예: `gemini-2.5-flash`) |

- 저장된 키는 [stored_api_key](../../src/jjabtero/ai.py#stored_api_key)가 풀어 준다. 없거나 풀 수 없으면 409, 마스터 키가 없으면 503이다.
- 키를 지우면 `ai.gemini_key`와 `ai.gemini_key_hint`를 지운다. 모델은 남긴다. 키를 바꿔도 같은 모델을 계속 쓰게 하기 위해서다.
- 대화 내용은 저장하지 않는다. 리더를 닫거나 다른 글로 대화를 시작하면 사라진다. 저장할지는 8절에 남긴다.

## 4. Gemini 호출

- 주소는 Gemini API([GEMINI_URL](../../src/jjabtero/ai.py#GEMINI_URL))다. 키는 주소에 넣지 않고 `x-goog-api-key` 머리글로 보낸다. 오류 메시지나 기록에 주소가 남아도 키가 드러나지 않게 하기 위해서다.
- 모델 목록은 [gemini_models](../../src/jjabtero/ai.py#gemini_models)가 `GET /models`로 받아 [ModelOut](../../src/jjabtero/ai.py#ModelOut)으로 돌려주고, `generateContent`를 지원하는 `gemini` 모델만 보인다.
- 대화에 쓰는 언어 모델만 보인다([is_chat_model](../../src/jjabtero/ai.py#is_chat_model)). 사용자가 대화가 안 되는 모델은 빼라고 했다([이슈 I35](../Issue.md)). 음성 합성(`tts`), 임베딩(`embedding`), 실시간(`live`), 음성(`audio`, `transcribe`, `translate`), 이미지(`image`), 로봇(`robotics`), 판정(`decision`) 모델은 `generateContent`를 지원해도 뺀다. 모델 이름을 `-`로 나눈 조각이 [NON_CHAT_PARTS](../../src/jjabtero/ai.py#NON_CHAT_PARTS)의 낱말과 같으면 뺀다. 조각으로 맞춰 보는 것은 이름 중간에 우연히 같은 글자가 든 모델을 빼지 않기 위해서다.
- 고를 수 있는 모델은 그 키로 쓸 수 있는 모델 가운데 오늘 무료 등급인 것만이다. 사용자가 무료 한도가 있는 모델만 매일 자정에 갱신해 보이라고 요청했다([이슈 I34](../Issue.md)).
  - 사용자는 Google AI Pro 구독의 무료 한도를 뜻했으나, 구글 문서에 따르면 Pro 구독 혜택은 AI Studio 웹 화면 안에서만 쓰이고 API 키 사용은 따로 셈한다([Google AI plans](https://aistudio.google.com/docs/google-ai-plans)). API 키로 무료로 쓸 수 있는 것은 Gemini API 무료 등급이므로 그것으로 거른다.
  - 무료 등급 모델은 구글 가격표([PRICING_URL](../../src/jjabtero/ai_models.py#PRICING_URL))를 읽어 정한다. 무료 등급 목록을 주는 API가 없기 때문이다. [parse_free_models](../../src/jjabtero/ai_models.py#parse_free_models)가 모델 절(`## `)마다 모델 ID와, 표준(Standard) 요금 탭의 입력 가격 행의 무료 등급 칸이 "Free of charge"인지 본다.
  - 같은 표에서 유료 등급의 100만 토큰당 입력·출력 가격([ModelPrice](../../src/jjabtero/ai_models.py#ModelPrice))도 읽어 모델마다 붙인다([parse_free_prices](../../src/jjabtero/ai_models.py#parse_free_prices)). 사용자가 가격을 보고 모델을 고르게 해 달라고 했다([이슈 I36](../Issue.md)). 가격 칸이 여러 줄(입력 종류별, 기간별, 프롬프트 길이별)이면 `; `로 잇고 가격표의 글을 그대로 둔다. 무료 등급은 한도 안에서 무료이고, 이 가격은 결제를 켠 키에 청구되는 값이다. 가격이 없는 예전 캐시 파일은 버리고 다시 읽는다.
  - [FreeModelCatalog](../../src/jjabtero/ai_models.py#FreeModelCatalog)가 목록([FreeModels](../../src/jjabtero/ai_models.py#FreeModels): 모델 ID, 읽은 시각, 지난 목록인지)을 가진다. 스레드가 매일 한국 자정([SEOUL](../../src/jjabtero/ai_models.py#SEOUL), 남은 시간은 [seconds_until_midnight](../../src/jjabtero/ai_models.py#FreeModelCatalog.seconds_until_midnight))에 [refresh](../../src/jjabtero/ai_models.py#FreeModelCatalog.refresh)로 다시 읽는다. 앱([create_app](../../src/jjabtero/app.py#create_app))을 실행 명령으로 띄울 때만(`run_model_refresh`) 스레드를 띄운다([start](../../src/jjabtero/ai_models.py#FreeModelCatalog.start), [stop](../../src/jjabtero/ai_models.py#FreeModelCatalog.stop)).
  - 서버가 자정에 잠들어 있었을 수 있으므로(Render 무료 플랜의 유휴 정지), 목록을 쓸 때([current](../../src/jjabtero/ai_models.py#FreeModelCatalog.current)) 오늘 읽은 것이 아니면 먼저 다시 읽는다.
  - 읽은 목록은 서재 폴더의 [FREE_MODELS_FILE](../../src/jjabtero/ai_models.py#FREE_MODELS_FILE)에 둬, 다시 띄워도 같은 날에는 다시 읽지 않는다.
  - 가격표를 읽지 못하거나 무료 모델을 하나도 찾지 못하면(페이지 모양이 바뀜) 지난 목록을 "지난 목록"으로 쓴다. 지난 목록도 없으면 [FreeModelsError](../../src/jjabtero/ai_models.py#FreeModelsError)로 502다.
- 대화는 [gemini_chat](../../src/jjabtero/ai.py#gemini_chat)이 `POST /models/<모델>:generateContent`로 보낸다. 답의 글 조각을 이어 붙이되, 생각 과정(`thought`) 조각은 뺀다. 답이 비면(막힘 등) 이유를 담아 실패로 본다. 시스템 지시에 논문 제목, 고른 글, 그 글이 있는 쪽을 넣고, 지금까지 주고받은 말을 차례로 넣는다. 시스템 지시([SYSTEM_PROMPT](../../src/jjabtero/ai.py#SYSTEM_PROMPT))는 "고른 글을 바탕으로 답하고, 따로 말하지 않으면 한국어로 답한다"이다.
- 키를 등록할 때 모델 목록을 한 번 받아 키가 맞는지 확인한다. 구글이 거절하면(400, 401, 403, [GeminiError](../../src/jjabtero/ai.py#GeminiError)의 `rejected`) 저장하지 않고 "구글이 이 키를 받아들이지 않았습니다"를 보인다.
- 모델을 고른 적이 없으면 등록할 때 고를 수 있는 목록(오늘 무료 등급)에서 기본 모델을 고른다. 무료 목록을 읽지 못하면 키만 저장하고 모델은 나중에 고른다. [default_model](../../src/jjabtero/ai.py#default_model)이 고른다. [DEFAULT_MODEL](../../src/jjabtero/ai.py#DEFAULT_MODEL)(`gemini-2.5-flash`)이 있으면 그것을, 없으면 목록의 첫 모델이다.

## 5. API

[router](../../src/jjabtero/ai.py#router)가 처리한다. 로그인이 켜져 있으면 로그인해야 쓴다([로그인 설계](Auth.md#4-막는-범위)). 키를 바꾸면 드라이브 자동 올리기를 예약한다.

| 요청 | 하는 일 |
| --- | --- |
| `GET /api/ai/key` | [read_key_status](../../src/jjabtero/ai.py#read_key_status)가 [key_status](../../src/jjabtero/ai.py#key_status)로 만든 [KeyStatusOut](../../src/jjabtero/ai.py#KeyStatusOut). 키 상태: 등록 여부, 끝 네 글자, 이곳에서 풀 수 있는지, 마스터 키가 있는지, 고른 모델 |
| `PUT /api/ai/key` | [save_key](../../src/jjabtero/ai.py#save_key). 본문 [KeyIn](../../src/jjabtero/ai.py#KeyIn) `{"api_key": "..."}`. 확인한 뒤 암호화해 저장한다. 등록과 변경이 같다. |
| `DELETE /api/ai/key` | [delete_key](../../src/jjabtero/ai.py#delete_key). 키를 지운다. |
| `GET /api/ai/models` | [list_models](../../src/jjabtero/ai.py#list_models). [ModelsOut](../../src/jjabtero/ai.py#ModelsOut): 등록한 키로 쓸 수 있고 오늘 무료 등급인 Gemini 모델 목록(이름, 표시 이름, 설명, 유료 등급 입력·출력 가격), 무료 목록을 읽은 시각, 지난 목록인지 |
| `PUT /api/ai/model` | [choose_model](../../src/jjabtero/ai.py#choose_model). 본문 [ModelIn](../../src/jjabtero/ai.py#ModelIn) `{"model": "..."}`. 고를 수 있는 목록(오늘 무료 등급)에 있는 모델만 받는다. |
| `POST /api/ai/chat` | [chat](../../src/jjabtero/ai.py#chat). 본문 [ChatIn](../../src/jjabtero/ai.py#ChatIn) `{"paper_id", "page", "context", "messages": [{"role": "user"\|"model", "text"}]}`([ChatMessage](../../src/jjabtero/ai.py#ChatMessage)). 마지막 말은 사용자의 것이어야 한다. Gemini의 답과 쓴 모델 [ChatOut](../../src/jjabtero/ai.py#ChatOut) `{"text", "model"}`을 돌려준다. 모델을 고르지 않았으면 409다. |

- 키가 없거나 풀 수 없으면 409, 마스터 키가 없으면 503, Gemini가 실패하면 502와 이유를 돌려준다.

## 6. 화면

- **프로필 버튼:** 머리줄의 계정 이메일을 버튼으로 바꾼다. 로그인이 꺼진 내 컴퓨터에서는 이메일이 없으므로 "프로필"로 보인다. 누르면 프로필 창이 열린다([App](../../frontend/src/App.vue)).
- **프로필 창:** [ProfileDialog](../../frontend/src/ProfileDialog.vue)이고, 상태는 [createProfileState](../../frontend/src/profileState.ts#createProfileState)가 가진다. API 호출은 [fetchAiKey](../../frontend/src/api.ts#fetchAiKey), [saveAiKey](../../frontend/src/api.ts#saveAiKey), [deleteAiKey](../../frontend/src/api.ts#deleteAiKey), [fetchAiModels](../../frontend/src/api.ts#fetchAiModels), [chooseAiModel](../../frontend/src/api.ts#chooseAiModel)이고 응답 모양은 [AiKeyStatus](../../frontend/src/api.ts#AiKeyStatus), [AiModel](../../frontend/src/api.ts#AiModel)이다. 실패하면 [aiRequest](../../frontend/src/api.ts#aiRequest)가 서버가 준 이유를 오류로 던진다. 계정(이메일 또는 "내 컴퓨터, 로그인 꺼짐")과 "Google AI API 키" 칸이 있다.
  - 키가 없으면 비밀번호 입력 칸과 "등록" 버튼, Google AI Studio에서 키를 만드는 링크를 보인다.
  - 키가 있으면 "등록됨 (…끝 네 글자)"와 "변경", "삭제" 버튼을 보인다. "변경"은 입력 칸을 다시 열고, "삭제"는 한 번 묻고 지운다.
  - 키가 있으면 "모델" 드롭다운에서 Gemini 모델을 고른다. 고르면 바로 저장한다. 모델 목록을 받지 못해도 고른 모델 이름은 보인다. 드롭다운 아래에 "오늘 무료 등급인 모델만 보이고 매일 자정에 다시 확인한다"와 마지막 확인 시각을 보인다. 지난 목록이면 그렇다고 알리고, 고른 모델이 오늘 무료 목록에 없으면 다른 모델을 고르라고 알린다. 응답 모양은 [AiModelList](../../frontend/src/api.ts#AiModelList)다. 드롭다운의 모델마다 유료 등급 가격(100만 토큰당 입력·출력)을 보이고, 고른 모델의 가격은 드롭다운 아래에도 보인다.
- **리더의 AI 대화:** [리더](../../frontend/src/ReaderView.vue)에서 글을 고르면 뜨는 하이라이트 색 옆에 "AI 대화" 버튼을 둔다. 이미 있는 하이라이트를 눌렀을 때 뜨는 상자에도 같은 버튼을 둔다. 누르면 리더 오른쪽에 대화 칸([AiChatPanel](../../frontend/src/AiChatPanel.vue))이 열린다. 상태는 [createAiChatState](../../frontend/src/aiChatState.ts#createAiChatState)가 고른 글([ChatContext](../../frontend/src/aiChatState.ts#ChatContext))과 주고받은 말을 가지고, [chatAi](../../frontend/src/api.ts#chatAi)로 보낸다([AiChatMessage](../../frontend/src/api.ts#AiChatMessage)).
  - 대화 칸 위에는 고른 글(몇 줄까지)과 쪽, 쓰는 모델이 보인다. "번역", "요약", "쉽게 설명" 버튼([QUICK_PROMPTS](../../frontend/src/aiChatState.ts#QUICK_PROMPTS))은 그 말을 바로 보낸다. 아래 입력 칸에는 직접 질문을 적고 Enter로 보낸다(Shift+Enter는 줄바꿈, 한글 조합 중의 Enter는 보내지 않음). 답은 받은 글 그대로(줄바꿈 유지) 보인다.
  - 보내기에 실패하면 그 질문을 입력 칸에 돌려놓고 이유를 보인다. 새 글로 대화를 시작한 뒤 늦게 온 지난 답은 버린다.
  - 키가 없으면 대화 칸에 "프로필에서 Google AI API 키를 등록하세요"와 프로필 창을 여는 버튼을 보인다. 프로필에서 키나 모델을 바꾸면 대화 칸이 키 상태를 다시 읽는다.
  - 다른 글로 "AI 대화"를 누르면 새 대화를 시작한다.

## 7. 테스트

- 백엔드 [test_ai](../../tests/test_ai.py)([GeminiWeb](../../tests/test_ai.py#GeminiWeb), [ChatWeb](../../tests/test_ai.py#ChatWeb)): 대화에 쓰는 언어 모델만 고르기, 오늘 무료 등급 모델만 보이고 고를 수 있는지, 마스터 키 고르기(환경 변수, 파일, 만들기, 서버에서는 만들지 않음), 암호화한 값만 저장되는지, 등록·변경·삭제·모델 고르기 API, 가짜 Gemini 응답으로 키 확인 실패와 대화 요청 모양, 키가 응답에 나가지 않는지.
- 백엔드 [test_ai_models](../../tests/test_ai_models.py)([Pages](../../tests/test_ai_models.py#Pages), [Clock](../../tests/test_ai_models.py#Clock)): 가격표에서 표준 탭의 입력 가격 무료 등급 읽기, 하루에 한 번 읽기와 파일 캐시, 실패하면 지난 목록, 한국 자정까지 남은 시간.
- 프론트엔드 [profileState.test](../../frontend/src/profileState.test.ts), [aiChatState.test](../../frontend/src/aiChatState.test.ts): 프로필 상태(등록, 변경, 삭제, 모델 고르기), 대화 상태(빠른 버튼, 주고받기, 실패, 새 대화).

## 8. 미결정 사항

- 대화를 저장해 다시 볼지, 하이라이트의 메모로 남길지.
- 답을 나눠 받아(스트리밍) 바로바로 보일지.
