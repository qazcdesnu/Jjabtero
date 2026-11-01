# Jjabtero

데이터사이언스 대학원생 한 명을 위한 개인 서지관리 앱이다. Zotero를 대체하는 것을 목표로, 내 컴퓨터에서 로컬 웹 앱으로 실행한다. 논문 검색과 필터, 읽기 상태와 메모 관리, 인용 관계로 논문을 연결하고 추천하는 기능, 서재 통계와 시각화 기능을 만든다.

아직 개발 초기 단계다. 지금은 OpenAlex와 arXiv에서 논문을 검색해 서재에 넣고, 서재 목록에서 정렬해 보고, 글자·태그·종류·읽기 상태·연도로 걸러 보고, 논문마다 읽기 상태와 메모를 남기고, 지울 수 있다. 서재를 구글 드라이브 `Jjabtero` 폴더와 동기화할 수 있다.

## 문서

- [제품 비전](docs/ProductVision.md): 목적, 핵심 요구사항, 범위.
- [시스템 구조](docs/Architecture.md): 디렉터리 구조, 언어와 도구, 테스트 방식.
- [로드맵](docs/Roadmap.md): 할 일과 진행 상태.
- [문서 인덱스](docs/index.md): 모든 문서의 목록.

## 설치와 실행

백엔드는 Python 3.14와 [uv](https://docs.astral.sh/uv/)를, 프론트엔드는 [Node.js](https://nodejs.org/)와 npm을 쓴다. uv와 Node.js가 없으면 먼저 설치한다. Python 3.14는 uv가 필요할 때 자동으로 받는다.

**설치**

```sh
uv sync                        # 백엔드 가상 환경과 의존성
npm --prefix frontend install  # 프론트엔드 의존성
```

**쓰기**: 화면을 빌드한 뒤 서버 하나를 띄우고 브라우저에서 http://127.0.0.1:8000 을 연다.

```sh
npm --prefix frontend run build
uv run jjabtero                # --host, --port로 주소를 바꿀 수 있다
```

**개발하기**: 터미널 두 개에서 백엔드와 프론트엔드 개발 서버를 띄우고, Vite가 알려 주는 주소(기본 http://localhost:5173 )를 연다. 코드를 고치면 화면이 바로 바뀐다.

```sh
uv run jjabtero                # 터미널 1: 백엔드
npm --prefix frontend run dev  # 터미널 2: 프론트엔드
```

**서재 데이터**: 서재는 SQLite 파일 하나에 저장한다. 기본 위치는 운영체제의 사용자 데이터 폴더이며(macOS: `~/Library/Application Support/Jjabtero/library.db`), 환경 변수 `JJABTERO_DB`로 바꿀 수 있다. 구글 드라이브 동기화는 아직 없다.

**논문 검색**: 첫 화면에서 OpenAlex와 arXiv를 검색하고, 결과를 골라 "서재에 추가"를 누른다. OpenAlex는 키 없이도 쓰지만 하루 사용량이 같은 IP 안에서 나뉜다. [OpenAlex 설정](https://openalex.org/settings/api)에서 무료 키를 받아 환경 변수 `OPENALEX_API_KEY`에 넣으면 사용량이 늘어난다.

**구글 드라이브 동기화**: 본인의 Google Cloud 프로젝트에서 Drive API를 켜고 웹 애플리케이션 OAuth 클라이언트(리디렉션 URI `http://127.0.0.1:8000/api/drive/callback`, 범위 `drive.file`)를 만든 뒤, 받은 JSON을 사용자 데이터 폴더의 `google_client_secret.json`(macOS: `~/Library/Application Support/Jjabtero/`)으로 둔다. 저장소 안에는 두지 않는다. 앱 오른쪽 위 "드라이브 연결"을 누르면 연결되고, 그 뒤로는 앱을 띄울 때와 서재를 고친 뒤 자동으로 동기화한다. 자세한 동작은 [구글 드라이브 동기화 설계](docs/design/DriveSync.md)에 있다.

**테스트**

```sh
uv run pytest                  # 백엔드
npm --prefix frontend test     # 프론트엔드
```
