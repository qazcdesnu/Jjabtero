# 완료

이 문서는 끝난 작업의 상세 기록이다. 최신 기록이 맨 위에 온다. 기록 형식은 [작업 관리 규칙](TaskRule.md#5-기록-형식)을 따르며, 할 일 목록은 [로드맵](Roadmap.md)과 [이슈](Issue.md)에 있다. 닫힌 마일스톤의 기록은 [작업 관리 규칙](TaskRule.md#47-완료-기록-보관)에 따라 보관 문서로 옮긴다. 보관 문서: [M0 시작](Done-M0.md). 전체 문서 목록은 [문서 인덱스](index.md)에서 확인한다.

## M1-T4 논문 추가 방법 결정과 구현

- 시작일: 2026-11-01
- 완료일: 2026-11-01
- 근거 문서: [제품 비전](ProductVision.md#5-미결정-사항), [서재 데이터 설계](design/Library.md)

### 계획
- 논문을 서재에 넣는 방법을 사용자와 정한다.
- 상세 설계 문서를 쓰고, 백엔드 앱에 데이터베이스를 연결한다.
- 논문 추가 API와 화면을 구현하고 테스트한다.
- 제품 비전의 미결정 사항과 README를 맞춘다.

### 진행 기록
- 2026-11-01: 작업을 시작했다. PR #9(M1-T3)가 병합되지 않아 `m1-t3-paper-model` 위에 작업 브랜치를 만들었다.
- 2026-11-01: 추가 방법으로 DOI 자동 채우기, 직접 입력, BibTeX 가져오기, Zotero 가져오기를 제시했다. 사용자는 논문 검색 기능을 원했다. arXiv, Google Scholar 같은 주요 논문 검색 사이트의 API를 쓰고 웹 검색을 보조로 해서, 검색된 논문을 보고 골라 넣는 방식이다. DOI로 서지 정보를 받는 API는 OpenAlex를 골랐다.
- 2026-11-01: 사용자 지시로 ProjInit 0.1.7 업그레이드(I7)를 먼저 처리했다. `projinit upgrade`가 커밋하지 않은 변경을 거부해 이 기록을 잠시 stash에 두고, `m1-t3-paper-model` 위에 I7 브랜치를 만들었다. 이 작업 브랜치는 커밋이 없어 지우고 I7 브랜치 위에 다시 만들었다.

- 2026-11-01: Google Scholar는 공식 API가 없고 수집은 약관 위반이라 빼고, OpenAlex와 arXiv로 검색하며 보조 웹 검색은 미결정으로 두자고 제안했다. 사용자가 권장대로 하라고 했다.
- 2026-11-01: OpenAlex를 확인했다. 키 없이 응답하지만 IP마다 하루 예산($0.10)을 나눠 쓴다는 안내가 응답에 있다. 무료 키는 하루 $1이고 검색 한 번은 $0.001이다. arXiv는 키가 필요 없고, 응답에 학술지 DOI가 없으면 `10.48550/arXiv.<번호>` DOI를 만들 수 있다.
- 2026-11-01: 논문 검색과 추가 설계를 쓰고 인덱스에 링크했다. 제품 비전의 추가 방법과 미결정 사항, 시스템 구조의 도구, 앱 골격 설계의 `create_app` 설명을 맞췄다. httpx2를 개발 의존성에서 실행 의존성으로 옮겼다.
- 2026-11-01: 실제 검색에서 두 문제를 찾았다. OpenAlex는 학회 논문에 `conference-paper` 종류를 바로 주어 대응을 더했다. arXiv는 `is` 같은 불용어를 `AND`로 이으면 결과가 0건이어서(`all:is` 단독 26건) Lucene 영어 불용어를 빼도록 하고 설계에 적었다.
- 2026-11-01: `search` 모듈, `papers_api` 모듈, 앱의 데이터베이스·HTTP 클라이언트 연결, 검색 화면(`SearchPanel.vue`)과 API 함수를 구현했다. 기존 `test_app`, `test_cli`가 실제 사용자 데이터 폴더에 데이터베이스를 만들지 않도록 임시 경로를 쓰게 고쳤다. 테스트 모듈끼리 가져오기가 안 되어 가짜 응답을 `tests/fakes.py`로 옮겼다.
- 2026-11-01: 포인터 검사기가 `PaperSearch.md`의 `PaperData`, `default_db_path`, `upgrade_database` 링크에 역방향 포인터가 없다고 알렸다. 이 문서는 그 심볼을 규정하지 않고 참조만 하므로, 코드 포인터를 서재 데이터 설계 절 링크로 바꿨다.
- 2026-11-01: 실제 서버를 임시 데이터베이스로 띄워 OpenAlex·arXiv 검색(오류 없음), 추가(201), 같은 논문 다시 추가(409), 다시 검색했을 때 `library_paper_id` 표시를 확인했다.

### 결정 사항
- 없음
- 위 "없음"은 시작할 때 적은 줄이다. 아래 결정을 작업 중에 내렸고, 근거 문서로 [논문 검색과 추가 설계](design/PaperSearch.md)를 새로 썼다.
- 검색원은 OpenAlex와 arXiv다. Google Scholar는 빼고 보조 웹 검색은 미결정으로 둔다. 사용자가 권장안을 골랐다.
- OpenAlex 키는 선택 환경 변수 `OPENALEX_API_KEY`로 받는다. 키 없이도 동작해야 처음 쓰기 쉽기 때문이다.
- 검색원이 여럿이면 OpenAlex를 먼저 두고 DOI가 겹치는 뒤 결과를 뺀다. OpenAlex 서지 정보가 더 풍부하기 때문이다.
- 검색원 하나가 실패해도 다른 결과는 보여 준다. 외부 서비스 하나의 장애로 검색 전체가 막히지 않게 하기 위해서다.
- 검색 결과는 서재에 넣기 전에는 저장하지 않는다. 넣을 때 태그를 함께 붙일 수 있다.
- 직접 입력, BibTeX, Zotero 가져오기는 이번에 만들지 않고 제품 비전의 미결정 사항으로 남긴다.

### 변경 파일
- `docs/design/PaperSearch.md`
- `docs/design/AppSkeleton.md`
- `docs/design/Library.md`
- `docs/ProductVision.md`
- `docs/Architecture.md`
- `docs/index.md`
- `README.md`
- `pyproject.toml`
- `uv.lock`
- `src/jjabtero/search.py`
- `src/jjabtero/papers_api.py`
- `src/jjabtero/app.py`
- `tests/fakes.py`
- `tests/test_search.py`
- `tests/test_papers_api.py`
- `tests/test_app.py`
- `tests/test_cli.py`
- `frontend/src/api.ts`
- `frontend/src/api.test.ts`
- `frontend/src/SearchPanel.vue`
- `frontend/src/App.vue`
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`

### 결과
- 첫 화면에서 OpenAlex와 arXiv를 검색하고, 결과를 보고 골라 태그와 함께 서재에 넣을 수 있다. 이미 서재에 있는 논문은 "서재에 있음"으로 보인다.
- 백엔드 앱이 데이터베이스에 연결되어, 앱을 띄우면 서재 스키마가 올라간다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.1.7 projinit check`: 모든 검사기, `uv run pytest`(테스트 51개), 프론트엔드 `npm test`(테스트 8개) 통과.
- `npm run build`: 타입 검사와 빌드 통과.
- 실제 서버와 실제 외부 API로 한 확인은 진행 기록에 적었다.

## I8 Render 배포 마일스톤 계획

- 시작일: 2026-11-01
- 완료일: 2026-11-01
- 근거 문서: [제품 비전](ProductVision.md#4-범위), [시스템 구조](Architecture.md#1-실행-형태)

### 계획
- Render 무료 플랜으로 배포할 수 있는지 리소스와 제약을 확인해 사용자에게 알린다.
- 사용자가 정한 시점에 맞춰 배포 마일스톤을 로드맵에 넣고 제품 비전과 시스템 구조를 맞춘다.

### 진행 기록
- 2026-11-01: 사용자가 Render 무료 플랜 배포 가능 여부와 리소스 사용량 확인을 요청했다.
- 2026-11-01: 프론트엔드를 빌드하고 서버를 띄워 측정했다. 서버 메모리는 약 57MB(요청 400번 뒤에도 같음), 빌드된 화면은 80KB였다. Render 문서상 무료 웹 서비스는 512MB RAM, 0.1 CPU, 15분 유휴 뒤 정지, 영구 디스크 없음(재배포·재시작 때 파일 삭제)이다.
- 2026-11-01: 리소스는 충분하지만 서재 파일이 지워지는 점, 로그인이 없는 점, 깨어나는 지연, 서버용 OAuth 설정, Python과 Node 빌드 환경을 문제로 알렸다.
- 2026-11-01: 사용자는 지금 배포하지 않고, 기본 기능을 쓸 수 있게 된 뒤 배포하도록 적당한 마일스톤을 정해 로드맵에 넣으라고 했다. M1 다음에 M2 Render 배포를 두고 태스크 4개를 적었다. 제품 비전의 범위와 시스템 구조의 실행 형태·미결정 사항을 고쳤다.

### 결정 사항
- Render 배포는 M2로 둔다. M1이 끝나면 논문 추가, 목록, 검색·필터, 읽기 상태·메모, 구글 드라이브 동기화를 쓸 수 있어 "기본 기능을 사용할 수 있을 때"에 맞는다.
- 배포 환경에서는 구글 드라이브 사본을 서재의 원본으로 삼는다. 무료 플랜의 파일 시스템이 지워지기 때문이다. 그래서 M1-T9 동기화를 서버에서도 쓸 수 있게 설계하도록 시스템 구조에 적었다.
- 로그인은 배포한 앱을 본인만 쓰게 하는 용도로만 범위에 넣는다. 여러 사용자와 회원 가입은 계속 제외한다.

### 변경 파일
- `docs/Roadmap.md`
- `docs/ProductVision.md`
- `docs/Architecture.md`
- `docs/Issue.md`
- `docs/Done.md`

### 결과
- 로드맵에 M2 Render 배포가 생겼고, 배포를 위해 M1에서 미리 고려할 점(드라이브 사본을 원본으로)이 시스템 구조에 적혔다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.1.7 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.

## M1-T3 논문 서지 정보 데이터 모델과 저장 구현

- 시작일: 2026-11-01
- 완료일: 2026-11-01
- 근거 문서: [시스템 구조](Architecture.md), [제품 비전](ProductVision.md#3-핵심-요구사항), [서재 데이터 설계](design/Library.md)

### 계획
- 저장할 서지 정보 항목, 데이터베이스 파일 위치, 스키마 변경 방식을 사용자와 정한다.
- 상세 설계 문서를 쓰고 인덱스에서 링크한다.
- 목업을 만든 뒤 SQLAlchemy 모델, 데이터베이스 연결, 논문 저장·조회·수정·삭제 함수를 구현하고 테스트한다.
- 시스템 구조의 미결정 사항과 README를 맞춘다.

### 진행 기록
- 2026-11-01: 작업을 시작했다. PR #8까지 병합되어 최신 `main`에서 작업 브랜치를 만들었다.
- 2026-11-01: 저장 항목, 데이터베이스 위치, 스키마 변경 방식을 물었다. 사용자는 연도·게재처·DOI·URL, 항목 종류, 태그(선택)를 골랐다. 초록은 고르지 않았다. 스키마 변경은 Alembic을 골랐다.
- 2026-11-01: 데이터베이스 위치로 사용자는 구글 드라이브 `Jjabtero` 폴더 연동을 원했다. 이 Mac에는 Google Drive 데스크톱 앱이 없다(`~/Library/CloudStorage`에 OneDrive만 있음). Drive API 동기화와 데스크톱 앱 동기화 폴더를 비교해 제시했고, 사용자는 Drive API 동기화를 별도 태스크로 하는 것을 골랐다. 로드맵에 M1-T9를 추가했다.
- 2026-11-01: 제품 비전의 범위 제외 항목에 "클라우드 동기화"가 있어 결정과 어긋났다. 핵심 요구사항에 구글 드라이브 보관을 더하고 제외 항목을 고쳤다. 저장 항목도 제품 비전에 적었다.
- 2026-11-01: 서재 데이터 설계를 쓰고 인덱스에 링크했다. 시스템 구조에 마이그레이션 디렉터리, `alembic.ini`, Alembic, platformdirs를 더하고 미결정 사항을 갱신했다.
- 2026-11-01: SQLAlchemy, Alembic, platformdirs를 추가하고 모델, 연결, 마이그레이션 환경과 첫 리비전 0001, 저장 함수를 구현했다. 임시 데이터베이스에서 `alembic upgrade head` 뒤 `alembic check`가 "No new upgrade operations detected"를 내어, 모델과 마이그레이션이 일치함을 확인했다.
- 2026-11-01: 테스트 `test_db.py`, `test_library.py`를 더해 백엔드 테스트 36개가 통과했다. README에 서재 데이터 위치를 적었다.

### 결정 사항
- 저장 항목은 제목, 저자(순서 있음), 연도, 게재처, DOI, URL, 항목 종류, 태그(선택)다. 사용자가 골랐다. [서재 데이터 설계](design/Library.md#1-데이터-모델)에 적었다.
- 저자와 태그는 별도 테이블로 두고 이름이 같으면 공유한다. 저자별 통계와 인용 연결, 태그 필터에서 같은 저자·태그를 하나로 다루기 위해서다.
- 항목 종류는 8가지(`journal-article`, `conference-paper`, `preprint`, `book`, `book-chapter`, `thesis`, `report`, `other`)로 하고 기본값은 `other`다.
- DOI는 정규화해 저장하고 겹치지 않게 한다. 같은 논문을 두 번 넣는 것을 막고, 인용 데이터 조회의 열쇠로 쓰기 위해서다.
- 서재는 구글 드라이브 `Jjabtero` 폴더에 Drive API로 동기화한다. 사용자가 골랐다. 구현은 M1-T9로 나눴다.
- 데이터베이스 파일은 동기화의 로컬 작업 사본으로, 기본 위치는 운영체제의 사용자 데이터 폴더이고 `JJABTERO_DB`로 바꿀 수 있다. Drive API 방식에서는 로컬 사본이 필요하고, 저장소 안에 두면 저장소와 함께 지워질 수 있기 때문이다.
- 스키마 변경은 Alembic으로 한다. 사용자가 골랐다. 마이그레이션은 패키지 안에 둬서 설치된 패키지에서도 `upgrade_database`가 찾게 한다.
- 백엔드 앱에 데이터베이스를 연결하는 일은 API를 처음 만드는 태스크로 미룬다.

### 변경 파일
- `docs/design/Library.md`
- `docs/ProductVision.md`
- `docs/Architecture.md`
- `docs/index.md`
- `README.md`
- `alembic.ini`
- `pyproject.toml`
- `uv.lock`
- `src/jjabtero/models.py`
- `src/jjabtero/db.py`
- `src/jjabtero/library.py`
- `src/jjabtero/migrations/env.py`
- `src/jjabtero/migrations/script.py.mako`
- `src/jjabtero/migrations/versions/0001_create_library.py`
- `tests/test_db.py`
- `tests/test_library.py`
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`

### 결과
- 논문 서지 정보를 SQLite에 저장·조회·수정·삭제하는 함수가 생겼다. 스키마는 Alembic 마이그레이션으로 만들고 바꾼다.
- 데이터베이스 위치는 사용자 데이터 폴더이며 환경 변수로 바꿀 수 있다. 구글 드라이브 동기화는 M1-T9에서 이 파일에 더한다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.1.5 projinit check`: 모든 검사기, `uv run pytest`(테스트 36개), 프론트엔드 `npm test` 통과.
- 임시 데이터베이스에서 `uv run alembic upgrade head`와 `uv run alembic check` 통과.

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
