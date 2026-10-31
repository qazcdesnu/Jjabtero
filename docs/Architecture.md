# 시스템 구조

이 문서는 Jjabtero의 디렉터리 구조, 개발 언어와 스타일, 테스트 방식을 정한다. [코드 작업 규칙](CodeRule.md#2-디렉터리-구조)이 프로젝트마다 정하라고 남긴 내용이다. 무엇을 만드는지는 [제품 비전](ProductVision.md)에 있다. 전체 문서 목록은 [문서 인덱스](index.md)에서 확인한다.

## 1. 실행 형태

- 사용자의 컴퓨터에서 실행하는 로컬 웹 앱이다. 서버를 로컬에서 띄우고 브라우저로 접속한다.
- 웹 프레임워크는 아직 정하지 않았다([6. 미결정 사항](#6-미결정-사항)).

## 2. 디렉터리 구조

[코드 작업 규칙](CodeRule.md#2-디렉터리-구조)의 공통 경로에 더해 다음 경로를 쓴다.

| 경로 | 용도 |
| --- | --- |
| `src/jjabtero/` | 제품 코드(Python 패키지). |
| `tests/` | pytest 테스트. |
| `pyproject.toml` | 패키지 정보와 의존성, pytest 설정. |
| `uv.lock` | uv가 만드는 의존성 잠금 파일. 커밋한다. |
| `.python-version` | uv가 쓰는 Python 버전. |
| `.gitignore` | 커밋하지 않을 파일(가상 환경 `.venv/`, 캐시). |
| `README.md` | 저장소 소개와 사용법. |

`src/`와 `tests/`는 [검증 도구의 설정](VerificationTools.md#11-설정)의 코드 루트다. 패키지 안의 모듈 구성은 기능별 상세 설계 문서(`docs/design/`)에서 정한다.

패키지의 최상위 모듈은 [jjabtero](../src/jjabtero/__init__.py)다. 지금은 패키지 버전을 [`__version__`](../src/jjabtero/__init__.py#__version__)으로 알리는 일만 한다. 값은 설치된 패키지 정보(`pyproject.toml`의 `version`)에서 읽어, 버전을 한 곳에서만 관리한다.

## 3. 언어와 도구

| 항목 | 내용 |
| --- | --- |
| 언어 | Python 3.14 |
| 버전·의존성 관리 | uv |
| 빌드 백엔드 | uv_build |
| 테스트 | pytest (개발 의존성 그룹 `dev`) |

Python 버전은 `.python-version`과 `pyproject.toml`의 `requires-python`(`>=3.14`)에 적는다.

## 4. 스타일

- [PEP 8](https://peps.python.org/pep-0008/)을 따른다. 모듈과 함수는 `snake_case`, 클래스는 `PascalCase`, 상수는 `UPPER_SNAKE_CASE`로 쓴다.
- 공개 함수와 메서드에는 타입 힌트를 단다.
- 문서 포인터는 docstring에 적는다([포인터 규약](Traceability.md)).

## 5. 테스트

- 테스트는 `tests/` 아래에 `test_<대상>.py` 이름으로 둔다.
- 실행 명령은 `uv run pytest`이고, [검증 도구의 설정](VerificationTools.md#11-설정)의 `check.commands`에 등록해 일괄 검사가 함께 실행한다.
- 패키지 골격 테스트는 [test_package](../tests/test_package.py)에 있다. 패키지를 불러올 수 있는지, `__version__`이 설치된 패키지 버전과 같은지 확인한다.
- 외부 서비스(인용 데이터 API 등)를 부르는 코드는 테스트에서 실제 네트워크 호출 대신 고정된 응답으로 대신한다.

## 6. 미결정 사항

아래 항목은 아직 정하지 않았다. 정하면 이 문서에 반영하고 이 목록에서 지운다.

- 웹 프레임워크(예: FastAPI, Streamlit, Flask).
- 데이터 저장 방식(예: SQLite).
- 화면 구성 방식(서버 렌더링 템플릿, 별도 프론트엔드 등).
- 시각화 라이브러리.
