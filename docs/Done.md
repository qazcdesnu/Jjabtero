# 완료

이 문서는 끝난 작업의 상세 기록이다. 최신 기록이 맨 위에 온다. 기록 형식은 [작업 관리 규칙](TaskRule.md#5-기록-형식)을 따르며, 할 일 목록은 [로드맵](Roadmap.md)과 [이슈](Issue.md)에 있다. 닫힌 마일스톤의 기록은 [작업 관리 규칙](TaskRule.md#47-완료-기록-보관)에 따라 보관 문서로 옮긴다. 보관 문서: [M0 시작](Done-M0.md), [M1 기본 서재](Done-M1.md), [M2 Render 배포](Done-M2.md), [M4 PDF 리더](Done-M4.md), [M3 인용 기반 연결·추천](Done-M3.md), [M6 리더 인용 미리보기](Done-M6.md), [M7 태그](Done-M7.md), [M8 AI 대화](Done-M8.md). 전체 문서 목록은 [문서 인덱스](index.md)에서 확인한다.

## I34 Gemini 모델 목록을 오늘 무료 등급인 모델로만 거르고 매일 자정(한국 시각)에 갱신

- 시작일: 2026-11-19
- 완료일: 2026-11-19
- 근거 문서: [AI 대화 설계](design/AiChat.md#4-gemini-호출)
- 참고 자료: [Google AI plans](https://aistudio.google.com/docs/google-ai-plans), [Gemini API 가격표](https://ai.google.dev/gemini-api/docs/pricing)

### 계획
- 프로필의 Gemini 모델 목록을 무료 한도가 있는 모델로만 거르고, 그 목록을 매일 자정에 갱신한다.

### 진행 기록
- 2026-11-19: 사용자가 모델 목록을 매일 자정에 구글에서 Pro 구독 사용자에게 무료 한도를 주는 모델로만 가져와 갱신하라고 요청했다. 병합되지 않은 가장 최근 브랜치 `m8-t3-reader-ai-chat`에서 작업 브랜치를 만들었다.
- 2026-11-19: 구글 문서를 확인하니 Pro 구독 혜택은 AI Studio 웹 화면 안에서만 쓰이고, API 키 사용은 따로 셈한다. 무료 등급 목록을 주는 API는 없어, 가격표 페이지를 받아 모양을 살폈다. 모델 절마다 모델 ID와 표준 탭의 입력 가격 무료 등급 칸이 있어 읽을 수 있었다. 받은 페이지에서 24개 무료 모델 ID를 읽었고, 구글 문서를 요약해 본 목록과 같았다.
- 2026-11-19: 무료 목록 모듈(`ai_models`)과 자정 갱신 스레드를 만들고, 모델 API가 무료 모델만 보이고 고르게 했다. 프로필 창에 무료 등급 안내, 마지막 확인 시각, 지난 목록·무료 목록 밖 모델 경고를 더했다.

### 결정 사항
- Pro 구독은 API 키에 무료 한도를 주지 않으므로, API 키로 무료로 쓸 수 있는 Gemini API 무료 등급(가격표의 표준 요금 입력 가격이 "Free of charge")으로 거른다.
- 자정은 한국 시각이다. 서버가 자정에 잠들어 있었을 수 있어, 목록을 쓸 때 오늘 것이 아니면 다시 읽는다.
- 가격표를 못 읽으면 지난 목록을 쓰고 화면에 알린다. 고른 모델이 무료 목록에서 빠져도 바꾸지 않고 알리기만 한다. 사용자의 선택을 몰래 바꾸지 않기 위해서다.

### 변경 파일
- `src/jjabtero/ai_models.py`, `src/jjabtero/ai.py`, `src/jjabtero/app.py`, `src/jjabtero/cli.py`, `tests/test_ai_models.py`, `tests/test_ai.py`
- `frontend/src/api.ts`, `frontend/src/profileState.ts`, `frontend/src/profileState.test.ts`, `frontend/src/ProfileDialog.vue`
- `docs/design/AiChat.md`, `docs/Issue.md`, `docs/Done.md`

### 결과
- 프로필의 모델 목록에는 그 키로 쓸 수 있고 오늘 무료 등급인 Gemini 모델만 나오며, 목록은 매일 한국 자정에 갱신된다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 앱과 같은 HTTP 설정으로 실제 가격표를 받아 무료 모델 24개를 읽었다(대화에 쓸 만한 것: gemini-3.8-flash, gemini-3.6-flash, gemini-3.5-flash-lite, gemini-4-hydrogen, gemini-2.5-pro, gemini-2.5-flash 등).
- 로컬 서재 사본(포트 8010)에서 키 상태와 모델 목록을 브라우저에서 가짜로 주어, 프로필 창의 무료 등급 안내·마지막 확인 시각·무료 목록 밖 모델 경고를 확인했다. 콘솔 오류는 없었다.

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
