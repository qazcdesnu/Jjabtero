# 문서 인덱스

프로젝트의 모든 문서로 들어가는 진입점이다. 작업을 시작하기 전에 이 문서에서 해당 작업에 필요한 문서를 찾아 읽는다.

모든 문서는 이 인덱스에서 링크를 따라 도달할 수 있어야 한다. 새 문서를 추가하면 반드시 이 인덱스(또는 인덱스에서 도달 가능한 상위 문서)에 링크를 추가한다. 자세한 규칙은 [문서 작업 규칙](DocumentationRule.md)을 따른다.

## 작업별 읽어야 할 문서

### 제품 이해

이 프로젝트가 무엇을 만들고 어떤 구조로 만드는지 이해할 때 읽는다.

| 문서 | 설명 |
| --- | --- |
| [README](../README.md) | 저장소 소개, 설치와 실행 방법 |
| [제품 비전](ProductVision.md) | 목적, 핵심 요구사항, 범위 |
| [시스템 구조](Architecture.md) | 디렉터리 구조, 개발 언어와 스타일, 테스트 방식 |

### 작업 관리

작업을 시작하거나 끝낼 때, 할 일을 계획하거나 이슈를 등록할 때, 커밋하거나 PR을 만들 때 읽는다. 모든 작업은 [로드맵](Roadmap.md) 또는 [이슈](Issue.md)의 ID로 시작한다.

| 문서 | 설명 |
| --- | --- |
| [작업 관리 규칙](TaskRule.md) | 작업 ID(M-T, I, H), 상태 표기(`[ ]`, `[~]`, `[x]`), 작업 흐름, 기록 형식 |
| [로드맵](Roadmap.md) | 마일스톤별 할 일 목록과 상태 (한 줄씩) |
| [진행 중](Ongoing.md) | 진행 중인 작업의 상세 내역 |
| [완료](Done.md) | 끝난 작업의 상세 기록 |
| [이슈](Issue.md) | 작업 중 발생한 문제, 계획과 별도의 사용자 요구사항 |
| [커밋 규칙](CommitRule.md) | 작업 ID 기준 커밋 단위·시점·메시지 형식, `commit-msg` hook |
| [PR 규칙](PullRequestRule.md) | 쌓는 작업 브랜치, 커밋 후 push, PR 제목·본문, 번호 순서 merge commit, CI |

### 상세 설계

구성 요소를 구현하기 전에 읽는다. 구성 요소별 상세 설계 문서는 `docs/design/`에 둔다.

