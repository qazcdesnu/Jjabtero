# 완료

이 문서는 끝난 작업의 상세 기록이다. 최신 기록이 맨 위에 온다. 기록 형식은 [작업 관리 규칙](TaskRule.md#5-기록-형식)을 따르며, 할 일 목록은 [로드맵](Roadmap.md)과 [이슈](Issue.md)에 있다. 닫힌 마일스톤의 기록은 [작업 관리 규칙](TaskRule.md#47-완료-기록-보관)에 따라 보관 문서로 옮긴다. 보관 문서: [M0 시작](Done-M0.md), [M1 기본 서재](Done-M1.md), [M2 Render 배포](Done-M2.md), [M4 PDF 리더](Done-M4.md). 전체 문서 목록은 [문서 인덱스](index.md)에서 확인한다.

## M3-T9 가까운 논문과 추천에 선행·후행 표시

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [인용 데이터 설계](design/Citations.md#6-api와-화면)
- 참고 자료: 없음

### 계획
- 가까운 논문과 추천 항목이 기준 논문보다 앞선 연구(선행)인지 뒤따른 연구(후행)인지 정하는 규칙을 설계 문서에 적는다.
- 가까운 논문 API와 추천 API(이어진 서재 논문마다, 그리고 항목 전체)에 방향과 그 근거를 더한다.
- 논문 상세의 "가까운 논문"과 추천 화면에 "선행"·"후행" 표시를 보여 준다.
- 백엔드·프론트엔드 테스트를 더하고 실제 데이터로 화면을 확인한다.

### 진행 기록
- 2026-11-15: 사용자가 추천과 가까운 논문이 선행 연구인지 후행 연구인지도 알려 주기를 바랐다. M3-T7 앞에 할 태스크로 로드맵에 더했다. 병합되지 않은 가장 최근 브랜치 `m3-t6-recommendations`에서 작업 브랜치를 만들었다.

- 2026-11-15: 설계 문서에 규칙을 적고, 가까운 논문 API와 추천 API에 방향과 근거를 더했다. 논문 상세의 가까운 논문과 추천 화면에 "선행"·"후행" 표시를 붙였다.
- 2026-11-15: 시연 서버(서재 논문 2편, 실제 OpenAlex 데이터)로 확인했다. 가까운 논문 30편은 모두 인용 근거로 정해졌고(선행 20, 후행 10), 추천 50편은 선행 37, 후행 7, 섞임 5, 없음 1이었다. 추천 화면에서 쉼표 앞에 빈칸이 생겨 고쳤다.

### 결정 사항
- 직접 인용이 있으면 인용 방향을 따른다(기준 논문이 인용한 논문은 선행, 기준 논문을 인용한 논문은 후행). 인용이 확실한 근거이기 때문이다.
- 직접 인용이 없거나 서로 인용하면 공개일을 비교한다(둘 다 날짜가 있으면 날짜, 아니면 연도). 같거나 알 수 없으면 표시하지 않는다. 화면에서는 근거(인용 또는 공개일)를 함께 알린다.

- 추천은 이어진 서재 논문마다 방향을 보여 주고, 항목 전체 방향은 모두 같을 때만 "선행"이나 "후행", 다르면 "선행·후행"으로 보여 준다. 추천은 여러 서재 논문을 기준으로 하기 때문이다.
- 피인용·참고문헌 탭에는 표시를 붙이지 않는다. 탭 이름이 이미 방향을 말해 주기 때문이다.

### 변경 파일
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/design/Citations.md`
- `src/jjabtero/citations.py`
- `tests/test_citations.py`
- `frontend/src/api.ts`
- `frontend/src/citationListState.ts`
- `frontend/src/citationListState.test.ts`
- `frontend/src/recommendState.test.ts`
- `frontend/src/CitationLists.vue`
- `frontend/src/RecommendView.vue`

### 결과
- 논문 상세의 "가까운 논문"과 "추천" 화면에서 각 논문이 기준 논문보다 앞선 연구(선행)인지 뒤따른 연구(후행)인지 볼 수 있다. 표시에 마우스를 올리면 근거(인용 관계 또는 공개일)를 알려 준다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 시연 서버에서 논문 상세의 가까운 논문과 추천 화면을 브라우저로 열어 표시를 확인했다.

## M3-T6 서재 밖 논문 추천

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [인용 데이터 설계](design/Citations.md#6-api와-화면)
- 참고 자료: 없음

### 계획
- 서재 논문 전체와 인용으로 가까운 서재 밖 논문을 점수 순으로 주는 API와 추천 화면을 만든다.

### 진행 기록
- 2026-11-15: M3-T5를 마치고 권장 순서대로 시작했다. PR #39(M3-T5)가 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-15: 추천 점수를 서재 논문마다의 가까운 논문 점수의 합으로 정했다. 추천 계산과 API를 구현하고 테스트를 더했다.
- 2026-11-15: 화면에 "추천" 화면(왼쪽 목록, 넓은 칸)과 상태 모듈을 더하고 테스트를 더했다. 추천을 어디에 보여 줄지는 앞서 사용자에게 제안했으나 답을 받지 못해, 제안대로 알림 없이 왼쪽 목록의 화면으로 두었다.
- 2026-11-15: 실제 OpenAlex 데이터로 서재 2편('Attention Is All You Need', 'Squeeze-and-Excitation Networks')의 추천을 확인했다. 두 논문 모두와 이어진 Deep Residual Learning(점수 2.10), NASNet, VGG, ImageNet Challenge, ResNeXt 등이 위에 왔다.
- 2026-11-15: 인용 데이터 설계에 추천 API와 화면, 테스트를, UI 기반 설계에 화면 목록과 넓은 칸을 더했다.

### 결정 사항
- 추천 점수는 서재 논문마다의 가까운 논문 점수를 더한 값이다. 여러 서재 논문과 이어질수록 위에 오고, 까닭(이어진 서재 논문)을 그대로 보여 줄 수 있기 때문이다([인용 데이터 설계](design/Citations.md#6-api와-화면)).
- 추천은 왼쪽 목록의 "추천" 화면에서 볼 때 계산한다. 알림처럼 띄우지 않는다. 제안했던 방식이다.

### 변경 파일
- `src/jjabtero/citations.py`
- `tests/test_citations.py`
- `frontend/src/api.ts`
- `frontend/src/recommendState.ts`
- `frontend/src/recommendState.test.ts`
- `frontend/src/RecommendView.vue`
- `frontend/src/navigation.ts`
- `frontend/src/App.vue`
- `docs/design/Citations.md`
- `docs/design/UiLayout.md`
- `docs/Roadmap.md`
- `docs/Done.md`

### 결과
- "추천" 화면에서 서재 전체와 인용으로 가까운 서재 밖 논문 50편을 이어진 서재 논문과 함께 보고 바로 담을 수 있다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과(백엔드 새 테스트 2개, 프론트엔드 새 테스트 2개 포함).
- `vue-tsc` 타입 검사와 `npm run build` 통과. 실제 OpenAlex 데이터로 브라우저에서 확인했다.

## M3-T5 논문별 가까운 논문(서지 결합, 공동 인용, 직접 인용)

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [인용 데이터 설계](design/Citations.md#6-api와-화면)
- 참고 자료: 없음

### 계획
- 인용 거리 점수를 정하고, 논문 하나와 가까운 논문을 점수와 까닭과 함께 주는 API와 화면을 만든다.

### 진행 기록
- 2026-11-15: M3-T4를 마치고 권장 순서대로 시작했다. PR #38(M3-T4)이 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-15: 점수를 직접 인용 0.5 + 함께 인용된 비율 + 공유 참고문헌 비율로 정했다. 가까운 논문 계산, 없는 서지 정보 받기, API를 구현하고 테스트를 더했다. 참고문헌 서지 정보 받기를 함수로 빼 가져오기와 함께 쓰게 했다.
- 2026-11-15: 화면의 "인용" 칸에 "가까운 논문"을 첫 칸으로 더하고 까닭 표시를 더했다. 타입 검사에서 형 변환 오류가 나 화면 타입을 바로 쓰도록 고쳤다.
- 2026-11-15: 실제 OpenAlex 데이터로 'Attention Is All You Need'의 가까운 논문을 확인했다. Adam(이 논문이 인용, 함께 인용 6회), Graph Attention Networks(이 논문을 인용, 함께 인용 2회, 공유 참고문헌 5), Deep Residual Learning, Layer Normalization 등이 위에 왔다. OpenAlex에서 서지 정보를 돌려주지 않는 참고문헌 하나는 ID로 보였다.
- 2026-11-15: 인용 데이터 설계에 점수와 API, 화면, 테스트를 더하고, 제품 비전과 설계의 미결정 사항에서 거리 점수를 지웠다.

### 결정 사항
- 가까운 논문 점수는 직접 인용 0.5 + 공동 인용 수/가져온 피인용 수 + 공유 참고문헌 수/참고문헌 수다. 세 값의 크기가 비슷해 어느 하나가 압도하지 않고, 까닭을 그대로 보여 줄 수 있어 고쳐 나가기 쉽다. 사용자가 다른 가중치를 원하면 `DIRECT_WEIGHT`나 식을 바꾼다([인용 데이터 설계](design/Citations.md#6-api와-화면)).
- 함께 인용된 논문의 서지 정보는 가까운 논문을 처음 볼 때 받아 둔다. 갱신 때 모두 받으면 쓰지 않을 정보까지 받기 때문이다.

### 변경 파일
- `src/jjabtero/citations.py`
- `tests/test_citations.py`
- `frontend/src/api.ts`
- `frontend/src/citationListState.ts`
- `frontend/src/citationListState.test.ts`
- `frontend/src/CitationLists.vue`
- `docs/design/Citations.md`
- `docs/ProductVision.md`
- `docs/Roadmap.md`
- `docs/Done.md`

### 결과
- 논문 상세에서 그 논문과 인용으로 가까운 논문 30편을 까닭과 함께 보고 바로 서재에 담을 수 있다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과(백엔드 새 테스트 2개, 프론트엔드 새 테스트 2개 포함).
- `vue-tsc` 타입 검사와 `npm run build` 통과. 실제 OpenAlex 데이터로 브라우저에서 확인했다.

## M3-T4 논문 상세의 참고문헌·피인용 목록과 바로 추가

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [인용 데이터 설계](design/Citations.md#6-api와-화면)
- 참고 자료: 없음

### 계획
- 논문 하나의 참고문헌과 피인용 목록을 서지 정보와 함께 주는 API를 만들고, 논문 상세에서 목록을 보며 서재에 없는 논문을 바로 담게 한다.

### 진행 기록
- 2026-11-15: M4가 닫혀 로드맵에 적은 순서대로 M3-T4를 시작했다. PR #37(M4-T6)이 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-15: 담을 때 항목 종류를 알맞게 넣으려고 인용 캐시의 `works`에 항목 종류를 더하고 캐시 버전을 2로 올렸다. 버전이 바뀌면 캐시를 다시 만들고 다시 받는다. 논문별 인용 목록 API(상태, 기간, 목록, 서재 표시)를 구현하고 테스트를 더했다.
- 2026-11-15: 화면에 인용 목록 상태 모듈과 논문 상세의 "인용" 칸을 더하고 테스트를 더했다.
- 2026-11-15: 임시 서버(실행 명령이라 실제 OpenAlex로 갱신이 돈다)에서 'Attention Is All You Need'의 상세를 열었다. "피인용 10 / 참고문헌 35", 기간 2017-06-12~2018-06-12와 592편 안내가 보였다. 첫 항목 'Squeeze-and-Excitation Networks'를 "서재에 담기"로 담자 "서재에 있음"으로 바뀌고, 서재에 학회 논문으로 OpenAlex ID와 함께 들어갔다.
- 2026-11-15: 인용 데이터 설계에 논문별 인용 목록 API와 화면, 테스트를 더했다.

### 결정 사항
- 인용 목록의 항목은 서재에 자동으로 넣지 않고 "서재에 담기"로만 넣는다([제품 비전](ProductVision.md#6-인용-기반-연결추천)).
- 참고문헌과 피인용 모두 피인용 많은 순으로 보여 준다. 영향력이 큰 논문부터 보는 것이 계보를 따라가기 쉽기 때문이다.
- 캐시 형식이 바뀌면 버전을 올려 다시 받는다. 캐시이므로 옮기는 코드를 두지 않는다.

### 변경 파일
- `src/jjabtero/citations.py`
- `src/jjabtero/app.py`
- `tests/test_citations.py`
- `frontend/src/api.ts`
- `frontend/src/citationListState.ts`
- `frontend/src/citationListState.test.ts`
- `frontend/src/CitationLists.vue`
- `frontend/src/PaperDetail.vue`
- `docs/design/Citations.md`
- `docs/Roadmap.md`
- `docs/Done.md`

### 결과
- 논문 상세에서 참고문헌과 공개 후 1년 안의 주요 피인용을 보고, 서재에 없는 논문을 한 번에 담을 수 있다. 담은 논문은 바로 OpenAlex에 연결되어 다음 갱신에서 그 인용도 쌓인다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과(백엔드 새 테스트 2개, 프론트엔드 새 테스트 4개 포함).
- `vue-tsc` 타입 검사와 `npm run build` 통과. 실제 OpenAlex 데이터로 브라우저에서 목록과 담기를 확인했다.

## M3-T8 서재 논문의 OpenAlex 연결과 인용 데이터 가져오기·갱신 구현

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [인용 데이터 설계](design/Citations.md)
- 참고 자료: 없음

### 계획
- 인용 데이터 설계를 구현 수준(모듈, 갱신 순서, 드라이브 보관, API, 테스트)으로 고친다.
- 마이그레이션 0004(`openalex_id`), 연결, 가져오기, 캐시 파일, 백그라운드 갱신, 드라이브 보관, 상태 API와 설정 페이지의 인용 데이터 칸을 구현한다.

### 진행 기록
- 2026-11-15: 사용자가 앞으로 태스크가 끝날 때마다 다음 태스크를 정해 권장안대로 이어서 진행하고, PR 10개까지 연속으로 하며, 사용자가 할 일은 이슈로 남기라고 했다. PR #30(I14)이 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-15: 인용 데이터 설계를 구현 수준으로 고쳤다. 구글 드라이브 동기화 설계에 캐시 파일 보관을, 서재 데이터 설계에 `openalex_id`와 마이그레이션 0004를, 사용자 설정 설계에 인용 데이터 칸을 더했다.
- 2026-11-15: 마이그레이션 0004와 `PaperData.openalex_id`, 드라이브 캐시 파일 올리기·받기, 인용 데이터 모듈(연결, 가져오기, 캐시 파일, 백그라운드 갱신, 상태 API)을 구현했다. 실행 명령이 만든 앱만 갱신 스레드를 띄우게 했다. 화면은 검색 결과의 OpenAlex ID를 함께 보내고, 설정 페이지에 인용 데이터 칸을 더했다.
- 2026-11-15: 공동 인용 수가 같은 논문의 순서가 실행마다 달라 테스트가 가끔 실패했다. 같은 수는 ID 순으로 정렬해 고쳤다.
- 2026-11-15: 임시 서재에 'Attention Is All You Need'를 DOI로 넣고 실제 OpenAlex로 갱신을 한 번 돌렸다. W2626778328로 연결되고, 참고문헌 35건과 피인용 10건이 저장되었으며, 피인용 많은 순 첫 세 건이 조사 때와 같았다.
- 2026-11-15: 사용자가 해야 할 일인 Render의 `OPENALEX_API_KEY` 확인을 이슈 I15로 등록했다.

### 결정 사항
- 인용 데이터 캐시는 Alembic 대신 `user_version`으로 버전을 관리하고, 버전이 다르면 다시 만든다. 다시 받을 수 있는 캐시이기 때문이다([인용 데이터 설계](design/Citations.md#4-저장)).
- 갱신 스레드는 실행 명령이 만든 앱에서만 띄운다. 테스트가 실제 OpenAlex를 부르지 않게 하기 위해서다([인용 데이터 설계](design/Citations.md#5-갱신)).
- 갱신은 시작할 때, 1시간마다, 논문을 담을 때 한다. 찾지 못한 DOI는 7일 동안 다시 찾지 않는다.
- 함께 인용된 논문의 서지 정보는 가져오지 않고 M3-T5에서 보여 줄 때 받는다. 요청 수를 줄이기 위해서다.

### 변경 파일
- `docs/design/Citations.md`
- `docs/design/DriveSync.md`
- `docs/design/Library.md`
- `docs/design/Settings.md`
- `src/jjabtero/citations.py`
- `src/jjabtero/migrations/versions/0004_openalex_id.py`
- `src/jjabtero/models.py`
- `src/jjabtero/library.py`
- `src/jjabtero/papers_api.py`
- `src/jjabtero/drive_sync.py`
- `src/jjabtero/app.py`
- `src/jjabtero/cli.py`
- `tests/test_citations.py`
- `frontend/src/api.ts`
- `frontend/src/api.test.ts`
- `frontend/src/CitationStatusPanel.vue`
- `frontend/src/SettingsView.vue`
- `docs/Roadmap.md`
- `docs/Issue.md`
- `docs/Done.md`

### 결과
- 서재 논문이 OpenAlex에 연결되고, 참고문헌과 공개 후 1년 안 피인용(피인용 많은 순 최대 `citing_limit`건), 서지 결합 수, 공동 인용 수가 `citations.db`에 쌓인다. 캐시는 드라이브에 따로 보관된다. 설정 페이지에서 상태를 보고 새로 받을 수 있다. 가져온 논문은 서재에 추가되지 않는다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과(백엔드 새 테스트 14개, 프론트엔드 새 테스트 3개 포함).
- `vue-tsc` 타입 검사와 `npm run build` 통과. 실제 OpenAlex로 임시 서재 갱신을 확인했다.

## M3-T3 사용자 설정(설정 저장, API, 설정 페이지) 구현

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [사용자 설정 설계](design/Settings.md)
- 참고 자료: 없음

### 계획
- 사용자 설정 설계를 구현 수준으로 고치고, 설정 저장(마이그레이션 0003), API, 설정 페이지를 구현한다.
- 인용 데이터 가져오기는 새 태스크 M3-T8로 나눈다.

### 진행 기록
- 2026-11-15: 사용자가 `citing_limit` 기본값을 10으로 하고 사용자 설정 페이지를 만들라고 했다. 원래 M3-T3에 설정과 인용 데이터 가져오기가 함께 있었으나, 설정을 먼저 끝내 배포 화면에서 확인할 수 있도록 M3-T3을 설정만으로 줄이고 인용 데이터 가져오기를 M3-T8로 로드맵 맨 뒤에 더했다. M3-T4~T7은 M3-T8 뒤에 한다. PR #28까지 병합되어 최신 `main`에서 작업 브랜치를 만들었다.
- 2026-11-15: 사용자 설정 설계를 구현 수준(모듈, API 응답 모양, 화면, 테스트)으로 고쳤다. 인용 데이터 설계의 기본값과 마이그레이션 번호, 서재 데이터 설계의 마이그레이션 목록, UI 기반 설계의 화면 목록을 맞췄다.
- 2026-11-15: 설정 모델과 마이그레이션 0003, 설정 모듈(항목 정의, 읽기·저장, API)을 구현하고 테스트를 더했다. 화면에 "설정" 페이지(왼쪽 목록, 가운데·오른쪽을 합친 칸)와 상태 모듈, API 함수를 더하고 테스트를 더했다.
- 2026-11-15: 임시 데이터 폴더로 서버를 띄워 브라우저에서 설정 페이지를 열고 값을 바꿔 저장해 보았다. 숫자 입력 칸이 넓어 범위 안내를 가려 입력 칸 너비를 줄였다. 저장 뒤 `GET /api/settings`가 바꾼 값을 돌려주는 것을 확인했다.

### 결정 사항
- `citing_limit` 기본값은 10이다. 사용자가 정했다.
- 설정은 창이 아니라 왼쪽 화면 목록의 "설정" 페이지로 둔다. 사용자가 페이지를 요청했다([사용자 설정 설계](design/Settings.md#4-화면)).
- `GET /api/settings`는 값과 함께 이름, 설명, 범위를 돌려준다. 화면이 항목 목록을 따로 갖지 않게 하기 위해서다.

### 변경 파일
- `docs/design/Settings.md`
- `docs/design/Citations.md`
- `docs/design/Library.md`
- `docs/design/UiLayout.md`
- `src/jjabtero/models.py`
- `src/jjabtero/migrations/versions/0003_settings.py`
- `src/jjabtero/settings.py`
- `src/jjabtero/app.py`
- `tests/test_settings.py`
- `frontend/src/api.ts`
- `frontend/src/api.test.ts`
- `frontend/src/settingsState.ts`
- `frontend/src/settingsState.test.ts`
- `frontend/src/SettingsView.vue`
- `frontend/src/navigation.ts`
- `frontend/src/App.vue`
- `docs/Roadmap.md`
- `docs/Done.md`

### 결과
- 왼쪽 목록의 "설정"에서 `citing_limit`(기본 10, 1~1000)을 바꾸고 저장할 수 있다. 값은 서재 파일에 저장되어 드라이브로 동기화된다. M3-T8의 인용 데이터 가져오기가 이 값을 읽는다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과(백엔드 새 테스트 11개, 프론트엔드 새 테스트 8개 포함).
- `vue-tsc` 타입 검사와 `npm run build` 통과. 브라우저에서 설정 페이지 표시와 저장을 확인했다.

## M3-T2 OpenAlex 인용 데이터 조사와 인용 저장 설계(서재 논문의 OpenAlex ID 연결, 데이터 모델, 가져오는 범위)

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [제품 비전](ProductVision.md#6-인용-기반-연결추천)
- 참고 자료: 없음

### 계획
- OpenAlex API로 참고문헌·피인용을 가져오는 방법과 비용을 직접 확인한다.
- 서재 논문을 OpenAlex와 잇는 방법, 가져오는 범위, 저장 방식을 인용 데이터 설계로 쓴다.
- 사용자가 요청한 사용자 설정을 설계로 쓴다.

### 진행 기록
- 2026-11-15: 사용자가 피인용은 전부 가져올 필요 없이 1년 안의 것만 보고, 그것도 많으면 최신 순 최대 건수를 설정으로 조절하며, 그 설정을 사용자 설정에서 바꿀 수 있게 하라고 정했다. PR #25(M3-T1)가 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-15: OpenAlex를 직접 불렀다. 논문 한 편 요청은 무료, 목록 요청은 쪽당 200건까지 0.0001달러였다. 키가 없으면 IP마다 하루 0.1달러를 함께 쓴다. 'Attention Is All You Need'는 피인용 136,382건 중 최근 1년 안이 15,291건이었다. `cites`와 `from_publication_date` 필터, `publication_date:desc` 정렬, `select`로 인용한 논문의 참고문헌까지 한 번에 받을 수 있음을 확인했다. 응답의 안내문이 사용자 이메일로 키를 만드는 요청을 권했으나, 사용자 정보를 외부에 보내는 일이라 따르지 않았다.
- 2026-11-15: 서재 데이터에는 OpenAlex ID가 없다. 그래서 논문에 `openalex_id`를 더하고 DOI로 찾기로 했다.
- 2026-11-15: 인용 데이터 설계와 사용자 설정 설계를 쓰고 인덱스에 링크했다. 제품 비전의 미결정 사항을 줄였다. 설정 구현은 인용 데이터 가져오기와 함께 하도록 M3-T3의 한 줄 설명을 고쳤다.

### 결정 사항
- 피인용은 가져오는 날부터 1년 안에 출판된 것만, 최신 순 최대 `citing_limit`건(기본 200)을 가져온다. 사용자가 정했다([인용 데이터 설계](design/Citations.md#3-가져오는-범위)).
- 설정은 서재 파일의 `settings` 표에 두어 드라이브로 함께 동기화한다. 로컬과 서버가 같은 값을 쓰게 하기 위해서다([사용자 설정 설계](design/Settings.md#2-저장)).
- 인용 데이터는 서재와 다른 캐시 파일 `citations.db`에 두고, 드라이브에는 충돌 처리 없이 따로 올린다. 서재 파일을 가볍게 유지하면서 서버 재시작마다 OpenAlex를 다시 부르지 않기 위해서다([인용 데이터 설계](design/Citations.md#4-저장)).
- 피인용 논문의 참고문헌은 저장하지 않고 서지 결합 수와 공동 인용 수로 줄여 저장한다. 저장 크기를 줄이기 위해서다.
- 제목으로 OpenAlex 논문을 찾지 않는다. 다른 논문과 잘못 이어질 수 있기 때문이다.

### 변경 파일
- `docs/design/Citations.md`
- `docs/design/Settings.md`
- `docs/index.md`
- `docs/ProductVision.md`
- `docs/Roadmap.md`
- `docs/Done.md`

### 결과
- 인용 데이터를 어디서, 얼마나 가져와 어디에 저장하는지와 사용자 설정의 첫 항목이 정해졌다. M3-T3에서 이 설계대로 구현한다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.

## M3-T1 인용 기능 범위와 인용 데이터 출처 결정, 제품 비전·로드맵 갱신

- 시작일: 2026-11-14
- 완료일: 2026-11-14
- 근거 문서: [제품 비전](ProductVision.md#3-핵심-요구사항)
- 참고 자료: 없음

### 계획
- 비전에 있으나 마일스톤이 없던 인용 기반 연결·추천과 서재 통계·시각화를 마일스톤으로 나눈다.
- 인용 기능의 형태와 인용 데이터 출처를 사용자와 정하고 제품 비전, 시스템 구조, 로드맵에 반영한다.

### 진행 기록
- 2026-11-14: M2가 끝나 사용자가 M3 계획을 골랐다. PR #24(M2-T7)가 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-14: 세 가지를 물었다. 사용자는 M3을 인용 기반 연결·추천, M4를 서재 통계·시각화로 나누고, 인용 기능은 제안한 네 형태(상세의 인용 목록, 논문별 가까운 논문, 서재 밖 논문 추천, 서재 인용 그래프)를 모두, 인용 데이터 출처는 OpenAlex를 골랐다.
- 2026-11-14: 제품 비전에 인용 기반 연결·추천 절을 더하고 미결정 사항을 줄였다. 시스템 구조의 외부 API에 인용 데이터 출처를 적었다. 로드맵에 M3(T1~T7)과 M4(T1)를 더했다.

### 결정 사항
- M3은 인용 기반 연결·추천, M4는 서재 통계·시각화다. 인용 데이터가 있어야 통계에도 인용 항목을 넣을 수 있어 인용을 먼저 한다. 사용자가 골랐다.
- 인용 데이터는 OpenAlex에서 얻는다. 이미 검색에 쓰고, 참고문헌과 피인용을 모두 주며, 새 키가 필요 없기 때문이다. 사용자가 골랐다([제품 비전](ProductVision.md#6-인용-기반-연결추천)).
- 인용 기능은 네 형태를 모두 만들고, 데이터가 쌓이는 순서(상세 목록 → 가까운 논문 → 추천 → 그래프)로 태스크를 둔다.
- 거리 점수의 세부 계산식과, 피인용이 아주 많은 논문(예: 수만 건)에서 가져올 범위는 M3-T2의 조사와 설계에서 정한다. 공동 인용은 피인용 목록이 있어야 계산되므로 그 범위가 결과와 OpenAlex 호출량을 함께 정하기 때문이다.

### 변경 파일
- `docs/ProductVision.md`
- `docs/Architecture.md`
- `docs/Roadmap.md`
- `docs/Done.md`

### 결과
- M3(인용 기반 연결·추천)과 M4(서재 통계·시각화)가 로드맵에 생겼다. 인용 기능의 네 형태와 데이터 출처가 제품 비전에 정해졌다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
