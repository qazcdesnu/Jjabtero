# 리더 인용 미리보기 설계

이 문서는 PDF 리더에서 본문의 인용 표시(예: `[110]`, `[Zhang et al., 2025b]`)에 마우스를 올리면 그 논문을 상자로 보여 주는 기능([제품 비전](../ProductVision.md#7-pdf-리더))을 정한다. 인용 표시를 찾는 방법, 참고문헌 항목의 글을 읽는 방법, 그 글로 논문을 찾는 방법, 상자의 모양과 동작이 범위다. 리더 자체는 [PDF 리더 설계](Reader.md)를 따른다. 태스크는 [로드맵의 M6](../Roadmap.md#m6-리더-인용-미리보기)에 있다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 흐름

```text
본문의 인용 표시 ─(1) 찾기─▶ 참고문헌 쪽의 위치 ─(2) 읽기─▶ 참고문헌 항목 글
                                                              │
                         상자 ◀─(4) 보여 주기─ 논문 ◀─(3) 찾기─┘
```

1. 브라우저(리더)가 인용 표시와 그 표시가 가리키는 참고문헌 위치를 찾는다.
2. 브라우저가 그 위치의 글을 읽어 참고문헌 항목 하나의 글을 만든다. pdf.js가 이미 쪽의 글과 좌표를 가지고 있기 때문이다.
3. 서버가 항목 글로 논문을 찾는다. 이 논문의 OpenAlex 참고문헌 목록과 먼저 맞춰 보고, 없으면 OpenAlex에서 검색한다.
4. 브라우저가 상자를 보여 주고, 서재에 담고 PDF 받기와 새 탭에서 읽기를 한다.

## 2. 인용 표시 찾기

**링크가 있는 PDF**(M6-T3)

- LaTeX의 `hyperref`로 만든 PDF(arXiv 논문 대부분)는 인용 표시마다 링크 주석이 있고, 목적지 이름이 `cite.`로 시작한다. 'Attention Is All You Need'는 링크 113개 가운데 76개가 `cite.` 목적지였다(예: `cite.hochreiter1997`, 2026-11-15 확인).
- 쪽을 그릴 때 pdf.js의 `page.getAnnotations()`로 링크 주석을 읽고, 목적지 이름이 `cite.`로 시작하는 것([isCitationDest](../../frontend/src/citationLinks.ts#isCitationDest))을 인용 링크([CitationLink](../../frontend/src/citationLinks.ts#CitationLink))로 삼는다. 쪽마다 한 번만 읽어 둔다. 목적지는 `pdf.getDestination(이름)`으로 [쪽 참조, `XYZ`, 왼쪽, 위, 배율]을 얻고 `pdf.getPageIndex`로 쪽 번호를 얻는다. 저자-연도 인용(`Zhang et al., 2025b, Wang et al., 2025`)은 저자마다 링크가 따로 있으므로 각각 따로 미리 본다.
- 링크 영역은 쪽 크기에 대한 비율(0~1)로 바꿔 둔다([linkRect](../../frontend/src/citationLinks.ts#linkRect), 꼭짓점은 pdf.js `PageViewport.convertToViewportPoint`로 화면 좌표로 바꾼다). 하이라이트와 같은 좌표계다([PDF 리더 설계](Reader.md#4-데이터)).
- 링크 위에 요소를 겹쳐 두지 않는다. 겹치면 그 아래 글을 고를 수 없어 하이라이트가 끊기기 때문이다. 대신 리더의 마우스 이동에서 마우스 위치가 인용 링크 영역 안인지 확인한다(하이라이트를 누를 때 쓰는 `hitTest`와 같은 방식). 안이면 마우스 모양을 손가락으로 바꾼다.
- 인용 링크를 누르면(글을 고르지 않았을 때) 목적지 쪽의 그 위치로 이동하고 상자를 닫는다.
- 이 일은 리더 화면([ReaderView](../../frontend/src/ReaderView.vue))이 한다.

**링크가 없는 PDF**(M6-T4)

출판사 PDF처럼 인용 링크가 없으면 글자만으로 참고문헌 항목과 본문 인용 표시를 찾는다([textCitations 모듈](../../frontend/src/textCitations.ts)). 'Attention Is All You Need'(번호 양식)와 'Darwin Gödel Machine'(저자-연도 양식, 72쪽)의 arXiv PDF에서 링크 주석을 지워 조사하고 확인했다(2026-11-15).

- **언제 쓰나**: 문서의 어느 쪽에도 `cite.` 링크가 없거나, 링크는 있어도 `cite.` 목적지를 하나도 찾을 수 없을 때 쓴다. 링크가 있는 PDF에서 수식의 `[0, 1]` 같은 글을 인용으로 잘못 잡지 않기 위해서다. 목적지가 없을 때는 쓸 수 없는 링크를 버리고 글자로 찾는다. 학술지 사이트(`s-rsa.com`)가 다시 올린 DGM PDF(23쪽, 번호 양식)는 `cite.` 링크 205개가 남아 있었지만 목적지는 하나도 없어, 링크를 따라가지도 글자로 찾지도 못했다([이슈 H4](../Issue.md), 2026-11-18). 처음 필요할 때 모든 쪽의 링크를 한 번 확인하고, 참고문헌 항목 목록을 한 번 만들어 둔다.
- **머리말·꼬리말 빼기**: 참고문헌 쪽들에서 같은 높이(반올림)에 같은 글(숫자는 무시)이 두 쪽 이상 나오면 머리말·꼬리말로 보고 뺀다. 학술지가 덧붙인 머리말("SuperIntelligence – Robotics – Safety & Alignment")은 위 6%보다 안쪽(758pt, 쪽 높이 792pt)에 있어, 번호 양식에서 들여쓰지 않은 줄로 보여 목록이 끝났다.
- **줄 만들기**([pageLines](../../frontend/src/textCitations.ts#pageLines), [PageText](../../frontend/src/textCitations.ts#PageText), [TextLine](../../frontend/src/textCitations.ts#TextLine)): 기준선이 2pt 안인 조각을 왼쪽부터 잇되, 40pt 넘게 떨어진 조각은 다른 단으로 보고 나눈다. 조각 사이가 떨어져 있으면 빈칸을 넣는다. 위아래 끝 6% 안의 줄(머리말, 꼬리말)과 숫자뿐인 줄(쪽 번호)은 뺀다.
- **참고문헌 절**: 문서 끝에서부터 "References", "Bibliography", "참고문헌" 제목 줄(앞의 절 번호 허용)을 찾는다([hasReferenceHeading](../../frontend/src/textCitations.ts#hasReferenceHeading)). 작은 대문자 제목은 "R"과 "EFERENCES"처럼 조각나 있어 빈칸을 빼고도 본다(DGM). 그 쪽부터 끝까지가 대상이다.
- **항목 나누기**([referenceEntries](../../frontend/src/textCitations.ts#referenceEntries), [ReferenceEntry](../../frontend/src/textCitations.ts#ReferenceEntry)): 두 단이면 쪽마다 왼쪽 단(가장 왼쪽 줄에서 150pt 안)을 다 읽고 오른쪽 단을 읽는다. 오른쪽에 있는 줄이 그 쪽 줄의 1/4 이상일 때만 두 단으로 본다. 한 단 쪽에서 낱말 사이가 40pt 넘게 벌어져 줄의 뒷부분이 따로 떨어지면(DGM 학술지판 12쪽의 "Gemini model “thinking” updates — march") 오른쪽 단으로 보아 목록이 [46]에서 끝났기 때문이다. 같은 높이의 줄은 왼쪽부터 읽는다.
  - 번호 양식: 세 줄 이상이 `[n]`이나 `n. `로 시작하면 번호 양식이다. 두 꼴 가운데 많은 쪽만 항목 번호로 본다. 번호로 시작하고 그 번호가 앞 항목 번호보다 크고 3 안([NUMBER_STEP](../../frontend/src/textCitations.ts#NUMBER_STEP))인 줄이 항목의 첫 줄이고, 번호를 기억한다. "2025. URL …"처럼 연도로 시작하는 이어지는 줄을 2025번 항목으로 보지 않기 위해서다. Attention은 항목 첫 줄이 113pt, 이어지는 줄이 129.6pt였다.
  - 내어쓰기 양식: 쪽·단마다 가장 왼쪽 줄(1.5pt 안)이 항목의 첫 줄이다. DGM은 108pt와 118pt였다.
  - 줄 끝 하이픈으로 끊긴 낱말은 붙인다.
  - **끝**: 부록 제목("Appendix", "Supplementary", 또는 `A APPENDIX`처럼 대문자 한 글자 뒤 모두 대문자인 짧은 줄)이 나오거나, 번호 양식에서 들여쓰지 않은 이어지는 줄이 나오거나, 같은 쪽에서 줄 사이가 줄 높이의 3.5배보다 벌어지면 목록이 끝난 것으로 본다. Attention의 마지막 항목이 뒤쪽 그림 부록(13~15쪽)의 글까지 끌어가서 더했다.
  - 항목마다 첫 저자의 성([firstSurname](../../frontend/src/textCitations.ts#firstSurname): `성, 이름`이면 쉼표 앞, `이름 성`이면 첫 저자의 마지막 낱말, 악센트를 뗀 소문자)과 항목에 나오는 연도들을 둔다.
- **본문 인용 표시**([findMarkers](../../frontend/src/textCitations.ts#findMarkers), [TextMarker](../../frontend/src/textCitations.ts#TextMarker)): 참고문헌 영역 안([inReferences](../../frontend/src/textCitations.ts#inReferences))은 건너뛴다. 목록의 `[5]` 같은 항목 번호를 인용으로 잡지 않기 위해서다.
  - 쪽의 조각을 줄바꿈으로 이은 글에서 찾는다. 여러 문헌을 한꺼번에 인용한 표시는 줄을 넘어가기 쉽기 때문이다(`[13, 29, 47, 66,` ↵ `112]`). 학술지판 DGM 본문에서 숫자 200개 가운데 25개가 줄을 넘어간 표시라 빠졌다([이슈 I26](../Issue.md), 2026-11-18). 표시가 두 조각에 걸치면 영역도 조각마다 둔다. 참고문헌 영역의 조각은 넘어갈 수 없게 한다.
  - 번호 양식: `[2]`, `[1, 3]`, `[1–4]`, `[ 3; 1 ]` 안의 숫자마다 그 번호의 항목과 잇는다. 범위는 양 끝 숫자만 잇는다.
  - 저자-연도 양식: `Zhang et al., 2025b`, `Darwin, 2023`, `Smith and Jones (2020)`처럼 대문자로 시작하는 성 뒤의 연도(글자 포함)를 찾아, 성과 연도가 같은 항목과 잇는다([authorYearEntry](../../frontend/src/textCitations.ts#authorYearEntry)). 같은 성·연도가 여럿이면 항목 글에 `2025b`가 그대로 있으면 그것, 없으면 참고문헌 순서(a가 첫째)다. 맞는 항목이 없는 글은 인용 표시가 아니다. 이것이 잘못 잡힘을 걸러 낸다.
  - 표시 영역은 조각 안의 글자 위치를 조각 너비에 비례해 잡는다. 브라우저에서는 그 조각의 글꼴 계열(pdf.js `styles`의 `fontFamily`)로 캔버스에서 글자 너비를 재어 그 비율을 쓴다([MeasureText](../../frontend/src/textCitations.ts#MeasureText)). 글자 수 비율만 쓰면 한 줄이 한 조각인 PDF에서 줄 앞쪽 숫자가 몇 pt 어긋나, 학술지판 DGM 3쪽의 `[2, 30, 32, 33, 113]` 같은 표시의 앞 숫자에 마우스를 올려도 상자가 뜨지 않았다. 재어 쓰자 2쪽 숫자 61개와 3쪽 여러 문헌 인용의 숫자 54개가 모두 맞는 항목을 보였다(2026-11-18).
- 찾은 표시는 링크와 같은 [CitationLink](../../frontend/src/citationLinks.ts#CitationLink)로 둔다. 목적지는 `text:<항목 번호>`이고, 항목 글은 이미 있으므로 3절의 계산 없이 그 글(600자까지)을 쓴다. 누르면 그 항목의 쪽과 위치로 간다.
- DGM 학술지판(목적지 없는 링크): 고친 뒤 항목 156개(빠진 번호 없음)와 본문 표시 179개를 찾았고, 1쪽 `[116]`에 마우스를 올리면 "Gödel Machines: Fully Self-referential Optimal Universal Self-improvers"(Schmidhuber, 2007)를 상자에 보였다(2026-11-18).
- 결과: 링크를 지운 Attention에서 항목 40개와 본문 표시 76개, DGM에서 항목 184개와 본문 표시 215개를 찾았다. 브라우저에서 Attention의 `[13]`은 LSTM 논문을, DGM의 `(Darwin, 2023)`은 그 항목을 상자에 보였고, 누르면 참고문헌 쪽으로 갔다. DGM의 그 항목은 책이라 OpenAlex에서 논문을 찾지 못해 "찾지 못했습니다"와 항목 글을 보였다.

## 3. 참고문헌 항목 읽기

- 인용 목적지는 처음 필요할 때 `pdf.getDestinations()`로 한 번에 읽어 [Anchor](../../frontend/src/citationLinks.ts#Anchor)로 바꿔 둔다([anchorFromDest](../../frontend/src/citationLinks.ts#anchorFromDest)). 목적지 쪽의 글(`page.getTextContent()`)을 PDF 좌표(아래가 0인 y, 글자의 기준선, 너비)로 읽어 [TextPiece](../../frontend/src/citationLinks.ts#TextPiece)로 둔다. 쪽마다 한 번만 읽는다.
- 데모 PDF에서 `cite.hochreiter1997`의 위 좌표는 453.4, 항목 첫 줄 기준선은 442.5, 앞 항목의 마지막 줄은 462.3이었다(2026-11-15 확인). 목적지의 위 좌표가 첫 줄보다 약 11pt 위에 있으므로 아래 경계 규칙으로 앞 항목이 섞이지 않는다.
- 같은 쪽의 모든 인용 목적지를 모아 항목의 경계를 정한다. 참고문헌 목록에서 각 항목의 머리가 곧 다른 인용의 목적지이기 때문이다.
  - 단(column): 이 목적지보다 왼쪽 좌표가 50pt([COLUMN_GAP](../../frontend/src/citationLinks.ts#COLUMN_GAP)) 넘게 큰 목적지가 있으면 그 왼쪽 좌표를 이 단의 오른쪽 끝으로 본다. 없으면 쪽의 오른쪽 끝이다.
  - 아래 끝: 같은 단(왼쪽 좌표 차이 50pt 이하)에서 이 목적지 바로 아래 목적지의 위 좌표다. 없으면 위 좌표에서 80pt([ENTRY_MAX_DROP](../../frontend/src/citationLinks.ts#ENTRY_MAX_DROP), 약 6줄) 아래까지다.
  - 글 조각 가운데 왼쪽 좌표가 단 안에 있고 기준선이 위 좌표 + 2pt 이하이며 아래 끝 + 2pt보다 위인 것을 위에서 아래, 왼쪽에서 오른쪽 순서로 잇는다. 같은 줄(기준선 차이 2pt 이하)의 조각 사이가 0.5pt 넘게 떨어져 있으면 빈칸을 넣는다. pdf.js 조각에는 빈칸이 빠져 있기도 해서, 빈칸 없이 이으면 `translate.CoRR`처럼 붙어 제목 후보 고르기와 검색이 틀렸다(2026-11-15 확인). 줄 끝 하이픈으로 끊긴 낱말은 붙이고, 빈칸은 하나로 줄이며, 600자([ENTRY_MAX_CHARS](../../frontend/src/citationLinks.ts#ENTRY_MAX_CHARS))에서 자른다.
- 목적지가 `XYZ`가 아니어서 왼쪽 좌표가 없으면 단을 쪽 전체로 본다.
- 이 계산은 순수 함수 [referenceEntryText](../../frontend/src/citationLinks.ts#referenceEntryText)로 두어 Vitest로 확인한다.

## 4. 논문 찾기

`POST /api/papers/{id}/references/resolve`(본문 [ResolveIn](../../src/jjabtero/references.py#ResolveIn) `{"text": 항목 글}`, 2,000자까지)를 [resolve_reference](../../src/jjabtero/references.py#resolve_reference)가 처리한다([router](../../src/jjabtero/references.py#router)). 찾는 일은 [_find](../../src/jjabtero/references.py#_find)가 한다. 로그인이 켜져 있으면 로그인해야 쓴다.

**0단계: 항목 글의 식별자**

- 항목 글에 DOI(`10.<번호>/…`)나 arXiv 주소(`arxiv.org/abs/<번호>`, `arxiv.org/pdf/<번호>`)·번호(`arXiv:<번호>`)가 있으면 DOI로 바꿔 모은다(arXiv는 `10.48550/arxiv.<번호>`, [reference_dois](../../src/jjabtero/references.py#reference_dois)). 식별자는 제목보다 확실하다.
- 이 논문의 참고문헌에 같은 DOI가 있으면 그것이고, 없으면 OpenAlex에서 `GET /works/doi:<DOI>`로 찾는다([_lookup_doi](../../src/jjabtero/references.py#_lookup_doi)). 찾은 경로는 `identifier`다. 못 찾으면 1단계로 간다.
- 사용자가 알려 준 'Darwin Gödel Machine' 항목 글("… Darwin godel machine: Openended evolution of self-improving agents, 2025b. URL https://arxiv.org/abs/2505.22954.")은 이 단계가 없을 때 찾지 못했다(2026-11-15, [이슈 H3](../Issue.md)).

**1단계: 이 논문의 참고문헌과 맞추기**

- 리더로 읽는 논문이 OpenAlex에 연결되어 인용 데이터가 있으면, 그 참고문헌 목록([인용 데이터 설계](Citations.md#4-저장)의 `references`와 `works`)의 제목과 항목 글을 맞춘다. 대부분 여기서 찾으므로 OpenAlex를 검색하지 않아도 된다.
- 맞추기([match_reference](../../src/jjabtero/references.py#match_reference)):
  - 둘 다 소문자로 바꾸고 악센트를 떼고, 글자·숫자가 아닌 것은 빈칸으로 바꾼다([normalize](../../src/jjabtero/titles.py#normalize)).
  - 제목이 항목 글 안에 그대로 있으면 점수 1이다. 빈칸을 모두 뺀 제목이 빈칸을 모두 뺀 항목 글 안에 있어도 1이다. PDF의 줄바꿈 하이픈이 사라져 낱말이 붙은 경우("Open-ended" → "Openended")를 맞추기 위해서다. 이 경우 낱말 비율로는 0.8이라 기준에 못 미쳤다.
  - 아니면 제목 낱말 가운데 항목 글에 있는 낱말의 비율이 점수다. 제목 낱말이 3개([MIN_TITLE_WORDS](../../src/jjabtero/references.py#MIN_TITLE_WORDS)) 이상이고 점수가 0.85([MATCH_MIN](../../src/jjabtero/references.py#MATCH_MIN)) 이상이어야 맞은 것으로 본다. 제목이 그대로 있는 경우에도 제목 낱말이 3개 이상이어야 한다. 짧은 제목은 우연히 맞기 쉽기 때문이다.
  - 후보의 연도가 항목 글에 있으면(저자-연도 양식의 `2025b`처럼 연도 뒤에 붙은 글자는 뗀다) 0.05([YEAR_BONUS](../../src/jjabtero/references.py#YEAR_BONUS))를 더한다. 가장 높은 후보를 고른다.

**2단계: OpenAlex 검색**

- 1단계에서 못 찾으면 OpenAlex 작업을 검색해(`search`, 5건 [SEARCH_LIMIT](../../src/jjabtero/references.py#SEARCH_LIMIT)) 같은 방법으로 맞춘다. 맞는 것이 없으면 "찾지 못함"이다.
- 항목 글 전체로 검색하면 저자·학회·쪽 번호 낱말까지 모두 맞아야 해서 엉뚱한 결과가 나온다. Sennrich 외 'Neural machine translation of rare words with subword units' 항목 글 전체로는 관계없는 논문 4건이 나왔고, 제목만으로는 그 논문이 첫 번째였다(2026-11-15 확인). 그래서 항목 글에서 제목일 만한 조각을 골라([title_candidates](../../src/jjabtero/references.py#title_candidates)) 앞의 두 조각([SEARCH_TRIES](../../src/jjabtero/references.py#SEARCH_TRIES))까지 차례로 검색한다. 검색어는 [normalize](../../src/jjabtero/titles.py#normalize)한 글의 앞 250자([SEARCH_CHARS](../../src/jjabtero/references.py#SEARCH_CHARS))다.
  - 앞의 번호 표시(`[12]`, `12.`)를 떼고, 마침표 뒤 빈칸에서 조각으로 나눈다. 이름 머리글자(대문자 한 글자, 예: `J.`)와 흔한 줄임말(`vol.`, `pp.`, `Proc.`, `Conf.` 등) 뒤에서는 나누지 않는다. `et al.`은 대개 저자 목록의 끝이므로 나눈다.
  - 주소(`http`, `URL`, `doi:`)가 든 조각은 뺀다. 조각 끝의 연도(`, 2025b`)는 뗀다. 저자-연도 양식에서 제목 뒤에 연도가 붙어 검색을 방해했기 때문이다.
  - 낱말이 3개 이상인 조각만 후보다. 저자처럼 보이는 정도(대문자로 시작하는 낱말, 쉼표와 `and`의 비율, 첫 조각이면 1.5배), 게재처 낱말(proceedings, conference, journal, arxiv 등)의 비율 두 배, 숫자 낱말의 비율 두 배를 더한 값이 작은 순서다.
- 검색으로 찾은 논문의 서지 정보는 인용 캐시의 `works`에 저장한다([CitationStore.save_works](../../src/jjabtero/citations.py#CitationStore.save_works)).
- OpenAlex가 하루 사용량 초과(429)나 연결 오류를 주면 502와 까닭을 돌려준다.

**응답**

- [ReferenceMatch](../../src/jjabtero/references.py#ReferenceMatch): 상태(`found`, `not_found`), 찾은 경로(`identifier`, `references`, `search`), 논문 정보(인용 목록의 [CitedWork](../../src/jjabtero/citations.py#CitedWork)와 같은 모양: OpenAlex ID, 제목, 저자, 항목 종류, 연도, 게재처, DOI, 피인용 수, 서재에 있으면 그 논문 ID), 서재 논문에 PDF가 있는지, 공개 PDF 주소다.
- 앞의 두 후보로 못 찾으면 첫 후보의 본제목(콜론 앞, 없으면 앞 네 낱말, [short_title](../../src/jjabtero/references.py#short_title))으로 한 번 더 검색한다. 붙은 낱말이 뒤쪽에 있어 검색이 틀어진 경우("Darwin godel machine: Openended …" → "Darwin godel machine")에 결과를 얻고, 맞추기는 빈칸을 뺀 비교로 한다.
- 공개 PDF 주소는 PDF 받기와 같은 규칙이다([open_access_pdf_url](../../src/jjabtero/pdfs.py#open_access_pdf_url), [PDF 리더 설계](Reader.md#2-pdf-가져오기): arXiv DOI면 arXiv PDF, 아니면 OpenAlex의 오픈 액세스 주소). 항목 글에 arXiv 번호가 있으면 그 arXiv PDF를 쓴다. OpenAlex가 같은 논문의 다른 판 기록(다른 DOI)을 줄 수 있기 때문이다. 찾은 논문마다 OpenAlex를 한 번 더 부를 수 있다.
- 같은 논문과 같은 항목 글로 찾은 결과(찾은 논문, 경로, 공개 PDF 주소)는 서버 메모리에 1,000건([CACHE_SIZE](../../src/jjabtero/references.py#CACHE_SIZE))까지 기억한다. 서재 상태(서재 논문 ID, PDF 있음)는 바뀌므로 기억하지 않고 매번 서재에서 읽는다. 찾지 못함도 기억하지만 OpenAlex 오류는 기억하지 않는다. 같은 인용에 여러 번 마우스를 올려도 OpenAlex를 다시 부르지 않게 하기 위해서다. 브라우저도 리더를 연 동안 결과를 기억한다.
- 이 API는 서재를 바꾸지 않는다. 서재에 담는 것은 사용자가 상자에서 누를 때뿐이다([제품 비전](../ProductVision.md#6-인용-기반-연결추천)).

## 5. 상자

- 상태(1초 기다림, 열고 닫기, 찾기, 담기)는 [createReferencePreview](../../frontend/src/referencePreview.ts#createReferencePreview)가, 상자 화면은 [ReferencePreview](../../frontend/src/ReferencePreview.vue)가 맡는다. API 호출은 [resolveReference](../../frontend/src/api.ts#resolveReference)(타입 [ReferenceMatch](../../frontend/src/api.ts#ReferenceMatch))다.
- 인용 링크 위에 마우스를 **1초**([HOVER_DELAY_MS](../../frontend/src/referencePreview.ts#HOVER_DELAY_MS)) 올려 두면 상자를 띄운다. 1초 전에 벗어나면 띄우지 않는다. 지나가다 스치는 것까지 띄우면 읽기를 방해하기 때문이다.
- 상자는 인용 표시 바로 아래(아래 공간이 모자라면 위)에 띄운다. 마우스가 인용 표시에서 상자로 옮겨 가도 닫히지 않고, 둘 다에서 벗어나 0.3초([CLOSE_DELAY_MS](../../frontend/src/referencePreview.ts#CLOSE_DELAY_MS))가 지나면 닫힌다. 상자의 위치([PreviewPlace](../../frontend/src/referencePreview.ts#PreviewPlace))는 링크 왼쪽에 맞추되, 상자가 리더 오른쪽으로 넘치지 않게 한다. 링크 아래 260px 안에 공간이 없으면 위에 띄운다. `Esc`로도 닫힌다.
- 찾는 동안에는 "찾는 중…"을 보여 준다. 링크마다 찾은 결과를 리더를 연 동안 기억하고, 실패(오류)는 기억하지 않아 다시 올리면 다시 찾는다. 항목 글은 상자 아래에 작게 보여 준다.
- 찾으면 제목(DOI 또는 OpenAlex로 이어지는 링크), 저자·연도·게재처, 피인용 수, 서재 상태("서재에 있음", "PDF 있음")를 보여 주고, 아래 두 버튼을 둔다.
  - **서재에 담고 PDF 받기**: 서재에 없으면 담고([citedWorkInput](../../frontend/src/citationListState.ts#citedWorkInput)), PDF가 없으면 공개 PDF를 받는다(`POST /api/papers/{id}/pdf/fetch`). 끝나면 "서재에 담고 PDF를 받았습니다." 또는 "서재에 담았습니다. PDF는 받지 못했습니다: <까닭>"을 알리고 서재 목록을 다시 읽는다(리더의 `added` 알림을 `App.vue`가 받는다). 이미 서재에 있는 DOI면 그 논문에 PDF만 받는다. 이미 서재에 있고 PDF도 있으면 이 버튼 대신 "서재에 있음 · PDF 있음"을 보인다.
  - **새 탭에서 읽기**([readTarget](../../frontend/src/referencePreview.ts#readTarget)): 서재 논문에 PDF가 있으면 그 PDF(`/api/papers/{id}/pdf`), 없으면 공개 PDF 주소를 새 탭에서 연다. 공개 PDF도 없으면 이름을 "원문 페이지 열기"로 바꾸고 DOI(없으면 OpenAlex) 페이지를 연다.
- 못 찾으면 항목 글과 "이 참고문헌을 찾지 못했습니다"를 보여 준다.

## 6. 테스트

- [test_references](../../tests/test_references.py)는 글 다듬기, 항목 글의 DOI·arXiv 식별자, 제목 후보 고르기(번호 표시, 이름 머리글자, `et al.`, APA 형식, 끝의 연도와 주소 조각 빼기, 본제목), 붙은 낱말과 `2025b` 연도 맞추기, 식별자로 찾기(OpenAlex 조회와 arXiv PDF, 이 논문의 참고문헌에 있으면 조회 없음), 맞추기 규칙(제목 그대로, 낱말 비율, 짧은 제목 빼기, 비슷한 낱말 빼기, 연도), API(참고문헌에서 찾기와 공개 PDF 주소, arXiv DOI, 서재에 담은 뒤의 서재 논문 ID, 검색으로 찾기, 같은 글은 다시 검색하지 않기, 찾지 못함, 없는 논문, 빈 글)를 가짜 OpenAlex로 확인한다.
- [citationLinks.test](../../frontend/src/citationLinks.test.ts)는 인용 목적지 고르기, 링크 영역 비율, 목적지 좌표 읽기(`XYZ`, `FitH`, 그 밖), 항목 글 읽기(같은 단, 오른쪽 단, 아래 목적지가 없을 때, 좌표가 없을 때, 떨어진 조각 사이 빈칸, 하이픈, 600자)를 확인한다.
- [textCitations.test](../../frontend/src/textCitations.test.ts)는 줄 만들기(조각 잇기, 단 나누기), 번호 양식 항목 나누기(하이픈, 들여쓰지 않은 줄에서 끝, 학술지 머리말과 낱말 사이가 벌어진 줄과 연도로 시작하는 이어지는 줄에서는 끝나지 않음), 내어쓰기 양식(조각난 대문자 제목, 부록 제목에서 끝), 제목이 없을 때, 첫 저자 성, 같은 성·연도의 글자 고르기, 본문 표시(번호와 위치, 없는 번호, 참고문헌 영역 건너뛰기, 줄을 넘어간 여러 문헌 인용, 잰 글자 너비로 자리 잡기, 저자-연도)를 확인한다.
- [referencePreview.test](../../frontend/src/referencePreview.test.ts)는 새 탭 주소 고르기, 1초 기다림과 스치기, 링크에서 상자로 옮겨 가기와 0.3초 뒤 닫기, 같은 링크를 다시 찾지 않기, 실패 표시와 다시 시도, 서재에 담고 PDF 받기, 이미 있는 논문, PDF를 못 받았을 때의 알림을 가짜 타이머로 확인한다.

## 7. 미결정 사항

- 없음. 내어쓰기도 번호도 없는 참고문헌(항목 사이를 빈 줄로만 나누는 양식)은 지금 나누지 못한다. 쓰다가 만나면 이슈로 더한다.
