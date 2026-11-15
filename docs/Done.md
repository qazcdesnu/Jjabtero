# 완료

이 문서는 끝난 작업의 상세 기록이다. 최신 기록이 맨 위에 온다. 기록 형식은 [작업 관리 규칙](TaskRule.md#5-기록-형식)을 따르며, 할 일 목록은 [로드맵](Roadmap.md)과 [이슈](Issue.md)에 있다. 닫힌 마일스톤의 기록은 [작업 관리 규칙](TaskRule.md#47-완료-기록-보관)에 따라 보관 문서로 옮긴다. 보관 문서: [M0 시작](Done-M0.md), [M1 기본 서재](Done-M1.md), [M2 Render 배포](Done-M2.md), [M4 PDF 리더](Done-M4.md), [M3 인용 기반 연결·추천](Done-M3.md). 전체 문서 목록은 [문서 인덱스](index.md)에서 확인한다.

## I17 논문 인용 양식(CS에서 자주 쓰는 5~10가지)을 골라 복사하기

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [인용 양식 설계](design/CitationStyles.md)
- 참고 자료: 없음

### 계획
- CS에서 자주 쓰는 인용 양식 8가지(BibTeX, IEEE, ACM, APA, MLA, Chicago, Harvard, Vancouver)의 규칙을 설계 문서에 적는다.
- 서재 논문 정보로 양식별 글(일반 글과 기울임이 있는 HTML)을 만드는 순수 함수를 만든다.
- 논문 상세에 "인용" 버튼과 양식 목록 창(양식마다 미리보기와 복사)을 둔다.
- 테스트를 더하고 브라우저에서 확인한다.

### 진행 기록
- 2026-11-15: M6-T3 작업 중에 사용자가 요청했다(구글 스칼라처럼 5~10개). I16 다음에 하기로 하고, 병합되지 않은 가장 최근 브랜치 `i16-library-links`에서 작업 브랜치를 만들었다.
- 2026-11-15: `citationStyles` 모듈(이름 나누기, 여덟 양식, BibTeX, 복사)과 인용 창(`CiteDialog.vue`)을 만들고 논문 상세에 "인용" 버튼을 두었다. primeicons에 따옴표 아이콘이 없어 복사 아이콘을 썼다.
- 2026-11-15: 세 논문('Attention Is All You Need' 8저자 학회, LSTM 2저자 저널, BERT arXiv)으로 여덟 양식 글을 뽑아 보았다. Chicago는 저자가 둘일 때 `, and`가 빠져 고쳤다.
- 2026-11-15: 시연 서버에서 브라우저로 확인했다. 창에 여덟 양식이 나왔고, APA 복사는 글과 기울임 HTML이 함께, BibTeX 복사는 글만 들어갔으며 버튼이 "복사됨"으로 바뀌었다. OpenAlex로 담은 Bahdanau 논문의 게재처가 "arXiv (Cornell University)"로 그대로 인용에 들어가, arXiv 저장소 이름은 게재처로 쓰지 않고 `arXiv preprint arXiv:<ID>`를 쓰게 고쳤다.

### 결정 사항
- 양식은 CS에서 많이 쓰는 BibTeX, IEEE, ACM과 구글 스칼라의 APA, MLA, Chicago, Harvard, Vancouver 여덟 가지다.
- 인용 양식 라이브러리를 쓰지 않고 직접 만든다. 규칙이 짧고, 라이브러리는 첫 화면 번들을 크게 키우기 때문이다([인용 양식 설계](design/CitationStyles.md#1-범위)).
- 제목 대소문자는 바꾸지 않는다. 고유 이름을 기계로 가려낼 수 없기 때문이다.
- 글과 HTML을 함께 복사해 붙여 넣는 곳에 기울임이 남게 한다. BibTeX는 글로만 복사한다.

### 변경 파일
- `docs/Issue.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/index.md`
- `docs/design/CitationStyles.md`
- `frontend/src/citationStyles.ts`
- `frontend/src/citationStyles.test.ts`
- `frontend/src/CiteDialog.vue`
- `frontend/src/PaperDetail.vue`

### 결과
- 논문 상세의 "인용" 버튼으로 여덟 양식(BibTeX, IEEE, ACM, APA, MLA, Chicago, Harvard, Vancouver)의 인용 글을 보고 골라 복사한다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 시연 서버에서 인용 창, APA·BibTeX 복사와 클립보드 내용을 브라우저로 확인했다. 브라우저 콘솔 오류는 없었다.

## I16 서재에 논문을 담으면 서재의 다른 논문들과의 인용·피인용 관계를 확인해 그래프에 정확히 보여 주기

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [인용 데이터 설계](design/Citations.md#9-semantic-scholar-참고문헌)
- 참고 자료: 없음

### 계획
- 서재 그래프에서 인용 선이 빠지는 경우를 실제 데이터로 찾는다.
- 원인에 맞게 서재 논문 사이 인용을 확인하는 방법을 정하고 만든다.
- 테스트를 더하고 시연 서재로 확인한다.

### 진행 기록
- 2026-11-15: M6-T3 작업 중에 사용자가 요청했다. 병합되지 않은 가장 최근 브랜치 `m6-t3-citation-preview`에서 작업 브랜치를 만들었다. 같은 때 받은 인용 양식 복사 요청은 I17로 등록했다.
- 2026-11-15: 시연 서재에 BERT, RoBERTa, GPT-3을 더해 그래프를 보았다. 서로의 인용은 잡혔지만 'Attention Is All You Need'가 실제로 인용하는 Bahdanau, GRU 논문으로 가는 인용 선이 없었다. OpenAlex에 있는 이 논문의 참고문헌은 35개(실제 40개)였고 LSTM, Bahdanau, GRU, Dropout이 빠져 있었다. 서재 논문의 참고문헌을 모두 보는 지금 계산은 맞았고, 데이터가 빠진 것이 원인이었다.
- 2026-11-15: 다른 출처를 비교했다. Semantic Scholar는 41개를 모두 주었고, Crossref는 arXiv 논문을 몰랐다. 사용자에게 물어 Semantic Scholar를 함께 쓰기로 했다.
- 2026-11-15: `semantic_scholar` 모듈(받기, 저장, 맞추기)을 만들고 인용 데이터 갱신과 그래프에 붙였다. `citations`와 `references`가 서로 불러오지 않게 제목 다듬기 함수를 `titles` 모듈로 옮겼다.
- 2026-11-15: 시연 서재에서 확인했다. 'Attention Is All You Need' → Bahdanau, → GRU 인용 선이 생겼다. SE Networks의 CVPR DOI는 Semantic Scholar에 없어 7편 가운데 6편만 확인되었다. 제목 맞추기로 찾는 단계를 더하자 84개를 받아 7편 모두 확인되었다. 손으로 보낸 요청에 429(공용 한도)를 한 번 받았다.
- 2026-11-15: Semantic Scholar 키를 넣는 일을 선택 사항인 사용자 할 일 I18로 등록했다.

### 결정 사항
- 서재 논문마다 Semantic Scholar 참고문헌을 받아 두고, 그래프를 그릴 때 서재 논문끼리 맞춘다. 새 논문을 담을 때 그 논문 하나만 받으면 양쪽 방향이 모두 확인되기 때문이다.
- 맞추기는 DOI, arXiv ID, 다듬은 제목(3낱말 이상) 가운데 하나라도 같으면 같은 논문으로 본다. 같은 논문이 arXiv판과 학회판으로 DOI가 다른 경우가 많기 때문이다.
- 키 없이 쓰되 요청 사이를 1.1초 띄우고 429에서 멈춘다. 키가 있으면 쓴다. 키를 받는 일은 사용자가 할 수 있는 선택 사항으로 남긴다.
- 표는 기존 인용 캐시 파일에 더하고 캐시 버전은 올리지 않는다. 버전을 올리면 OpenAlex 인용 데이터를 모두 다시 받아야 하기 때문이다.

### 변경 파일
- `docs/Issue.md`
- `docs/Done.md`
- `docs/ProductVision.md`
- `docs/Architecture.md`
- `docs/design/Citations.md`
- `docs/design/CitationGraph.md`
- `docs/design/ReaderCitations.md`
- `src/jjabtero/semantic_scholar.py`
- `src/jjabtero/titles.py`
- `src/jjabtero/references.py`
- `src/jjabtero/citations.py`
- `src/jjabtero/citation_graph.py`
- `tests/test_semantic_scholar.py`
- `tests/test_citations.py`
- `tests/test_references.py`
- `tests/conftest.py`
- `frontend/src/api.ts`
- `frontend/src/api.test.ts`
- `frontend/src/CitationStatusPanel.vue`

### 결과
- 서재에 논문을 담으면 Semantic Scholar 참고문헌으로 서재의 다른 논문들과의 인용·피인용을 확인해 그래프에 인용 선을 긋는다. OpenAlex 참고문헌에 빠진 인용도 보인다. 설정 페이지에서 Semantic Scholar로 확인한 논문 수를 본다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 시연 서재(7편, 실제 OpenAlex·Semantic Scholar)에서 7편 모두 확인되고, OpenAlex에 빠졌던 'Attention Is All You Need' → Bahdanau, → GRU 인용 선이 그래프 API에 나오는 것을 확인했다.

## M6-T3 리더의 인용 링크 미리보기 상자와 서재에 담기·PDF 받기·새 탭에서 읽기

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [리더 인용 미리보기 설계](design/ReaderCitations.md)
- 참고 자료: 없음

### 계획
- 인용 링크 영역과 참고문헌 항목 글을 계산하는 순수 함수를 만든다.
- 마우스 1초 대기, 상자 열고 닫기, 논문 찾기, 서재에 담고 PDF 받기, 새 탭 주소를 다루는 상태 모듈을 만든다.
- 리더에 인용 링크 찾기, 마우스 위치 확인, 링크 누르면 이동, 상자를 붙인다.
- 테스트를 더하고 실제 PDF로 브라우저에서 확인한다.

### 진행 기록
- 2026-11-15: 병합되지 않은 가장 최근 브랜치 `m6-t2-reference-resolve`에서 작업 브랜치를 만들었다.
- 2026-11-15: 데모 PDF에서 목적지 좌표와 글 기준선을 비교했다. `cite.hochreiter1997`의 위 좌표는 453.4이고 항목 첫 줄 기준선은 442.5, 앞 항목의 마지막 줄은 462.3이었다. 설계한 경계(위 좌표 + 2pt 이하)로 앞 항목이 섞이지 않는다.
- 2026-11-15: 순수 함수 모듈(`citationLinks`), 상자 상태 모듈(`referencePreview`), 상자 화면(`ReferencePreview.vue`)을 만들고 리더에 붙였다. pdf.js 6의 `PageViewport`에는 사각형 변환이 없어 두 꼭짓점을 따로 바꿨다.
- 2026-11-15: 시연 서버('Attention Is All You Need', 실제 OpenAlex)에서 브라우저로 확인했다. 0.5초 스치기에는 상자가 뜨지 않았고, 1초 머물면 Hochreiter 인용의 LSTM 논문이 떴다. 상자로 옮겨 가도 열려 있었고, 벗어나자 닫혔다. 링크를 누르자 참고문헌이 있는 11쪽으로 갔다.
- 2026-11-15: Bahdanau 인용은 처음에 찾지 못했다. 같은 줄의 글 조각을 빈칸 없이 이어 `translate.CoRR`처럼 붙는 바람에 제목 후보가 학회 이름과 한 덩어리가 되어 검색이 틀렸다. 조각 너비로 간격을 계산해 빈칸을 넣자 찾았고, "서재에 담고 PDF 받기"로 담고 arXiv PDF를 받았다.
- 2026-11-15: 오른쪽 끝 링크에서 상자가 리더 가장자리에 붙어 넘칠 수 있어 위치를 제한했다. GRU 인용은 앞 실행에서 담겨 "서재에 있음 · PDF 있음"과 서재 PDF로 여는 "새 탭에서 읽기"만 보였다. 한 번은 OpenAlex가 502를 돌려 상자에 오류가 보였고, 다시 올리자 찾았다.
- 2026-11-15: 사용자가 작업 중에 새 요청을 했다. 서재에 논문을 담으면 서재의 다른 논문들과의 인용·피인용 관계를 확인해 그래프를 정확히 보여 달라는 것이다. 이슈 I16으로 등록했고, 이 작업을 마친 뒤 이어서 한다. 사용자는 이 작업을 다시 이어 하라고 했다.

### 결정 사항
- 리더 위에 투명 요소를 겹치지 않고 마우스 이동에서 링크 영역을 확인한다(설계대로). 하이라이트용 글 고르기를 막지 않기 위해서다.
- 같은 줄 글 조각 사이 간격이 0.5pt를 넘으면 빈칸을 넣는다. 낱말 안에서 글꼴이 바뀌어 조각이 나뉘는 경우는 드물고, 빈칸이 빠지는 쪽이 검색을 더 크게 망치기 때문이다.

### 변경 파일
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/Issue.md`
- `docs/design/ReaderCitations.md`
- `frontend/src/citationLinks.ts`
- `frontend/src/citationLinks.test.ts`
- `frontend/src/referencePreview.ts`
- `frontend/src/referencePreview.test.ts`
- `frontend/src/ReferencePreview.vue`
- `frontend/src/ReaderView.vue`
- `frontend/src/App.vue`
- `frontend/src/api.ts`

### 결과
- 리더에서 인용 표시(링크가 있는 PDF)에 마우스를 1초 올리면 그 논문이 상자로 뜬다. 상자에서 서재에 담고 PDF를 받거나, 새 탭에서 PDF(없으면 원문 페이지)를 연다. 인용 표시를 누르면 참고문헌 쪽으로 간다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 시연 서버에서 스치기, 1초 머물기, 상자로 옮겨 가기, 닫기, 서재에 담고 PDF 받기, 서재에 있는 논문, 링크 눌러 이동을 브라우저로 확인했다. 브라우저 콘솔 오류는 없었다.

## M6-T2 참고문헌 항목 글로 논문을 찾는 API

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [리더 인용 미리보기 설계](design/ReaderCitations.md#4-논문-찾기)
- 참고 자료: 없음

### 계획
- 항목 글과 후보 논문 제목을 맞추는 함수를 만든다.
- 이 논문의 OpenAlex 참고문헌과 먼저 맞추고, 없으면 OpenAlex를 검색하는 API를 만든다. 찾은 논문의 서재 상태와 공개 PDF 주소를 함께 준다.
- 공개 PDF 주소를 찾는 코드를 PDF 받기와 함께 쓰도록 나눈다.
- 테스트를 더하고 실제 PDF의 참고문헌 항목으로 확인한다.

### 진행 기록
- 2026-11-15: 병합되지 않은 가장 최근 브랜치 `m6-t1-reader-citations-design`에서 작업 브랜치를 만들었다.
- 2026-11-15: `references` 모듈(맞추기, API, 결과 기억)을 만들고, 공개 PDF 주소 찾기를 `open_access_pdf_url`로 나눴다.
- 2026-11-15: 시연 서버에서 SE Networks 논문으로 실제 OpenAlex를 불러 확인했다. LSTM과 ResNet 항목은 참고문헌에서 찾았다. 참고문헌에 없는 Sennrich 항목은 항목 글 전체로 검색하자 관계없는 결과만 나와 찾지 못했다. OpenAlex 검색은 낱말을 모두 맞추려 해서 저자·학회 낱말이 방해가 됐다. 제목일 만한 조각을 골라 검색하도록 바꾸자 Sennrich와 Adam 항목을 찾았다. 꾸며 낸 항목은 찾지 못함이었다.
- 2026-11-15: OpenAlex가 Adam 논문의 공개 주소를 arXiv 소개 페이지(`arxiv.org/abs/...`)로 주었다. 이 주소로는 PDF 받기도 실패하므로 PDF 주소로 바꾸게 했다.
- 2026-11-15: 확인하던 중 `curl` 오류 메시지에 `.env`의 OpenAlex 키가 이 세션의 명령 출력에 한 번 찍혔다. 저장소나 외부로 나가지는 않았다. 이후에는 키를 출력하지 않는 방법으로만 확인했고, 사용자에게 알렸다.

### 결정 사항
- 결과 기억은 서버 메모리에 둔다. 인용 캐시 파일에 표를 더하면 캐시 버전을 올려 모든 인용 데이터를 다시 받아야 하기 때문이다. 서버가 다시 시작하면 사라져도 다시 찾으면 된다.
- 서재 상태는 기억하지 않고 매번 읽는다. 상자에서 서재에 담은 뒤 다시 마우스를 올리면 "서재에 있음"이 보여야 하기 때문이다.
- 검색은 제목 후보 두 개까지만 한다. 마우스를 올릴 때마다 OpenAlex를 여러 번 부르지 않게 하기 위해서다.

### 변경 파일
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/design/ReaderCitations.md`
- `docs/design/Reader.md`
- `src/jjabtero/references.py`
- `src/jjabtero/pdfs.py`
- `src/jjabtero/citations.py`
- `src/jjabtero/app.py`
- `tests/test_references.py`
- `tests/test_pdfs.py`

### 결과
- `POST /api/papers/{id}/references/resolve`에 참고문헌 항목 글을 보내면 그 논문(서지 정보, 서재 상태, 공개 PDF 주소)을 돌려준다. 이 논문의 참고문헌에서 먼저 찾고, 없으면 제목일 만한 조각으로 OpenAlex를 검색한다.
- PDF 받기에서 OpenAlex가 arXiv 소개 페이지를 주는 경우에도 PDF를 받는다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- 시연 서버와 실제 OpenAlex로 참고문헌에서 찾기(LSTM, ResNet), 검색으로 찾기(Sennrich, Adam), 찾지 못함(꾸며 낸 항목)을 확인했다.

## M6-T1 인용 미리보기 설계(인용 표시 찾기, 참고문헌 항목 읽기, 논문 찾기, 상자와 동작)

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [리더 인용 미리보기 설계](design/ReaderCitations.md)
- 참고 자료: 없음

### 계획
- 데모 PDF와 arXiv PDF로 인용 링크가 어떻게 들어 있는지 조사한다.
- 인용 표시를 찾는 방법, 참고문헌 항목 글을 읽는 방법, 그 글로 논문을 찾는 방법, 미리보기 상자의 동작을 설계 문서에 적는다.
- 제품 비전의 PDF 리더 절과 로드맵에 M6을 더한다.

### 진행 기록
- 2026-11-15: 사용자가 리더에서 인용 표시에 마우스를 1초 올리면 그 논문을 상자로 보여 주고, 내려받기와 새 탭에서 읽기를 하게 해 달라고 했다. "내려받기"는 서재에 담고 PDF 받기로, 시기는 지금 바로(M5보다 먼저)로 사용자가 골랐다. 새 마일스톤 M6으로 로드맵에 더했다. 병합되지 않은 가장 최근 브랜치 `h1-stale-chunk`에서 작업 브랜치를 만들었다.
- 2026-11-15: pdf.js로 링크 주석을 세었다. 'Attention Is All You Need'(arXiv)는 링크 113개 가운데 76개가 `cite.` 이름의 목적지(예: `cite.hochreiter1997`)였고, 목적지는 참고문헌 쪽의 좌표(`XYZ`, 왼쪽 108, 위 453.4)였다. SE Networks(206개), BERT(290개)의 arXiv PDF도 링크가 있었다.
- 2026-11-15: 리더 인용 미리보기 설계 문서를 쓰고 문서 인덱스, 제품 비전, 로드맵에 더했다.

### 결정 사항
- 인용 표시와 참고문헌 항목 글은 브라우저(pdf.js)가 찾고, 항목 글로 논문을 찾는 일은 서버가 한다. pdf.js가 이미 쪽의 글과 좌표를 가지고 있고, 서버는 인용 데이터와 OpenAlex 키를 가지고 있기 때문이다.
- 논문은 먼저 이 논문의 OpenAlex 참고문헌 목록과 제목으로 맞추고, 못 찾을 때만 OpenAlex를 검색한다. 대부분 OpenAlex 호출 없이 찾고, 엉뚱한 논문을 고를 위험이 적기 때문이다.
- 인용 링크 위에 요소를 겹치지 않고 마우스 위치로 영역을 확인한다. 겹치면 그 아래 글을 고를 수 없어 하이라이트가 끊기기 때문이다.
- 링크가 있는 PDF(arXiv 대부분)를 먼저 하고(M6-T3), 링크가 없는 PDF는 따로 한다(M6-T4). 링크는 정확한 목적지를 주지만 글자 모양 찾기는 추측이라 규칙을 따로 다듬어야 하기 때문이다.

### 변경 파일
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/ProductVision.md`
- `docs/index.md`
- `docs/design/ReaderCitations.md`

### 결과
- 리더 인용 미리보기의 흐름(인용 표시 찾기 → 참고문헌 항목 읽기 → 논문 찾기 → 상자)과 각 단계의 규칙, API, 상자의 동작이 정해졌다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.

## H1 배포 뒤 열어 둔 탭에서 리더·그래프 화면이 빈 칸으로 나옴(옛 화면 파일을 못 불러옴)

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [UI 기반 설계](design/UiLayout.md#3-화면-배치)
- 참고 자료: 없음

### 계획
- 원인을 재현해 확인한다.
- 나중에 불러오는 화면(리더, 그래프)을 불러오지 못하면 한 번 자동으로 새로고침하고, 그래도 안 되면 빈 칸 대신 안내와 "새로고침" 버튼을 보여 준다.
- 설계 문서와 테스트를 더하고, 실패를 흉내 낸 브라우저에서 확인한다.

### 진행 기록
- 2026-11-15: 사용자가 배포된 앱에서 "읽기"를 누르면 가운데 칸이 비어 있다고 알렸다. #30~#42가 모두 병합되어 배포된 상태였다.
- 2026-11-15: 배포된 파일은 로컬 빌드와 해시까지 같았고, PDF 작업자 파일도 `text/javascript`로 내려왔다. 로컬에서는 Chrome 157과 WebKit 27.2 모두 리더가 열렸다. PDF를 열지 못하면 리더가 오류 문구를 보이므로, 빈 칸은 리더 화면 파일 자체를 불러오지 못한 경우다. 배포마다 첫 화면 파일 해시가 바뀌면 그것을 불러오는 리더 파일 이름도 바뀌고, 서버는 없는 파일에 404를 준다. 배포 전에 연 탭은 옛 이름을 청하다 실패하고, `defineAsyncComponent`는 실패하면 아무것도 그리지 않는다. 이것을 가장 유력한 원인으로 보았다.
- 2026-11-15: 사용자에게 우선 새로고침해 보라고 안내했다.
- 2026-11-15: 나중에 불러오는 화면을 `lazyView`로 감쌌다. 불러오기에 실패하면 한 번 새로고침하고, 그래도 안 되면 안내 화면을 보여 준다. 서버는 `assets/` 파일에 오래 캐시하라는 지시를, `index.html`에 매번 확인하라는 지시를 붙인다.
- 2026-11-15: 브라우저에서 리더 화면 파일 요청을 404로 바꿔 옛 탭을 흉내 냈다. 첫 실패에 페이지가 한 번 새로고침되었고, 1분 안의 두 번째 실패에는 안내 화면이 나왔으며, 요청을 되돌리고 "새로고침"을 누르자 리더가 열렸다. 캐시 지시가 붙는 것도 응답 머리글로 확인했다.

### 결정 사항
- 실패하면 자동으로 한 번 새로고침한다. 배포 뒤 옛 탭에서는 새로고침만으로 풀리고, 사용자가 원인을 몰라도 되기 때문이다. 되풀이를 막으려고 1분 안에는 다시 하지 않는다.
- 자동 새로고침 뒤에는 처음 화면(논문 검색)으로 돌아간다. 화면 상태를 주소에 담는 일은 이번 결함의 범위 밖이라 하지 않는다.

### 변경 파일
- `docs/Issue.md`
- `docs/Ongoing.md`
- `docs/Done.md`
- `docs/design/UiLayout.md`
- `docs/design/AppSkeleton.md`
- `docs/design/Reader.md`
- `docs/design/CitationGraph.md`
- `frontend/src/lazyView.ts`
- `frontend/src/lazyView.test.ts`
- `frontend/src/LoadFailedView.vue`
- `frontend/src/App.vue`
- `src/jjabtero/app.py`
- `tests/test_app.py`

### 결과
- 배포 전에 열어 둔 탭에서 리더나 그래프를 열어도 빈 칸이 나오지 않는다. 한 번 자동으로 새로고침되고, 그래도 안 되면 까닭과 "새로고침" 버튼이 보인다.
- 새로 배포한 뒤 새로고침하면 브라우저가 항상 새 `index.html`을 받는다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- `npx vue-tsc --noEmit -p tsconfig.app.json`, `npm run build`: 통과.
- 시연 서버에서 화면 파일 404를 흉내 내어 자동 새로고침, 안내 화면, 새로고침 뒤 리더 열림을 브라우저로 확인했다.
