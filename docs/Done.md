# 완료

이 문서는 끝난 작업의 상세 기록이다. 최신 기록이 맨 위에 온다. 기록 형식은 [작업 관리 규칙](TaskRule.md#5-기록-형식)을 따르며, 할 일 목록은 [로드맵](Roadmap.md)과 [이슈](Issue.md)에 있다. 닫힌 마일스톤의 기록은 [작업 관리 규칙](TaskRule.md#47-완료-기록-보관)에 따라 보관 문서로 옮긴다. 보관 문서: [M0 시작](Done-M0.md). 전체 문서 목록은 [문서 인덱스](index.md)에서 확인한다.

## M1-T8 FastAPI 서버와 Vue 프론트엔드 골격 구성

- 시작일: 2026-10-31
- 완료일: 2026-10-31
- 근거 문서: [시스템 구조](Architecture.md), [앱 골격 설계](design/AppSkeleton.md)

### 계획
- 상세 설계 문서 `docs/design/AppSkeleton.md`를 쓰고 인덱스에서 링크한다. 백엔드 앱 생성, 상태 확인 API, 빌드된 화면 제공, 실행 명령, 프론트엔드의 API 호출 모듈을 정한다.
- 목업을 만들고 검사를 통과시킨 뒤 구현한다.
- 백엔드: FastAPI, uvicorn 의존성과 테스트용 httpx를 추가하고 실행 명령 `jjabtero`를 등록한다.
- 프론트엔드: Vite의 Vue + TypeScript 템플릿으로 `frontend/`를 만들고, Vitest와 `/api` 프록시를 설정한다.
- `frontend/src`를 코드 루트에, 프론트엔드 테스트 명령을 `check.commands`에 더한다.
- README에 개발·실행 방법을 적는다.

### 진행 기록
- 2026-10-31: 작업을 시작했다. PR #6까지 병합되어 최신 `main`에서 작업 브랜치를 만들었다.
- 2026-10-31: 앱 골격 설계를 쓰고 인덱스의 상세 설계 절에 링크했다. 백엔드(`app.py`, `cli.py`)와 프론트엔드(`api.ts`)의 목업을 만든 뒤 구현했다.
- 2026-10-31: `npm create vite@latest`의 `vue-ts` 템플릿으로 `frontend/`를 만들고, 템플릿 예제(HelloWorld 컴포넌트, 이미지, 스타일, `README.md`, `.vscode/`)를 지웠다.
- 2026-10-31: 테스트용으로 httpx를 넣었더니 Starlette가 httpx2를 쓰라는 사용 중단 경고를 냈다. httpx2로 바꿔 경고를 없앴다.
- 2026-10-31: `uv run jjabtero`로 실제 서버를 띄워 `/api/health`(200, 버전 0.1.0), 빌드된 `/`(제목 Jjabtero), `/api/nope`(404)를 확인했다. 처음 쓴 포트 8765는 다른 프로그램이 쓰고 있어 빈 포트로 다시 확인했다.

### 결정 사항
- 상태 확인 API `GET /api/health`를 첫 API로 둔다. 화면과 서버가 연결되는지 확인하는 가장 작은 기능이라서다. [앱 골격 설계](design/AppSkeleton.md#1-백엔드-앱)에 적었다.
- 빌드된 화면이 없으면 정적 파일을 제공하지 않는다. 개발할 때는 Vite가 화면을 제공하므로 빌드 없이도 백엔드가 떠야 한다.
- 실행 명령의 기본 주소는 `127.0.0.1:8000`이다. 혼자 쓰는 앱을 외부에 열지 않기 위해서다.
- 프론트엔드 검사 명령은 `node_modules`가 없을 때만 `npm ci`를 실행한다. 매 검사마다 설치하면 Stop hook이 느려지고, 아예 안 하면 CI에서 실패하기 때문이다.
- 테스트 클라이언트 의존성은 httpx 대신 httpx2를 쓴다. Starlette가 권하는 쪽이다.
- 프론트엔드 테스트 파일은 대상 옆에 `<대상>.test.ts`로 둔다. [시스템 구조](Architecture.md#5-테스트)에 적었다.

### 변경 파일
- `docs/design/AppSkeleton.md`
- `docs/index.md`
- `docs/Architecture.md`
- `README.md`
- `projinit.toml`
- `pyproject.toml`
- `uv.lock`
- `src/jjabtero/app.py`
- `src/jjabtero/cli.py`
- `tests/test_app.py`
- `tests/test_cli.py`
- `frontend/` (Vite 프로젝트 전체: `package.json`, `package-lock.json`, `vite.config.ts`, `index.html`, `tsconfig*.json`, `.gitignore`, `public/favicon.svg`, `src/main.ts`, `src/App.vue`, `src/api.ts`, `src/api.test.ts`)
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`

### 결과
- `uv run jjabtero`로 서버를 띄우면 빌드된 화면과 `/api`가 함께 제공된다. 개발할 때는 Vite 개발 서버가 `/api`를 백엔드로 넘긴다.
- 화면 첫 페이지가 서버 연결 상태와 버전을 보여 준다.
- 일괄 검사가 백엔드 pytest와 프론트엔드 Vitest를 함께 실행한다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.1.4 projinit check`: 모든 검사기, `uv run pytest`(테스트 9개), 프론트엔드 `npm test`(테스트 2개) 통과.
- `npm run build`: `vue-tsc` 타입 검사와 빌드 통과.
- 실제 서버 실행 확인은 진행 기록에 적었다.

## M1-T2 웹 프레임워크와 데이터 저장 방식 결정

- 시작일: 2026-10-31
- 완료일: 2026-10-31
- 근거 문서: [시스템 구조](Architecture.md#6-미결정-사항)

### 계획
- 웹 프레임워크와 데이터 저장 방식의 후보를 비교해 사용자에게 제시하고, 사용자가 고른다.
- 고른 내용을 시스템 구조에 반영하고 미결정 사항에서 지운다. 화면 구성 방식처럼 프레임워크를 고르면 함께 정해지는 항목도 반영한다.
- 의존성 추가와 코드 골격은 로드맵에 새 태스크 M1-T8로 등록해 그 작업에서 한다.

### 진행 기록
- 2026-10-31: 작업을 시작했다. PR #5까지 병합되어 최신 `main`에서 작업 브랜치를 만들었다.
- 2026-10-31: 웹 프레임워크(FastAPI + HTMX, Streamlit, NiceGUI)와 저장 방식(SQLite, DuckDB, JSON/YAML 파일) 후보를 제시했다. 사용자는 백엔드 FastAPI에 Vite 기반의 별도 프론트엔드, 저장은 SQLite를 골랐다.
- 2026-10-31: 이어서 프론트엔드 프레임워크(React, Svelte, Vue), 언어(TypeScript, JavaScript), SQLite 접근 방식(SQLModel, SQLAlchemy, sqlite3)을 물었다. 사용자는 Vue, TypeScript, SQLAlchemy를 골랐다.
- 2026-10-31: 시스템 구조에 구성 요소, 디렉터리, 도구, 스타일, 테스트 방식을 반영하고 미결정 사항을 갱신했다. 로드맵에 M1-T8 골격 구성을 추가했다.

### 결정 사항
- 백엔드는 FastAPI(uvicorn), 프론트엔드는 Vue 3 + TypeScript + Vite, 데이터는 SQLite + SQLAlchemy로 한다. 사용자가 골랐다. [시스템 구조](Architecture.md#1-실행-형태)에 반영했다.
- 개발할 때는 Vite 개발 서버가 `/api`를 FastAPI로 넘기고, 쓸 때는 FastAPI가 빌드한 프론트엔드를 함께 제공해 서버 하나로 실행한다.
- 패키지 관리는 이 컴퓨터에 설치된 npm, 프론트엔드 테스트는 Vite와 짝인 Vitest로 한다.
- 포인터 검사기가 `.vue` 파일을 해석하지 않으므로, 프론트엔드 로직은 `.ts` 모듈에 두고 포인터를 단다.
- 이 태스크는 결정과 문서 반영까지만 한다. 의존성 추가와 서버·프론트엔드 골격은 M1-T8로 나눴다. 로드맵 번호 규칙상 맨 뒤에 붙였지만 M1-T3보다 먼저 한다.

### 변경 파일
- `docs/Architecture.md`
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`

### 결과
- 백엔드, 프론트엔드, 데이터 저장의 기술 스택과 개발·실행 구성이 시스템 구조에 정해져, 골격 구성(M1-T8)을 시작할 수 있다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.1.4 projinit check`: 모든 검사기와 `uv run pytest` 통과.

## M1-T1 Python 프로젝트 골격(uv, pytest) 구성과 테스트 명령 등록

- 시작일: 2026-10-31
- 완료일: 2026-10-31
- 근거 문서: [시스템 구조](Architecture.md)

### 계획
- 시스템 구조 문서에 Python 버전, 골격 파일, 테스트 파일을 먼저 적는다.
- `pyproject.toml`, `.python-version`, `.gitignore`, `src/jjabtero/__init__.py`, `tests/test_package.py`를 만들고 `uv sync`로 `uv.lock`을 만든다.
- `projinit.toml`의 `check.commands`에 `uv run pytest`를 등록한다.
- README에 설치와 실행 방법을 적는다.

### 진행 기록
- 2026-10-31: 작업을 시작했다. PR #3(I4)이 병합되지 않아 `i4-projinit-0-1-3` 위에 작업 브랜치를 만들었다.
- 2026-10-31: 시스템 구조에 Python 3.14, 골격 파일, 최상위 모듈과 테스트 포인터를 적었다.
- 2026-10-31: `pyproject.toml`(빌드 백엔드 uv_build, 개발 의존성 그룹 `dev`에 pytest), `.python-version`, `.gitignore`, 패키지와 테스트를 만들고 `uv sync`로 `uv.lock`을 만들었다. `uv run pytest`에서 테스트 2개가 통과했다.
- 2026-10-31: `check.commands`에 `uv run pytest`를 등록하고 README에 설치와 테스트 방법을 적었다.

### 결정 사항
- Python 버전은 3.14로 한다. 사용자가 따로 정하지 않아 제안대로 정했다. 3.15.0은 막 나와서 라이브러리 지원이 따라오지 않았을 수 있다.
- 패키지 버전은 `pyproject.toml`에만 적고 `__version__`은 설치된 패키지 정보에서 읽는다. 버전을 두 곳에서 관리하지 않기 위해서다.
- 웹 프레임워크가 미정이므로 실행 진입점(`project.scripts`)은 아직 두지 않는다. M1-T2에서 프레임워크를 정한 뒤 추가한다.

### 변경 파일
- `docs/Architecture.md`
- `README.md`
- `projinit.toml`
- `pyproject.toml`
- `uv.lock`
- `.python-version`
- `.gitignore`
- `src/jjabtero/__init__.py`
- `tests/test_package.py`
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`

### 결과
- `uv sync`로 개발 환경을 만들고 `uv run pytest`로 테스트를 실행할 수 있다. 일괄 검사가 테스트도 함께 실행한다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.1.3 projinit check`: 모든 검사기와 `uv run pytest` 통과(테스트 2개).

## I3 ProjInit 0.1.2 업그레이드

- 시작일: 2026-10-31
- 완료일: 2026-10-31
- 근거 문서: [검증 도구의 설정](VerificationTools.md#11-설정)

### 계획
- `projinit.toml`의 `version`을 0.1.2로 바꾼다.
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.1.2 projinit init --refresh-common`으로 공통 파일을 다시 만든다.
- 바뀐 규칙을 확인해 사용자에게 알리고, 프로젝트 문서가 바뀐 규칙에 맞는지 검사를 통과시킨다.

### 진행 기록
- 2026-10-31: 사용자 지시로 이슈를 등록하고 시작했다. PR #1이 병합되지 않아 `i1-remote-repository` 위에 작업 브랜치를 만들었다.
- 2026-10-31: `version`을 0.1.2로 바꾸고 `init --refresh-common`을 실행했다. 공통 파일 6개가 다시 쓰였다. 규칙 변경은 `docs/TaskRule.md`에 4.9 ProjInit 버전 올리기 절이 추가된 것뿐이고, 나머지 파일은 검사기 명령의 버전만 바뀌었다. 진행 중인 다른 작업이 없어 영향받는 작업은 없다.

### 결정 사항
- 규칙 문서와 검사기 버전이 바뀌므로 경량 이슈가 아닌 일반 경로로 처리한다.

### 변경 파일
- `projinit.toml`
- `.claude/settings.json`
- `.githooks/commit-msg`
- `.githooks/pre-commit`
- `.github/pull_request_template.md`
- `.github/workflows/verify.yml`
- `docs/TaskRule.md`
- `docs/Issue.md`
- `docs/Ongoing.md`
- `docs/Done.md`

### 결과
- 프로젝트가 ProjInit 0.1.2 검사기와 공통 규칙 문서를 쓴다. ProjInit 버전을 올리는 절차가 [작업 관리 규칙](TaskRule.md#49-projinit-버전-올리기)에 생겼다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.1.2 projinit check`: 모든 검사기 통과(check_docs, check_pointers, check_tasks, check_hooks, check_commits, check_template).

## I2 ProjInit 0.1.1 업그레이드

- 시작일: 2026-10-31
- 완료일: 2026-10-31
- 근거 문서: [검증 도구의 설정](VerificationTools.md#11-설정)

### 계획
- 작업 트리에 생긴 ProjInit 0.1.1 업그레이드 변경을 확인하고, I1과 섞지 않고 별도 커밋으로 반영한다.

### 진행 기록
- 2026-10-31: I1 작업 중 작업 트리에서 ProjInit 버전이 0.1.0에서 0.1.1로 바뀐 것을 발견했다. `projinit.toml`의 `version`, `.claude/settings.json`, `.githooks/pre-commit`, `.githooks/commit-msg`, `.github/` 파일의 검사기 명령, `docs/TaskRule.md`의 4.8 첫 작업 절차가 바뀌어 있었다.
- 2026-10-31: 사용자가 의도한 업그레이드임을 확인했고, I2로 등록해 I1과 같은 PR의 별도 커밋으로 처리하기로 했다.

### 결정 사항
- 업그레이드는 규칙 문서(`docs/TaskRule.md`)와 검사기 버전을 바꾸므로 경량 이슈가 아닌 일반 경로로 처리한다.
- I1과 같은 작업 브랜치 `i1-remote-repository`에서 처리하되 커밋은 나눈다([커밋 규칙](CommitRule.md#2-커밋-단위와-시점)).

### 변경 파일
- `projinit.toml`(`version`만)
- `.claude/commands/start.md`
- `.claude/settings.json`
- `.githooks/commit-msg`
- `.githooks/pre-commit`
- `.github/pull_request_template.md`
- `.github/workflows/verify.yml`
- `docs/TaskRule.md`
- `docs/Issue.md`
- `docs/Done.md`

### 결과
- 프로젝트가 ProjInit 0.1.1 검사기와 공통 규칙 문서를 쓴다. 첫 작업 절차가 질문을 하나씩 가볍게 하는 방식으로 바뀌었다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.1.1 projinit check`: 모든 검사기 통과(check_docs, check_pointers, check_tasks, check_hooks, check_commits, check_template).
