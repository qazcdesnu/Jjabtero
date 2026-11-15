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
- 쪽을 그릴 때 pdf.js의 `page.getAnnotations()`로 링크 주석을 읽고, 목적지 이름이 `cite.`로 시작하는 것을 인용 링크로 삼는다. 목적지는 `pdf.getDestination(이름)`으로 [쪽 참조, `XYZ`, 왼쪽, 위, 배율]을 얻고 `pdf.getPageIndex`로 쪽 번호를 얻는다. 저자-연도 인용(`Zhang et al., 2025b, Wang et al., 2025`)은 저자마다 링크가 따로 있으므로 각각 따로 미리 본다.
- 링크 영역은 쪽 크기에 대한 비율(0~1)로 바꿔 둔다. 하이라이트와 같은 좌표계다([PDF 리더 설계](Reader.md#4-데이터)).
- 링크 위에 요소를 겹쳐 두지 않는다. 겹치면 그 아래 글을 고를 수 없어 하이라이트가 끊기기 때문이다. 대신 리더의 마우스 이동에서 마우스 위치가 인용 링크 영역 안인지 확인한다(하이라이트를 누를 때 쓰는 `hitTest`와 같은 방식). 안이면 마우스 모양을 손가락으로 바꾼다.
- 인용 링크를 누르면(글을 고르지 않았을 때) 목적지 쪽으로 이동한다.

**링크가 없는 PDF**(M6-T4)

- 출판사 PDF 등 링크가 없으면 글자 층에서 인용 표시 모양(`[숫자]`, `[숫자, 숫자]`, `[숫자–숫자]`, `(저자 et al., 연도)` 등)을 찾고, 참고문헌 절(제목 "References", "Bibliography", "참고문헌" 뒤)에서 번호나 저자·연도가 맞는 항목을 찾는다. 자세한 규칙은 M6-T4에서 정해 이 문서에 더한다.

## 3. 참고문헌 항목 읽기

- 목적지 쪽의 글(`page.getTextContent()`)을 PDF 좌표(아래가 0인 y, 글자의 기준선)로 읽는다.
- 같은 쪽의 모든 인용 목적지를 모아 항목의 경계를 정한다. 참고문헌 목록에서 각 항목의 머리가 곧 다른 인용의 목적지이기 때문이다.
  - 단(column): 이 목적지보다 왼쪽 좌표가 50pt 넘게 큰 목적지가 있으면 그 왼쪽 좌표를 이 단의 오른쪽 끝으로 본다. 없으면 쪽의 오른쪽 끝이다.
  - 아래 끝: 같은 단(왼쪽 좌표 차이 50pt 이하)에서 이 목적지 바로 아래 목적지의 위 좌표다. 없으면 위 좌표에서 80pt(약 6줄) 아래까지다.
  - 글 조각 가운데 왼쪽 좌표가 단 안에 있고 기준선이 위 좌표 + 2pt 이하이며 아래 끝 + 2pt보다 위인 것을 위에서 아래, 왼쪽에서 오른쪽 순서로 잇는다. 줄 끝 하이픈으로 끊긴 낱말은 붙이고, 빈칸은 하나로 줄이며, 600자에서 자른다.
- 목적지가 `XYZ`가 아니어서 왼쪽 좌표가 없으면 단을 쪽 전체로 본다.
- 이 계산은 순수 함수(예정 이름 `referenceEntryText`, 모듈 `frontend/src/citationLinks.ts`)로 두어 Vitest로 확인한다.

## 4. 논문 찾기

`POST /api/papers/{id}/references/resolve`(본문 [ResolveIn](../../src/jjabtero/references.py#ResolveIn) `{"text": 항목 글}`, 2,000자까지)를 [resolve_reference](../../src/jjabtero/references.py#resolve_reference)가 처리한다([router](../../src/jjabtero/references.py#router)). 찾는 일은 [_find](../../src/jjabtero/references.py#_find)가 한다. 로그인이 켜져 있으면 로그인해야 쓴다.

**1단계: 이 논문의 참고문헌과 맞추기**

- 리더로 읽는 논문이 OpenAlex에 연결되어 인용 데이터가 있으면, 그 참고문헌 목록([인용 데이터 설계](Citations.md#4-저장)의 `references`와 `works`)의 제목과 항목 글을 맞춘다. 대부분 여기서 찾으므로 OpenAlex를 검색하지 않아도 된다.
- 맞추기([match_reference](../../src/jjabtero/references.py#match_reference)):
  - 둘 다 소문자로 바꾸고 악센트를 떼고, 글자·숫자가 아닌 것은 빈칸으로 바꾼다([normalize](../../src/jjabtero/references.py#normalize)).
  - 제목이 항목 글 안에 그대로 있으면 점수 1이다.
  - 아니면 제목 낱말 가운데 항목 글에 있는 낱말의 비율이 점수다. 제목 낱말이 3개([MIN_TITLE_WORDS](../../src/jjabtero/references.py#MIN_TITLE_WORDS)) 이상이고 점수가 0.85([MATCH_MIN](../../src/jjabtero/references.py#MATCH_MIN)) 이상이어야 맞은 것으로 본다. 제목이 그대로 있는 경우에도 제목 낱말이 3개 이상이어야 한다. 짧은 제목은 우연히 맞기 쉽기 때문이다.
  - 후보의 연도가 항목 글에 있으면 0.05([YEAR_BONUS](../../src/jjabtero/references.py#YEAR_BONUS))를 더한다. 가장 높은 후보를 고른다.

**2단계: OpenAlex 검색**

- 1단계에서 못 찾으면 OpenAlex 작업을 검색해(`search`, 5건 [SEARCH_LIMIT](../../src/jjabtero/references.py#SEARCH_LIMIT)) 같은 방법으로 맞춘다. 맞는 것이 없으면 "찾지 못함"이다.
- 항목 글 전체로 검색하면 저자·학회·쪽 번호 낱말까지 모두 맞아야 해서 엉뚱한 결과가 나온다. Sennrich 외 'Neural machine translation of rare words with subword units' 항목 글 전체로는 관계없는 논문 4건이 나왔고, 제목만으로는 그 논문이 첫 번째였다(2026-11-15 확인). 그래서 항목 글에서 제목일 만한 조각을 골라([title_candidates](../../src/jjabtero/references.py#title_candidates)) 앞의 두 조각([SEARCH_TRIES](../../src/jjabtero/references.py#SEARCH_TRIES))까지 차례로 검색한다. 검색어는 [normalize](../../src/jjabtero/references.py#normalize)한 글의 앞 250자([SEARCH_CHARS](../../src/jjabtero/references.py#SEARCH_CHARS))다.
  - 앞의 번호 표시(`[12]`, `12.`)를 떼고, 마침표 뒤 빈칸에서 조각으로 나눈다. 이름 머리글자(대문자 한 글자, 예: `J.`)와 흔한 줄임말(`vol.`, `pp.`, `Proc.`, `Conf.` 등) 뒤에서는 나누지 않는다. `et al.`은 대개 저자 목록의 끝이므로 나눈다.
  - 낱말이 3개 이상인 조각만 후보다. 저자처럼 보이는 정도(대문자로 시작하는 낱말, 쉼표와 `and`의 비율, 첫 조각이면 1.5배), 게재처 낱말(proceedings, conference, journal, arxiv 등)의 비율 두 배, 숫자 낱말의 비율 두 배를 더한 값이 작은 순서다.
- 검색으로 찾은 논문의 서지 정보는 인용 캐시의 `works`에 저장한다([CitationStore.save_works](../../src/jjabtero/citations.py#CitationStore.save_works)).
- OpenAlex가 하루 사용량 초과(429)나 연결 오류를 주면 502와 까닭을 돌려준다.

**응답**

- [ReferenceMatch](../../src/jjabtero/references.py#ReferenceMatch): 상태(`found`, `not_found`), 찾은 경로(`references`, `search`), 논문 정보(인용 목록의 [CitedWork](../../src/jjabtero/citations.py#CitedWork)와 같은 모양: OpenAlex ID, 제목, 저자, 항목 종류, 연도, 게재처, DOI, 피인용 수, 서재에 있으면 그 논문 ID), 서재 논문에 PDF가 있는지, 공개 PDF 주소다.
- 공개 PDF 주소는 PDF 받기와 같은 규칙이다([open_access_pdf_url](../../src/jjabtero/pdfs.py#open_access_pdf_url), [PDF 리더 설계](Reader.md#2-pdf-가져오기): OpenAlex의 오픈 액세스 주소, 없으면 arXiv DOI). 찾은 논문마다 OpenAlex를 한 번 더 부른다.
- 같은 논문과 같은 항목 글로 찾은 결과(찾은 논문, 경로, 공개 PDF 주소)는 서버 메모리에 1,000건([CACHE_SIZE](../../src/jjabtero/references.py#CACHE_SIZE))까지 기억한다. 서재 상태(서재 논문 ID, PDF 있음)는 바뀌므로 기억하지 않고 매번 서재에서 읽는다. 찾지 못함도 기억하지만 OpenAlex 오류는 기억하지 않는다. 같은 인용에 여러 번 마우스를 올려도 OpenAlex를 다시 부르지 않게 하기 위해서다. 브라우저도 리더를 연 동안 결과를 기억한다.
- 이 API는 서재를 바꾸지 않는다. 서재에 담는 것은 사용자가 상자에서 누를 때뿐이다([제품 비전](../ProductVision.md#6-인용-기반-연결추천)).

## 5. 상자

- 인용 링크 위에 마우스를 **1초** 올려 두면 상자를 띄운다. 1초 전에 벗어나면 띄우지 않는다. 지나가다 스치는 것까지 띄우면 읽기를 방해하기 때문이다.
- 상자는 인용 표시 바로 아래(아래 공간이 모자라면 위)에 띄운다. 마우스가 인용 표시에서 상자로 옮겨 가도 닫히지 않고, 둘 다에서 벗어나 0.3초가 지나면 닫힌다. `Esc`로도 닫힌다.
- 찾는 동안에는 항목 글과 "찾는 중…"을 보여 준다.
- 찾으면 제목(DOI 또는 OpenAlex로 이어지는 링크), 저자·연도·게재처, 피인용 수, 서재 상태("서재에 있음", "PDF 있음")를 보여 주고, 아래 두 버튼을 둔다.
  - **서재에 담고 PDF 받기**: 서재에 없으면 담고([citedWorkInput](../../frontend/src/citationListState.ts#citedWorkInput)), PDF가 없으면 공개 PDF를 받는다(`POST /api/papers/{id}/pdf/fetch`). 끝나면 "서재에 담고 PDF를 받았습니다" 또는 "공개 PDF가 없어 서재에만 담았습니다"를 알리고 서재 목록을 다시 읽는다. 이미 서재에 있고 PDF도 있으면 이 버튼 대신 "서재에 있음 · PDF 있음"을 보인다.
  - **새 탭에서 읽기**: 서재 논문에 PDF가 있으면 그 PDF(`/api/papers/{id}/pdf`), 없으면 공개 PDF 주소를 새 탭에서 연다. 공개 PDF도 없으면 이름을 "원문 페이지 열기"로 바꾸고 DOI(없으면 OpenAlex) 페이지를 연다.
- 못 찾으면 항목 글과 "이 참고문헌을 찾지 못했습니다"를 보여 준다.

## 6. 미결정 사항

- 링크가 없는 PDF의 인용 표시 모양과 참고문헌 절 찾기 규칙(M6-T4에서 정한다).

## 7. 테스트

- [test_references](../../tests/test_references.py)는 글 다듬기, 제목 후보 고르기(번호 표시, 이름 머리글자, `et al.`, APA 형식), 맞추기 규칙(제목 그대로, 낱말 비율, 짧은 제목 빼기, 비슷한 낱말 빼기, 연도), API(참고문헌에서 찾기와 공개 PDF 주소, arXiv DOI, 서재에 담은 뒤의 서재 논문 ID, 검색으로 찾기, 같은 글은 다시 검색하지 않기, 찾지 못함, 없는 논문, 빈 글)를 가짜 OpenAlex로 확인한다.
