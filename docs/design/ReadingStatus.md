# 읽기 상태와 메모 설계

이 문서는 논문마다 읽기 상태와 메모를 남기는 기능을 정한다. 데이터 모델 전체는 [서재 데이터 설계](Library.md)에, 서재 화면은 [서재 화면 설계](LibraryView.md)에 있다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 데이터

`papers` 테이블에 두 열을 더한다([서재 데이터 설계](Library.md#1-데이터-모델)).

| 열 | 타입 | 필수 | 설명 |
| --- | --- | --- | --- |
| `read_status` | 문자열 | 예 | 읽기 상태. [READ_STATUSES](../../src/jjabtero/models.py#READ_STATUSES) 중 하나이며 기본값은 `to-read`다. |
| `note` | 문자열 | 아니요 | 메모. 논문마다 하나이며 길이 제한이 없다. |

- 읽기 상태는 `to-read`(읽을 것), `reading`(읽는 중), `read`(다 읽음)다. 새 논문은 읽을 것으로 시작한다.
- 마이그레이션 0002가 두 열을 더한다. 이미 있는 논문은 읽을 것, 메모 없음이 된다.

## 2. 저장 함수와 API

- [ReadingUpdate](../../src/jjabtero/library.py#ReadingUpdate)는 읽기 상태와 메모를 바꾸는 입력이다. `read_status`와 `note`를 가지며, 둘 다 빠져도 된다. 보낸 항목만 바꾼다.
  - `read_status`는 `READ_STATUSES` 중 하나여야 한다. `null`이면 검증 오류다.
  - `note`는 앞뒤 공백을 지운 뒤 비면 메모를 지운다(`null`과 같다).
- [update_reading](../../src/jjabtero/library.py#update_reading)은 논문의 읽기 상태와 메모를 바꾸고 `updated_at`을 갱신해 돌려준다. 없는 ID면 `PaperNotFoundError`다. 서지 정보, 저자, 태그는 건드리지 않는다.
- 서지 정보를 고치는 `update_paper`는 읽기 상태와 메모를 건드리지 않는다. 두 기능이 서로의 값을 덮어쓰지 않게 하기 위해서다.
- `PATCH /api/papers/{paper_id}`는 [change_reading](../../src/jjabtero/papers_api.py#change_reading)이 처리한다. 본문은 `ReadingUpdate`이고, 성공하면 200과 논문(`PaperOut`)을, 없는 ID면 404를, 검증 오류면 422를 돌려준다.
- 논문 응답 `PaperOut`에 `read_status`와 `note`를 더한다.

## 3. 화면

- API 함수는 [updateReading](../../frontend/src/api.ts#updateReading)이다. 바뀐 논문을 돌려주고, 404면 `PaperNotFoundError`를 던진다.
- 표시 이름은 [labels 모듈](../../frontend/src/labels.ts)의 [READ_STATUSES](../../frontend/src/labels.ts#READ_STATUSES)(값, 한국어 이름, 태그 색)이고, [readStatusInfo](../../frontend/src/labels.ts#readStatusInfo)는 값으로 이름과 색을 찾는다(모르는 값은 그대로 이름으로 쓴다). 읽을 것은 회색, 읽는 중은 파랑, 다 읽음은 초록이다.
- 서재 상태 [createLibraryState](../../frontend/src/libraryState.ts#createLibraryState)에 `changeReading(paper, update)`를 더한다. 성공하면 목록의 그 논문을 응답으로 바꾸고 참을 돌려준다. 404면 목록에서 빼고, 그 밖의 실패는 `readingError`로 둔다. 실패하면 거짓을 돌려준다.
- 서재 표에 "상태" 열(색 태그, 정렬 가능)을 더한다. 추가일 열은 표에서 빼고 상세에서 보여 준다. 제목 열 너비를 지키기 위해서다.
- 서재 필터에 읽기 상태 여러 개 고르기를 더한다. 고른 상태 가운데 하나면 남긴다([서재 필터 설계](LibraryFilter.md#2-필터-조건)).
- 상세 칸(`PaperDetail.vue`)
  - 제목 아래에 읽기 상태 단추 묶음(PrimeVue `SelectButton`)이 있다. 누르면 바로 저장한다.
  - 메모 칸(PrimeVue `Textarea`, 내용에 맞춰 늘어남)과 "메모 저장" 단추가 있다. 고친 내용이 있을 때만 단추가 켜지고, 저장하면 "저장됨"을 잠깐 보여 준다. 다른 논문을 고르면 메모 칸을 그 논문의 메모로 바꾼다.
  - 저장 오류는 그 아래에 보여 준다.

## 4. 테스트

- [test_db](../../tests/test_db.py)는 0001 상태의 데이터베이스에 논문을 넣은 뒤 0002로 올리면 그 논문이 읽을 것, 메모 없음이 되는지 확인한다.
- [test_library](../../tests/test_library.py)는 `update_reading`의 일부 항목만 바꾸기, 메모 지우기, 잘못된 상태, 없는 ID, `update_paper`가 상태와 메모를 지키는지 확인한다.
- [test_papers_api](../../tests/test_papers_api.py)는 `PATCH`의 200, 404, 422와 새 논문의 기본 상태를 확인한다.
- 프론트엔드는 `updateReading`([api.test](../../frontend/src/api.test.ts)), 서재 상태의 `updateReading`([libraryState.test](../../frontend/src/libraryState.test.ts)), 읽기 상태 필터([libraryFilter.test](../../frontend/src/libraryFilter.test.ts)), 표시 이름([labels.test](../../frontend/src/labels.test.ts))을 확인한다.
