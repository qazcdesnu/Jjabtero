# 완료

이 문서는 끝난 작업의 상세 기록이다. 최신 기록이 맨 위에 온다. 기록 형식은 [작업 관리 규칙](TaskRule.md#5-기록-형식)을 따르며, 할 일 목록은 [로드맵](Roadmap.md)과 [이슈](Issue.md)에 있다. 닫힌 마일스톤의 기록은 [작업 관리 규칙](TaskRule.md#47-완료-기록-보관)에 따라 보관 문서로 옮긴다. 보관 문서: [M0 시작](Done-M0.md), [M1 기본 서재](Done-M1.md), [M2 Render 배포](Done-M2.md), [M4 PDF 리더](Done-M4.md), [M3 인용 기반 연결·추천](Done-M3.md). 전체 문서 목록은 [문서 인덱스](index.md)에서 확인한다.

## I21 드라이브 동기화에서 양쪽이 모두 바뀌었을 때 겹치지 않는 변경을 자동으로 합치기

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [구글 드라이브 동기화 설계](design/DriveSync.md#5-동기화)
- 참고 자료: 없음

### 계획
- 마지막으로 맞춘 서재를 기준 사본으로 남긴다.
- 기준·이쪽·드라이브 세 사본으로 표·행·칸 단위 3방향 합치기를 하는 순수 함수를 만든다(새 행의 ID 겹침과 연결 행 바꾸기, 같은 이름·DOI 잇기, 수정 시각으로 같은 칸 고르기).
- 동기화에서 둘 다 바뀌었을 때 먼저 합치기를 시도하고, 못 합치면 지금처럼 충돌로 둔다.
- 테스트를 더하고 두 앱이 드라이브 하나를 함께 쓰는 상황으로 확인한다.

### 진행 기록
- 2026-11-15: H2와 함께 사용자가 진행하라고 했다. 병합되지 않은 가장 최근 브랜치 `h2-drive-sync-freshness`에서 작업 브랜치를 만들었다.

- 2026-11-15: 합치기 함수(`drive_merge`)와 테스트 8개를 만들었다. 행을 쓸 때 `INSERT OR REPLACE`를 쓰면 SQLite가 기존 행을 지웠다 넣어 외래 키의 연쇄 삭제로 자식 행(저자 연결, 태그, PDF, 주석)까지 지우므로, 있는 행은 UPDATE, 없는 행만 INSERT하게 했다.
- 2026-11-15: 작업 중에 사용자가 리더 인용 미리보기가 참고문헌("Darwin godel machine: Openended evolution …, URL https://arxiv.org/abs/2505.22954")을 찾지 못했다고 알렸다. 원인을 확인해 H3로 등록했다. 줄바꿈 하이픈이 붙어 "Openended"가 되어 제목 낱말 비율이 0.8로 기준에 못 미쳤고, 검색어도 틀어졌으며, 항목 글의 arXiv 주소를 쓰지 않았다. 사용자가 이 작업을 이어서 하라고 해 I21을 마친 뒤 H3을 한다.
- 2026-11-15: 기준 사본(`drive_sync_base.db`)과 `DriveSync._merge_or_conflict`로 동기화에 합치기를 붙였다. "양쪽 다 바뀌면 충돌"을 전제로 한 테스트 다섯 개는 합칠 수 없는 변경(같은 설정을 다른 값으로)으로 충돌을 만들게 바꾸었다. 예전 동작을 보여 주던 테스트(상태를 이어받지 않은 스키마 올리기)는 이제 합쳐지는 것을 확인한다.
- 2026-11-15: 깨진 드라이브 사본으로 합치면 SQLAlchemy 오류가 그대로 올라가는 것을 테스트에서 찾아, 합치기 함수 안의 데이터베이스 오류를 모두 "합칠 수 없음"(충돌)으로 바꿨다. "올리기 직전에 드라이브가 바뀜" 테스트는 파일 끝에 쓰레기 바이트를 붙여 흉내 냈는데 SQLite가 그것을 무시해, 다른 컴퓨터가 그 순간 실제로 올리는 상황으로 바꿨다.
- 2026-11-15: 원인 분석 때 충돌을 재현했던 상황(서버가 논문을 담은 직후 이 컴퓨터가 드라이브를 다시 보지 않고 읽던 위치 저장)이 합쳐져, 두 앱 모두 논문 둘과 읽던 위치를 갖는 것을 앱 수준 테스트로 확인했다. 전체 테스트를 3번 연속 돌려 모두 통과했다.

### 결정 사항
- 3방향 합치기의 기준으로 마지막에 맞춘 사본을 파일로 남긴다. 기준 없이는 "한쪽이 넣은 것"과 "다른 쪽이 지운 것"을 가를 수 없기 때문이다.
- 드라이브 사본에서 출발해 이쪽 변경만 적용한다. 드라이브 쪽 변경을 따로 적용하지 않아도 되어 단순하다.
- 같은 칸을 양쪽이 다르게 고쳤으면 수정 시각이 늦은 쪽을 쓴다. 시각이 없는 설정만 충돌로 둔다. 설정은 드물게 바뀌고 어느 쪽이 맞는지 사용자가 정하는 게 낫기 때문이다.
- 지우기와 고치기가 겹치면 고친 쪽을 남긴다(드라이브가 고쳤으면 남기고, 이쪽이 고친 행을 드라이브가 지웠으면 충돌). 데이터를 잃는 쪽을 피하기 위해서다.
- 합치기 전 양쪽 사본을 백업하되 가장 최근 20개만 남긴다. 합치기가 잦을 수 있어 백업 폴더가 끝없이 커지지 않게 하기 위해서다.

### 변경 파일
- `docs/Issue.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/design/DriveSync.md`
- `src/jjabtero/drive_merge.py`
- `src/jjabtero/drive_sync.py`
- `tests/test_drive_merge.py`
- `tests/test_drive_sync.py`
- `tests/test_drive_api.py`

### 결과
- 이 컴퓨터와 드라이브가 둘 다 바뀌어도 겹치지 않는 변경(서로 다른 논문 추가, 다른 칸 수정, 읽던 위치, 주석 등)은 자동으로 합쳐 충돌이 나지 않는다. 같은 칸을 양쪽이 고치면 늦게 고친 쪽을 쓴다. 합칠 수 없을 때만 지금처럼 충돌로 남고 그 까닭을 보여 준다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- 합치기 규칙 8개, 동기화 합치기 7개, 앱 수준 1개 테스트를 더했고 전체 테스트를 3번 연속 통과했다.

## H2 드라이브 동기화가 자주 충돌함: 스키마 올리기를 로컬 변경으로 셈, 드라이브 변경을 앱 시작 때만 받아 옴

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [구글 드라이브 동기화 설계](design/DriveSync.md#5-동기화)
- 참고 자료: 없음

### 계획
- 앱 시작 때 스키마를 올리기 전 서재가 마지막 동기화 때와 같으면, 올린 뒤의 해시를 동기화 상태로 이어받는다.
- 드라이브 파일 정보를 1분마다 확인해 드라이브만 바뀌었으면 받아 온다. 화면이 다시 보일 때도 확인한다.
- 쓰기 요청 전에 마지막 확인이 30초보다 오래되었으면 드라이브를 먼저 확인한다.
- 테스트를 더하고 두 앱이 드라이브 하나를 함께 쓰는 상황으로 확인한다.

### 진행 기록
- 2026-11-15: 사용자가 드라이브와 컴퓨터의 동기화가 자주 깨진다며 원인을 물었다. 이 컴퓨터의 마지막 동기화 성공은 11월 1일이었고, 11월 13일 드라이브 재연결 뒤에도 상태 파일이 바뀌지 않았으며 충돌 백업도 없었다.
- 2026-11-15: 원인 두 가지를 재현했다. ① 이 컴퓨터 서재 사본(스키마 0002)의 내용 해시는 저장된 해시와 같았지만, 스키마를 0007로 올리자 달라져 "로컬이 바뀜"이 되었다. 서버 쪽도 바뀌었으므로 충돌이다. ② 가짜 드라이브를 함께 쓰는 두 앱에서, 서버가 논문을 담아 올린 뒤 이 컴퓨터가 드라이브를 확인하지 않은 채 읽던 위치만 저장해도 충돌이 났다. 드라이브 변경은 앱 시작, 이쪽의 쓰기 뒤, "지금 동기화" 때만 확인했다.
- 2026-11-15: 사용자가 해결책 1~3을 이슈 하나(H2)로, 자동 합치기를 다른 이슈(I21)로 진행하라고 했다. 병합되지 않은 가장 최근 브랜치 `i20-search-modes`에서 작업 브랜치를 만들었다.
- 2026-11-15: `upgrade_keeping_sync`, `DriveSync.check`·`ensure_fresh`·확인 스레드, 쓰기 앞 미들웨어, `POST /api/drive/check`, 화면이 다시 보일 때의 확인을 만들었다.
- 2026-11-15: 테스트로 확인했다. 옛 스키마(0002) 서재가 새 버전으로 켜질 때 드라이브 변경을 받았고(이전 동작은 충돌), 원인 재현에 썼던 상황(서버가 논문을 담은 뒤 이 컴퓨터가 API로 읽던 위치 저장)도 충돌 없이 끝났다. 이 컴퓨터 서재의 사본으로도 상태를 이어받는 것을 확인했다(원본과 실제 드라이브는 건드리지 않았다).
- 2026-11-15: 전체 테스트에서 앱 수준 테스트가 가끔 실패했다. 앱을 만들 때 백그라운드 첫 동기화가 사본을 올리는 사이 논문이 들어오면, 올린 뒤의 서재로 해시를 계산해 그 논문을 "올렸음"으로 적고 다시 올리지 않았다. 실제로도 생길 수 있는 문제라 해시를 올리거나 받은 사본에서 계산하게 고치고 회귀 테스트를 더했다. 그 뒤 전체 테스트를 5번 연속 돌려 모두 통과했다.

### 결정 사항
- 드라이브 확인은 파일 정보(`checksum`)만 읽는다. 드라이브가 그대로면 내용 해시도 계산하지 않아 1분마다 해도 가볍다.
- 쓰기 앞의 확인은 30초에 한 번까지만 한다. 읽던 위치 저장처럼 잦은 쓰기마다 드라이브를 부르지 않기 위해서다. 그 사이의 거의 동시 쓰기는 I21의 자동 합치기가 맡는다.
- 확인은 이쪽 변경을 올리지 않는다. 올리기는 지금처럼 쓰기 5초 뒤 자동 올리기가 한다.
- 상태 파일의 로컬 해시는 올리거나 받은 사본에서 계산한다. 올리는 도중의 쓰기를 잃지 않기 위해서다. 받은 사본은 덮어쓰기 전에 사본에서 스키마를 올려, 적는 해시와 덮어쓴 서재가 같게 한다.

### 변경 파일
- `docs/Issue.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/design/DriveSync.md`
- `src/jjabtero/drive_sync.py`
- `src/jjabtero/drive_api.py`
- `src/jjabtero/app.py`
- `tests/test_drive_sync.py`
- `tests/test_drive_api.py`
- `tests/conftest.py`
- `frontend/src/api.ts`
- `frontend/src/driveState.ts`
- `frontend/src/driveState.test.ts`

### 결과
- 새 버전 앱이 스키마를 올려도 충돌하지 않고 드라이브 변경을 받는다. 다른 곳(서버, 다른 컴퓨터)이 올린 변경을 1분마다, 쓰기 전에, 앱 창으로 돌아올 때 받아 와, 두 곳을 함께 켜 두어도 충돌이 크게 줄어든다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 이 컴퓨터 서재 사본에 `upgrade_keeping_sync`를 적용해 스키마 0007로 올라가고 동기화에서는 바뀌지 않음으로 세는 것을 확인했다.

## I20 검색에서 제목이 많이 일치하는 결과를 위로 올리고, 일반·제목·저자 검색 옵션 두기

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [논문 검색과 추가 설계](design/PaperSearch.md)
- 참고 자료: 없음

### 계획
- 사용자가 알려 준 검색("a self-improving coding agent")이 왜 원하는 논문(Robeyns, Szummer, Aitchison)을 놓치는지 확인한다.
- 검색원들의 결과를 검색어와의 일치도로 다시 정렬한다.
- 일반·제목·저자 검색 옵션을 API와 화면에 더하고, 검색원마다 맞는 질의로 바꾼다.
- 테스트를 더하고 실제 검색으로 확인한다.

### 진행 기록
- 2026-11-15: 사용자가 요청했다. 병합되지 않은 가장 최근 브랜치 `i19-citation-copy-modes`에서 작업 브랜치를 만들었다.
- 2026-11-15: 같은 검색어로 확인했다. arXiv는 그 논문을 2번째로 주었고, OpenAlex는 상위 20개에 없었다. OpenAlex에는 그 논문이 있었지만(`W6948264221`) 일반 검색, `title.search`, `raw_author_name.search` 어느 것으로도 나오지 않았다. 앱은 OpenAlex 결과 뒤에 arXiv 결과를 이어 붙이므로 그 논문이 12번째쯤에 묻혔다. arXiv는 `ti:`와 `au:` 검색으로도 정확히 찾았다.
- 2026-11-15: 검색 방식(일반·제목·저자)과 맞는 정도로 다시 정렬하기를 백엔드에 더했다. 실제 검색으로 확인했다. 일반·제목 검색 모두 그 논문이 1번째로 왔고, 저자 이름만 일반 검색에 넣어도 1번째였다. 저자 검색("Robeyns, Aitchison")은 같은 점수가 많아 같은 점수끼리 최신 논문을 앞에 두게 했고, 그 논문은 3번째였다.
- 2026-11-15: 검색 화면에 일반·제목·저자 단추를 두고 안내 글을 방식에 맞췄다. 브라우저에서 같은 검색어로 그 논문이 첫 줄에 나오는 것을 확인했다.

### 결정 사항
- 두 방법을 함께 한다. 일치도 정렬은 모든 검색에서 원하는 논문을 앞으로 올리고, 검색 방식은 원하는 것을 좁혀 찾게 한다.
- 정렬은 서버에서 한다. 검색원들의 결과를 합치는 곳이 서버이고, 같은 규칙을 화면과 테스트에서 한 번에 확인할 수 있기 때문이다.
- OpenAlex가 그 논문을 검색으로 돌려주지 않는 것은 OpenAlex 쪽 색인 문제로 보고 따로 고치지 않는다. arXiv가 찾고, 정렬로 앞에 오기 때문이다.

### 변경 파일
- `docs/Issue.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/design/PaperSearch.md`
- `src/jjabtero/search.py`
- `src/jjabtero/papers_api.py`
- `src/jjabtero/titles.py`
- `tests/test_search.py`
- `tests/test_papers_api.py`
- `frontend/src/api.ts`
- `frontend/src/api.test.ts`
- `frontend/src/searchState.ts`
- `frontend/src/searchState.test.ts`
- `frontend/src/SearchView.vue`

### 결과
- 검색 결과가 검색어와 맞는 정도로 정렬되어 제목이 같은 논문이 맨 위에 온다. 검색창 옆에서 일반·제목·저자 검색을 고른다. 저자는 쉼표로 여럿을 넣는다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 실제 OpenAlex·arXiv로 세 방식을 검색하고, 브라우저에서 일반·저자 검색을 확인했다. 브라우저 콘솔 오류는 없었다.

## I19 인용 양식 복사를 문서용(워드·구글 문서)과 LaTeX용 두 모드로 나누기

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [인용 양식 설계](design/CitationStyles.md#5-복사)
- 참고 자료: 없음

### 계획
- 양식마다 LaTeX 글을 함께 만든다(특수 문자 이스케이프, 기울임, 따옴표, 주소).
- 인용 창에 복사 모드 두 가지를 두고, 고른 모드를 기억한다.
- 테스트를 더하고 브라우저에서 확인한다.

### 진행 기록
- 2026-11-15: I17(PR #48)을 올린 뒤 사용자가 복사 모드를 워드·구글 문서용과 LaTeX용 두 가지로 나눠 달라고 했다. 병합되지 않은 가장 최근 브랜치 `i17-citation-styles`에서 작업 브랜치를 만들었다.
- 2026-11-15: 글 조각에 주소(`url`)와 따옴표(`quote`) 종류를 더해, 한 번에 일반 글, HTML, LaTeX를 만들게 했다. IEEE의 쉼표 위치를 조각 수로 정하던 것을 게재처가 있는지로 정하게 고쳤다.
- 2026-11-15: 시연 서버에서 브라우저로 확인했다. LaTeX 모드에서 APA는 `\& … \textit{…} … \url{…}`, IEEE는 ``` ``…,'' ```로 복사되었고, 창을 다시 열어도 LaTeX 모드가 남아 있었다. 문서용으로 바꾸자 기울임 HTML이 함께 복사되었다.

### 결정 사항
- 주소는 `\url{}`로 쓴다. DOI 주소의 `_` 같은 문자를 이스케이프하지 않아도 되고, CS 논문은 거의 `url`이나 `hyperref`를 쓰기 때문이다.
- 악센트 글자는 LaTeX 명령으로 바꾸지 않고 UTF-8 그대로 둔다. 요즘 LaTeX는 UTF-8을 기본으로 읽기 때문이다.
- 고른 모드는 브라우저 `localStorage`에 기억한다. 사람마다 쓰는 곳이 대개 정해져 있어 매번 고르지 않게 하기 위해서다. 기억하지 못해도 복사에는 지장이 없다.

### 변경 파일
- `docs/Issue.md`
- `docs/Done.md`
- `docs/design/CitationStyles.md`
- `frontend/src/citationStyles.ts`
- `frontend/src/citationStyles.test.ts`
- `frontend/src/CiteDialog.vue`

### 결과
- 인용 창에서 "문서용(워드·구글 문서)"과 "LaTeX" 가운데 하나를 고른다. 문서용은 기울임이 남는 서식 있는 글로, LaTeX는 `\textit`·`\url`과 이스케이프가 된 LaTeX 글로 복사한다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 시연 서버에서 두 모드의 미리보기, 복사된 클립보드 내용, 모드 기억을 브라우저로 확인했다. 브라우저 콘솔 오류는 없었다.

## I17 논문 인용 양식(CS에서 자주 쓰는 5~10가지)을 골라 복사하기

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [인용 양식 설계](design/CitationStyles.md)
- 참고 자료: 없음

### 계획
- CS에서 자주 쓰는 인용 양식 8가지(BibTeX, IEEE, ACM, APA, MLA, Chicago, Harvard, Vancouver)의 규칙을 설계 문서에 적는다.
- 서재 논문 정보로 양식별 글(일반 글과 기울임이 있는 HTML)을 만드는 순수 함수를 만든다.
- 논문 상세에 "인용" 버튼과 양식 목록 창(양식마다 미리보기와 복사)을 둔다.
- 테스트를 더하고 브라우저에서 확인한다.

### 진행 기록
- 2026-11-15: M6-T3 작업 중에 사용자가 요청했다(구글 스칼라처럼 5~10개). I16 다음에 하기로 하고, 병합되지 않은 가장 최근 브랜치 `i16-library-links`에서 작업 브랜치를 만들었다.
- 2026-11-15: `citationStyles` 모듈(이름 나누기, 여덟 양식, BibTeX, 복사)과 인용 창(`CiteDialog.vue`)을 만들고 논문 상세에 "인용" 버튼을 두었다. primeicons에 따옴표 아이콘이 없어 복사 아이콘을 썼다.
- 2026-11-15: 세 논문('Attention Is All You Need' 8저자 학회, LSTM 2저자 저널, BERT arXiv)으로 여덟 양식 글을 뽑아 보았다. Chicago는 저자가 둘일 때 `, and`가 빠져 고쳤다.
- 2026-11-15: 시연 서버에서 브라우저로 확인했다. 창에 여덟 양식이 나왔고, APA 복사는 글과 기울임 HTML이 함께, BibTeX 복사는 글만 들어갔으며 버튼이 "복사됨"으로 바뀌었다. OpenAlex로 담은 Bahdanau 논문의 게재처가 "arXiv (Cornell University)"로 그대로 인용에 들어가, arXiv 저장소 이름은 게재처로 쓰지 않고 `arXiv preprint arXiv:<ID>`를 쓰게 고쳤다.

### 결정 사항
- 양식은 CS에서 많이 쓰는 BibTeX, IEEE, ACM과 구글 스칼라의 APA, MLA, Chicago, Harvard, Vancouver 여덟 가지다.
- 인용 양식 라이브러리를 쓰지 않고 직접 만든다. 규칙이 짧고, 라이브러리는 첫 화면 번들을 크게 키우기 때문이다([인용 양식 설계](design/CitationStyles.md#1-범위)).
- 제목 대소문자는 바꾸지 않는다. 고유 이름을 기계로 가려낼 수 없기 때문이다.
- 글과 HTML을 함께 복사해 붙여 넣는 곳에 기울임이 남게 한다. BibTeX는 글로만 복사한다.

### 변경 파일
- `docs/Issue.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/index.md`
- `docs/design/CitationStyles.md`
- `frontend/src/citationStyles.ts`
- `frontend/src/citationStyles.test.ts`
- `frontend/src/CiteDialog.vue`
- `frontend/src/PaperDetail.vue`

### 결과
- 논문 상세의 "인용" 버튼으로 여덟 양식(BibTeX, IEEE, ACM, APA, MLA, Chicago, Harvard, Vancouver)의 인용 글을 보고 골라 복사한다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 시연 서버에서 인용 창, APA·BibTeX 복사와 클립보드 내용을 브라우저로 확인했다. 브라우저 콘솔 오류는 없었다.

## I16 서재에 논문을 담으면 서재의 다른 논문들과의 인용·피인용 관계를 확인해 그래프에 정확히 보여 주기

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [인용 데이터 설계](design/Citations.md#9-semantic-scholar-참고문헌)
- 참고 자료: 없음

### 계획
- 서재 그래프에서 인용 선이 빠지는 경우를 실제 데이터로 찾는다.
- 원인에 맞게 서재 논문 사이 인용을 확인하는 방법을 정하고 만든다.
- 테스트를 더하고 시연 서재로 확인한다.

### 진행 기록
- 2026-11-15: M6-T3 작업 중에 사용자가 요청했다. 병합되지 않은 가장 최근 브랜치 `m6-t3-citation-preview`에서 작업 브랜치를 만들었다. 같은 때 받은 인용 양식 복사 요청은 I17로 등록했다.
- 2026-11-15: 시연 서재에 BERT, RoBERTa, GPT-3을 더해 그래프를 보았다. 서로의 인용은 잡혔지만 'Attention Is All You Need'가 실제로 인용하는 Bahdanau, GRU 논문으로 가는 인용 선이 없었다. OpenAlex에 있는 이 논문의 참고문헌은 35개(실제 40개)였고 LSTM, Bahdanau, GRU, Dropout이 빠져 있었다. 서재 논문의 참고문헌을 모두 보는 지금 계산은 맞았고, 데이터가 빠진 것이 원인이었다.
- 2026-11-15: 다른 출처를 비교했다. Semantic Scholar는 41개를 모두 주었고, Crossref는 arXiv 논문을 몰랐다. 사용자에게 물어 Semantic Scholar를 함께 쓰기로 했다.
- 2026-11-15: `semantic_scholar` 모듈(받기, 저장, 맞추기)을 만들고 인용 데이터 갱신과 그래프에 붙였다. `citations`와 `references`가 서로 불러오지 않게 제목 다듬기 함수를 `titles` 모듈로 옮겼다.
- 2026-11-15: 시연 서재에서 확인했다. 'Attention Is All You Need' → Bahdanau, → GRU 인용 선이 생겼다. SE Networks의 CVPR DOI는 Semantic Scholar에 없어 7편 가운데 6편만 확인되었다. 제목 맞추기로 찾는 단계를 더하자 84개를 받아 7편 모두 확인되었다. 손으로 보낸 요청에 429(공용 한도)를 한 번 받았다.
- 2026-11-15: Semantic Scholar 키를 넣는 일을 선택 사항인 사용자 할 일 I18로 등록했다.

### 결정 사항
- 서재 논문마다 Semantic Scholar 참고문헌을 받아 두고, 그래프를 그릴 때 서재 논문끼리 맞춘다. 새 논문을 담을 때 그 논문 하나만 받으면 양쪽 방향이 모두 확인되기 때문이다.
- 맞추기는 DOI, arXiv ID, 다듬은 제목(3낱말 이상) 가운데 하나라도 같으면 같은 논문으로 본다. 같은 논문이 arXiv판과 학회판으로 DOI가 다른 경우가 많기 때문이다.
- 키 없이 쓰되 요청 사이를 1.1초 띄우고 429에서 멈춘다. 키가 있으면 쓴다. 키를 받는 일은 사용자가 할 수 있는 선택 사항으로 남긴다.
- 표는 기존 인용 캐시 파일에 더하고 캐시 버전은 올리지 않는다. 버전을 올리면 OpenAlex 인용 데이터를 모두 다시 받아야 하기 때문이다.

### 변경 파일
- `docs/Issue.md`
- `docs/Done.md`
- `docs/ProductVision.md`
- `docs/Architecture.md`
- `docs/design/Citations.md`
- `docs/design/CitationGraph.md`
- `docs/design/ReaderCitations.md`
- `src/jjabtero/semantic_scholar.py`
- `src/jjabtero/titles.py`
- `src/jjabtero/references.py`
- `src/jjabtero/citations.py`
- `src/jjabtero/citation_graph.py`
- `tests/test_semantic_scholar.py`
- `tests/test_citations.py`
- `tests/test_references.py`
- `tests/conftest.py`
- `frontend/src/api.ts`
- `frontend/src/api.test.ts`
- `frontend/src/CitationStatusPanel.vue`

### 결과
- 서재에 논문을 담으면 Semantic Scholar 참고문헌으로 서재의 다른 논문들과의 인용·피인용을 확인해 그래프에 인용 선을 긋는다. OpenAlex 참고문헌에 빠진 인용도 보인다. 설정 페이지에서 Semantic Scholar로 확인한 논문 수를 본다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 시연 서재(7편, 실제 OpenAlex·Semantic Scholar)에서 7편 모두 확인되고, OpenAlex에 빠졌던 'Attention Is All You Need' → Bahdanau, → GRU 인용 선이 그래프 API에 나오는 것을 확인했다.

## M6-T3 리더의 인용 링크 미리보기 상자와 서재에 담기·PDF 받기·새 탭에서 읽기

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [리더 인용 미리보기 설계](design/ReaderCitations.md)
- 참고 자료: 없음

### 계획
- 인용 링크 영역과 참고문헌 항목 글을 계산하는 순수 함수를 만든다.
- 마우스 1초 대기, 상자 열고 닫기, 논문 찾기, 서재에 담고 PDF 받기, 새 탭 주소를 다루는 상태 모듈을 만든다.
- 리더에 인용 링크 찾기, 마우스 위치 확인, 링크 누르면 이동, 상자를 붙인다.
- 테스트를 더하고 실제 PDF로 브라우저에서 확인한다.

### 진행 기록
- 2026-11-15: 병합되지 않은 가장 최근 브랜치 `m6-t2-reference-resolve`에서 작업 브랜치를 만들었다.
- 2026-11-15: 데모 PDF에서 목적지 좌표와 글 기준선을 비교했다. `cite.hochreiter1997`의 위 좌표는 453.4이고 항목 첫 줄 기준선은 442.5, 앞 항목의 마지막 줄은 462.3이었다. 설계한 경계(위 좌표 + 2pt 이하)로 앞 항목이 섞이지 않는다.
- 2026-11-15: 순수 함수 모듈(`citationLinks`), 상자 상태 모듈(`referencePreview`), 상자 화면(`ReferencePreview.vue`)을 만들고 리더에 붙였다. pdf.js 6의 `PageViewport`에는 사각형 변환이 없어 두 꼭짓점을 따로 바꿨다.
- 2026-11-15: 시연 서버('Attention Is All You Need', 실제 OpenAlex)에서 브라우저로 확인했다. 0.5초 스치기에는 상자가 뜨지 않았고, 1초 머물면 Hochreiter 인용의 LSTM 논문이 떴다. 상자로 옮겨 가도 열려 있었고, 벗어나자 닫혔다. 링크를 누르자 참고문헌이 있는 11쪽으로 갔다.
- 2026-11-15: Bahdanau 인용은 처음에 찾지 못했다. 같은 줄의 글 조각을 빈칸 없이 이어 `translate.CoRR`처럼 붙는 바람에 제목 후보가 학회 이름과 한 덩어리가 되어 검색이 틀렸다. 조각 너비로 간격을 계산해 빈칸을 넣자 찾았고, "서재에 담고 PDF 받기"로 담고 arXiv PDF를 받았다.
- 2026-11-15: 오른쪽 끝 링크에서 상자가 리더 가장자리에 붙어 넘칠 수 있어 위치를 제한했다. GRU 인용은 앞 실행에서 담겨 "서재에 있음 · PDF 있음"과 서재 PDF로 여는 "새 탭에서 읽기"만 보였다. 한 번은 OpenAlex가 502를 돌려 상자에 오류가 보였고, 다시 올리자 찾았다.
- 2026-11-15: 사용자가 작업 중에 새 요청을 했다. 서재에 논문을 담으면 서재의 다른 논문들과의 인용·피인용 관계를 확인해 그래프를 정확히 보여 달라는 것이다. 이슈 I16으로 등록했고, 이 작업을 마친 뒤 이어서 한다. 사용자는 이 작업을 다시 이어 하라고 했다.

### 결정 사항
- 리더 위에 투명 요소를 겹치지 않고 마우스 이동에서 링크 영역을 확인한다(설계대로). 하이라이트용 글 고르기를 막지 않기 위해서다.
- 같은 줄 글 조각 사이 간격이 0.5pt를 넘으면 빈칸을 넣는다. 낱말 안에서 글꼴이 바뀌어 조각이 나뉘는 경우는 드물고, 빈칸이 빠지는 쪽이 검색을 더 크게 망치기 때문이다.

### 변경 파일
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/Issue.md`
- `docs/design/ReaderCitations.md`
- `frontend/src/citationLinks.ts`
- `frontend/src/citationLinks.test.ts`
- `frontend/src/referencePreview.ts`
- `frontend/src/referencePreview.test.ts`
- `frontend/src/ReferencePreview.vue`
- `frontend/src/ReaderView.vue`
- `frontend/src/App.vue`
- `frontend/src/api.ts`

### 결과
- 리더에서 인용 표시(링크가 있는 PDF)에 마우스를 1초 올리면 그 논문이 상자로 뜬다. 상자에서 서재에 담고 PDF를 받거나, 새 탭에서 PDF(없으면 원문 페이지)를 연다. 인용 표시를 누르면 참고문헌 쪽으로 간다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 시연 서버에서 스치기, 1초 머물기, 상자로 옮겨 가기, 닫기, 서재에 담고 PDF 받기, 서재에 있는 논문, 링크 눌러 이동을 브라우저로 확인했다. 브라우저 콘솔 오류는 없었다.

## M6-T2 참고문헌 항목 글로 논문을 찾는 API

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [리더 인용 미리보기 설계](design/ReaderCitations.md#4-논문-찾기)
- 참고 자료: 없음

### 계획
- 항목 글과 후보 논문 제목을 맞추는 함수를 만든다.
- 이 논문의 OpenAlex 참고문헌과 먼저 맞추고, 없으면 OpenAlex를 검색하는 API를 만든다. 찾은 논문의 서재 상태와 공개 PDF 주소를 함께 준다.
- 공개 PDF 주소를 찾는 코드를 PDF 받기와 함께 쓰도록 나눈다.
- 테스트를 더하고 실제 PDF의 참고문헌 항목으로 확인한다.

### 진행 기록
- 2026-11-15: 병합되지 않은 가장 최근 브랜치 `m6-t1-reader-citations-design`에서 작업 브랜치를 만들었다.
- 2026-11-15: `references` 모듈(맞추기, API, 결과 기억)을 만들고, 공개 PDF 주소 찾기를 `open_access_pdf_url`로 나눴다.
- 2026-11-15: 시연 서버에서 SE Networks 논문으로 실제 OpenAlex를 불러 확인했다. LSTM과 ResNet 항목은 참고문헌에서 찾았다. 참고문헌에 없는 Sennrich 항목은 항목 글 전체로 검색하자 관계없는 결과만 나와 찾지 못했다. OpenAlex 검색은 낱말을 모두 맞추려 해서 저자·학회 낱말이 방해가 됐다. 제목일 만한 조각을 골라 검색하도록 바꾸자 Sennrich와 Adam 항목을 찾았다. 꾸며 낸 항목은 찾지 못함이었다.
- 2026-11-15: OpenAlex가 Adam 논문의 공개 주소를 arXiv 소개 페이지(`arxiv.org/abs/...`)로 주었다. 이 주소로는 PDF 받기도 실패하므로 PDF 주소로 바꾸게 했다.
- 2026-11-15: 확인하던 중 `curl` 오류 메시지에 `.env`의 OpenAlex 키가 이 세션의 명령 출력에 한 번 찍혔다. 저장소나 외부로 나가지는 않았다. 이후에는 키를 출력하지 않는 방법으로만 확인했고, 사용자에게 알렸다.

### 결정 사항
- 결과 기억은 서버 메모리에 둔다. 인용 캐시 파일에 표를 더하면 캐시 버전을 올려 모든 인용 데이터를 다시 받아야 하기 때문이다. 서버가 다시 시작하면 사라져도 다시 찾으면 된다.
- 서재 상태는 기억하지 않고 매번 읽는다. 상자에서 서재에 담은 뒤 다시 마우스를 올리면 "서재에 있음"이 보여야 하기 때문이다.
- 검색은 제목 후보 두 개까지만 한다. 마우스를 올릴 때마다 OpenAlex를 여러 번 부르지 않게 하기 위해서다.

### 변경 파일
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/design/ReaderCitations.md`
- `docs/design/Reader.md`
- `src/jjabtero/references.py`
- `src/jjabtero/pdfs.py`
- `src/jjabtero/citations.py`
- `src/jjabtero/app.py`
- `tests/test_references.py`
- `tests/test_pdfs.py`

### 결과
- `POST /api/papers/{id}/references/resolve`에 참고문헌 항목 글을 보내면 그 논문(서지 정보, 서재 상태, 공개 PDF 주소)을 돌려준다. 이 논문의 참고문헌에서 먼저 찾고, 없으면 제목일 만한 조각으로 OpenAlex를 검색한다.
- PDF 받기에서 OpenAlex가 arXiv 소개 페이지를 주는 경우에도 PDF를 받는다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- 시연 서버와 실제 OpenAlex로 참고문헌에서 찾기(LSTM, ResNet), 검색으로 찾기(Sennrich, Adam), 찾지 못함(꾸며 낸 항목)을 확인했다.

## M6-T1 인용 미리보기 설계(인용 표시 찾기, 참고문헌 항목 읽기, 논문 찾기, 상자와 동작)

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [리더 인용 미리보기 설계](design/ReaderCitations.md)
- 참고 자료: 없음

### 계획
- 데모 PDF와 arXiv PDF로 인용 링크가 어떻게 들어 있는지 조사한다.
- 인용 표시를 찾는 방법, 참고문헌 항목 글을 읽는 방법, 그 글로 논문을 찾는 방법, 미리보기 상자의 동작을 설계 문서에 적는다.
- 제품 비전의 PDF 리더 절과 로드맵에 M6을 더한다.

### 진행 기록
- 2026-11-15: 사용자가 리더에서 인용 표시에 마우스를 1초 올리면 그 논문을 상자로 보여 주고, 내려받기와 새 탭에서 읽기를 하게 해 달라고 했다. "내려받기"는 서재에 담고 PDF 받기로, 시기는 지금 바로(M5보다 먼저)로 사용자가 골랐다. 새 마일스톤 M6으로 로드맵에 더했다. 병합되지 않은 가장 최근 브랜치 `h1-stale-chunk`에서 작업 브랜치를 만들었다.
- 2026-11-15: pdf.js로 링크 주석을 세었다. 'Attention Is All You Need'(arXiv)는 링크 113개 가운데 76개가 `cite.` 이름의 목적지(예: `cite.hochreiter1997`)였고, 목적지는 참고문헌 쪽의 좌표(`XYZ`, 왼쪽 108, 위 453.4)였다. SE Networks(206개), BERT(290개)의 arXiv PDF도 링크가 있었다.
- 2026-11-15: 리더 인용 미리보기 설계 문서를 쓰고 문서 인덱스, 제품 비전, 로드맵에 더했다.

### 결정 사항
- 인용 표시와 참고문헌 항목 글은 브라우저(pdf.js)가 찾고, 항목 글로 논문을 찾는 일은 서버가 한다. pdf.js가 이미 쪽의 글과 좌표를 가지고 있고, 서버는 인용 데이터와 OpenAlex 키를 가지고 있기 때문이다.
- 논문은 먼저 이 논문의 OpenAlex 참고문헌 목록과 제목으로 맞추고, 못 찾을 때만 OpenAlex를 검색한다. 대부분 OpenAlex 호출 없이 찾고, 엉뚱한 논문을 고를 위험이 적기 때문이다.
- 인용 링크 위에 요소를 겹치지 않고 마우스 위치로 영역을 확인한다. 겹치면 그 아래 글을 고를 수 없어 하이라이트가 끊기기 때문이다.
- 링크가 있는 PDF(arXiv 대부분)를 먼저 하고(M6-T3), 링크가 없는 PDF는 따로 한다(M6-T4). 링크는 정확한 목적지를 주지만 글자 모양 찾기는 추측이라 규칙을 따로 다듬어야 하기 때문이다.

### 변경 파일
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/ProductVision.md`
- `docs/index.md`
- `docs/design/ReaderCitations.md`

### 결과
- 리더 인용 미리보기의 흐름(인용 표시 찾기 → 참고문헌 항목 읽기 → 논문 찾기 → 상자)과 각 단계의 규칙, API, 상자의 동작이 정해졌다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.

## H1 배포 뒤 열어 둔 탭에서 리더·그래프 화면이 빈 칸으로 나옴(옛 화면 파일을 못 불러옴)

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [UI 기반 설계](design/UiLayout.md#3-화면-배치)
- 참고 자료: 없음

### 계획
- 원인을 재현해 확인한다.
- 나중에 불러오는 화면(리더, 그래프)을 불러오지 못하면 한 번 자동으로 새로고침하고, 그래도 안 되면 빈 칸 대신 안내와 "새로고침" 버튼을 보여 준다.
- 설계 문서와 테스트를 더하고, 실패를 흉내 낸 브라우저에서 확인한다.

### 진행 기록
- 2026-11-15: 사용자가 배포된 앱에서 "읽기"를 누르면 가운데 칸이 비어 있다고 알렸다. #30~#42가 모두 병합되어 배포된 상태였다.
- 2026-11-15: 배포된 파일은 로컬 빌드와 해시까지 같았고, PDF 작업자 파일도 `text/javascript`로 내려왔다. 로컬에서는 Chrome 157과 WebKit 27.2 모두 리더가 열렸다. PDF를 열지 못하면 리더가 오류 문구를 보이므로, 빈 칸은 리더 화면 파일 자체를 불러오지 못한 경우다. 배포마다 첫 화면 파일 해시가 바뀌면 그것을 불러오는 리더 파일 이름도 바뀌고, 서버는 없는 파일에 404를 준다. 배포 전에 연 탭은 옛 이름을 청하다 실패하고, `defineAsyncComponent`는 실패하면 아무것도 그리지 않는다. 이것을 가장 유력한 원인으로 보았다.
- 2026-11-15: 사용자에게 우선 새로고침해 보라고 안내했다.
- 2026-11-15: 나중에 불러오는 화면을 `lazyView`로 감쌌다. 불러오기에 실패하면 한 번 새로고침하고, 그래도 안 되면 안내 화면을 보여 준다. 서버는 `assets/` 파일에 오래 캐시하라는 지시를, `index.html`에 매번 확인하라는 지시를 붙인다.
- 2026-11-15: 브라우저에서 리더 화면 파일 요청을 404로 바꿔 옛 탭을 흉내 냈다. 첫 실패에 페이지가 한 번 새로고침되었고, 1분 안의 두 번째 실패에는 안내 화면이 나왔으며, 요청을 되돌리고 "새로고침"을 누르자 리더가 열렸다. 캐시 지시가 붙는 것도 응답 머리글로 확인했다.

### 결정 사항
- 실패하면 자동으로 한 번 새로고침한다. 배포 뒤 옛 탭에서는 새로고침만으로 풀리고, 사용자가 원인을 몰라도 되기 때문이다. 되풀이를 막으려고 1분 안에는 다시 하지 않는다.
- 자동 새로고침 뒤에는 처음 화면(논문 검색)으로 돌아간다. 화면 상태를 주소에 담는 일은 이번 결함의 범위 밖이라 하지 않는다.

### 변경 파일
- `docs/Issue.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/design/UiLayout.md`
- `docs/design/AppSkeleton.md`
- `docs/design/Reader.md`
- `docs/design/CitationGraph.md`
- `frontend/src/lazyView.ts`
- `frontend/src/lazyView.test.ts`
- `frontend/src/LoadFailedView.vue`
- `frontend/src/App.vue`
- `src/jjabtero/app.py`
- `tests/test_app.py`

### 결과
- 배포 전에 열어 둔 탭에서 리더나 그래프를 열어도 빈 칸이 나오지 않는다. 한 번 자동으로 새로고침되고, 그래도 안 되면 까닭과 "새로고침" 버튼이 보인다.
- 새로 배포한 뒤 새로고침하면 브라우저가 항상 새 `index.html`을 받는다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 시연 서버에서 화면 파일 404를 흉내 내어 자동 새로고침, 안내 화면, 새로고침 뒤 리더 열림을 브라우저로 확인했다.
