# UI 기반 설계

이 문서는 프론트엔드의 UI 도구, 테마, 화면 배치를 정한다. 기능별 화면의 내용은 기능 설계 문서(예: [논문 검색과 추가 설계](PaperSearch.md#4-화면))에 있다. 기술 스택은 [시스템 구조](../Architecture.md)에 있다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. UI 도구

| 도구 | 버전 | 쓰는 곳 |
| --- | --- | --- |
| PrimeVue | 4.5.5 (고정) | 표, 입력, 버튼, 분할 패널, 알림 같은 컴포넌트 |
| @primeuix/themes | 2.0.3 (고정) | PrimeVue 테마. Aura 프리셋을 쓴다. |
| primeicons | 7.0.0 (고정) | 아이콘 |
| Tailwind CSS | 4 | 배치, 여백, 글자 크기 같은 세부 스타일 |
| tailwindcss-primeui | 0.6 | Tailwind에서 PrimeVue 테마 색(`primary`, `surface` 등)을 쓰게 하는 플러그인 |

- PrimeVue, 테마, 아이콘은 정확한 버전으로 고정한다. 이 세 패키지는 다음 주 버전(PrimeVue 5, 테마 3, primeicons 8)부터 MIT가 아니라 라이선스 키가 필요한 상용 라이선스(PrimeUI License)로 바뀌었기 때문이다. 이 버전들로 올리는 일은 사용자가 정한다.
- 표와 입력처럼 동작이 많은 부품은 PrimeVue로 쓰고, PrimeVue에 없는 배치와 간격은 Tailwind 클래스로 쓴다. 같은 일을 하는 컴포넌트를 직접 만들지 않는다.

## 2. 설정과 테마

- 진입점 [main 모듈](../../frontend/src/main.ts)이 PrimeVue를 등록한다. 테마는 Aura 프리셋이다.
- 다크 모드는 운영체제 설정을 따른다(PrimeVue `darkModeSelector: 'system'`, Tailwind 기본 `dark:`). 바꾸는 단추는 아직 두지 않는다.
- PrimeVue 스타일은 CSS 계층 `primevue`에 넣고, 계층 순서를 `theme, base, primevue`로 둔다. Tailwind 유틸리티가 PrimeVue 스타일보다 우선하게 하기 위해서다.
- 전역 스타일 `style.css`는 Tailwind와 `tailwindcss-primeui`를 불러오고, 화면 전체 높이를 앱에 준다.

## 3. 화면 배치

Zotero형 3단 배치다. 사용자가 골랐다.

```text
┌──────────────────────────────────────────────────────┐
│ Jjabtero                                 서버 상태    │  머리줄
├──────────┬──────────────────────────┬────────────────┤
│ 서재     │                          │                │
│ 논문 검색│   가운데: 고른 화면       │  오른쪽: 상세  │
│          │   (목록, 검색 결과)       │  (고른 항목)   │
│          │                          │                │
└──────────┴──────────────────────────┴────────────────┘
```

- `App.vue`가 머리줄과 PrimeVue `Splitter`의 세 칸(왼쪽 약 15%, 가운데 약 55%, 오른쪽 약 30%)을 그린다. 칸 너비는 끌어서 바꿀 수 있다. 앱은 창 높이를 꽉 채우고, 칸마다 따로 스크롤한다.
- 머리줄 오른쪽은 서버 상태(연결됨과 버전, 또는 연결 실패)를 태그로 보여 준다.
- 왼쪽 칸 `Sidebar.vue`는 화면 목록이다. 지금은 "서재"와 "논문 검색" 둘이며, 고른 화면을 강조한다. 태그 목록은 M1-T6에서 더한다.
- 가운데 칸은 고른 화면을 보여 준다. "서재" 화면은 M1-T5에서 만들며, 그 전에는 준비 중이라는 안내를 보여 준다. 처음 열면 "논문 검색" 화면이다.
- 오른쪽 칸은 가운데에서 고른 항목의 상세를 보여 준다. 고른 항목이 없으면 항목을 고르라는 안내를 보여 준다.
- 화면 이름과 상태는 [navigation 모듈](../../frontend/src/navigation.ts)이 가진다. [VIEWS](../../frontend/src/navigation.ts#VIEWS)는 화면 목록(이름, 표시 이름, 아이콘)이고, [DEFAULT_VIEW](../../frontend/src/navigation.ts#DEFAULT_VIEW)는 처음 화면이다.

## 4. 테스트와 확인

- 화면 로직은 `.ts` 모듈에 두고 Vitest로 테스트한다([시스템 구조](../Architecture.md#2-디렉터리-구조)의 `.vue` 제약). [navigation.test](../../frontend/src/navigation.test.ts)는 화면 목록과 처음 화면을 확인한다.
- 모양은 자동 테스트로 확인하지 않는다. 화면을 크게 바꾼 작업은 빌드한 앱을 헤드리스 브라우저로 찍어 확인하고, 그 결과를 작업 기록에 적는다.
