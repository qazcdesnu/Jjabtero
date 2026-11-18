# 사용자 설정 설계

이 문서는 사용자가 앱 안에서 바꾸는 설정을 정한다. 처음 생기는 설정은 인용 데이터를 가져오는 양이다([인용 데이터 설계](Citations.md#3-가져오는-범위)). 비밀 값과 배포 환경 값은 설정이 아니라 환경 변수로 둔다([배포 설계](Deployment.md#3-데이터와-비밀-값)). 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 항목

항목은 [settings 모듈](../../src/jjabtero/settings.py)의 [SETTINGS](../../src/jjabtero/settings.py#SETTINGS)에 [SettingSpec](../../src/jjabtero/settings.py#SettingSpec)(키, 이름, 설명, 기본값, 최솟값, 최댓값)으로 적는다. 지금 설정은 모두 정수다.

| 키 | 이름 | 뜻 | 기본값 | 허용 범위 |
| --- | --- | --- | --- | --- |
| `citing_limit` | 가져올 피인용 수 | 서재 논문마다 가져올 피인용(공개 후 1년 안)의 최대 건수. 피인용 많은 순으로 고른다. | 10 | 1~1000의 정수 |

- 사용자가 정한 것만 설정으로 둔다. `citing_limit`의 기본값 10은 사용자가 정했다. 피인용 기간(공개 후 1년)은 설정이 아니다. 사용자가 최대 건수만 조절하면 된다고 정했다.
- 항목을 더할 때는 `SETTINGS`와 이 표에 함께 적는다.

## 2. 저장

- 설정은 서재 파일(`library.db`)의 `settings` 표에 둔다. 모델은 [Setting](../../src/jjabtero/models.py#Setting)(`key` 기본 키, `value` 문자열)이다. 서재와 함께 드라이브로 동기화되어, 로컬과 서버 어디서 바꿔도 같은 값을 쓰기 위해서다. 표는 마이그레이션 0003이 만든다([서재 데이터 설계의 스키마 변경](Library.md#3-스키마-변경)).
- 같은 표에 AI 대화의 암호화한 API 키와 모델도 둔다(`ai.`로 시작하는 키, [AI 대화 설계](AiChat.md#3-데이터)). 설정 항목이 아니므로 설정 화면과 이 API에는 나오지 않는다.
- 표에는 사용자가 바꾼 항목만 있다. 없는 키는 기본값을 쓴다. 기본값을 바꿔도 사용자가 고친 적 없는 설정은 새 기본값을 따르게 하기 위해서다.
- [read_settings](../../src/jjabtero/settings.py#read_settings)는 모든 항목의 현재 값을 돌려준다. 저장된 값이 정수가 아니거나 범위를 벗어나면 기본값을 쓴다.
- [update_settings](../../src/jjabtero/settings.py#update_settings)는 바꿀 항목만 받아 모두 검사한 뒤 저장한다. 하나라도 모르는 키이거나 범위를 벗어나면 [SettingError](../../src/jjabtero/settings.py#SettingError)를 던지고 아무것도 저장하지 않는다.
- 다른 기능은 `read_settings`로 값을 읽는다. 인용 데이터 가져오기(M3-T8)가 `citing_limit`을 읽는다.

## 3. API

[router](../../src/jjabtero/settings.py#router)가 처리한다. 로그인이 켜져 있으면 로그인해야 쓴다([로그인 설계](Auth.md#4-막는-범위)).

- `GET /api/settings`는 [read_settings_api](../../src/jjabtero/settings.py#read_settings_api)가 처리한다. 항목마다 [SettingOut](../../src/jjabtero/settings.py#SettingOut)(키, 이름, 설명, 현재 값, 기본값, 최솟값, 최댓값)을 `SETTINGS` 순서대로 돌려준다. 화면이 항목 목록을 따로 갖지 않고 이 응답으로 그리게 하기 위해서다.
- `PUT /api/settings`는 [update_settings_api](../../src/jjabtero/settings.py#update_settings_api)가 처리한다. 본문은 `{"<키>": <값>, ...}`이고, 바뀐 뒤의 전체 목록을 돌려준다. 모르는 키, 정수가 아닌 값, 범위를 벗어난 값은 422와 `{"detail": "<이유>"}`로 거절한다. 저장하면 드라이브 자동 올리기를 예약한다([구글 드라이브 동기화 설계](DriveSync.md#5-동기화)).

## 4. 화면

- 왼쪽 칸 화면 목록에 "설정"(톱니 아이콘)을 더한다([UI 기반 설계의 화면 배치](UiLayout.md#3-화면-배치)).
- 설정 화면은 [SettingsView](../../frontend/src/SettingsView.vue)이다. 고를 항목이 없으므로 가운데와 오른쪽 칸을 합친 넓은 칸 하나에 보여 준다.
- 항목마다 이름, 설명, 숫자 입력 칸(최솟값·최댓값 제한), 기본값을 보여 준다. "저장"을 누르면 바뀐 항목만 보낸다. 저장되면 "저장했습니다"를, 거절되면 서버가 준 이유를 보여 준다. "기본값으로"를 누르면 입력 칸을 기본값으로 바꾼다(저장은 따로 누른다).
- 설정 항목 아래에 "인용 데이터" 칸을 두어 인용 데이터 상태와 "인용 데이터 새로 받기" 버튼을 보여 준다([인용 데이터 설계](Citations.md#6-api와-화면)).
- 화면 상태는 [settingsState 모듈](../../frontend/src/settingsState.ts)의 [createSettingsState](../../frontend/src/settingsState.ts#createSettingsState)가 가진다. API 호출은 [api 모듈](../../frontend/src/api.ts)의 [fetchSettings](../../frontend/src/api.ts#fetchSettings)와 [saveSettings](../../frontend/src/api.ts#saveSettings)다.

## 5. 테스트

- [test_settings](../../tests/test_settings.py): 기본값, 저장과 읽기, 모르는 키·범위 밖·정수가 아닌 값 거절(아무것도 저장 안 함), 저장된 값이 깨졌을 때 기본값, API 응답 모양과 422, 저장 뒤 드라이브 올리기 예약.
- [settingsState.test](../../frontend/src/settingsState.test.ts): 불러오기, 바뀐 항목만 보내기, 기본값으로, 저장 실패 메시지.
- [api.test](../../frontend/src/api.test.ts): `fetchSettings`, `saveSettings`의 요청과 422 오류 메시지.
