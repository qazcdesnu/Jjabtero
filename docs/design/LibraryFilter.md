# 서재 필터 설계

이 문서는 서재 화면에서 논문을 글자, 태그, 항목 종류, 연도로 걸러 보는 기능을 정한다. 서재 화면 자체는 [서재 화면 설계](LibraryView.md)에 있다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 거르는 위치

서재 화면은 서재 전체를 한 번에 불러오므로([서재 화면 설계](LibraryView.md#1-api)), 거르기는 화면에서 한다. 서버 API는 더하지 않는다. 개인 서재 크기에서는 입력할 때마다 바로 걸러도 충분히 빠르고, 서버를 다시 부르지 않아도 되기 때문이다.

## 2. 필터 조건

거르기는 [libraryFilter 모듈](../../frontend/src/libraryFilter.ts)에 둔다.

- [LibraryFilter](../../frontend/src/libraryFilter.ts#LibraryFilter)는 필터 조건이다. `text`(글자), `tags`(태그 목록), `itemTypes`(항목 종류 목록), `readStatuses`(읽기 상태 목록), `yearFrom`, `yearTo`(연도, 없으면 `null`)를 가진다. [emptyFilter](../../frontend/src/libraryFilter.ts#emptyFilter)는 아무것도 거르지 않는 조건이다.
- [filterPapers](../../frontend/src/libraryFilter.ts#filterPapers)는 조건을 모두 만족하는 논문만 순서를 지켜 돌려준다.
  - 글자: 앞뒤 공백을 지우고 공백으로 나눈 낱말이 모두, 대소문자를 가리지 않고 제목·저자·게재처·DOI·태그 가운데 어딘가에 들어 있어야 한다. 비면 거르지 않는다.
  - 태그: 고른 태그를 모두 가진 논문만 남긴다. 태그를 더 고를수록 좁아진다.
  - 항목 종류: 고른 종류 가운데 하나인 논문만 남긴다. 비면 거르지 않는다.
  - 읽기 상태: 고른 상태 가운데 하나인 논문만 남긴다. 비면 거르지 않는다.
  - 연도: `yearFrom` 이상, `yearTo` 이하인 논문만 남긴다(양 끝 포함). 둘 중 하나라도 있으면 연도가 없는 논문은 빠진다.
- [isFilterActive](../../frontend/src/libraryFilter.ts#isFilterActive)는 조건이 하나라도 걸려 있으면 참이다.
- [tagCounts](../../frontend/src/libraryFilter.ts#tagCounts)는 서재 전체(거르기 전)의 태그마다 논문 수를 세어 태그 이름 가나다순으로 돌려준다.

## 3. 화면 상태

[createLibraryState](../../frontend/src/libraryState.ts#createLibraryState)에 더한다.

- 상태 `filter`(처음은 `emptyFilter()`), 거른 목록 `visible`, 태그 목록 `tags`(`tagCounts`의 결과)를 둔다.
- `toggleTag(name)`은 태그를 필터에 넣거나 뺀다. `clearFilter()`는 필터를 처음으로 돌린다.
- 고른 논문은 거른 목록 안에서 찾는다. 거르기로 사라지면 상세 칸도 빈다.
- 앱을 열 때 서재를 한 번 불러온다. 사이드바 태그 목록이 처음부터 보이게 하기 위해서다.

## 4. 화면

- 사이드바(`Sidebar.vue`): 화면 목록 아래에 "태그" 제목과 태그 목록을 둔다. 태그마다 이름과 논문 수가 보이고, 누르면 그 태그를 필터에 넣거나 빼며 서재 화면으로 간다. 필터에 든 태그는 강조한다. 태그가 없으면 안내 문구를 보여 준다.
- 서재 화면(`LibraryView.vue`) 위쪽, 제목줄 아래에 필터 줄을 둔다.
  - 글자 입력(검색 아이콘), 항목 종류와 읽기 상태 여러 개 고르기(PrimeVue `MultiSelect`), 연도 시작·끝 입력(PrimeVue `InputNumber`), 필터 지우기 단추(필터가 걸려 있을 때만).
  - 필터에 든 태그는 지울 수 있는 칩으로 필터 줄에 보여 준다.
  - 제목줄의 논문 수는 필터가 걸리면 "전체 N편 중 M편"으로 보인다.
  - 거른 결과가 비면 "조건에 맞는 논문이 없습니다."를 보여 준다.

## 5. 테스트

- [libraryFilter.test](../../frontend/src/libraryFilter.test.ts)는 조건마다 거르기(글자의 여러 낱말과 대소문자, 태그 AND, 항목 종류 OR, 연도 양 끝과 연도 없는 논문), 조건 합치기, 빈 조건, `isFilterActive`, `tagCounts`를 확인한다.
- [libraryState.test](../../frontend/src/libraryState.test.ts)는 `visible`, `toggleTag`, `clearFilter`, 거르기로 고른 논문이 사라지는 경우를 확인한다.
