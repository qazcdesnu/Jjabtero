# 태그 설계

이 문서는 서재 논문에 태그를 붙이고 떼는 일, 태그 이름 바꾸기·지우기, 태그로 서재와 인용 그래프를 걸러 보는 일을 정한다. 태그 데이터 모델은 [서재 데이터 설계](Library.md#1-데이터-모델)에, 서재 목록의 태그 필터는 [서재 필터 설계](LibraryFilter.md)에 있다. 태스크는 [로드맵의 M7](../Roadmap.md#m7-태그)에 있다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 지금 있는 것과 더할 것

- 태그는 `tags`(이름 고유)와 `paper_tags`(논문–태그 연결) 표에 있다. 논문 검색에서 서재에 담을 때 태그를 붙일 수 있다([논문 검색과 추가 설계](PaperSearch.md#4-화면)).
- 왼쪽 목록의 태그를 누르면 서재 목록이 그 태그를 모두 가진 논문만 보인다(AND, [서재 필터 설계](LibraryFilter.md#2-필터-조건)). 이것은 그대로 쓴다.
- 더할 것: 서재 논문에 태그 붙이기·떼기(한 편, 여러 편), 태그 이름 바꾸기·지우기(M7-T2, 3·4절), 고른 태그로 인용 그래프 걸러 보기(M7-T3, 5절).

## 2. 태그 이름 규칙

- 앞뒤 빈칸을 지우고, 안의 연속 빈칸은 하나로 줄인다. 빈 이름은 버린다. 50자([MAX_TAG_LENGTH](../../src/jjabtero/tags.py#MAX_TAG_LENGTH))를 넘으면 422다([clean_tags](../../src/jjabtero/tags.py#clean_tags), [TagNameError](../../src/jjabtero/tags.py#TagNameError)).
- 대소문자는 그대로 둔다. 같은 논문에 같은 이름을 두 번 붙이지 않는다.
- 어느 논문에도 붙어 있지 않은 태그는 지운다([drop_unused_tags](../../src/jjabtero/tags.py#drop_unused_tags)). 왼쪽 목록에 쓰지 않는 태그가 남지 않게 하기 위해서다.
- 태그를 붙이거나 떼면 그 논문의 `updated_at`을 바꾼다. 드라이브 자동 합치기가 늦게 고친 쪽을 고를 수 있게 하기 위해서다([구글 드라이브 동기화 설계](DriveSync.md#10-자동-합치기)). 바꾼 뒤에는 드라이브 자동 올리기를 예약한다.

## 3. API

[tags 모듈](../../src/jjabtero/tags.py)의 [router](../../src/jjabtero/tags.py#router)가 처리한다. 로그인이 켜져 있으면 로그인해야 쓴다.

- `PUT /api/papers/{id}/tags` 본문 `{"tags": [이름, …]}`([TagsIn](../../src/jjabtero/tags.py#TagsIn), [put_paper_tags](../../src/jjabtero/tags.py#put_paper_tags), [set_paper_tags](../../src/jjabtero/tags.py#set_paper_tags)): 그 논문의 태그를 이 목록으로 바꾼다. 바뀐 논문(`PaperOut`)을 돌려준다. 없는 논문은 404다.
- `POST /api/tags/apply` 본문 `{"paper_ids": [ID, …], "add": [이름, …], "remove": [이름, …]}`([ApplyIn](../../src/jjabtero/tags.py#ApplyIn), [post_apply_tags](../../src/jjabtero/tags.py#post_apply_tags), [apply_tags](../../src/jjabtero/tags.py#apply_tags)): 여러 논문에 태그를 붙이고 뗀다. 바뀐 논문 수([ChangedOut](../../src/jjabtero/tags.py#ChangedOut))를 돌려준다. 없는 논문 ID가 섞여 있으면 아무것도 바꾸지 않고 404다.
- `PATCH /api/tags/{이름}` 본문 `{"name": 새 이름}`([RenameIn](../../src/jjabtero/tags.py#RenameIn), [patch_tag](../../src/jjabtero/tags.py#patch_tag), [rename_tag](../../src/jjabtero/tags.py#rename_tag)): 태그 이름을 바꾼다. 새 이름의 태그가 이미 있으면 두 태그를 합친다(옛 태그가 붙은 논문에 새 태그를 붙이고 옛 태그를 지운다). 없는 태그는 404다.
- `DELETE /api/tags/{이름}`([remove_tag](../../src/jjabtero/tags.py#remove_tag), [delete_tag](../../src/jjabtero/tags.py#delete_tag)): 모든 논문에서 그 태그를 떼고 지운다. 논문은 지우지 않는다. 없는 태그는 404다.

## 4. 화면

- **논문 상세**([PaperDetail](../../frontend/src/PaperDetail.vue)): 태그 칸에 태그마다 지울 수 있는 칩을 두고, 그 옆 입력란에 이름을 넣고 Enter를 누르면 붙인다. 입력하는 동안 서재의 기존 태그 이름을 자동 완성으로 보여 준다(브라우저 `datalist`). 붙이거나 떼면 바로 저장한다(`PUT /api/papers/{id}/tags`, [setPaperTags](../../frontend/src/api.ts#setPaperTags)). 저장 오류는 태그 칸 아래에 보인다.
- **서재 목록**([LibraryView](../../frontend/src/LibraryView.vue)): 맨 앞에 고르기 칸(체크 상자)을 둔다. 머리 칸의 체크 상자는 지금 보이는(거른) 논문을 모두 고르거나 푼다. 하나 이상 고르면 목록 위에 "고른 n편", 태그 이름 입력(자동 완성), "태그 붙이기", "태그 떼기", "고르기 해제"가 나온다. 붙이거나 떼면 `POST /api/tags/apply`([applyTags](../../frontend/src/api.ts#applyTags))를 부르고 서재를 다시 읽는다. 행을 누르면 지금처럼 상세를 연다. 다시 읽었을 때 서재에 없는 논문은 고르기에서 뺀다.
- **왼쪽 태그 목록**([Sidebar](../../frontend/src/Sidebar.vue)): 태그에 마우스를 올리면 메뉴 단추가 보이고, "이름 바꾸기"와 "지우기"가 있다. 이름 바꾸기는 대화 상자에서 새 이름을 받고 같은 이름이 있으면 합친다고 알린다([renameTag](../../frontend/src/api.ts#renameTag)). 지우기는 확인을 받는다("n편에서 뗍니다. 논문은 지우지 않습니다", [deleteTag](../../frontend/src/api.ts#deleteTag)). 이름을 바꾸거나 지우면 서재 필터에 그 태그가 있었을 때 필터도 함께 바꾼다.
- 상태와 동작(붙이기·떼기, 고르기, 이름 바꾸기·지우기와 필터 맞추기, 오류)은 [createLibraryState](../../frontend/src/libraryState.ts#createLibraryState)가 가진다.

## 5. 태그별 그래프

- 그래프 화면도 왼쪽에서 고른 태그(서재 필터의 태그)를 쓴다. 고른 태그를 모두 가진 서재 논문만 그래프에 넣고, 서재 밖 추천 논문도 그 논문들로만 계산한다. 서재 목록과 그래프가 같은 태그 선택을 보여야 헷갈리지 않기 때문이다.
- API: `GET /api/citations/graph?tags=<이름>&tags=<이름>`([citation_graph](../../src/jjabtero/citation_graph.py#citation_graph), [인용 그래프 설계](CitationGraph.md#3-api)). 서재 밖 추천에서 빼는 것은 태그와 관계없이 서재 전체다. 고른 태그가 없는 서재 논문을 추천하지 않기 위해서다. 화면은 [fetchCitationGraph](../../frontend/src/api.ts#fetchCitationGraph)에 태그를 넘긴다([createGraphState](../../frontend/src/graphState.ts#createGraphState)의 `tags`).
- 그래프 화면([GraphView](../../frontend/src/GraphView.vue))에 있을 때 왼쪽 태그를 누르면 서재 화면으로 가지 않고 그래프를 다시 그린다. 그래프 위쪽에 고른 태그를 지울 수 있는 칩으로 보여 주고, 칩을 지우면 왼쪽 선택에서도 빠진다.
- 시연 서재(9편)에서 `language`(2편)를 고르자 서재 논문 2편, 인용 선 1개로 다시 그렸고, 칩을 지우자 9편으로 돌아왔다(2026-11-16).

## 6. 테스트

- [test_tags](../../tests/test_tags.py)는 이름 규칙(빈칸, 겹침, 50자), 논문 태그 바꾸기(고친 시각, 쓰지 않는 태그 지우기, 자동 올리기 예약, 404, 422), 여러 편에 붙이기·떼기(바뀐 수, 없는 논문이 섞이면 아무것도 안 바꿈, 빈 목록 422), 이름 바꾸기와 합치기, 지우기(논문은 남김)를 확인한다.
- [test_citation_graph](../../tests/test_citation_graph.py)는 태그 하나·둘(모두 가진 논문만), 없는 태그(빈 그래프), 태그로 거른 그래프의 추천이 서재의 다른 논문을 빼는 것을 확인한다. [graphState.test](../../frontend/src/graphState.test.ts)는 고른 태그로 그래프를 청하는 것을 확인한다.
- [libraryState.test](../../frontend/src/libraryState.test.ts)는 한 편 태그 바꾸기와 오류, 여러 편 고르기·모두 고르기·붙이기·떼기, 이름 바꾸기·지우기 뒤의 필터, 다시 읽을 때 고르기 정리를 확인한다.

## 7. 미결정 사항

- 없음.
