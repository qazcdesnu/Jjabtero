# 로그인 설계

이 문서는 배포한 Jjabtero를 본인만 쓰게 하는 로그인을 정한다. 무엇을 공개하고 무엇을 막는지는 [배포 설계](Deployment.md#2-공개-범위)에 있다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 방식

- 구글 로그인(OpenID Connect)으로 사용자의 이메일을 확인하고, 허용한 이메일 하나와 같을 때만 들여보낸다. 사용자가 골랐다. 이미 드라이브 동기화에 같은 OAuth 클라이언트를 쓰고 있어 새로 관리할 비밀번호가 생기지 않기 때문이다.
- 범위는 `openid email`이다. 이메일만 확인하고 다른 정보는 받지 않는다. 갱신 토큰도 받지 않는다.
- 드라이브 연결과는 따로다. 로그인은 "누가 쓰는가"를, 드라이브 연결은 "서재를 어디에 보관하는가"를 정한다.

## 2. 켜고 끄기

[AuthSettings](../../src/jjabtero/auth.py#AuthSettings)가 설정을 가지며, [auth_settings_from_env](../../src/jjabtero/auth.py#auth_settings_from_env)가 환경 변수에서 읽는다.

| 환경 변수 | 뜻 |
| --- | --- |
| `JJABTERO_ALLOWED_EMAIL` | 들여보낼 구글 계정 이메일. 있으면 로그인이 켜진다. 대소문자는 가리지 않는다. |
| `JJABTERO_SESSION_SECRET` | 세션 쿠키 서명 키(32자 이상). 로그인이 켜졌는데 없거나 짧으면 앱이 시작하지 않는다([AuthConfigError](../../src/jjabtero/auth.py#AuthConfigError)). |
| `JJABTERO_SECURE_COOKIE` | `1`이면 세션 쿠키에 `Secure`를 붙여 HTTPS에서만 보낸다. 배포 환경에서 켠다. |

- `JJABTERO_ALLOWED_EMAIL`이 없으면 로그인이 꺼진다. 내 컴퓨터에서 `127.0.0.1`로 쓸 때의 기본이다.
- 실행 명령([main](../../src/jjabtero/cli.py#main))은 로그인이 꺼진 채 `127.0.0.1`·`localhost`·`::1`이 아닌 주소로 띄우려 하면 오류로 끝난다. 서재를 실수로 외부에 그대로 여는 일을 막기 위해서다.
- 서명 키가 서버 재시작마다 바뀌면 다시 로그인해야 하므로, 키는 환경 변수로 고정한다.

## 3. 세션

- [create_app](../../src/jjabtero/app.py#create_app)은 인자 `auth`(없으면 환경 변수)로 설정을 받아 검사하고, 로그인이 켜져 있을 때만 세션 미들웨어와 로그인 검사를 단다. 세션 미들웨어가 로그인 검사보다 바깥에 있어야 로그인 검사가 세션을 읽을 수 있다.
- Starlette의 `SessionMiddleware`(서명된 쿠키, `itsdangerous`)를 쓴다. 쿠키 이름은 `jjabtero_session`, 유효 기간은 30일, `SameSite=Lax`다. 배포 환경에서는 `JJABTERO_SECURE_COOKIE`로 `Secure`를 붙인다. 로컬에서 HTTP로 로그인을 시험할 때는 끈다.
- 세션에는 로그인한 이메일과, 로그인 중인 요청의 `state`·PKCE 검증 값·돌아갈 주소만 둔다. 구글 토큰은 두지 않는다.
- 쿠키가 `SameSite=Lax`라 구글에서 콜백으로 돌아오는 최상위 이동(GET)에도 쿠키가 실린다.

## 4. 막는 범위

[require_login](../../src/jjabtero/auth.py#require_login) 미들웨어가 로그인이 켜져 있을 때 요청을 거른다.

- `/api` 아래는 로그인해야 한다. 예외는 `/api/health`와 `/api/auth/` 아래뿐이다. 로그인하지 않은 요청은 401과 `{"detail": "로그인이 필요합니다."}`를 받는다.
- 화면 파일(`/`, `/assets/...`)은 막지 않는다. 화면 코드에는 서재 데이터가 없고, 화면이 로그인 상태를 묻고 로그인 화면을 보여 주기 때문이다. 서재 데이터는 모두 `/api`로만 나간다.
- `/api/drive/callback`도 막는 범위다. 드라이브 연결은 로그인한 뒤에 한다.

## 5. API

[auth 모듈](../../src/jjabtero/auth.py)의 라우터다.

- `GET /api/auth/me`: [Me](../../src/jjabtero/auth.py#Me)(`enabled`, `email`)를 돌려준다. 로그인이 꺼져 있으면 `enabled`가 거짓이고 `email`은 `null`이다.
- `GET /api/auth/login?return_to=<주소>`: `state`와 PKCE 값을 세션에 두고 구글 로그인 화면으로 보낸다(302). 범위는 `openid email`, `prompt=select_account`다. `return_to`는 같은 사이트 안의 경로(`/`로 시작하고 `//`로 시작하지 않음)만 받고, 아니면 `/`로 한다. 로그인이 꺼져 있으면 404.
- `GET /api/auth/callback?code=&state=`: 세션의 `state`와 맞으면 코드를 접근 토큰으로 바꾸고, 구글 사용자 정보(`https://openidconnect.googleapis.com/v1/userinfo`)에서 이메일을 받는다. 이메일이 확인된(`email_verified`) 허용 이메일이면 세션에 적고 돌아갈 주소로 보낸다(302). 다른 계정이면 403, `state`가 맞지 않거나 `error`가 오면 400이다.
- 리디렉션 URI는 요청이 들어온 주소로 만든 `<scheme>://<host>/api/auth/callback`이다. OAuth 클라이언트에 이 주소를 등록해야 한다.
- `POST /api/auth/logout`: 세션을 비우고 `Me`를 돌려준다.
- OAuth 요청은 [google_auth 모듈](../../src/jjabtero/google_auth.py)의 클라이언트 읽기, PKCE, 동의 주소 만들기를 함께 쓴다. 코드는 [exchange_code_for_access](../../src/jjabtero/google_auth.py#exchange_code_for_access)로 접근 토큰만 받는다.

## 6. 화면

- [auth 모듈](../../frontend/src/auth.ts)의 [fetchMe](../../frontend/src/auth.ts#fetchMe), [logout](../../frontend/src/auth.ts#logout), [loginUrl](../../frontend/src/auth.ts#loginUrl)이 API를 부른다.
- [createAuthState](../../frontend/src/auth.ts#createAuthState)가 로그인 상태를 가진다. `needsLogin`은 로그인이 켜져 있고 로그인하지 않았을 때 참이다.
- [watchUnauthorized](../../frontend/src/auth.ts#watchUnauthorized)는 `fetch`를 감싸, `/api/auth/` 밖의 요청이 401을 받으면 콜백을 부른다. 앱은 그때 로그인 상태를 다시 불러온다. 세션이 끝나면 로그인 화면으로 돌아가기 위해서다.
- 앱(`App.vue`)은 처음에 로그인 상태를 불러오고, 그 전에는 아무것도 그리지 않는다. `needsLogin`이면 앱 대신 `LoginView.vue`(앱 이름과 "Google로 로그인" 단추)를 보여 주고, 서재와 드라이브 상태를 불러오지 않는다.
- 로그인이 켜져 있으면 머리줄 오른쪽에 로그인한 이메일과 "로그아웃" 단추를 둔다.

## 7. 테스트

- [test_auth](../../tests/test_auth.py): 환경 변수 읽기와 서명 키 검사, 로그인이 꺼졌을 때의 동작, 막는 범위와 공개 예외, 로그인 흐름(가짜 토큰·사용자 정보 응답)의 성공과 다른 계정·확인 안 된 이메일·`state` 불일치·`return_to` 검사, 로그아웃.
- [test_cli](../../tests/test_cli.py): 로그인이 꺼진 채 외부 주소로 띄우면 거부하는지.
- [auth.test](../../frontend/src/auth.test.ts): API 함수, `needsLogin`, 401 감시.
