# 인용 데이터 설계

이 문서는 인용 기반 연결·추천([제품 비전](../ProductVision.md#6-인용-기반-연결추천))이 쓰는 인용 데이터를 OpenAlex에서 어디까지 가져와 어떻게 저장하는지 정한다. 가져오는 양은 사용자 설정으로 조절한다([사용자 설정 설계](Settings.md)). 거리 점수의 계산식과 화면은 M3-T4~T7에서 정한다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. OpenAlex 조사

2026-11-15에 OpenAlex API를 직접 불러 확인한 내용이다.

| 요청 | 형태 | 비용 |
| --- | --- | --- |
| 논문 한 편 | `GET /works/doi:<DOI>` 또는 `GET /works/W<번호>` | 무료 |
| 목록 | `GET /works?filter=...&per-page=200` | 요청당 0.0001달러(쪽당 200건까지 같은 값) |

- 하루 예산은 키가 없으면 같은 IP가 함께 쓰는 0.1달러, 무료 키가 있으면 키마다 1달러다. 응답 헤더 `X-RateLimit-Remaining-USD`에 남은 예산이 온다. Render 서버는 IP를 다른 서비스와 함께 쓰므로 배포 환경에서는 `OPENALEX_API_KEY`를 넣는다([논문 검색 설계](PaperSearch.md#1-검색원)).
- 논문 한 편 응답의 `referenced_works`가 참고문헌 OpenAlex ID 목록이다.
- 피인용은 `filter=cites:W<번호>`로 찾는다. `from_publication_date:<날짜>`, `to_publication_date:<날짜>`로 기간을, `sort=cited_by_count:desc`로 피인용 많은 순을 정한다. `select=id,publication_date,referenced_works`로 인용한 논문의 참고문헌까지 한 번에 받는다.
- 예: 'Attention Is All You Need'(W2626778328)는 피인용이 136,382건이고, 그중 최근 1년 안의 것이 15,291건이었다. 전부 가져오는 것은 비용과 저장 크기 모두 맞지 않는다.
- 2026-11-15에 다시 확인했다. 이 논문의 공개일(2017-06-12)부터 1년 안(2018-06-12까지)에 이 논문을 인용한 논문은 592건이고, 피인용 많은 순으로 첫 결과는 'Squeeze-and-Excitation Networks'(피인용 37,192건)였다.
- 여러 논문의 제목 등은 `filter=openalex_id:W1|W2|...`로 한 번에 100건까지 받는다.

## 2. 서재 논문과 OpenAlex 연결

- 논문에 `openalex_id`(예: `W2626778328`, 없으면 비어 있음)를 더한다. 마이그레이션 0004가 열을 만든다(0003은 [사용자 설정](Settings.md#2-저장)의 표)([서재 데이터 설계의 스키마 변경](Library.md#3-스키마-변경)).
- OpenAlex 검색 결과에서 추가한 논문은 결과의 ID를 그대로 넣는다. 화면의 `toPaperInput`이 검색원이 OpenAlex인 결과의 `source_id`를 [PaperInput.openalex_id](../../frontend/src/api.ts#PaperInput.openalex_id)에 담아 [PaperData](../../src/jjabtero/library.py#PaperData)의 `openalex_id`로 보낸다. `https://openalex.org/W…` 꼴도 받아 `W…`만 남긴다([short_id](../../src/jjabtero/citations.py#short_id)).
- 그 밖의 논문(arXiv 검색 결과, 이미 서재에 있는 논문)은 DOI로 `GET /works/doi:<DOI>`를 불러 찾는다([link_paper](../../src/jjabtero/citations.py#link_paper)). arXiv 검색 결과는 이미 `10.48550/arXiv.<arXiv ID>`를 DOI로 가지므로 따로 처리하지 않는다. 찾지 못하면 비워 두고 그 DOI와 시각을 기억해, 7일 동안 다시 찾지 않는다. DOI가 없는 논문은 연결하지 않는다. 제목으로 찾는 것은 다른 논문과 잘못 이어질 수 있어 하지 않는다.
- 연결은 서재 파일을 바꾸므로 연결한 뒤 드라이브 자동 올리기를 예약한다.

## 3. 가져오는 범위


서재 논문 A마다 다음을 가져온다.

- **참고문헌**: A의 `referenced_works` 전부. 논문 한 편 요청 한 번(무료)이다.
- **피인용**: A를 인용한 논문 가운데 **A의 공개일부터 1년 안에 출판된 것만**, 그 논문 자신의 **피인용 많은 순**으로 **최대 N건**을 가져온다. 사용자가 정했다.
  - 공개일은 OpenAlex의 `publication_date`다. OpenAlex는 프리프린트를 포함해 가장 이른 공개일을 쓴다.
  - 기간을 공개 후 1년으로 두는 이유: 그보다 늦게 A를 인용한 논문은 A를 직접 이어받았다기보다 A의 후속 논문들과 함께 인용하는 경우가 많다. 그런 논문은 계보를 따라가다 보면 후속 논문을 거쳐 만나게 되므로 A의 인용 데이터로서는 의미가 적다.
  - 피인용 많은 순으로 고르는 이유: 그 1년 안에서도 영향력이 큰 후속 논문이 계보의 주된 줄기이기 때문이다.
  - N은 사용자 설정 `citing_limit`이다. 기본값은 10이고 1~1000 사이로 바꿀 수 있다. 사용자가 정했다. 목록 요청 한 쪽이 200건까지이므로 요청 수는 N/200을 올림한 값이다.
  - 피인용 논문의 출판일과 참고문헌을 함께 받는다. 공동 인용(A와 함께 인용된 논문)과 서지 결합(A와 참고문헌을 공유하는 논문)을 이 범위 안에서 계산하기 위해서다.
- 기간은 [citing_window](../../src/jjabtero/citations.py#citing_window)가 계산한다. 가져온 결과는 [FetchResult](../../src/jjabtero/citations.py#FetchResult)다.
- 기간은 A마다 정해져 있다. 공개된 지 1년이 안 된 논문은 기간의 끝이 아직 오지 않았으므로, 그때까지 나온 피인용만 받는다.

## 4. 저장

- 인용 데이터는 서재가 아니다. 가져온 논문은 서재에 추가하지 않고, 사용자가 화면에서 골라 "서재에 담기"를 누를 때만 서재에 들어간다([제품 비전](../ProductVision.md#6-인용-기반-연결추천)).
- 인용 데이터는 서재 파일과 **다른 파일 `citations.db`**(SQLite)에 둔다. 위치는 서재 파일과 같은 폴더다. [CitationStore](../../src/jjabtero/citations.py#CitationStore)가 이 파일을 다룬다.
  - 서재 파일은 고칠 때마다 드라이브에 통째로 올라간다([구글 드라이브 동기화 설계](DriveSync.md#5-동기화)). 인용 데이터는 서재보다 훨씬 크고 OpenAlex에서 다시 받을 수 있으므로, 함께 두면 올리기만 무거워진다.
  - 다시 받을 수 있는 캐시이므로 Alembic 마이그레이션을 쓰지 않는다. 파일의 `user_version`이 [CACHE_VERSION](../../src/jjabtero/citations.py#CACHE_VERSION)과 다르면 표를 지우고 다시 만든다.
- 저장하는 것(A는 서재 논문의 OpenAlex ID):

| 표 | 내용 |
| --- | --- |
| `fetches` | A마다 가져온 시각, A의 공개일과 피인용 기간의 끝 날짜, 그때의 `citing_limit`, 기간 안 피인용 전체 건수 |
| `references` | A → A가 인용한 논문 |
| `citations` | A를 인용한 논문 → A, 그 논문의 출판일, A와 공유하는 참고문헌 수(서지 결합) |
| `cocitations` | A와 함께 인용된 논문, 함께 인용된 횟수. 2회 이상인 것 가운데 많은 순으로 A마다 최대 100건 |
| `works` | 참고문헌과 피인용 논문의 제목, 저자(앞 10명), 연도, 공개일, 게재처, DOI, 피인용 수, 항목 종류(검색과 같은 규칙으로 OpenAlex `type`을 바꾼 값). 항목 종류는 캐시 버전 2에서 더했다 |
| `link_misses` | OpenAlex에서 찾지 못한 DOI와 시도한 시각 |

- 피인용 논문의 참고문헌 목록 자체는 저장하지 않는다. N이 크면(예: 200) A마다 1만 건쯤이 되어 파일이 커지기 때문이다. 가져올 때 서지 결합과 공동 인용 수로 줄여 저장한다.
- 함께 인용된 논문의 `works`는 가져오지 않는다. 화면에서 보여 줄 때(M3-T5) 받는다.
- 서재에서 지운 논문의 인용 데이터는 다음 갱신 때 지운다. 어느 표에서도 쓰지 않는 `works`도 함께 지운다([CitationStore.prune](../../src/jjabtero/citations.py#CitationStore.prune)).

**드라이브 보관**

- 서버는 재시작 때 디스크가 지워진다. 그때마다 모든 논문의 인용을 다시 받으면 OpenAlex 예산을 쓰므로, `citations.db`도 드라이브 `Jjabtero` 폴더에 올린다. 다시 받을 수 있는 캐시라 충돌을 따지지 않고 나중에 올린 쪽이 남는다.
- 갱신에서 하나라도 가져오면 끝날 때 올린다. 올리는 내용은 `VACUUM INTO`로 만든 사본이라, 쓰는 중인 파일을 올리지 않는다.
- 시작할 때 로컬에 `citations.db`가 없고 드라이브가 연결되어 있으면 받는다.
- 드라이브 쪽 읽고 쓰기는 [DriveSync.put_cache](../../src/jjabtero/drive_sync.py#DriveSync.put_cache)와 [DriveSync.get_cache](../../src/jjabtero/drive_sync.py#DriveSync.get_cache)가 한다. 서재 동기화와 같은 폴더와 토큰을 쓴다. `CitationSync`는 드라이브를 [DriveLike](../../src/jjabtero/citations.py#DriveLike) 모양으로만 쓴다.

## 5. 갱신

[CitationSync](../../src/jjabtero/citations.py#CitationSync)가 백그라운드 스레드 하나에서 갱신한다. [create_app](../../src/jjabtero/app.py#create_app)이 앱마다 하나를 만들고, 인자 `run_citations`가 참일 때만 [CitationSync.start](../../src/jjabtero/citations.py#CitationSync.start)로 스레드를 띄운다. 실행 명령만 참을 넘긴다. 테스트가 실제 OpenAlex를 부르지 않게 하기 위해서다. 앱이 끝날 때 멈춘다.

- 갱신 한 번([CitationSync.run_once](../../src/jjabtero/citations.py#CitationSync.run_once))은 다음 순서다.
  1. 서재에서 지운 논문의 인용 데이터를 지운다.
  2. 연결되지 않은 논문을 DOI로 연결한다.
  3. 연결된 논문 가운데 가져온 적이 없거나 가져온 지 7일이 지난 것을 가져온다([fetch_citations](../../src/jjabtero/citations.py#fetch_citations)). 오래된 것부터 한다.
  4. 하나라도 가져왔으면 `citations.db`를 드라이브에 올린다.
- 갱신은 시작할 때, 그 뒤 1시간마다, 그리고 깨울 때([CitationSync.wake](../../src/jjabtero/citations.py#CitationSync.wake)) 한다. 논문을 서재에 넣으면 깨운다.
- 가져온 지 7일이 지난 논문은 다시 가져온다. 기간이 끝나지 않은 논문은 새 피인용이 생기고, 기간이 끝난 논문도 후속 논문들의 피인용 수가 늘어 상위 N건이 바뀔 수 있기 때문이다.
- `citing_limit`을 바꾸면 다음에 가져올 때 새 값을 쓴다. 바로 다시 받고 싶으면 설정 화면에서 "인용 데이터 새로 받기"를 누른다. 모든 논문을 가져올 대상으로 표시하고 깨운다.
- OpenAlex 예산이 다 떨어지면(응답 429, [OpenAlexBudgetError](../../src/jjabtero/citations.py#OpenAlexBudgetError)) 이번 갱신을 멈추고 다음 갱신 때 이어서 한다. 다른 오류(네트워크, 5xx)는 그 논문만 건너뛰고 상태에 마지막 오류로 남긴다.
- 키 `OPENALEX_API_KEY`가 있으면 모든 요청에 `api_key`로 붙인다.

## 6. API와 화면

[router](../../src/jjabtero/citations.py#router)가 처리한다. 로그인이 켜져 있으면 로그인해야 쓴다.

- `GET /api/citations/status`는 [citation_status](../../src/jjabtero/citations.py#citation_status)가 처리하며 [CitationStatus](../../src/jjabtero/citations.py#CitationStatus)를 돌려준다. 서재 논문 수, OpenAlex에 연결된 수, 찾지 못한 수, 인용 데이터를 가져온 수, 갱신 중인지, 마지막 갱신 시각, 마지막 오류다.
- `POST /api/citations/refresh`는 [refresh_citations](../../src/jjabtero/citations.py#refresh_citations)가 처리한다. 모든 논문을 가져올 대상으로 표시하고 갱신을 깨운 뒤 상태를 돌려준다.
- `GET /api/papers/{id}/citations`는 [paper_citations](../../src/jjabtero/citations.py#paper_citations)가 처리하며([paper_router](../../src/jjabtero/citations.py#paper_router)) 논문 하나의 인용 목록 [PaperCitations](../../src/jjabtero/citations.py#PaperCitations)을 돌려준다.
  - `state`: `no_doi`(DOI가 없어 연결할 수 없음), `not_found`(7일 안에 찾지 못함), `pending`(연결 전이거나 아직 가져오지 않음), `ready`.
  - `ready`면 피인용 기간(시작·끝), 기간 안 피인용 전체 건수, 그때의 `citing_limit`, 가져온 시각과 함께 참고문헌과 피인용 목록을 준다. 둘 다 피인용 많은 순이다([CitationStore.paper_lists](../../src/jjabtero/citations.py#CitationStore.paper_lists)).
  - 목록의 항목은 [CitedWork](../../src/jjabtero/citations.py#CitedWork)(OpenAlex ID, 제목, 저자, 항목 종류, 연도, 게재처, DOI, 피인용 수, 피인용 항목은 공유 참고문헌 수)이고, OpenAlex ID나 DOI가 같은 서재 논문이 있으면 그 ID(`library_paper_id`)를 담는다.
- `GET /api/papers/{id}/related`는 [paper_related](../../src/jjabtero/citations.py#paper_related)가 처리하며 가까운 논문 목록 [PaperRelated](../../src/jjabtero/citations.py#PaperRelated)(상태, 가져온 피인용 수, 참고문헌 수, 항목)을 돌려준다. 항목은 [RelatedWork](../../src/jjabtero/citations.py#RelatedWork)로, `CitedWork`에 점수와 까닭(이 논문을 인용, 이 논문이 인용, 함께 인용된 횟수, 공유 참고문헌 수)을 더한 것이다.
  - 후보는 이 논문의 참고문헌, 가져온 피인용, 함께 인용된 논문이다([CitationStore.relation_rows](../../src/jjabtero/citations.py#CitationStore.relation_rows)). 논문 자신은 뺀다.
  - 점수([related_works](../../src/jjabtero/citations.py#related_works), 까닭은 [Relation](../../src/jjabtero/citations.py#Relation))는 직접 인용이면 0.5([DIRECT_WEIGHT](../../src/jjabtero/citations.py#DIRECT_WEIGHT)) + 함께 인용된 비율(공동 인용 수 / 가져온 피인용 수) + 공유 참고문헌 비율(공유 참고문헌 수 / 이 논문의 참고문헌 수)이다. 세 값 모두 0~1 근처라 어느 하나가 압도하지 않고, 화면에 까닭을 그대로 보여 줄 수 있다. 같은 점수는 ID 순이다. 상위 30편([RELATED_LIMIT](../../src/jjabtero/citations.py#RELATED_LIMIT))을 준다.
  - 함께 인용된 논문은 서지 정보가 없으므로 이 API를 부를 때 없는 것만 OpenAlex에서 100건씩 받아 `works`에 둔다([lookup_works](../../src/jjabtero/citations.py#lookup_works), [CitationStore.works_by_id](../../src/jjabtero/citations.py#CitationStore.works_by_id), [CitationStore.save_works](../../src/jjabtero/citations.py#CitationStore.save_works)). 받지 못하면 제목 없이 ID로 보여 준다.
- 논문 상세에 "인용" 칸([CitationLists](../../frontend/src/CitationLists.vue))을 둔다. "가까운 논문"이 첫 칸이고, 항목마다 까닭을 작은 표시로 보여 준다([relationReasons](../../frontend/src/citationListState.ts#relationReasons)). API 호출은 [fetchPaperRelated](../../frontend/src/api.ts#fetchPaperRelated)(타입 [PaperRelated](../../frontend/src/api.ts#PaperRelated), [RelatedWork](../../frontend/src/api.ts#RelatedWork))다. "피인용 n"과 "참고문헌 n"을 바꿔 보고, 피인용은 기간과 "n편 가운데 피인용 많은 순 m편"을 알린다. 항목마다 제목(DOI 또는 OpenAlex로 이어지는 링크), 저자·연도·게재처, 피인용 수, 공유 참고문헌 수를 보여 주고, 서재에 있으면 "서재에 있음", 없으면 "서재에 담기"를 둔다. 상태가 `ready`가 아니면 그 까닭을 한 줄로 알린다.
  - "서재에 담기"는 항목을 서재 입력으로 바꿔([citedWorkInput](../../frontend/src/citationListState.ts#citedWorkInput): 원문 주소는 DOI, 없으면 OpenAlex 주소, OpenAlex ID 포함) 논문을 추가하고, 그 항목을 "서재에 있음"으로 바꾼 뒤 서재 목록을 다시 읽는다. DOI가 이미 있으면 그 논문으로 표시한다. 상태는 [createCitationListState](../../frontend/src/citationListState.ts#createCitationListState)가 가지며, 다른 논문을 고른 뒤 늦게 온 응답은 버린다. API 호출은 [fetchPaperCitations](../../frontend/src/api.ts#fetchPaperCitations)(타입 [PaperCitations](../../frontend/src/api.ts#PaperCitations), [CitedWork](../../frontend/src/api.ts#CitedWork))다.
- 설정 페이지([사용자 설정 설계](Settings.md#4-화면))에 "인용 데이터" 칸을 두어 상태를 보여 주고 "인용 데이터 새로 받기" 버튼을 둔다. 화면은 [CitationStatusPanel](../../frontend/src/CitationStatusPanel.vue)이고, 응답 타입은 [CitationStatus](../../frontend/src/api.ts#CitationStatus), API 호출은 [fetchCitationStatus](../../frontend/src/api.ts#fetchCitationStatus)와 [refreshCitations](../../frontend/src/api.ts#refreshCitations)다.

## 7. 테스트

[test_citations](../../tests/test_citations.py)는 가짜 OpenAlex 응답으로 다음을 확인한다.

- 공개 후 1년 기간(윤년 2월 29일 포함)과 요청 인자(`cites`, 기간, `cited_by_count:desc`, 쪽 크기).
- DOI로 연결, 찾지 못한 DOI를 7일 동안 다시 찾지 않음, OpenAlex 검색 결과의 ID 저장.
- 참고문헌, 피인용, 서지 결합 수, 공동 인용 수(2회 이상, A 자신 제외) 저장과 다시 가져올 때 옛 데이터 교체.
- `citing_limit`이 200을 넘으면 여러 쪽을 받음.
- 7일 지난 논문만 다시 가져옴, 지운 논문의 데이터 정리, 429에서 멈춤.
- 캐시 버전이 다르면 다시 만듦, 드라이브에 올리고 받기.
- API 상태와 새로 받기.
- 가까운 논문 점수(직접 인용, 함께 인용된 비율, 공유 참고문헌 비율, 자신 빼기, 순서)와 API(점수 순, 없는 서지 정보를 한 번만 받기).
- 논문의 인용 목록 API: 가져오기 전 `pending`, 가져온 뒤 기간·건수·한도, 피인용 많은 순 목록과 서지 정보, 서재에 있는 논문 표시, DOI 없음·찾지 못함·없는 논문.

[citationListState.test](../../frontend/src/citationListState.test.ts)는 인용 논문의 서재 입력 변환, 목록 읽기, 담기와 표시, 이미 있는 DOI, 실패 메시지, 늦게 온 응답 버리기, 가까운 논문 읽기와 담기 표시, 까닭 문구를 확인한다.

[api.test](../../frontend/src/api.test.ts)는 `toPaperInput`의 OpenAlex ID와 인용 데이터 API 호출을 확인한다.

## 8. 미결정 사항

- 서재 밖 추천 점수: M3-T6.
