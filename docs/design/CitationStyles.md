# 인용 양식 설계

이 문서는 서재 논문의 인용 글을 여러 양식으로 만들어 복사하는 기능을 정한다. 사용자가 구글 스칼라의 "인용"처럼 CS에서 자주 쓰는 양식 5~10가지를 골라 복사하게 해 달라고 했다([이슈 I17](../Issue.md)). 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 범위

- 서재 논문의 정보(제목, 저자, 항목 종류, 연도, 게재처, DOI, 원문 주소, [CitableWork](../../frontend/src/citationStyles.ts#CitableWork))만으로 만든다. 권·호·쪽은 서재에 없으므로 넣지 않는다. 구글 스칼라의 인용 글도 이 정도다.
- 인용 양식 라이브러리(citation-js 등)를 들이지 않고 직접 만든다. 여덟 양식은 규칙이 짧고, 라이브러리는 CSL 양식 파일과 함께 수백 KB라 첫 화면 번들([이슈 I11](../Issue.md))을 키우기 때문이다.
- 브라우저에서만 만든다. 서버 API는 없다.

## 2. 양식

[CITATION_STYLES](../../frontend/src/citationStyles.ts#CITATION_STYLES)가 아래 순서로 여덟 양식을 가진다. CS 논문에서 많이 쓰는 BibTeX, IEEE, ACM을 앞에 두고, 구글 스칼라가 주는 다섯 양식(APA, MLA, Chicago, Harvard, Vancouver)을 뒤에 둔다. 양식마다 일반 글과 기울임(`<i>`)이 있는 HTML을 함께 만든다([FormattedCitation](../../frontend/src/citationStyles.ts#FormattedCitation)).

| 양식 | 함수 | 저자 | 모양(예: 학회 논문) |
| --- | --- | --- | --- |
| BibTeX | [bibtex](../../frontend/src/citationStyles.ts#bibtex) | 모두, `성, 이름 and …` | [4절](#4-bibtex) |
| IEEE | [ieee](../../frontend/src/citationStyles.ts#ieee) | 여섯까지 `A. Vaswani, …, and I. Polosukhin`, 일곱 이상이면 `A. Vaswani et al.`(기울임) | `저자, "제목," in 게재처, 연도.` 저널은 `in` 없이 `, doi: …`, 게재처 없는 arXiv는 `arXiv:<ID>, 연도.` |
| ACM | [acm](../../frontend/src/citationStyles.ts#acm) | 모두, 이름 성 | `저자. 연도. 제목. In 게재처. DOI 주소` (저널은 `In` 없음) |
| APA 7 | [apa](../../frontend/src/citationStyles.ts#apa) | 스물까지 `성, 머리글자`와 `&`, 넘으면 열아홉 … 마지막 | `저자 (연도). 제목. 게재처. DOI 주소` 연도가 없으면 `(n.d.)` |
| MLA 9 | [mla](../../frontend/src/citationStyles.ts#mla) | 하나 `성, 이름`, 둘 `성, 이름, and 이름 성`, 셋 이상 `성, 이름, et al.` | `저자. "제목." 게재처, 연도, DOI 주소.` |
| Chicago | [chicago](../../frontend/src/citationStyles.ts#chicago) | 열까지 모두(첫 저자만 뒤집음, 둘이어도 `, and`), 넘으면 일곱과 `et al.` | `저자. "제목." 게재처 (연도). DOI 주소` |
| Harvard | [harvard](../../frontend/src/citationStyles.ts#harvard) | 셋까지 `성, 머리글자`와 `and`, 넷 이상 `첫 저자 et al.` | `저자 (연도) '제목', 게재처. Available at: DOI 주소.` |
| Vancouver | [vancouver](../../frontend/src/citationStyles.ts#vancouver) | 여섯까지 `성 머리글자`(마침표 없음), 넘으면 `, et al.` | `저자. 제목. 게재처. 연도. doi:DOI` |

- 게재처는 기울인다(Vancouver 제외). 학회 논문과 책의 장은 "학회 묶음"으로 보아 IEEE는 `in`, ACM은 `In`을 붙인다.
- 게재처가 없거나, OpenAlex가 주는 arXiv 저장소 이름("arXiv (Cornell University)" 등 `arXiv`로 시작하는 이름)이면 게재처가 없는 것으로 보고([publishedVenue](../../frontend/src/citationStyles.ts#publishedVenue)), DOI가 arXiv DOI이면 `arXiv preprint arXiv:<ID>`를 게재처로 쓴다([arxivId](../../frontend/src/citationStyles.ts#arxivId)). OpenAlex로 담은 arXiv 논문은 게재처가 저장소 이름으로 들어 있었다(2026-11-15 확인).
- 주소는 DOI가 있으면 `https://doi.org/<DOI>`, 없으면 원문 주소다.
- 제목의 대소문자는 바꾸지 않는다. APA는 문장식 대소문자를 쓰지만, 고유 이름(BERT, ImageNet 등)을 기계로 가려낼 수 없어 바꾸면 틀리기 쉽기 때문이다. 구글 스칼라도 원래 모양을 쓴다.

## 3. 저자 이름

- 서재의 저자 이름은 `이름 성` 한 줄이다. [splitName](../../frontend/src/citationStyles.ts#splitName)이 성과 이름으로 나눈다([PersonName](../../frontend/src/citationStyles.ts#PersonName)).
  - 쉼표가 있으면 `성, 이름`으로 읽는다.
  - 아니면 마지막 낱말이 성이다. 바로 앞의 소문자 이음말(van, von, de, der, di, da, du, le, la 등)은 성에 붙이고, 끝의 `Jr.`, `III` 등은 성 뒤에 남긴다.
  - 낱말이 하나뿐이면 성으로 본다.
- 머리글자([initials](../../frontend/src/citationStyles.ts#initials))는 이름 낱말마다 첫 글자에 마침표를 붙인다(`Aidan N.` → `A. N.`, `Jean-Paul` → `J.-P.`). Vancouver는 마침표와 빈칸 없이 붙인다(`AN`).

## 4. BibTeX

- 항목 종류에 따라 형식과 게재처 필드를 고른다: 저널 논문 `@article`(journal), 학회 논문 `@inproceedings`(booktitle), 책의 장 `@incollection`(booktitle), 책 `@book`(publisher), 학위논문 `@phdthesis`(school), 보고서 `@techreport`(institution). 그 밖은 `@misc`(howpublished)이고, 게재처가 없는 arXiv 논문은 `@article`(journal = `arXiv preprint arXiv:<ID>`)이다.
- 키([bibtexKey](../../frontend/src/citationStyles.ts#bibtexKey))는 첫 저자 성(악센트와 기호를 뗀 소문자) + 연도 + 제목에서 네 글자 넘는 첫 낱말이다(예: `vaswani2017attention`). 구글 스칼라와 같은 모양이다.
- 제목은 이중 중괄호로 감싸 대소문자를 지킨다. arXiv 논문은 `eprint`와 `archivePrefix = {arXiv}`를 넣는다. DOI가 있으면 `doi`, 없으면 `url`을 넣는다. 값 안의 중괄호는 뗀다.
- BibTeX는 서식 없이 글로만 복사하므로 HTML을 만들지 않는다.

## 5. 복사

- 논문 상세([PaperDetail](../../frontend/src/PaperDetail.vue)) 맨 위 오른쪽의 "인용" 버튼이 창([CiteDialog](../../frontend/src/CiteDialog.vue))을 연다. 창은 여덟 양식을 위 순서로 한 줄씩 보여 주고, 줄마다 미리보기와 "복사" 버튼을 둔다. 구글 스칼라의 인용 창과 같은 모양이다. BibTeX는 고정폭 글꼴 상자로 보여 준다.
- "복사"를 누르면 [copyCitation](../../frontend/src/citationStyles.ts#copyCitation)이 일반 글과 HTML을 함께 클립보드에 넣는다(`ClipboardItem`). 워드나 구글 문서에 붙여 넣으면 기울임이 남고, 글만 받는 곳에는 일반 글이 들어간다. 브라우저가 `ClipboardItem`을 지원하지 않거나 막으면 일반 글만 넣는다. 버튼은 2초 동안 "복사됨"으로 바뀐다.
- HTML 미리보기는 `v-html`로 그린다. 서재 정보는 모두 HTML 특수 문자를 바꾼 뒤 `<i>`로만 감싸므로 다른 태그가 들어가지 않는다.

## 6. 테스트

- [citationStyles.test](../../frontend/src/citationStyles.test.ts)는 이름 나누기(머리글자, 이음말, Jr., 쉼표, 한 낱말), 여덟 양식의 글(저자 수에 따른 et al., 학회·저널·arXiv, 연도 없음), 기울임 HTML과 특수 문자, BibTeX 형식·키·arXiv 저장소 게재처, 복사(HTML과 함께, 글만, 실패하면 글만)를 확인한다.

## 7. 미결정 사항

- 없음. 권·호·쪽을 서재에 담게 되면 양식에 더한다.
