# 논문 검색과 추가 설계

이 문서는 외부 논문 검색 사이트에서 논문을 찾고, 검색 결과를 보고 골라 서재에 넣는 기능을 정한다. 저장 방식은 [서재 데이터 설계](Library.md)에, 앱 골격은 [앱 골격 설계](AppSkeleton.md)에 있다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 검색원

| 검색원 | 이름 | 방식 | 비고 |
| --- | --- | --- | --- |
| OpenAlex | `openalex` | `GET https://api.openalex.org/works?search=<검색어>` | 서지 정보가 가장 넓다. 같은 API를 나중에 인용 데이터에도 쓴다. |
| arXiv | `arxiv` | `GET https://export.arxiv.org/api/query?search_query=<검색어>` (Atom XML) | 최신 프리프린트를 빨리 찾는다. |

- Google Scholar는 공식 API가 없고 화면 수집은 이용 약관 위반이라 쓰지 않는다. 보조 웹 검색은 별도 검색 API(대개 유료 키)가 필요해 미결정으로 둔다([제품 비전](../ProductVision.md#5-미결정-사항)).
- OpenAlex는 키 없이도 쓰지만, 키가 없으면 같은 IP가 하루 예산을 나눠 쓴다. 환경 변수 `OPENALEX_API_KEY`가 있으면 요청에 `api_key`로 붙인다.
- 모든 요청에 `User-Agent: Jjabtero/<버전>`을 붙이고, 제한 시간은 10초다.

## 2. 검색 결과

검색 모듈은 [search 모듈](../../src/jjabtero/search.py)이다.

- [SearchResult](../../src/jjabtero/search.py#SearchResult)는 검색 결과 하나다. `source`(검색원 이름), `source_id`(검색원 안의 ID), `title`, `authors`, `item_type`, `year`, `venue`, `doi`(정규화), `url`과, 서재에 같은 DOI의 논문이 있으면 그 ID인 `library_paper_id`를 가진다. 항목 이름과 뜻은 `PaperData`([서재 데이터 설계](Library.md#4-저장-함수))와 같다.
- [search_openalex](../../src/jjabtero/search.py#search_openalex)는 OpenAlex 결과를 바꾼다.
  - `display_name` → 제목, `authorships[].author.display_name` → 저자(순서대로), `publication_year` → 연도, `primary_location.source.display_name` → 게재처, `doi` → DOI, `primary_location.landing_page_url`(없으면 DOI 주소, 그것도 없으면 OpenAlex ID) → URL.
  - 항목 종류: `conference-paper`는 같은 이름이다. `article`은 게재처 종류가 `conference`이면 `conference-paper`, 아니면 `journal-article`이다. `review`는 `journal-article`, `preprint`·`book`·`book-chapter`·`report`는 같은 이름, `dissertation`은 `thesis`, 그 밖은 `other`다.
  - 제목이 없는 결과는 버린다.
- [search_arxiv](../../src/jjabtero/search.py#search_arxiv)는 arXiv 결과를 바꾼다.
  - 검색어의 낱말을 모두 포함하도록 `all:<낱말>`을 `AND`로 잇는다. arXiv는 낱말 사이를 기본으로 `OR`로 보기 때문이다. 영어 불용어(`is`, `the`, `of` 등 Lucene 영어 불용어 목록)는 뺀다. arXiv가 이 낱말들을 색인하지 않아 `AND`에 들어가면 결과가 비기 때문이다. 낱말이 모두 불용어면 빼지 않는다.
  - 항목 종류는 `preprint`, 게재처는 `arXiv`, 연도는 `published`의 연도, URL은 초록 페이지다. 제목과 저자 이름의 줄바꿈과 겹친 공백은 하나로 줄인다.
  - DOI는 항목에 `arxiv:doi`(학술지 DOI)가 있으면 그것이고, 없으면 arXiv가 모든 논문에 주는 `10.48550/arXiv.<번호>`다(버전 표시 `v1` 등은 뺀다). OpenAlex 결과와 겹치는 것을 찾기 위해서다.
- [search_papers](../../src/jjabtero/search.py#search_papers)는 고른 검색원을 차례로 부르고 결과를 합쳐 [SearchResponse](../../src/jjabtero/search.py#SearchResponse)로 돌려준다.
  - 검색원 순서(OpenAlex, arXiv)대로 결과를 잇고, 앞에 나온 결과와 DOI가 같은 결과는 뺀다.
  - 한 검색원이 실패해도(네트워크 오류, 응답 오류, 해석 오류) 나머지 결과는 돌려주고, 실패는 [SourceError](../../src/jjabtero/search.py#SourceError)(`source`, `message`)로 `errors`에 담는다.
  - 검색원마다 결과 수는 `limit`(1~25, 기본 10)이다.

## 3. API

API는 [papers_api 모듈](../../src/jjabtero/papers_api.py)의 라우터다. 앱은 [create_app](../../src/jjabtero/app.py#create_app)에서 데이터베이스와 HTTP 클라이언트를 준비한다.

- `create_app`은 인자 `db_path`(기본 `default_db_path()`의 값)로 엔진을 만들고 `upgrade_database`로 스키마를 올린다([서재 데이터 설계](Library.md#2-데이터베이스-파일과-연결)). 인자 `http_client`가 없으면 위 설정의 HTTP 클라이언트를 만든다. 테스트는 임시 데이터베이스와 가짜 응답 클라이언트를 넘긴다.
- `GET /api/search`는 [search](../../src/jjabtero/papers_api.py#search)가 처리한다.
  - 질의 인자: `q`(검색어, 앞뒤 공백을 지운 뒤 비면 422), `sources`(여러 번 줄 수 있음, 기본 모든 검색원, 모르는 이름은 422), `limit`.
  - 돌려주기 전에 결과의 DOI로 서재를 찾아 `library_paper_id`를 채운다.
- `POST /api/papers`는 [create_paper](../../src/jjabtero/papers_api.py#create_paper)가 처리한다.
  - 본문은 `PaperData`다. 검증 오류는 422다.
  - 성공하면 201과 [PaperOut](../../src/jjabtero/papers_api.py#PaperOut)을 돌려준다. `PaperOut`은 `id`, 서지 항목, `authors`, `tags`, `created_at`, `updated_at`을 가진다.
  - DOI가 겹치면 409이고, `detail`에 `message`와 이미 있는 논문의 `paper_id`를 담는다.

## 4. 화면

- API 호출과 변환은 [api 모듈](../../frontend/src/api.ts)에 둔다([시스템 구조](../Architecture.md#2-디렉터리-구조)의 `.vue` 제약).
  - [searchPapers](../../frontend/src/api.ts#searchPapers)는 `GET /api/search`를 불러 [SearchResponse](../../frontend/src/api.ts#SearchResponse)를 돌려준다.
  - [addPaper](../../frontend/src/api.ts#addPaper)는 `POST /api/papers`를 불러 [Paper](../../frontend/src/api.ts#Paper)를 돌려준다. 409면 이미 있는 논문 ID를 담은 [DuplicatePaperError](../../frontend/src/api.ts#DuplicatePaperError)를, 그 밖의 실패면 상태 코드를 담은 오류를 던진다.
  - [toPaperInput](../../frontend/src/api.ts#toPaperInput)은 검색 결과와 태그 목록을 [PaperInput](../../frontend/src/api.ts#PaperInput)으로 바꾼다. 태그의 앞뒤 공백을 지우고, 빈 태그와 겹치는 태그는 버린다.
- 검색 화면의 상태와 동작은 [searchState 모듈](../../frontend/src/searchState.ts)의 [createSearchState](../../frontend/src/searchState.ts#createSearchState)가 만든다. 검색과 추가 함수를 인자로 받아, 테스트에서 가짜로 바꿀 수 있다.
  - 상태: 검색어, 고른 검색원(기본 모두), 검색 중 여부, 검색 오류, 결과, 검색원별 실패, 고른 결과, 결과별 추가 오류.
  - `run()`은 검색어가 비거나 검색원이 없으면 아무것도 하지 않는다. 검색하면 결과를 바꾸고 고른 결과와 추가 상태를 비운다.
  - `add(result, tags)`는 결과를 서재에 넣는다. 성공하거나 409면 그 결과를 서재에 있는 것으로 표시하고, 그 밖의 실패는 결과별 추가 오류로 둔다.
  - `isInLibrary(result)`는 결과에 `library_paper_id`가 있거나 이번에 넣었으면 참이다.
  - 결과의 열쇠는 [resultKey](../../frontend/src/searchState.ts#resultKey)(`<검색원>:<검색원 ID>`)다.
  - 화면에는 영어 코드 대신 표시 이름을 쓴다. 검색원은 [sourceLabel](../../frontend/src/searchState.ts#sourceLabel)(`OpenAlex`, `arXiv`), 항목 종류는 `labels.ts`의 `ITEM_TYPE_LABELS`(저널 논문, 학회 논문 등)다([서재 화면 설계](LibraryView.md#2-화면-상태)).
- 화면은 [UI 기반 설계](UiLayout.md#3-화면-배치)의 3단 배치를 쓴다.
  - 가운데 칸 `SearchView.vue`: 위에 검색어 입력, 검색원 선택, 검색 단추가 있다. 검색 중에는 단추가 돈다. 아래는 결과 표(PrimeVue `DataTable`)로 제목, 저자, 연도, 게재처, 검색원, 상태를 보여 준다. 제목 열이 남는 너비를 모두 쓰고 두 줄까지 보이며, 저자와 게재처는 한 줄로 줄이고 전체는 마우스를 올리면 보인다. 서재에 있는 결과는 체크 아이콘(툴팁 "서재에 있음")으로 표시한다. 행을 누르면 그 결과를 고른다. 실패한 검색원은 표 위에 경고로 알린다.
  - 오른쪽 칸 `SearchResultDetail.vue`: 고른 결과의 제목, 저자, 연도, 게재처, 항목 종류, DOI, 원문 링크를 보여 주고, 태그 입력(입력하고 Enter로 하나씩 더함)과 "서재에 추가" 단추를 둔다. 서재에 있으면 단추 대신 "서재에 있음"을 보여 준다.

## 5. 테스트

외부 API는 실제로 부르지 않고 고정된 응답을 돌려주는 가짜 전송(`httpx2.MockTransport`)으로 대신한다. 가짜 응답과 클라이언트는 [fakes](../../tests/fakes.py)에 둔다.

- [test_search](../../tests/test_search.py)는 OpenAlex·arXiv 응답 해석(항목 종류 대응, arXiv DOI, 공백 정리, 제목 없는 결과), 검색어 구성과 API 키, 결과 합치기와 DOI 중복 제거, 검색원 하나가 실패할 때를 확인한다.
- [test_papers_api](../../tests/test_papers_api.py)는 검색 API의 정상 응답, 서재에 있는 논문 표시, 잘못된 질의(빈 검색어, 모르는 검색원)와 논문 추가 API의 201, 409, 422를 확인한다.
- [api.test](../../frontend/src/api.test.ts)는 `searchPapers`, `addPaper`(성공, 409, 그 밖의 실패), `toPaperInput`을 확인한다.
- [searchState.test](../../frontend/src/searchState.test.ts)는 검색 실행과 건너뛰기, 검색 오류, 추가 성공·409·실패, 서재 표시를 확인한다.
