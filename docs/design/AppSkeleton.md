# 앱 골격 설계

이 문서는 백엔드 서버와 프론트엔드 앱의 골격을 정한다. 기능은 아직 없고, 서버를 띄우고 화면에서 서버 상태를 확인하는 데까지가 범위다. 기술 스택과 디렉터리는 [시스템 구조](../Architecture.md)에 있다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 백엔드 앱

백엔드 앱은 [app 모듈](../../src/jjabtero/app.py)에 있다.

- [create_app](../../src/jjabtero/app.py#create_app)은 FastAPI 앱을 만들어 돌려준다. 인자 `frontend_dist`는 빌드된 프론트엔드 디렉터리이며, 기본값은 [DEFAULT_FRONTEND_DIST](../../src/jjabtero/app.py#DEFAULT_FRONTEND_DIST)(저장소의 `frontend/dist`)다.
  - API는 모두 `/api` 아래에 둔다.
  - `frontend_dist`가 디렉터리로 있으면 그 안의 정적 파일을 `/`에서 제공하고, `/`에는 `index.html`을 준다. 없으면 정적 파일을 제공하지 않는다. 개발할 때는 Vite 개발 서버가 화면을 제공하므로 빌드 없이도 앱이 떠야 하기 때문이다.
  - API 경로를 정적 파일보다 먼저 등록해, 정적 파일이 API를 가리지 않게 한다.
- [Health](../../src/jjabtero/app.py#Health)는 상태 확인 응답이다. `status`(항상 `"ok"`)와 `version`(패키지 버전)을 가진다.
- `GET /api/health`는 [health](../../src/jjabtero/app.py#health)가 처리하며 `Health`를 돌려준다. 서버가 떠 있는지와 버전을 확인하는 데 쓴다.
- 없는 API 경로는 404를 돌려준다.

## 2. 실행 명령

[cli 모듈](../../src/jjabtero/cli.py)의 [main](../../src/jjabtero/cli.py#main)이 실행 명령 `jjabtero`다. `pyproject.toml`의 `project.scripts`에 등록한다.

- `create_app()`으로 앱을 만들어 uvicorn으로 띄운다.
- 옵션은 `--host`(기본 `127.0.0.1`)와 `--port`(기본 `8000`)다. 기본값이 로컬 주소인 것은 혼자 쓰는 앱을 외부에 열지 않기 위해서다.
- 인자 `argv`를 받으면 명령줄 대신 그것을 해석한다. 테스트에서 쓴다.

## 3. 프론트엔드 앱

프론트엔드는 `frontend/`의 Vite 프로젝트다.

- API 호출은 [api 모듈](../../frontend/src/api.ts)에 모은다. 화면 컴포넌트는 이 모듈만 부른다([시스템 구조](../Architecture.md#2-디렉터리-구조)의 `.vue` 제약).
  - [Health](../../frontend/src/api.ts#Health)는 백엔드 `Health`와 같은 모양의 타입이다.
  - [fetchHealth](../../frontend/src/api.ts#fetchHealth)는 `GET /api/health`를 불러 `Health`를 돌려준다. 응답 상태가 성공이 아니면 상태 코드를 담은 오류를 던진다.
- 진입점은 [main 모듈](../../frontend/src/main.ts)이다. 루트 컴포넌트 `App.vue`를 `#app`에 붙인다.
- `App.vue`는 첫 화면이다. 앱 이름과 `fetchHealth`로 얻은 서버 상태(버전)를 보여 주고, 실패하면 서버에 연결할 수 없다고 보여 준다.
- Vite 개발 서버는 `/api` 요청을 `http://127.0.0.1:8000`(백엔드 기본 주소)로 넘긴다.

## 4. 테스트

- [test_app](../../tests/test_app.py)은 상태 확인 API, 없는 API 경로, 빌드된 화면이 있을 때와 없을 때의 `/`를 확인한다.
- [test_cli](../../tests/test_cli.py)는 실행 명령이 기본값과 지정한 옵션으로 uvicorn을 부르는지 확인한다. 실제 서버는 띄우지 않는다.
- [api.test](../../frontend/src/api.test.ts)는 `fetchHealth`의 성공과 실패를 `fetch`를 대신한 가짜 응답으로 확인한다.
