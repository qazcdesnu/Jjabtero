# 완료

이 문서는 끝난 작업의 상세 기록이다. 최신 기록이 맨 위에 온다. 기록 형식은 [작업 관리 규칙](TaskRule.md#5-기록-형식)을 따르며, 할 일 목록은 [로드맵](Roadmap.md)과 [이슈](Issue.md)에 있다. 닫힌 마일스톤의 기록은 [작업 관리 규칙](TaskRule.md#47-완료-기록-보관)에 따라 보관 문서로 옮긴다. 보관 문서: [M0 시작](Done-M0.md), [M1 기본 서재](Done-M1.md), [M2 Render 배포](Done-M2.md), [M4 PDF 리더](Done-M4.md), [M3 인용 기반 연결·추천](Done-M3.md), [M6 리더 인용 미리보기](Done-M6.md), [M7 태그](Done-M7.md). 전체 문서 목록은 [문서 인덱스](index.md)에서 확인한다.

## I29 서재 목록에 Jjabtero 리더에서 마지막으로 읽은 날 칸을 더해 최근에 연 순으로 정렬하기

- 시작일: 2026-11-18
- 완료일: 2026-11-18
- 근거 문서: [서재 화면 설계](design/LibraryView.md#3-화면), [PDF 리더 설계](design/Reader.md#4-데이터)
- 참고 자료: 없음

### 계획
- 읽던 위치의 저장 시각을 마지막으로 읽은 시각으로 쓰고, 리더를 열 때도 위치를 저장해 시각을 바꾼다.
- 논문 응답에 `last_read_at`을 더하고, 서재 표에 "읽은 날" 열과 상세에 마지막으로 읽은 시각을 보인다.
- 리더를 닫으면 서재 목록을 다시 불러온다.

### 진행 기록
- 2026-11-18: 사용자가 Jjabtero 안에서 마지막으로 읽은 날을 보여 최근에 열어 본 논문을 찾게 해 달라고 했다. 앞의 PR이 모두 병합되어 `main`에서 작업 브랜치를 만들었다.
- 2026-11-18: 처음에는 연 적이 없으면 비워 두려 했으나, 사용자가 연 적이 없으면 담은 날을 읽은 날로 보라고 했다. 논문 응답의 `last_read_at`은 읽던 위치의 저장 시각, 없으면 담은 시각이다.
- 2026-11-18: 리더를 열면 서재 표가 내려갔다가 닫을 때 다시 만들어져 고른 정렬이 풀리는 것을 브라우저 확인에서 찾았다. 정렬 열과 방향을 서재 상태에 두어 지키게 했다. 열이 늘어 제목 칸이 좁아져, 두 날짜 열을 두 자리 연도로 보이고 다른 열 너비를 줄였다.
- 2026-11-18: 로컬 서재 사본(드라이브 없이, 포트 8010)에서 "읽은 날" 최근 순으로 정렬한 뒤 DGM 논문을 리더로 열고 닫았다. 목록이 다시 불러와지고 정렬이 유지되며 그 논문의 읽은 시각이 바뀌는 것을 확인했다. 연 적 없는 논문(Gödel Machines)은 담은 시각(04:48)이 보였다. 브라우저 콘솔 오류는 없었다.

### 결정 사항
- 새 열을 더하지 않고 읽던 위치의 `updated_at`을 마지막으로 읽은 시각으로 쓴다. 이미 읽던 논문의 시각을 그대로 쓸 수 있고, 드라이브 합치기도 그 표의 시각을 따른다.
- 연 적이 없으면 담은 시각으로 본다(사용자 결정).

### 변경 파일
- `docs/Issue.md`
- `docs/Done.md`
- `docs/design/LibraryView.md`
- `docs/design/Reader.md`
- `src/jjabtero/papers_api.py`
- `tests/test_reading.py`
- `frontend/src/api.ts`
- `frontend/src/App.vue`
- `frontend/src/ReaderView.vue`
- `frontend/src/LibraryView.vue`
- `frontend/src/PaperDetail.vue`
- `frontend/src/labels.ts`
- `frontend/src/labels.test.ts`
- `frontend/src/libraryState.ts`
- `frontend/src/libraryState.test.ts`
- `frontend/src/libraryFilter.test.ts`

### 결과
- 서재 목록의 "읽은 날" 열로 최근에 연 논문 순으로 정렬하고, 상세에서 읽은 시각을 본다. 리더를 다녀와도 표의 정렬이 유지된다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 로컬 서재 사본으로 브라우저에서 확인했다.

## I28 서재 목록에 서재에 담은 시각 칸을 더해 담은 순으로 정렬하기

- 시작일: 2026-11-18
- 완료일: 2026-11-18
- 근거 문서: [서재 화면 설계](design/LibraryView.md#3-화면)
- 참고 자료: 없음

### 계획
- 서재 표에 담은 날 열을 더하고, 누르면 담은 시각 순으로 정렬한다.
- 브라우저에서 정렬을 확인한다.

### 진행 기록
- 2026-11-18: 사용자가 서재 목록에 서재에 담은 시간을 더해 추가한 순으로도 정렬하게 해 달라고 했다. 병합되지 않은 가장 최근 브랜치 `i27-open-alternatives`에서 작업 브랜치를 만들었다.
- 2026-11-18: 서버가 UTC 시각을 시간대 표시 없이 주고(`2026-11-17T19:48:12.197842`), 상세의 추가일은 앞 10글자만 잘라 한국 시각(11-18 04:48)보다 하루 앞선 날짜를 보이고 있었다. 시간대 표시가 없으면 UTC로 읽고 이 컴퓨터의 시간대로 보이게 바꿨다.
- 2026-11-18: 표 끝에 "담은 날" 열(날짜, 마우스를 올리면 시각)을 더하고, 정렬은 UTC ISO 문자열(`timeKey`)로 시각 순서가 되게 했다. 로컬 서재 사본(드라이브 없이, 포트 8010)에서 열을 눌러 오래된 순(2026-11-01부터)과 최근 순으로 바뀌는 것을 확인했다. 브라우저 콘솔 오류는 없었다. 확인 뒤 로컬 앱이 쓰는 `frontend/dist`를 `main`에서 다시 빌드했다.

### 결정 사항
- 열에는 날짜만 보이고 시각은 마우스를 올리면 보인다. 제목 열 너비를 덜 줄이기 위해서다.

### 변경 파일
- `docs/Issue.md`
- `docs/Done.md`
- `docs/design/LibraryView.md`
- `docs/design/ReadingStatus.md`
- `frontend/src/labels.ts`
- `frontend/src/labels.test.ts`
- `frontend/src/LibraryView.vue`
- `frontend/src/PaperDetail.vue`

### 결과
- 서재 목록의 "담은 날" 열을 눌러 담은 순으로 정렬한다. 날짜는 이 컴퓨터의 시간대로 보인다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 로컬 서재 사본으로 브라우저에서 확인했다.

## I27 공개 PDF가 없으면 비슷한 공개판(같은 저자의 예비판 등)을 찾아 그 PDF를 받을지 묻기

- 시작일: 2026-11-18
- 완료일: 2026-11-18
- 근거 문서: [PDF 리더 설계](design/Reader.md#2-pdf-가져오기)
- 참고 자료: 없음

### 계획
- OpenAlex에서 같은 첫 저자의 공개 논문을 제목으로 찾아, 제목이 비슷한 것을 공개판 후보로 고르는 API를 만든다.
- 논문 상세의 "PDF 받기"와 리더 인용 미리보기의 "서재에 담고 PDF 받기"가 공개 PDF를 찾지 못하면 후보를 보여 주고 받을지 묻는다.
- 서재의 "Gödel Machines" 장(Springer, 비공개)으로 브라우저에서 확인한다.

### 진행 기록
- 2026-11-18: 사용자가 서재에 담은 Schmidhuber의 "Gödel Machines: Fully Self-referential Optimal Universal Self-improvers"(Springer 책의 장)가 PDF를 받지 못하는 것을 보고, 비슷한 공개판을 받을 수 있으면 받을지 묻게 해 달라고 했다. OpenAlex에서 이 장은 비공개(`closed`)였고, 같은 저자의 arXiv 예비판 "Goedel Machines: Self-Referential Universal Problem Solvers Making Provably Optimal Self-Improvements"(`cs/0309048`)가 공개되어 있었다. 병합되지 않은 가장 최근 브랜치 `i26-multi-citations`에서 작업 브랜치를 만들었다.
- 2026-11-18: OpenAlex 질의를 시험했다. 제목 검색만 하면 다른 저자의 비슷한 제목(Gödel Agent 등)이 먼저 나오고, 첫 저자 이름 거르기(`raw_author_name.search`)와 공개 거르기(`is_oa:true`)를 함께 쓰면 예비판이 맨 위에 나왔다. 같은 저자의 다른 논문도 함께 나오므로 제목 비슷함으로 다시 거르기로 했다.

- 2026-11-18: 공개판 찾기 API(`GET /api/papers/{id}/pdf/alternatives`)와 공개판으로 받기(`POST …/pdf/fetch` 본문 `openalex_id`)를 만들고, 논문 응답에 PDF 출처를 더했다. 논문 상세의 PDF 칸과 인용 미리보기 상자가 공개 PDF가 없으면(404) 후보를 찾아 "이 PDF 받기"와 "받지 않기"로 묻게 했다(`OpenVersionChoice`).
- 2026-11-18: 로컬 서재 사본(드라이브 없이, 포트 8010)에서 "Gödel Machines" 장의 "PDF 받기"를 누르자 후보로 arXiv 예비판 하나("Goedel Machines: Self-Referential Universal Problem Solvers …", 2003)가 나왔고, "이 PDF 받기"로 받은 뒤 "읽기"와 "비슷한 공개판에서 받은 PDF입니다"가 보였다. 콘솔에는 공개 PDF가 없다는 404 응답 기록만 있었다. 확인 뒤 로컬 앱이 쓰는 `frontend/dist`를 `main`에서 다시 빌드했다.

### 결정 사항
- 공개판은 사용자가 고를 때만 받는다. 판이 달라 내용이 조금 다를 수 있기 때문이다.

### 변경 파일
- `docs/Issue.md`
- `docs/Ongoing.md`
- `docs/design/Reader.md`
- `docs/design/ReaderCitations.md`
- `docs/Done.md`
- `src/jjabtero/pdfs.py`
- `src/jjabtero/papers_api.py`
- `tests/test_pdfs.py`
- `frontend/src/api.ts`
- `frontend/src/api.test.ts`
- `frontend/src/pdfState.ts`
- `frontend/src/pdfState.test.ts`
- `frontend/src/PdfPanel.vue`
- `frontend/src/OpenVersionChoice.vue`
- `frontend/src/referencePreview.ts`
- `frontend/src/referencePreview.test.ts`
- `frontend/src/ReferencePreview.vue`

### 결과
- 공개 PDF가 없는 논문은 같은 저자의 비슷한 공개판을 보여 주고, 사용자가 고르면 그 PDF를 받는다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 로컬 서재 사본으로 브라우저에서 확인했다.

## I26 리더 인용 미리보기가 여러 문헌을 한꺼번에 인용한 표시(`[4, 23, 61]`)에서도 숫자마다 동작하기(줄을 넘어간 표시, 줄 앞쪽 숫자의 영역)

- 시작일: 2026-11-18
- 완료일: 2026-11-18
- 근거 문서: [리더 인용 미리보기 설계](design/ReaderCitations.md#2-인용-표시-찾기)
- 참고 자료: 없음

### 계획
- 학술지판 DGM PDF에서 여러 문헌 인용이 어떻게 실패하는지 확인하고 고친다.
- 브라우저에서 숫자마다 마우스를 올려 맞는 항목이 나오는지 확인한다.

### 진행 기록
- 2026-11-18: 사용자가 `[4,23,61]`처럼 여러 문헌을 한꺼번에 인용한 경우에도 잘 동작하게 해 달라고 했다. 병합되지 않은 가장 최근 브랜치 `h4-numbered-citations`에서 작업 브랜치를 만들었다.
- 2026-11-18: 한 조각 안의 `[42, 115, 116]`은 이미 숫자마다 찾았다. 학술지판 DGM 본문(1~9쪽)의 숫자 200개 가운데 25개를 못 찾았는데, 모두 `[13, 29, 47, 66,` ↵ `112]`처럼 줄을 넘어간 표시였다. 조각 하나씩 찾던 것을 쪽의 조각을 줄바꿈으로 이은 글에서 찾게 바꾸자 200개를 모두 찾았다.
- 2026-11-18: 로컬 서재 사본(드라이브 없이, 포트 8010)의 리더에서 3쪽 여러 문헌 인용의 숫자마다 마우스를 올려 보니 54개 가운데 5개가 상자를 띄우지 않았다. 한 줄이 한 조각인 PDF라 글자 수 비율로 잡은 영역이 줄 앞쪽(`[2, 30, 32, 33, 113]`)에서 몇 pt 어긋났다. 캔버스로 그 글꼴 계열의 글자 너비를 재어 비율을 잡게 하자 3쪽 54개, 2쪽 숫자 61개가 모두 맞는 항목을 보였다. 브라우저 콘솔 오류는 없었다. 확인 뒤 로컬 앱이 쓰는 `frontend/dist`를 `main`에서 다시 빌드했다.

### 결정 사항
- 범위 표시(`[1–4]`)는 지금처럼 양 끝 숫자만 잇는다. 가운데 번호는 글자로 보이지 않아 마우스를 올릴 곳이 없기 때문이다.

### 변경 파일
- `docs/Issue.md`
- `docs/Done.md`
- `docs/design/ReaderCitations.md`
- `frontend/src/textCitations.ts`
- `frontend/src/textCitations.test.ts`
- `frontend/src/citationLinks.ts`
- `frontend/src/ReaderView.vue`

### 결과
- 여러 문헌을 한꺼번에 인용한 표시는 줄을 넘어가도 숫자마다 마우스를 올리면 그 항목의 논문이 상자에 나온다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 로컬 서재 사본으로 브라우저에서 숫자마다 확인했다.

## H4 리더 인용 미리보기가 학술지판 DGM PDF의 번호 인용(`[116]`)에서 논문을 찾지 못함(목적지 없는 인용 링크, 학술지 머리말, 벌어진 줄)

- 시작일: 2026-11-18
- 완료일: 2026-11-18
- 근거 문서: [리더 인용 미리보기 설계](design/ReaderCitations.md#2-인용-표시-찾기)
- 참고 자료: 없음

### 계획
- 사용자의 DGM PDF로 실패 원인을 찾고, 링크 경로와 글자 경로 가운데 어디서 실패하는지 확인해 고친다.
- 로컬 서재 사본으로 브라우저에서 확인한다.

### 진행 기록
- 2026-11-18: 사용자가 Darwin Gödel Machine 논문의 `[116]` 같은 번호 인용에 마우스를 올리면 어떤 논문인지 찾지 못한다며, 번호는 맞추기 쉽지 않느냐고 물었다. `main`에서 작업 브랜치를 만들었다.
- 2026-11-18: 로컬 앱에서 그 PDF를 읽기만 해 받아 조사했다. arXiv판(72쪽, 저자-연도 양식)이 아니라 학술지 사이트 `s-rsa.com`에서 받은 23쪽 번호 양식판이었다. `cite.` 링크 주석이 205개 있지만 문서의 목적지(`getDestinations`)에는 `cite.` 목적지가 하나도 없었다. 그래서 링크가 있다는 이유로 글자 경로를 쓰지 않았고, 링크의 목적지를 찾지 못해 항목 글이 비었다.
- 2026-11-18: 글자 경로로도 항목 156개 가운데 46개만 찾았다. 원인은 두 가지였다. 학술지 머리말(758pt)이 위 6%보다 안쪽에 있어 들여쓰지 않은 줄로 보였고, 12쪽의 한 줄이 낱말 사이가 40pt 넘게 벌어져 뒷부분이 오른쪽 단으로 보였다(이것이 실제로 목록을 끊었다). 또 "2025. URL …"처럼 연도로 시작하는 이어지는 줄을 2025번 항목으로 볼 수 있었다.
- 2026-11-18: 목적지가 하나도 없으면 링크를 버리고 글자 경로를 쓰게 했다. 여러 쪽에 되풀이되는 머리말·꼬리말을 빼고, 오른쪽 줄이 1/4 이상인 쪽만 두 단으로 보며, 번호는 앞 번호보다 크고 3 안일 때만 항목의 시작으로 보게 했다. 그 PDF에서 항목 156개(빠진 번호 없음)와 본문 표시 179개를 찾았다. 새 테스트는 고치기 전 코드에서 실패하고 고친 뒤 통과했다.
- 2026-11-18: 로컬 서재 사본과 그 PDF를 드라이브 없이 다른 포트(8010)로 띄워, 1쪽 `[116]`에 마우스를 올리면 "Gödel Machines: Fully Self-referential Optimal Universal Self-improvers"(Schmidhuber, 2007, 피인용 225)가 상자에 나오는 것을 확인했다. 브라우저 콘솔 오류는 없었다. 확인 뒤 로컬 앱이 쓰는 `frontend/dist`를 `main`에서 다시 빌드했다.

### 결정 사항
- 목적지가 일부만 있는 PDF는 지금처럼 링크 경로를 쓴다. 이번 PDF처럼 하나도 없을 때만 글자 경로로 바꾼다. 일부만 없는 경우는 아직 보지 못했기 때문이다.

### 변경 파일
- `docs/Issue.md`
- `docs/Done.md`
- `docs/design/ReaderCitations.md`
- `frontend/src/textCitations.ts`
- `frontend/src/textCitations.test.ts`
- `frontend/src/ReaderView.vue`

### 결과
- 목적지 없는 인용 링크만 남은 학술지판 PDF에서도 번호 인용에 마우스를 올리면 그 참고문헌의 논문이 상자에 나온다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 로컬 서재 사본으로 브라우저에서 확인했다.

## I25 그래프의 점마다 그래프 안에서 인용된 수 보여 주기(추천 논문끼리의 인용 포함)

- 시작일: 2026-11-18
- 완료일: 2026-11-18
- 근거 문서: [서재 인용 그래프 설계](design/CitationGraph.md#2-그래프-데이터)
- 참고 자료: 없음

### 계획
- 서재 밖 추천 논문의 참고문헌을 OpenAlex에서 100편씩 묶어 받아 인용 캐시에 두고, 추천 논문끼리와 추천 논문 → 서재 논문의 인용 선을 더한다.
- 점마다 그래프 안에서 인용된 수(들어오는 인용 선 수)를 세어 도움말과 논문 카드에 보이고, 점 크기를 그 수로 고를 수 있게 한다.
- 로컬 앱 데이터로 브라우저에서 확인한다.

### 진행 기록
- 2026-11-18: 사용자가 그래프의 논문 점마다 그래프 안에서의 피인용 수를 보여 달라고 했다. 추천 논문을 고를 때 추천 그래프 안에서 얼마나 인용되는지가 전체 피인용 수만큼 중요하다는 것이다. 지금 그래프에는 서재 밖 논문끼리의 인용 선이 없어(서재 밖 논문의 참고문헌을 저장하지 않음) 그대로 세면 서재 논문이 인용한 수만 나온다. 그래서 추천 논문의 참고문헌을 받기로 했다. 병합되지 않은 가장 최근 브랜치 `m5-t1-stats-design`에서 작업 브랜치를 만들었다.

- 2026-11-18: 인용 캐시에 `outside_references` 표를 더하고, 그래프를 그릴 때 서재 밖 논문의 참고문헌을 받아 인용 선을 더했다. 화면은 점마다 그래프 안 피인용 수를 세어 도움말과 카드에 보이고, 도구 줄 "점 크기"에서 그 수로 점 크기를 고르게 했다.
- 2026-11-18: 로컬 서재(20편)와 인용 캐시의 사본을 드라이브 없이 다른 포트(8010)로 띄워 확인했다. 추천 15편을 함께 보면 "Evaluating Large Language Models Trained on Code"가 그래프 안 피인용 13(전체 15,141), "Goedel Machines"가 6(전체 133)으로 나와, 전체 피인용은 적어도 그래프 안에서 많이 인용되는 추천 논문이 드러났다. 도움말·카드·점 크기 전환이 동작했고 브라우저 콘솔 오류는 없었다. 확인 뒤 로컬 앱이 쓰는 `frontend/dist`를 `main`에서 다시 빌드했다.

### 결정 사항
- 그래프 안 피인용 수는 지금 그래프에 있는 점에서 들어오는 인용 선 수다. 태그 거르기와 추천 논문 수에 따라 바뀐다.
- 추천 논문의 참고문헌은 그래프를 그릴 때 없거나 7일이 지난 것만 받는다. OpenAlex 요청은 30편까지 한 번이다.

### 변경 파일
- `docs/Issue.md`
- `docs/Ongoing.md`
- `docs/design/CitationGraph.md`
- `docs/design/Citations.md`
- `docs/Done.md`
- `src/jjabtero/citations.py`
- `src/jjabtero/citation_graph.py`
- `tests/test_citations.py`
- `tests/test_citation_graph.py`
- `frontend/src/graphOption.ts`
- `frontend/src/graphOption.test.ts`
- `frontend/src/GraphView.vue`

### 결과
- 그래프의 점마다 그래프 안 피인용 수가 도움말과 카드에 보이고, 점 크기를 그 수로 바꿀 수 있다. 추천 논문끼리의 인용 선도 그린다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 로컬 서재 사본으로 브라우저에서 확인했다.

## M5-T1 통계·시각화 항목 결정과 태스크 계획

- 시작일: 2026-11-18
- 완료일: 2026-11-18
- 근거 문서: [서재 통계 설계](design/LibraryStats.md)
- 참고 자료: 없음

### 계획
- 통계·시각화에서 정할 것을 사용자에게 정리해 묻고, 정한 대로 항목·데이터·API·화면을 설계한다.
- 로드맵에 M5의 나머지 태스크를 더한다.

### 진행 기록
- 2026-11-17: 사용자가 M5-T1에서 무엇을 정해야 하는지 물었다. 항목, 주제 출처, 다 읽은 시각 기록, 화면 위치, 태그 거르기, 누르면 거르기의 여섯 가지와 권장안을 알렸다.
- 2026-11-18: 사용자가 OpenAlex 주제가 얼마나 잘 붙는지 확인하라고 했다. 로컬 서재 17편과 인용 캐시 670편을 OpenAlex에서 읽기만 해 확인했다. 모두 대표 주제가 있었으나, 주제 단계는 서재 17편 가운데 4편이 어긋났고 세부 학문은 11편이 "Artificial Intelligence"로 거칠었다.
- 2026-11-18: 사용자가 세부 학문까지만 가져오자고 했다. 나머지는 권장안대로 하기로 하고, `main`에서 작업 브랜치를 만들어 서재 통계 설계 문서를 쓰고 로드맵에 M5-T2~T5를 더했다.
- 2026-11-18: 설계 문서에 인용 캐시를 드라이브로 옮기지 않는다고 잘못 적었다. 인용 캐시도 드라이브에 올라가므로 고쳤다.

### 결정 사항
- 지금 데이터로 볼 수 있는 항목을 모두 넣고 주제 분포를 더한다. 공동 저자 연결망은 나중에 한다.
- 주제는 태그 분포와 OpenAlex 학문·세부 학문 분포로 본다. 주제 단계는 어긋나는 것이 많아 가져오지 않는다. 사용자가 정했다.
- 다 읽은 시각을 앞으로 기록한다. 통계는 새 "통계" 화면에 두고, 왼쪽에서 고른 태그로 거르며, 차트를 누르면 서재 목록을 거른다.
- 세부 학문은 인용을 가져올 때 이미 부르는 OpenAlex 요청에 함께 받아 인용 캐시에 둔다. 요청 수를 늘리지 않기 위해서다.

### 변경 파일
- `docs/Roadmap.md`
- `docs/Done.md`
- `docs/index.md`
- `docs/ProductVision.md`
- `docs/design/LibraryStats.md`

### 결과
- 통계 항목 11가지, 다 읽은 시각과 OpenAlex 세부 학문 데이터, 통계 API, 통계 화면, 태스크 M5-T2~T5가 정해졌다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.

## I24 그래프 화면 안에서 태그를 골라 그 태그 논문만 그리기(태그 선택 칸)

- 시작일: 2026-11-17
- 완료일: 2026-11-17
- 근거 문서: [태그 설계](design/Tags.md#5-태그별-그래프)
- 참고 자료: 없음

### 계획
- 그래프 화면의 도구 줄에 태그 선택 칸(여러 개, 논문 수 표시)을 둔다. 왼쪽 목록의 태그 선택과 같은 상태를 쓴다.
- 브라우저로 확인한다.

### 진행 기록
- 2026-11-17: 사용자가 그래프 화면에서는 서재 전체 그래프만 볼 수 있다며 고른 태그의 논문만 그리는 기능을 요청했다. 이 기능은 M7-T3에서 왼쪽 목록의 태그를 누르는 방식으로 이미 있었고, 로컬 앱에서 `RSI`(12편)로 그리면 12편, 전체는 16편이 나오는 것을 확인했다. 그래프 화면 안에는 태그를 고르는 곳이 없어 찾기 어려웠던 것으로 보고, 화면 안에 선택 칸을 두기로 했다. 병합되지 않은 가장 최근 브랜치 `i23-graph-date-order`에서 작업 브랜치를 만들었다.
- 2026-11-17: 그래프 도구 줄에 태그 선택 칸(PrimeVue `MultiSelect`, 논문 수 표시, 찾기, 모두 지우기)과 "서재 전체 보기" 단추를 두었다. 시연 서버에서 `language (2)`를 고르자 9편에서 2편으로 다시 그렸고 왼쪽 목록에도 강조되었으며, "서재 전체 보기"로 9편으로 돌아왔다. 브라우저 콘솔 오류는 없었다.

### 결정 사항
- 그래프의 태그 선택은 왼쪽 목록과 같은 상태(서재 필터의 태그)를 쓴다. 서재 목록과 그래프가 같은 선택을 보여야 헷갈리지 않기 때문이다(M7-T1 결정과 같음).

### 변경 파일
- `docs/Issue.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/design/Tags.md`
- `frontend/src/GraphView.vue`
- `frontend/src/App.vue`

### 결과
- 그래프 화면 안에서 태그를 골라 그 태그 논문만 그리고, "서재 전체 보기"로 돌아온다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 시연 서버에서 태그 고르기, 왼쪽 목록과 맞춰짐, 서재 전체 보기를 브라우저로 확인했다.

## I23 그래프의 같은 연도 논문을 공개일과 인용 관계 순(선행이 위)으로 쌓기

- 시작일: 2026-11-17
- 완료일: 2026-11-17
- 근거 문서: [서재 인용 그래프 설계](design/CitationGraph.md#4-화면)
- 참고 자료: 없음

### 계획
- 그래프 점에 공개일과 그 정밀도(일, 월, 연도)를 더한다. 1월 1일은 연도만 아는 것으로 보고, arXiv 논문은 번호에서 연·월을 얻는다.
- 같은 연도 안에서 날짜가 이른 논문을 위에 두되, 같은 연도의 인용 관계는 인용된 논문(선행)이 위에 오게 한다. 날짜를 모르는 논문은 인용 관계로만 자리를 정하고, 그것도 없으면 그해 아래에 둔다.
- 도움말에 날짜와 정밀도를 보이고, 테스트와 브라우저로 확인한다.

### 진행 기록
- 2026-11-17: 사용자가 같은 연도 논문의 위아래 순서를 물었다. 지금은 서재 논문을 위, 그다음 피인용 많은 순이었다. 날짜순, 선행·후행 순으로 하고, 정확히 정할 수 없는 경우를 알려 달라고 했다. 모든 PR이 병합되어 `main`에서 작업 브랜치를 만들었다.
- 2026-11-17: 인용 캐시를 보니 이 컴퓨터는 680편 가운데 170편, 시연 서재는 369편 가운데 122편의 공개일이 1월 1일이었다. OpenAlex가 연도만 알 때 1월 1일로 채우기 때문이다(예: 'Self-Attention with Relative Position Representations'는 실제 2018년 3월 arXiv, 6월 학회인데 `2018-01-01`). 날짜가 없는 것은 각각 1편, 2편이었다.
- 2026-11-17: 서버에 `publication_when`과 점의 공개일·정밀도를, 화면에 `orderWithinYear`(인용 관계 위상 정렬과 날짜순), 날짜 표시, 안내 줄을 더했다.
- 2026-11-17: 시연 서재(추천 15편 포함 24점)로 확인했다. 공개일 정밀도는 일 16, 연도만 5, 없음 3이었다. 2019년 열에서 연도만 아는 BERT가 같은 해 논문들에 인용되어 맨 위에 왔고, 나머지는 XLNet(06-19), RoBERTa(07-26), ALBERT(09-26), T5(10-23) 순이었다. 2014년 열은 날짜로는 Bahdanau(09-01)가 Sutskever(09-10)보다 이르지만 인용 관계로 Sutskever가 위였다.
- 2026-11-17: 사용자의 로컬 앱(8000번)이 저장소의 `frontend/dist`를 쓰므로 이 브랜치에서 빌드하면 그 앱의 화면도 바뀐다. 확인한 뒤 `main` 기준으로 다시 빌드해 두었다.

### 결정 사항
- 1월 1일은 날짜로 믿지 않는다. OpenAlex가 연도만 알 때 채우는 값이라 날짜로 쓰면 그해 맨 위로 잘못 올라가기 때문이다.
- 같은 연도 안에서는 인용 관계를 날짜보다 앞세운다. 사용자가 선행·후행 순을 원했고, 판에 따라 날짜가 뒤바뀌기 때문이다.
- 연도만 아는 논문은 인용 관계가 없으면 그해 아래에 두고, 그 수를 안내 줄에 알린다. 정확히 정할 수 없는 경우를 숨기지 않기 위해서다.

### 변경 파일
- `docs/Issue.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/design/CitationGraph.md`
- `src/jjabtero/citation_graph.py`
- `tests/test_citation_graph.py`
- `frontend/src/api.ts`
- `frontend/src/graphOption.ts`
- `frontend/src/graphOption.test.ts`
- `frontend/src/graphState.test.ts`
- `frontend/src/GraphView.vue`

### 결과
- 그래프의 같은 연도 논문이 먼저 공개된 순으로 위에서 아래로 쌓이고, 같은 해의 인용 관계는 인용된 논문이 위에 온다. 날짜를 연도까지만 아는 논문은 안내 줄과 도움말로 알린다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 시연 서버의 그래프 데이터와 화면으로 같은 연도 순서를 확인했다.

