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
| `outside_references` | 그래프에 그린 서재 밖 논문의 참고문헌 목록(JSON)과 받은 시각. 그래프 안 인용 선에 쓴다([서재 인용 그래프 설계](CitationGraph.md#2-그래프-데이터), [이슈 I25](../Issue.md)) |

- 피인용 논문의 참고문헌 목록 자체는 저장하지 않는다. N이 크면(예: 200) A마다 1만 건쯤이 되어 파일이 커지기 때문이다. 가져올 때 서지 결합과 공동 인용 수로 줄여 저장한다.
- 함께 인용된 논문의 `works`는 가져오지 않는다. 화면에서 보여 줄 때(M3-T5) 받는다.
- 서재에서 지운 논문의 인용 데이터는 다음 갱신 때 지운다. 어느 표에서도 쓰지 않는 `works`와 `outside_references`도 함께 지운다([CitationStore.prune](../../src/jjabtero/citations.py#CitationStore.prune)).

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

- `GET /api/citations/status`는 [citation_status](../../src/jjabtero/citations.py#citation_status)가 처리하며 [CitationStatus](../../src/jjabtero/citations.py#CitationStatus)를 돌려준다. 서재 논문 수, OpenAlex에 연결된 수, 찾지 못한 수, 인용 데이터를 가져온 수, Semantic Scholar로 확인한 수([9절](#9-semantic-scholar-참고문헌)), 갱신 중인지, 마지막 갱신 시각, 마지막 오류다.
- `POST /api/citations/refresh`는 [refresh_citations](../../src/jjabtero/citations.py#refresh_citations)가 처리한다. 모든 논문을 가져올 대상으로 표시하고 갱신을 깨운 뒤 상태를 돌려준다.
- `GET /api/papers/{id}/citations`는 [paper_citations](../../src/jjabtero/citations.py#paper_citations)가 처리하며([paper_router](../../src/jjabtero/citations.py#paper_router)) 논문 하나의 인용 목록 [PaperCitations](../../src/jjabtero/citations.py#PaperCitations)을 돌려준다.
  - `state`: `no_doi`(DOI가 없어 연결할 수 없음), `not_found`(7일 안에 찾지 못함), `pending`(연결 전이거나 아직 가져오지 않음), `ready`.
  - `ready`면 피인용 기간(시작·끝), 기간 안 피인용 전체 건수, 그때의 `citing_limit`, 가져온 시각과 함께 참고문헌과 피인용 목록을 준다. 둘 다 피인용 많은 순이다([CitationStore.paper_lists](../../src/jjabtero/citations.py#CitationStore.paper_lists)).
  - 목록의 항목은 [CitedWork](../../src/jjabtero/citations.py#CitedWork)(OpenAlex ID, 제목, 저자, 항목 종류, 연도, 게재처, DOI, 피인용 수, 피인용 항목은 공유 참고문헌 수)이고, OpenAlex ID나 DOI가 같은 서재 논문이 있으면 그 ID(`library_paper_id`)를 담는다.
- `GET /api/papers/{id}/related`는 [paper_related](../../src/jjabtero/citations.py#paper_related)가 처리하며 가까운 논문 목록 [PaperRelated](../../src/jjabtero/citations.py#PaperRelated)(상태, 가져온 피인용 수, 참고문헌 수, 항목)을 돌려준다. 항목은 [RelatedWork](../../src/jjabtero/citations.py#RelatedWork)로, `CitedWork`에 점수와 까닭(이 논문을 인용, 이 논문이 인용, 함께 인용된 횟수, 공유 참고문헌 수)을 더한 것이다.
  - 후보는 이 논문의 참고문헌, 가져온 피인용, 함께 인용된 논문이다([CitationStore.relation_rows](../../src/jjabtero/citations.py#CitationStore.relation_rows)). 논문 자신은 뺀다.
  - 점수([related_works](../../src/jjabtero/citations.py#related_works), 까닭은 [Relation](../../src/jjabtero/citations.py#Relation))는 직접 인용이면 0.5([DIRECT_WEIGHT](../../src/jjabtero/citations.py#DIRECT_WEIGHT)) + 함께 인용된 비율(공동 인용 수 / 가져온 피인용 수) + 공유 참고문헌 비율(공유 참고문헌 수 / 이 논문의 참고문헌 수)이다. 세 값 모두 0~1 근처라 어느 하나가 압도하지 않고, 화면에 까닭을 그대로 보여 줄 수 있다. 같은 점수는 ID 순이다. 상위 30편([RELATED_LIMIT](../../src/jjabtero/citations.py#RELATED_LIMIT))을 준다.
  - 항목마다 기준 논문의 선행(`prior`)인지 후행(`later`)인지와 그 근거(`citation`, `date`)를 준다([work_direction](../../src/jjabtero/citations.py#work_direction), 타입 [Direction](../../src/jjabtero/citations.py#Direction), [DirectionBasis](../../src/jjabtero/citations.py#DirectionBasis)). 한쪽으로만 인용하면 인용 방향을 따른다. 기준 논문이 인용한 논문은 선행, 기준 논문을 인용한 논문은 후행이다. 인용이 없거나 서로 인용하면 공개일을 비교하고, 한쪽이라도 연도뿐이면 연도로 비교한다([when](../../src/jjabtero/citations.py#when)). 기준 논문의 공개일은 인용 데이터를 가져올 때 받은 공개일이고, 없으면 서재의 연도다. 같거나 알 수 없으면 표시하지 않는다.
  - 함께 인용된 논문은 서지 정보가 없으므로 이 API를 부를 때 없는 것만 OpenAlex에서 100건씩 받아 `works`에 둔다([lookup_works](../../src/jjabtero/citations.py#lookup_works), [CitationStore.works_by_id](../../src/jjabtero/citations.py#CitationStore.works_by_id), [CitationStore.save_works](../../src/jjabtero/citations.py#CitationStore.save_works)). 받지 못하면 제목 없이 ID로 보여 준다.
- 논문 상세에 "인용" 칸([CitationLists](../../frontend/src/CitationLists.vue))을 둔다. "가까운 논문"이 첫 칸이고, 항목마다 까닭을 작은 표시로 보여 준다([relationReasons](../../frontend/src/citationListState.ts#relationReasons)). 까닭 앞에 "선행" 또는 "후행" 표시를 두고, 마우스를 올리면 근거(기준 논문이 인용한 앞선 연구, 기준 논문보다 먼저 공개된 논문 등)를 보여 준다([directionTag](../../frontend/src/citationListState.ts#directionTag), 타입 [Direction](../../frontend/src/api.ts#Direction), [DirectionBasis](../../frontend/src/api.ts#DirectionBasis)). API 호출은 [fetchPaperRelated](../../frontend/src/api.ts#fetchPaperRelated)(타입 [PaperRelated](../../frontend/src/api.ts#PaperRelated), [RelatedWork](../../frontend/src/api.ts#RelatedWork))다. "피인용 n"과 "참고문헌 n"을 바꿔 보고, 피인용은 기간과 "n편 가운데 피인용 많은 순 m편"을 알린다. 항목마다 제목(DOI 또는 OpenAlex로 이어지는 링크), 저자·연도·게재처, 피인용 수, 공유 참고문헌 수를 보여 주고, 서재에 있으면 "서재에 있음", 없으면 "서재에 담기"를 둔다. 상태가 `ready`가 아니면 그 까닭을 한 줄로 알린다.
  - "서재에 담기"는 항목을 서재 입력으로 바꿔([citedWorkInput](../../frontend/src/citationListState.ts#citedWorkInput): 원문 주소는 DOI, 없으면 OpenAlex 주소, OpenAlex ID 포함) 논문을 추가하고, 그 항목을 "서재에 있음"으로 바꾼 뒤 서재 목록을 다시 읽는다. DOI가 이미 있으면 그 논문으로 표시한다. 상태는 [createCitationListState](../../frontend/src/citationListState.ts#createCitationListState)가 가지며, 다른 논문을 고른 뒤 늦게 온 응답은 버린다. API 호출은 [fetchPaperCitations](../../frontend/src/api.ts#fetchPaperCitations)(타입 [PaperCitations](../../frontend/src/api.ts#PaperCitations), [CitedWork](../../frontend/src/api.ts#CitedWork))다.
- `GET /api/citations/recommendations`는 [recommendations](../../src/jjabtero/citations.py#recommendations)가 처리하며 서재 밖 추천 [Recommendations](../../src/jjabtero/citations.py#Recommendations)(서재 논문 수, 계산에 쓴 논문 수, 항목)을 돌려준다.
  - 인용 데이터가 있는 서재 논문 A마다 가까운 논문 점수(`related_works`)를 구해 같은 논문끼리 더한다([recommend_works](../../src/jjabtero/citations.py#recommend_works), 결과는 [Recommendation](../../src/jjabtero/citations.py#Recommendation)). 여러 서재 논문과 이어질수록 점수가 커진다. 같은 점수는 이어진 서재 논문 수, ID 순이다.
  - 서재에 있는 논문(OpenAlex ID 또는 DOI가 같은 것)은 뺀다. 상위 50편([RECOMMEND_LIMIT](../../src/jjabtero/citations.py#RECOMMEND_LIMIT))을 주고, 서지 정보가 없는 것은 가까운 논문처럼 OpenAlex에서 받아 둔다.
  - 항목은 [RecommendedWork](../../src/jjabtero/citations.py#RecommendedWork)로, `CitedWork`에 점수와 이어진 서재 논문 목록([RecommendationSource](../../src/jjabtero/citations.py#RecommendationSource): 논문 ID, 제목)을 더한 것이다.
  - 이어진 서재 논문마다 그 논문을 기준으로 한 선행·후행과 근거를 가까운 논문과 같은 규칙으로 준다. 서재 논문의 공개일은 [CitationStore.publication_dates](../../src/jjabtero/citations.py#CitationStore.publication_dates)로 읽는다. 항목 전체의 방향([overall_direction](../../src/jjabtero/citations.py#overall_direction))은 모두 같으면 그 방향, 서로 다르면 `mixed`, 하나도 없으면 없음이다.
- 왼쪽 화면 목록에 "추천"을 두고, 설정처럼 가운데·오른쪽을 합친 넓은 칸에 추천 화면([RecommendView](../../frontend/src/RecommendView.vue))을 보여 준다. 알림처럼 띄우지 않는다. 항목마다 제목, 저자·연도·게재처, 이어진 서재 논문(논문마다 괄호 안에 선행·후행), 항목 전체의 선행·후행 표시("선행·후행"은 섞임), 점수, 피인용 수, "서재에 담기"를 두고, "다시 계산"으로 새로 읽는다. 상태는 [createRecommendState](../../frontend/src/recommendState.ts#createRecommendState), API 호출은 [fetchRecommendations](../../frontend/src/api.ts#fetchRecommendations)(타입 [Recommendations](../../frontend/src/api.ts#Recommendations), [RecommendedWork](../../frontend/src/api.ts#RecommendedWork))다.
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
- 추천 점수 더하기(여러 서재 논문과 이어진 논문이 위로, 서재 논문 빼기, 한도)와 API(빈 서재, 이어진 서재 논문, 서재 DOI 빼기, 없는 서지 정보 받기).
- 가까운 논문 점수(직접 인용, 함께 인용된 비율, 공유 참고문헌 비율, 자신 빼기, 순서)와 API(점수 순, 없는 서지 정보를 한 번만 받기).
- 선행·후행: 한쪽 인용이면 인용 방향, 아니면 공개일(한쪽이 연도뿐이면 연도), 같거나 모르면 없음, 항목 전체 방향 모으기(같음, 섞임, 없음). 가까운 논문 API와 추천 API(이어진 서재 논문마다와 항목 전체)의 방향과 근거.
- 논문의 인용 목록 API: 가져오기 전 `pending`, 가져온 뒤 기간·건수·한도, 피인용 많은 순 목록과 서지 정보, 서재에 있는 논문 표시, DOI 없음·찾지 못함·없는 논문.

[citationListState.test](../../frontend/src/citationListState.test.ts)는 인용 논문의 서재 입력 변환, 목록 읽기, 담기와 표시, 이미 있는 DOI, 실패 메시지, 늦게 온 응답 버리기, 가까운 논문 읽기와 담기 표시, 까닭 문구, 선행·후행 표시와 근거 문구를 확인한다. [recommendState.test](../../frontend/src/recommendState.test.ts)는 추천 읽기, 담기와 표시, 이미 있음, 실패 메시지를 확인한다.

[api.test](../../frontend/src/api.test.ts)는 `toPaperInput`의 OpenAlex ID와 인용 데이터 API 호출을 확인한다.

## 8. 미결정 사항

- 없음. 점수 식은 쓰면서 고친다.

## 9. Semantic Scholar 참고문헌

OpenAlex의 참고문헌 목록은 빠진 것이 많아 서재 논문 사이의 인용 선이 빠진다. 'Attention Is All You Need'는 OpenAlex에 참고문헌이 35개뿐이었고(실제 40개), LSTM, Bahdanau, GRU 논문이 빠져 서재에 그 논문들이 있어도 인용 선이 없었다. Semantic Scholar에는 41개가 모두 있었다(2026-11-15 확인). Crossref에는 arXiv 논문의 참고문헌이 없었다. 그래서 사용자가 Semantic Scholar를 함께 쓰기로 골랐다([이슈 I16](../Issue.md)). 코드는 [semantic_scholar 모듈](../../src/jjabtero/semantic_scholar.py)이다.

**받기**

- 인용 데이터 갱신([CitationSync](../../src/jjabtero/citations.py#CitationSync), [5. 갱신](#5-갱신))이 OpenAlex 다음에 DOI가 있는 서재 논문마다 Semantic Scholar 참고문헌을 받는다([refresh_references](../../src/jjabtero/semantic_scholar.py#refresh_references)). 논문을 담으면 갱신이 바로 깨어나므로 곧 받는다. 받은 지 7일([S2_REFRESH_AFTER](../../src/jjabtero/semantic_scholar.py#S2_REFRESH_AFTER))이 지나면 다시 받는다. 서재에서 지운 논문의 기록은 지운다.
- `GET https://api.semanticscholar.org/graph/v1/paper/DOI:<DOI>/references?fields=title,externalIds&limit=1000`([S2_PAPER_URL](../../src/jjabtero/semantic_scholar.py#S2_PAPER_URL), [S2_REFERENCE_LIMIT](../../src/jjabtero/semantic_scholar.py#S2_REFERENCE_LIMIT))로 받는다([fetch_references](../../src/jjabtero/semantic_scholar.py#fetch_references)). DOI로 없으면 제목 맞추기(`/paper/search/match`)로 찾은 논문의 제목이 서재 제목과 똑같을 때만 그 논문의 참고문헌을 받는다. SE Networks의 CVPR DOI(`10.1109/cvpr.2018.00745`)는 DOI로 없었고 제목으로 찾아 84개를 받았다(2026-11-15 확인). 둘 다 없으면 "없음"으로 적고 7일 뒤 다시 본다.
- Semantic Scholar에는 서재 논문의 DOI와 제목만 보낸다. 키 없이도 쓰지만 공용 한도가 있어, 요청 사이를 1.1초([S2_REQUEST_GAP_SECONDS](../../src/jjabtero/semantic_scholar.py#S2_REQUEST_GAP_SECONDS)) 띄우고, 429를 받으면([S2BudgetError](../../src/jjabtero/semantic_scholar.py#S2BudgetError)) 그 회차를 멈추고 다음 갱신(1시간 뒤)에 이어 받는다. 환경 변수 `SEMANTIC_SCHOLAR_API_KEY`가 있으면 `x-api-key` 머리글로 보낸다. 키는 저장소에 두지 않는다.

**저장**

- 인용 캐시 파일 `citations.db` 안의 표 두 개에 둔다([S2Store](../../src/jjabtero/semantic_scholar.py#S2Store)). `s2_fetches`(서재 논문 DOI, 받은 시각, 찾았는지)와 `s2_references`(서재 논문 DOI, 참고문헌의 DOI, arXiv ID, 다듬은 제목)다. 새 표만 더하므로 캐시 버전을 올리지 않는다. 캐시 파일 전체가 드라이브에 함께 보관된다([4. 저장](#4-저장)).
- 식별자는 [PaperKeys](../../src/jjabtero/semantic_scholar.py#PaperKeys)다([paper_keys](../../src/jjabtero/semantic_scholar.py#paper_keys)). DOI는 소문자, arXiv ID는 소문자에 버전(`v5`)과 `arXiv:` 머리를 뗀 것이다([arxiv_id](../../src/jjabtero/semantic_scholar.py#arxiv_id)). arXiv DOI(`10.48550/arxiv.<ID>`)에서도 arXiv ID를 얻는다. 제목은 [normalize](../../src/jjabtero/titles.py#normalize)한 글이며 낱말이 3개([MIN_TITLE_WORDS](../../src/jjabtero/semantic_scholar.py#MIN_TITLE_WORDS)) 이상일 때만 쓴다.

**맞추기**

- 서재 논문 A의 Semantic Scholar 참고문헌 가운데 서재 논문 B와 DOI, arXiv ID, 제목 가운데 하나라도 같은 것([same_paper](../../src/jjabtero/semantic_scholar.py#same_paper))이 있으면 A가 B를 인용한다([library_cites](../../src/jjabtero/semantic_scholar.py#library_cites)). 서재 그래프의 인용 선에 더한다([서재 인용 그래프 설계](CitationGraph.md#2-그래프-데이터)).
- 새 논문 Y를 담으면 Y의 참고문헌으로 Y가 인용한 서재 논문을 찾고, 다른 서재 논문의 참고문헌은 이미 받아 두었으므로 Y를 인용한 서재 논문도 다시 받지 않고 찾는다. OpenAlex ID가 없는 논문도 DOI만 있으면 선이 생긴다.
- 상태 API의 `s2_checked`는 Semantic Scholar에서 참고문헌을 받은 서재 논문 수다([CitationSync.s2_store](../../src/jjabtero/citations.py#CitationSync.s2_store), [S2Store.checked_count](../../src/jjabtero/semantic_scholar.py#S2Store.checked_count)). 설정 페이지의 "인용 데이터" 칸에 "Semantic Scholar 확인"으로 보인다.
- [test_semantic_scholar](../../tests/test_semantic_scholar.py)가 식별자, DOI와 제목으로 받기, 429, 오래된 것만 받기와 지우기, 맞추기, 그래프와 상태 API를 가짜 Semantic Scholar로 확인한다.
