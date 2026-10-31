# 시스템 구조

이 문서는 Jjabtero의 디렉터리 구조, 개발 언어와 스타일, 테스트 방식을 정한다. [코드 작업 규칙](CodeRule.md#2-디렉터리-구조)이 프로젝트마다 정하라고 남긴 내용이다. 무엇을 만드는지는 [제품 비전](ProductVision.md)에 있다. 전체 문서 목록은 [문서 인덱스](index.md)에서 확인한다.

## 1. 실행 형태

사용자의 컴퓨터에서 실행하는 로컬 웹 앱이다. 서버를 로컬에서 띄우고 브라우저로 접속한다. 앱은 백엔드와 프론트엔드 두 부분으로 나뉜다.

| 구성 요소 | 기술 | 하는 일 |
| --- | --- | --- |
| 백엔드 | FastAPI (Python), uvicorn | `/api` 아래에서 JSON API를 제공한다. 서지 데이터의 저장·검색과 인용·통계 계산을 맡는다. |
| 프론트엔드 | Vue 3, TypeScript, Vite | 브라우저에서 도는 단일 페이지 앱(SPA)이다. 백엔드 API를 불러 화면을 그린다. |
| 데이터 | SQLite, SQLAlchemy | 서재 데이터를 SQLite 파일 하나에 저장하고, 백엔드가 SQLAlchemy로 읽고 쓴다. |

- **개발할 때**: Vite 개발 서버가 화면을 제공하고, `/api` 요청은 FastAPI 개발 서버로 넘긴다(proxy). 두 서버를 함께 띄운다.
- **쓸 때**: 프론트엔드를 빌드한 정적 파일을 FastAPI가 함께 제공한다. 서버 하나만 띄우면 된다.

## 2. 디렉터리 구조

[코드 작업 규칙](CodeRule.md#2-디렉터리-구조)의 공통 경로에 더해 다음 경로를 쓴다.

| 경로 | 용도 |
| --- | --- |
| `src/jjabtero/` | 백엔드 코드(Python 패키지). |
| `tests/` | 백엔드 pytest 테스트. |
| `frontend/` | 프론트엔드 앱(Vue, TypeScript, Vite). `package.json`, `package-lock.json`, Vite 설정, 자체 `.gitignore`(`node_modules/`, 빌드 결과 `dist/`)를 이 안에 둔다. |
| `frontend/src/` | 프론트엔드 코드. |
| `pyproject.toml` | 패키지 정보와 의존성, pytest 설정. |
| `uv.lock` | uv가 만드는 의존성 잠금 파일. 커밋한다. |
| `.python-version` | uv가 쓰는 Python 버전. |
| `.gitignore` | 커밋하지 않을 파일(가상 환경 `.venv/`, 캐시). |
| `README.md` | 저장소 소개와 사용법. |

`src/`, `tests/`, `frontend/src/`는 [검증 도구의 설정](VerificationTools.md#11-설정)의 코드 루트다. 패키지와 프론트엔드 안의 모듈 구성은 기능별 상세 설계 문서(`docs/design/`)에서 정한다.

[포인터 검사기](VerificationTools.md#4-포인터-검사기)는 `.ts` 파일은 해석하지만 Vue 단일 파일 컴포넌트(`.vue`)는 해석하지 않는다([포인터 규약의 언어별 심볼 규칙](Traceability.md#7-언어별-심볼-규칙)). 그래서 상태 관리, API 호출, 계산 같은 로직은 `.ts` 모듈에 두고 포인터를 단다. `.vue` 컴포넌트는 화면 구성에 집중하고, 근거 문서는 주석으로 적되 검사되지 않는다.

패키지의 최상위 모듈은 [jjabtero](../src/jjabtero/__init__.py)다. 지금은 패키지 버전을 [`__version__`](../src/jjabtero/__init__.py#__version__)으로 알리는 일만 한다. 값은 설치된 패키지 정보(`pyproject.toml`의 `version`)에서 읽어, 버전을 한 곳에서만 관리한다.

## 3. 언어와 도구

| 항목 | 내용 |
| --- | --- |
**백엔드**

| 항목 | 내용 |
| --- | --- |
| 언어 | Python 3.14 |
| 버전·의존성 관리 | uv |
| 빌드 백엔드 | uv_build |
| 웹 프레임워크 | FastAPI, ASGI 서버 uvicorn |
| 데이터베이스 | SQLite, SQLAlchemy |
| 테스트 | pytest (개발 의존성 그룹 `dev`) |

Python 버전은 `.python-version`과 `pyproject.toml`의 `requires-python`(`>=3.14`)에 적는다.

**프론트엔드**

| 항목 | 내용 |
| --- | --- |
| 언어 | TypeScript |
| 프레임워크 | Vue 3 |
| 빌드·개발 서버 | Vite |
| 패키지 관리 | npm |
| 테스트 | Vitest |

## 4. 스타일

- [PEP 8](https://peps.python.org/pep-0008/)을 따른다. 모듈과 함수는 `snake_case`, 클래스는 `PascalCase`, 상수는 `UPPER_SNAKE_CASE`로 쓴다.
- 공개 함수와 메서드에는 타입 힌트를 단다.
- Python 코드의 문서 포인터는 docstring에 적는다([포인터 규약](Traceability.md)).
- TypeScript 코드의 문서 포인터는 주석에 적는다. Vue 컴포넌트 파일 이름은 `PascalCase.vue`로 쓴다.

## 5. 테스트

- 백엔드 테스트는 `tests/` 아래에 `test_<대상>.py` 이름으로 둔다.
- API 테스트는 FastAPI의 테스트 클라이언트로 하고, 데이터베이스를 쓰는 테스트는 테스트마다 새 임시 SQLite 데이터베이스를 쓴다.
- 프론트엔드 테스트는 Vitest로 하며 `frontend/src/` 안에 대상 옆에 `<대상>.test.ts` 이름으로 둔다. 실행 명령은 `frontend/`에서 `npm test`이고, `check.commands`에는 `node_modules`가 없으면 `npm ci`로 먼저 설치하도록 등록한다. CI처럼 처음 받은 저장소에서도 검사가 돌게 하기 위해서다.
- 백엔드 실행 명령은 `uv run pytest`이고, [검증 도구의 설정](VerificationTools.md#11-설정)의 `check.commands`에 등록해 일괄 검사가 함께 실행한다.
- 패키지 골격 테스트는 [test_package](../tests/test_package.py)에 있다. 패키지를 불러올 수 있는지, `__version__`이 설치된 패키지 버전과 같은지 확인한다.
- 외부 서비스(인용 데이터 API 등)를 부르는 코드는 테스트에서 실제 네트워크 호출 대신 고정된 응답으로 대신한다.

## 6. 미결정 사항

아래 항목은 아직 정하지 않았다. 정하면 이 문서에 반영하고 이 목록에서 지운다.

- 시각화 라이브러리(통계 차트, 인용 그래프).
- UI 컴포넌트 라이브러리를 쓸지, 쓴다면 무엇을 쓸지.
- SQLite 데이터베이스 파일의 위치.
- 데이터베이스 스키마를 바꾸는 방식(예: Alembic 마이그레이션).
- 백엔드 API의 타입을 프론트엔드와 공유하는 방식(예: OpenAPI 명세에서 TypeScript 타입 생성).
- Node.js 버전과 프론트엔드 린터·포매터.