| 문서 | 설명 | 관련 태스크 |
| --- | --- | --- |
| [앱 골격 설계](design/AppSkeleton.md) | 백엔드 앱과 실행 명령, 프론트엔드 API 모듈, 상태 확인 | M1-T8 |
| [서재 데이터 설계](design/Library.md) | 논문 데이터 모델, 데이터베이스 파일과 연결, 마이그레이션, 저장 함수 | M1-T3 |
| [논문 검색과 추가 설계](design/PaperSearch.md) | OpenAlex·arXiv 검색, 검색·추가 API, 검색 화면 | M1-T4, M1-T10 |
| [UI 기반 설계](design/UiLayout.md) | PrimeVue·Tailwind, 테마, 3단 화면 배치 | M1-T10 |
| [서재 화면 설계](design/LibraryView.md) | 서재 목록·삭제 API, 목록 표와 상세 | M1-T5 |
| [서재 필터 설계](design/LibraryFilter.md) | 글자·태그·항목 종류·연도 필터, 사이드바 태그 목록 | M1-T6, M1-T7 |
| [로그인 설계](design/Auth.md) | 구글 로그인으로 본인 계정만 허용, 세션, 막는 범위, 로그인 화면 | M2-T2 |
| [배포 설계](design/Deployment.md) | Render 배포의 주소(jjabtero.qazcde.kr), 공개 범위, 비밀 값, 동의 화면 게시 | M2-T1 |
| [인용 데이터 설계](design/Citations.md) | OpenAlex 조사, 서재 논문의 OpenAlex ID 연결, 피인용을 가져오는 범위(공개 후 1년, 피인용 많은 순 최대 건수), 인용 캐시 파일 | M3-T2 |
| [서재 인용 그래프 설계](design/CitationGraph.md) | 시각화 라이브러리(ECharts), 서재 논문 사이 인용·가까움 그래프 데이터, API, 연도 순·자유 배치 화면 | M3-T7 |
| [인용 양식 설계](design/CitationStyles.md) | 논문 인용 글 여덟 양식(BibTeX, IEEE, ACM, APA, MLA, Chicago, Harvard, Vancouver), 저자 이름 나누기, 복사 창 | I17 |
| [서재 통계 설계](design/LibraryStats.md) | 통계 항목, 다 읽은 시각, OpenAlex 학문·세부 학문, 통계 API, 통계 화면 | M5-T1 |
| [태그 설계](design/Tags.md) | 태그 이름 규칙, 붙이기·떼기·이름 바꾸기·지우기 API, 논문 상세·서재 목록·왼쪽 목록 화면, 태그별 그래프 | M7-T1 |
| [사용자 설정 설계](design/Settings.md) | 앱 안에서 바꾸는 설정 항목, 저장, API와 설정 창 | M3-T2 |
| [PDF 리더 설계](design/Reader.md) | pdf.js 뷰어, PDF 가져오기(공개 PDF, 올리기)와 드라이브 보관, 읽던 위치·하이라이트·영역 메모 데이터, API, 화면 | M4-T1 |
| [AI 대화 설계](design/AiChat.md) | 프로필 창의 Google AI API 키(암호화 저장, 마스터 키)와 Gemini 모델, 리더에서 고른 글로 Gemini와 대화하는 API와 화면 | M8-T1 |
| [PDF 판 설계](design/PdfVersions.md) | 논문마다 여러 PDF 판(arXiv 개정판, 출판판, 올린 파일), 판 찾기, 판마다의 주석·읽던 위치, 판 선택 API와 드롭다운 | I30 |
| [리더 인용 미리보기 설계](design/ReaderCitations.md) | 리더의 인용 표시 찾기, 참고문헌 항목 읽기, 항목 글로 논문 찾기 API, 미리보기 상자와 서재에 담기·새 탭에서 읽기 | M6-T1 |
| [공개 페이지 설계](design/PublicPages.md) | 로그인 없이 여는 앱 소개·개인정보처리방침 페이지, 검색 노출 막기 | M2-T5 |
| [구글 드라이브 동기화 설계](design/DriveSync.md) | OAuth 인증, 드라이브 파일, 동기화·충돌, API, 머리줄 상태 | M1-T9 |
| [읽기 상태와 메모 설계](design/ReadingStatus.md) | 읽기 상태·메모 데이터, 마이그레이션 0002, API, 상세 편집 | M1-T7 |

### 문서 작업

문서를 새로 만들거나 수정할 때 읽는다.

| 문서 | 설명 |
| --- | --- |
| [문서 작업 규칙](DocumentationRule.md) | 문서 작성 형식, 링크·앵커 규칙, 고아 문서 금지, 문서 우선 원칙 |
| [포인터 규약](Traceability.md) | 문서에 코드 포인터를 걸 때의 형식 |
| [자료 폴더 규칙](MaterialRule.md) | 참고 자료 `reference/`와 기존 프로젝트 `legacy/`, 목록 문서 |
| [검증 도구](VerificationTools.md) | 링크·고아 문서·포인터 검사 실행 방법 |

### 코드 작업

코드를 작성하거나 수정할 때 읽는다. 코드 작업 전에는 항상 [문서 작업 규칙](DocumentationRule.md)의 문서 우선 원칙을 먼저 확인한다.

| 문서 | 설명 |
| --- | --- |
| [코드 작업 규칙](CodeRule.md) | 문서 우선 작업 절차, 디렉터리 구조, 스타일, 테스트, 완료 조건 |
| [포인터 규약](Traceability.md) | 문서 ↔ 코드 양방향 포인터(구문 트리 심볼 포인터, `@doc:` 포인터, 언어별 심볼 규칙) 규칙 |
| [검증 도구](VerificationTools.md) | 검사기가 무엇을 검사하는지, 실행 방법, 자동 실행 장치, 설정 |
