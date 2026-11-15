# 서재 인용 그래프 설계

이 문서는 서재 논문들이 인용으로 어떻게 이어져 있는지 네트워크 그림으로 보는 "그래프" 화면([제품 비전](../ProductVision.md#6-인용-기반-연결추천))과, 그 화면과 서재 통계(M5)가 함께 쓸 시각화 라이브러리를 정한다. 인용 데이터 자체는 [인용 데이터 설계](Citations.md)를 따른다. 태스크는 [로드맵의 M3](../Roadmap.md#m3-인용-기반-연결추천)에 있다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 시각화 라이브러리

- **Apache ECharts**(npm `echarts`, Apache-2.0)를 쓴다. 버전은 6.1.0으로 고정한다(2026-05-19 배포, 이 문서를 쓸 때의 최신 정식판).
- 비교한 후보와 고른 까닭은 다음과 같다.

| 후보 | 네트워크 그래프 | 통계 차트(M5) | 판단 |
| --- | --- | --- | --- |
| ECharts | `graph` 시리즈(힘 배치, 고정 배치, 좌표축 위 배치, 화살표, 확대·이동, 끌기) | 막대, 선, 원, 히트맵, 산점도 등 모두 | **고름**. 한 라이브러리로 그래프와 통계를 같은 모양으로 그린다. |
| Cytoscape.js | 아주 강함(배치 알고리즘이 많음) | 없음 | 통계용 라이브러리를 하나 더 들여야 한다. |
| D3 | 무엇이든 그릴 수 있음 | 무엇이든 그릴 수 있음 | 저수준이라 축, 범례, 도움말, 확대를 모두 직접 짜야 한다. |
| vis-network | 쉬움 | 없음 | 관리가 뜸하고 통계를 못 그린다. |

- 서재 그래프는 많아야 수백 개 점이라 ECharts의 힘 배치로 충분하다.
- 무거우므로(전체 약 1MB) `echarts/core`에 필요한 부품(`GraphChart`, 축·격자·도움말·범례 부품, `CanvasRenderer`)만 등록해 크기를 줄이고, 그래프 화면을 처음 열 때만 불러온다(`App.vue`의 `defineAsyncComponent`). 첫 화면 번들을 키우지 않기 위해서다([이슈 I11](../Issue.md)).

## 2. 그래프 데이터

[citation_graph 모듈](../../src/jjabtero/citation_graph.py)의 [build_graph](../../src/jjabtero/citation_graph.py#build_graph)가 만든다. 결과는 [CitationGraph](../../src/jjabtero/citation_graph.py#CitationGraph)(점 [GraphNode](../../src/jjabtero/citation_graph.py#GraphNode), 선 [GraphEdge](../../src/jjabtero/citation_graph.py#GraphEdge))다.

**점**

- 서재 논문은 모두 점이 된다. 인용 데이터가 없는 논문도 넣되 `has_data`를 거짓으로 둔다. 점 ID는 `p<논문 ID>`다.
- 사용자가 고르면(화면은 15편, [OUTSIDE_COUNT](../../frontend/src/graphState.ts#OUTSIDE_COUNT)) 서재 밖 추천 논문을 점수 순으로 최대 30편([OUTSIDE_LIMIT](../../src/jjabtero/citation_graph.py#OUTSIDE_LIMIT)) 더한다. 추천은 [추천](Citations.md#6-api와-화면)과 같은 계산([recommend_works](../../src/jjabtero/citations.py#recommend_works))이다. 점 ID는 OpenAlex ID다.
- 점마다 제목, 저자, 연도, 게재처, DOI, 피인용 수(아는 경우), 서재 논문이면 논문 ID, 서재 밖이면 추천 점수를 담는다. 연도는 서재 논문이면 서재의 연도, 없으면 인용 데이터의 공개일 연도다.

**선**

- `cites`: 인용. 방향이 있다(인용한 논문 → 인용된 논문). 서재 논문 A의 참고문헌에 B가 있거나, B의 가져온 피인용에 A가 있으면 A → B다. 선행·후행([인용 데이터 설계](Citations.md#6-api와-화면))이 화살표 방향으로 보인다.
- `related`: 직접 인용은 없지만 가까움. 방향이 없다. 두 서재 논문이 참고문헌을 2개 이상 공유하거나([COUPLING_MIN](../../src/jjabtero/citation_graph.py#COUPLING_MIN)) 함께 2번 이상 인용되면 잇고, 공유 참고문헌 수와 함께 인용된 횟수를 담는다. 같은 두 점 사이에 인용 선이 있으면 그리지 않는다. 그림이 복잡해지지 않게 하기 위해서다.
- 서재 밖 논문은 이어진 서재 논문마다 선 하나를 둔다. 서재 논문이 인용했으면 서재 논문 → 그 논문, 그 논문이 서재 논문을 인용했으면 그 논문 → 서재 논문의 `cites`, 그 밖에는 `related`다.
- 서재 논문 사이의 선은 [library_edges](../../src/jjabtero/citation_graph.py#library_edges)가, 서재 밖 논문의 선은 [outside_edges](../../src/jjabtero/citation_graph.py#outside_edges)가 만든다.

## 3. API

- `GET /api/citations/graph?outside=<0~30>`는 [citation_graph](../../src/jjabtero/citation_graph.py#citation_graph)가 처리한다([router](../../src/jjabtero/citation_graph.py#router)). `outside`는 더할 서재 밖 논문 수이고 기본값은 0이다. 로그인이 켜져 있으면 로그인해야 쓴다.
- 서지 정보가 없는 서재 밖 논문은 추천 API처럼 OpenAlex에서 받아 둔다.

## 4. 화면

- 왼쪽 목록에 "그래프"를 두고, 추천처럼 가운데·오른쪽을 합친 넓은 칸에 그래프 화면([GraphView](../../frontend/src/GraphView.vue))을 보여 준다.
- 위쪽 도구줄에서 배치("연도 순", "자유 배치")와 "추천 논문 함께 보기"를 고르고, "다시 그리기"로 새로 읽는다.
  - **연도 순**(처음 배치): 가로축이 공개 연도다. 왼쪽이 선행, 오른쪽이 후행이라 연구의 흐름이 보인다. 점이 있는 연도만 열로 두고 빈 연도는 건너뛴다. 오래된 논문 하나 때문에 축이 길게 늘어나 나머지가 한쪽에 몰리지 않게 하기 위해서다. 같은 연도의 점은 서재 논문을 위로, 그다음 피인용 많은 순으로 세로로 쌓는다. 휠로 연도 범위를 넓히고 좁힌다. 연도를 모르는 점은 이 배치에서 빼고 그 수를 알린다. 위치는 [yearLayout](../../frontend/src/graphOption.ts#yearLayout)이 정한다.
  - **자유 배치**: 힘 배치(force)로 이어진 점끼리 모인다. 끌어서 옮길 수 있다.
- 서재 논문은 기본 색, 서재 밖 논문은 회색, 인용 데이터가 없는 서재 논문은 흐리게 그린다. 점 크기는 피인용 수의 로그에 비례한다([symbolSize](../../frontend/src/graphOption.ts#symbolSize)). 이름표는 서재 논문에만 붙이고, 겹치면 숨긴다. 인용 선은 실선과 화살표, 가까움 선은 점선이다. 마우스를 올리면 이웃만 강조하고 도움말(점은 제목, 연도, 피인용 수, 추천 점수, 선은 관계와 공유 참고문헌 수·함께 인용 횟수 [edgeText](../../frontend/src/graphOption.ts#edgeText))을 보여 준다. 확대·이동이 된다.
- 점을 누르면 아래에 그 논문 카드가 열린다. 서재 논문이면 "서재에서 보기"(서재 화면에서 그 논문을 고름), 서재 밖 논문이면 "서재에 담기"를 둔다. 담으면 그래프를 다시 읽는다.
- ECharts 설정은 [graphOption](../../frontend/src/graphOption.ts#graphOption)(배치 이름 [GraphLayout](../../frontend/src/graphOption.ts#GraphLayout), 밝은·어두운 테마 색 [GraphPalette](../../frontend/src/graphOption.ts#GraphPalette))이 만든다. 상태(읽기, 고른 점, 담기)는 [createGraphState](../../frontend/src/graphState.ts#createGraphState)가 가진다. API 호출은 [fetchCitationGraph](../../frontend/src/api.ts#fetchCitationGraph)(타입 [CitationGraph](../../frontend/src/api.ts#CitationGraph), [GraphNode](../../frontend/src/api.ts#GraphNode), [GraphEdge](../../frontend/src/api.ts#GraphEdge))다.

## 5. 테스트

- [test_citation_graph](../../tests/test_citation_graph.py)는 서재 논문 사이의 인용 선(참고문헌과 피인용 양쪽), 가까움 선의 기준과 인용 선이 있을 때 빼기, 서재 밖 논문과 그 선의 방향, API(인용 데이터 없는 논문, `outside` 범위, 서지 정보 받기)를 확인한다.
- [graphOption.test](../../frontend/src/graphOption.test.ts)는 연도 순 위치(연도별 열, 같은 연도 쌓기, 연도 모름 빼기)와 설정(점 종류별 모양, 선 모양, 배치 전환)을 확인한다. [graphState.test](../../frontend/src/graphState.test.ts)는 읽기, 고르기, 담기와 다시 읽기, 실패 메시지를 확인한다.

## 6. 미결정 사항

- 없음. 서재가 커져 그림이 복잡해지면 선 기준(공유 참고문헌 수)을 올리거나 주제별로 거르는 기능을 이슈로 더한다.
