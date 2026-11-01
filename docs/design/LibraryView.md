# 서재 화면 설계

이 문서는 서재에 넣은 논문을 목록으로 보고, 골라서 상세를 보고, 지우는 화면과 그 API를 정한다. 저장 함수는 [서재 데이터 설계](Library.md#4-저장-함수)에, 화면 배치는 [UI 기반 설계](UiLayout.md#3-화면-배치)에 있다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. API

[papers_api 모듈](../../src/jjabtero/papers_api.py)에 더한다. 응답 모양은 논문 추가 API와 같은 `PaperOut`이다([논문 검색과 추가 설계](PaperSearch.md#3-api)).

- `GET /api/papers`는 [read_papers](../../src/jjabtero/papers_api.py#read_papers)가 처리한다. 서재의 모든 논문을 최근에 넣은 것부터 돌려준다. 개인 서재는 많아야 수천 편이라 한 번에 모두 돌려주고, 정렬은 화면에서 한다.
- `DELETE /api/papers/{paper_id}`는 [remove_paper](../../src/jjabtero/papers_api.py#remove_paper)가 처리한다. 성공하면 204, 없는 ID면 404다.

## 2. 화면 상태

서재 화면의 상태와 동작은 [libraryState 모듈](../../frontend/src/libraryState.ts)의 [createLibraryState](../../frontend/src/libraryState.ts#createLibraryState)가 만든다. 목록·삭제 함수를 인자로 받아, 테스트에서 가짜로 바꿀 수 있다.

- 상태: 논문 목록, 불러오는 중 여부, 불러오기 오류, 고른 논문 ID, 삭제 오류.
- `load()`는 목록을 불러온다. 고른 논문이 새 목록에 없으면 고른 것을 비운다.
- `select(paper)`는 논문을 고르고, `null`이면 고른 것을 비운다.
- `remove(paper)`는 논문을 지우고 목록에서 뺀다. 고른 논문이었으면 고른 것을 비운다. 404면 이미 없는 것이므로 똑같이 목록에서 뺀다. 그 밖의 실패는 삭제 오류로 둔다.
- API 함수는 [api 모듈](../../frontend/src/api.ts)의 [listPapers](../../frontend/src/api.ts#listPapers)와 [deletePaper](../../frontend/src/api.ts#deletePaper)다. `deletePaper`는 404면 [PaperNotFoundError](../../frontend/src/api.ts#PaperNotFoundError)를, 그 밖의 실패면 상태 코드를 담은 오류를 던진다.
- 화면에 쓰는 표시 이름과 형식은 [labels 모듈](../../frontend/src/labels.ts)에 둔다. [ITEM_TYPE_LABELS](../../frontend/src/labels.ts#ITEM_TYPE_LABELS)는 항목 종류의 한국어 이름이고, [formatDate](../../frontend/src/labels.ts#formatDate)는 시각 문자열을 `YYYY-MM-DD`로 바꾼다. 검색 화면도 같은 모듈을 쓴다.

## 3. 화면

- 사이드바에서 "서재"를 고르면 가운데 칸에 `LibraryView.vue`가 보인다. 이 화면으로 올 때마다 목록을 다시 불러온다. 검색 화면에서 넣은 논문이 바로 보이게 하기 위해서다.
- `LibraryView.vue`
  - 위에 "서재"와 논문 수, 새로 고침 단추가 있다. 불러오기 오류는 경고로 보여 준다.
  - 표(PrimeVue `DataTable`) 열은 제목, 저자, 연도, 상태, 종류다. 게재처와 추가일은 표에 넣지 않고 상세에서 보여 준다. 상태 열은 [읽기 상태와 메모 설계](ReadingStatus.md#3-화면)에 있다. 열마다 정렬 아이콘이 자리를 차지해, 가운데 칸 너비에서 제목이 가장 넓게 보이도록 하기 위해서다. 모든 열을 눌러 정렬할 수 있고, 처음 순서는 최근에 넣은 것부터다. 제목은 두 줄까지, 저자는 한 줄로 줄이고 전체는 마우스를 올리면 보인다. 표 모양은 검색 결과 표와 맞춘다.
  - 행을 누르면 그 논문을 고른다. 서재가 비었으면 "논문 검색"에서 논문을 넣으라고 안내한다.
- 오른쪽 칸 `PaperDetail.vue`는 고른 논문의 종류, 제목, 저자, 연도, 게재처, DOI, 원문, 태그, 추가일을 보여 준다. 읽기 상태와 메모 편집은 [읽기 상태와 메모 설계](ReadingStatus.md#3-화면)에 있다. 아래에 "서재에서 삭제" 단추가 있고, 누르면 확인을 받은 뒤 지운다(PrimeVue `ConfirmPopup`). 확인 팝업을 쓰려고 [main 모듈](../../frontend/src/main.ts)이 PrimeVue `ConfirmationService`를 등록한다. 삭제 오류는 단추 아래에 보여 준다.

## 4. 테스트

- [test_papers_api](../../tests/test_papers_api.py)는 목록 API의 순서와 빈 서재, 삭제 API의 204와 404를 확인한다.
- [libraryState.test](../../frontend/src/libraryState.test.ts)는 불러오기 성공·실패, 고른 논문 유지와 비우기, 삭제 성공·404·실패를 확인한다.
- [api.test](../../frontend/src/api.test.ts)는 `listPapers`, `deletePaper`(204, 404, 그 밖의 실패)를 확인한다.
- [labels.test](../../frontend/src/labels.test.ts)는 항목 종류 이름과 날짜 형식을 확인한다.
