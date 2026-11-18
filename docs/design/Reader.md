# PDF 리더 설계

이 문서는 서재 논문의 PDF를 Jjabtero 안에서 읽는 리더([제품 비전](../ProductVision.md#7-pdf-리더))를 정한다. PDF를 어디서 가져와 어디에 보관하고, 화면이 어떻게 받아 그리며, 읽던 위치·하이라이트·영역 메모를 어떤 데이터로 저장하는지가 범위다. 태스크는 [로드맵의 M4](../Roadmap.md#m4-pdf-리더)에 있다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 뷰어 라이브러리

- PDF 렌더링은 Mozilla의 **pdf.js**(npm `pdfjs-dist`, Apache-2.0)를 쓴다. 버전은 6.4.299로 고정한다(2026-10-03 배포, 이 문서를 쓸 때 최신은 2주 전에 나온 6.5.438).
  - 브라우저에서 PDF를 그리는 사실상 표준이고, 글자 층(text layer)을 함께 그려 글을 고를 수 있다. 하이라이트가 이 글자 층의 선택을 쓴다.
  - 라이선스가 Apache-2.0이라 PrimeVue처럼 상용 라이선스 문제가 없다.
- 뷰어 컴포넌트는 직접 만든다. Vue용 포장 라이브러리는 하이라이트·영역 메모 같은 주석 층을 우리 데이터에 맞게 얹기 어렵기 때문이다. 쪽마다 캔버스, 글자 층, 주석 층(하이라이트와 영역 메모를 그리는 절대 위치 `div`)을 겹친다.
- pdf.js는 무거우므로(작업자 스크립트 포함 1MB 이상) 리더 화면을 처음 열 때만 불러온다([UI 기반 설계의 나중에 불러오는 화면](UiLayout.md#5-나중에-불러오는-화면)). 빌드하면 리더가 따로 묶이고(약 435KB, gzip 131KB), 작업자 스크립트(약 1.3MB)는 별도 파일이다. 첫 화면 번들을 키우지 않기 위해서다([이슈 I11](../Issue.md)).
- 화면에 보이는 쪽과 그 앞뒤 쪽만 그리고, 두 쪽보다 멀어진 쪽은 지운다. 긴 논문도 메모리를 적게 쓰기 위해서다. 모든 쪽의 크기는 열 때 먼저 읽어 자리를 잡아 두므로 스크롤 길이가 바뀌지 않는다.
- 글자 층 스타일은 `pdfjs-dist/web/pdf_viewer.css`를 리더에서만 불러온다. 글자 층 크기는 쪽 요소의 CSS 변수 `--scale-factor`, `--total-scale-factor`로 맞춘다.

## 2. PDF 가져오기

논문마다 PDF 판을 여러 개 둘 수 있다. 새로 넣으면 판으로 더하고 지금 판으로 고른다. 처음에는 논문마다 하나였고 새로 넣으면 옛 것을 바꿨다. 판과 판마다의 주석·읽던 위치는 [PDF 판 설계](PdfVersions.md)에 있다([이슈 I30](../Issue.md)).

가져오기와 보관은 [pdfs 모듈](../../src/jjabtero/pdfs.py)에 있다.

**자동: 공개 PDF 받기**

- [open_pdf_url](../../src/jjabtero/pdfs.py#open_pdf_url)이 주소를 찾는다. 서재 논문의 OpenAlex 작업([인용 데이터 설계](Citations.md#2-서재-논문과-openalex-연결))에서 `best_oa_location.pdf_url`, 없으면 `open_access.oa_url`을 쓴다. 주소가 arXiv 소개 페이지(`arxiv.org/abs/<ID>`)이면 PDF 주소(`arxiv.org/pdf/<ID>`)로 바꾼다. Adam 논문은 소개 페이지 주소가 왔다(2026-11-15 확인). 찾는 일은 [open_access_pdf_url](../../src/jjabtero/pdfs.py#open_access_pdf_url)이 하며, 인용 미리보기도 같이 쓴다([리더 인용 미리보기 설계](ReaderCitations.md#4-논문-찾기)). 'Attention Is All You Need'는 `https://arxiv.org/pdf/1706.03762`였다(2026-11-15 확인).
- DOI가 `10.48550/arxiv.<ID>`(arXiv 논문)이면 OpenAlex를 보지 않고 `https://arxiv.org/pdf/<ID>`를 먼저 쓴다. OpenAlex는 arXiv 논문에도 다른 저장소의 사본 주소를 주기도 하기 때문이다('Darwin Gödel Machine'은 낯선 미러 주소였다, 2026-11-15 확인, [이슈 H3](../Issue.md)). OpenAlex에 연결되지 않은 논문도 같다.
- [download_pdf](../../src/jjabtero/pdfs.py#download_pdf)가 넘겨주기(redirect)를 따라가며 받는다. 받은 내용이 PDF(`%PDF-`로 시작)가 아니면 버린다([check_pdf](../../src/jjabtero/pdfs.py#check_pdf), [NotPdfError](../../src/jjabtero/pdfs.py#NotPdfError)). 출판사 페이지가 PDF 대신 HTML을 주는 경우가 있기 때문이다.
- 자동 받기는 사용자가 논문 상세에서 "PDF 받기"를 누를 때 한다. 서재에 담을 때마다 자동으로 받으면 쓰지 않을 PDF까지 드라이브를 채우기 때문이다.

**비슷한 공개판 받기**([이슈 I27](../Issue.md))

- 공개 PDF가 없으면(책의 장, 유료 학술지) 같은 저자가 공개한 비슷한 판(예비판, 학위논문, 저장소 사본)을 찾아 보여 주고, 사용자가 고르면 그 PDF를 받는다. Schmidhuber의 "Gödel Machines: Fully Self-referential Optimal Universal Self-improvers"(Springer 책의 장, OpenAlex `closed`)에는 같은 저자의 arXiv 예비판 "Goedel Machines: Self-Referential Universal Problem Solvers Making Provably Optimal Self-Improvements"(`cs/0309048`)가 있었다(2026-11-18 확인).
- 찾기([open_alternatives](../../src/jjabtero/pdfs.py#open_alternatives), 결과 [OpenVersion](../../src/jjabtero/pdfs.py#OpenVersion)): OpenAlex에 제목으로 검색하되(`search`) 첫 저자의 성으로 거르고(`raw_author_name.search`) 공개된 것만(`is_oa:true`) 10건 받는다. 제목 검색만 하면 다른 저자의 비슷한 제목(Gödel Agent 등)이 먼저 나왔다. 저자 이름이 없는 논문은 찾지 않는다.
- 받은 것 가운데 다음을 모두 만족하는 것을 비슷함이 큰 순으로 3건까지 고른다([title_similarity](../../src/jjabtero/pdfs.py#title_similarity)).
  - 저자 가운데 서재 논문의 첫 저자와 성이 같은 사람이 있다(악센트를 떼고 비교).
  - 제목이 비슷하다: 쌍점(`:`) 앞 본제목끼리의 글자 비슷함(`difflib`)이 0.85 이상이고 본제목이 두 낱말 이상이거나, 전체 제목의 낱말(앞 5글자) 겹침(Jaccard)이 0.5 이상이다. 기준은 [ALTERNATIVE_MIN_SIMILARITY](../../src/jjabtero/pdfs.py#ALTERNATIVE_MIN_SIMILARITY)다. "Gödel"과 "Goedel"처럼 표기가 다른 것은 글자 비슷함이 잡는다. 같은 저자의 다른 논문("Developmental robotics …")은 둘 다 낮아 빠진다.
  - 연도가 5년 안이다.
  - 공개 PDF 주소가 있다(`best_oa_location.pdf_url`, 없으면 `open_access.oa_url`, arXiv 소개 페이지는 PDF 주소로).
  - 서재 논문 자신(같은 OpenAlex ID나 DOI)이 아니다.
- 받기: `POST /api/papers/{id}/pdf/fetch`에 본문 `{"openalex_id": 공개판 ID}`를 주면 그 공개판의 공개 PDF를 받아 이 논문의 PDF로 둔다. 출처는 `alternate`, 출처 주소는 받은 주소다.

**수동: PDF 올리기**

- 논문 상세의 "PDF 올리기"로 사용자가 가진 PDF를 올린다. 같은 검사(`%PDF-`)를 한다.
- 크기 제한은 100MB다([MAX_PDF_BYTES](../../src/jjabtero/pdfs.py#MAX_PDF_BYTES), [PdfTooLargeError](../../src/jjabtero/pdfs.py#PdfTooLargeError)). 받을 때는 받다가 넘으면 멈춘다. Render 무료 서버의 메모리(512MB)를 넘지 않기 위해서다.

## 3. 보관

[PdfStore](../../src/jjabtero/pdfs.py#PdfStore)가 맡는다. [create_app](../../src/jjabtero/app.py#create_app)이 데이터베이스 옆 `pdfs/` 폴더로 하나를 만든다. 드라이브는 [DriveFilesLike](../../src/jjabtero/pdfs.py#DriveFilesLike) 모양으로만 쓴다.

- PDF는 구글 드라이브 `Jjabtero/pdfs/` 폴더에 `<SHA-256>.pdf` 이름으로 올린다([DriveSync.put_file](../../src/jjabtero/drive_sync.py#DriveSync.put_file)). 같은 이름이 이미 있으면 다시 올리지 않는다. 내용 해시를 이름으로 쓰면 같은 PDF를 두 번 올리지 않고, 다른 컴퓨터에서 받은 파일이 맞는지 확인할 수 있다. 드라이브 권한은 지금의 `drive.file`(앱이 만든 파일만)로 충분하다.
- 로컬에는 데이터 폴더의 `pdfs/<SHA-256>.pdf`에 사본을 둔다. 드라이브에 연결되어 있지 않으면 로컬 사본만 있다.
- 서재 파일에는 논문과 PDF의 연결만 둔다(4절의 `paper_pdfs`). 서재와 함께 동기화되므로, 다른 컴퓨터는 이 연결을 보고 드라이브에서 받는다.
- 서버(Render)는 재시작 때 디스크가 지워지므로, 로컬 사본이 없으면 열 때 드라이브에서 받아 둔다([PdfStore.read](../../src/jjabtero/pdfs.py#PdfStore.read), [DriveSync.download_file](../../src/jjabtero/drive_sync.py#DriveSync.download_file)). 받은 내용의 해시가 다르면 버린다.
- 저장은 [PdfStore.save](../../src/jjabtero/pdfs.py#PdfStore.save)가 한다. 로컬에 먼저 임시 파일로 쓴 뒤 이름을 바꾼다.
- 논문을 지우거나 PDF를 바꾸면 연결만 지운다. 드라이브의 파일은 지우지 않는다. 사용자가 실수로 지운 것을 되살릴 수 있게 하기 위해서다. 쓰지 않는 파일 정리는 나중에 필요하면 이슈로 다룬다.

## 4. 데이터

모두 서재 파일(`library.db`)에 두어 드라이브로 동기화한다. 읽기 자취가 서재의 일부이기 때문이다. 표는 마이그레이션으로 만든다([서재 데이터 설계의 스키마 변경](Library.md#3-스키마-변경)).

| 표 | 열 | 내용 |
| --- | --- | --- |
| `paper_pdfs`([PaperPdf](../../src/jjabtero/models.py#PaperPdf), 마이그레이션 0005) | `paper_id`·`sha256`(함께 기본 키, 0008부터, 논문 지우면 함께 지움), `size`, `source`(`openalex`, `arxiv`, `alternate`, `upload`), `source_url`, `drive_file_id`, `page_count`, `added_at`, `selected_at`(0008부터) | 논문의 PDF 판([PDF 판 설계](PdfVersions.md#3-데이터)) |
| `reading_positions`([ReadingPosition](../../src/jjabtero/models.py#ReadingPosition), 마이그레이션 0006) | `paper_id`·`pdf_sha256`(함께 기본 키, 0008부터, 논문 지우면 함께 지움), `page`(1부터), `offset`(그 쪽 안의 세로 위치 0~1), `zoom`, `updated_at` | 읽던 위치 |
| `annotations`([Annotation](../../src/jjabtero/models.py#Annotation), 마이그레이션 0007) | `id`, `paper_id`(논문 지우면 함께 지움), `pdf_sha256`(속한 판, 0008부터), `kind`([ANNOTATION_KINDS](../../src/jjabtero/reading.py#ANNOTATION_KINDS): `highlight`, `note`), `page`, `rects`(JSON), `text`, `color`, `note`, `created_at`, `updated_at` | 하이라이트와 영역 메모 |

- 좌표는 쪽 크기에 대한 비율(0~1)로 저장한다. 확대·축소와 화면 크기에 상관없이 같은 자리에 그리기 위해서다. `rects`는 `[{"x":…, "y":…, "w":…, "h":…}]` 목록이다. 하이라이트는 여러 줄에 걸치므로 사각형이 여럿이고, 영역 메모는 하나다.
- 하이라이트는 고른 글(`text`)과 색(`color`, [ANNOTATION_COLORS](../../src/jjabtero/reading.py#ANNOTATION_COLORS): `yellow`, `green`, `blue`, `pink`, `purple`)을, 영역 메모는 메모(`note`)를 가진다. 사각형은 [Rect](../../src/jjabtero/reading.py#Rect)(x, y는 0~1, w, h는 0 초과 1 이하, 화면 쪽 타입은 [Rect](../../frontend/src/annotations.ts#Rect))이고 주석마다 1~200개다. 하이라이트에도 메모를 달 수 있다.
- 주석은 PDF가 아니라 논문에 묶는다. PDF를 다른 판으로 바꿔도 주석이 남는다. 쪽 구성이 다르면 자리가 어긋날 수 있으므로, PDF를 바꿀 때 화면에서 알린다.
- 읽던 위치는 스크롤이 멈춘 뒤 2초가 지나면 저장하고([createPositionSaver](../../frontend/src/readerState.ts#createPositionSaver), [POSITION_SAVE_DELAY_MS](../../frontend/src/readerState.ts#POSITION_SAVE_DELAY_MS)), 리더를 닫을 때 남은 것을 바로 저장한다. 리더를 열어 저장한 자리(없으면 첫 쪽)를 보여 주면 그 위치를 바로 한 번 저장한다. 그래서 위치의 `updated_at`은 이 논문을 Jjabtero 리더에서 마지막으로 열었거나 읽은 시각이 된다([이슈 I29](../Issue.md)). 닫기 단추는 남은 위치를 저장한 뒤 닫는다. 저장 실패는 리더를 멈추지 않는다. 쪽은 화면 위 끝에서 쪽 간격만큼 아래를 기준으로 센다. 다시 열면 저장한 확대 배율로 그 자리를 보여 주고, 저장한 위치가 없으면 너비에 맞춰 첫 쪽부터 보여 준다. 저장할 때마다 서재 자동 올리기가 예약되지만, 자동 올리기 자체가 5초 동안 모아서 하므로 드라이브 요청이 많아지지 않는다.

## 5. API

PDF API는 [pdfs 모듈](../../src/jjabtero/pdfs.py)의 [router](../../src/jjabtero/pdfs.py#router)다. 정보 응답은 [PdfOut](../../src/jjabtero/pdfs.py#PdfOut)(논문 ID, SHA-256, 크기, 출처, 출처 주소, 드라이브에 있는지)이다.

| 메서드와 경로 | 내용 |
| --- | --- |
| `GET /api/papers/{id}/pdf`([read_pdf](../../src/jjabtero/pdfs.py#read_pdf)) | PDF 내용(`application/pdf`). 로컬 사본이 없으면 드라이브에서 받아 둔다. 없으면 404 |
| `POST /api/papers/{id}/pdf/fetch`([fetch_pdf](../../src/jjabtero/pdfs.py#fetch_pdf)) | 공개 PDF를 받아 보관하고 `paper_pdfs` 정보를 돌려준다. 본문 `{"openalex_id": …}`([FetchIn](../../src/jjabtero/pdfs.py#FetchIn))를 주면 그 공개판의 PDF를 받는다(2절). `{"version": …}`을 주면 받을 수 있는 판 하나를 받는다([PDF 판 설계](PdfVersions.md#5-api)). 받은 PDF는 판으로 더하고 지금 판으로 고른다. 공개 PDF가 없으면 404, PDF가 아니거나 받지 못하면 502 |
| `GET /api/papers/{id}/pdf/alternatives`([pdf_alternatives](../../src/jjabtero/pdfs.py#pdf_alternatives)) | 비슷한 공개판 후보(2절, [OpenVersion](../../src/jjabtero/pdfs.py#OpenVersion): OpenAlex ID, 제목, 저자 앞 3명, 연도, 게재처, PDF 주소, 비슷함). 없으면 빈 목록, OpenAlex를 쓰지 못하면 502 |
| `PUT /api/papers/{id}/pdf`([upload_pdf](../../src/jjabtero/pdfs.py#upload_pdf)) | 올린 PDF(본문이 PDF 내용)를 보관하고 정보를 돌려준다. PDF가 아니면 415, 너무 크면 413 |
| `GET`, `PUT /api/papers/{id}/position`([read_position](../../src/jjabtero/reading.py#read_position), [save_position](../../src/jjabtero/reading.py#save_position)) | 읽던 위치를 읽고 쓴다. 저장한 위치가 없으면 204다. 입력은 [PositionIn](../../src/jjabtero/reading.py#PositionIn)(쪽 1 이상, 쪽 안 위치 0~1, 확대 0.25~5, 벗어나면 422), 응답은 [PositionOut](../../src/jjabtero/reading.py#PositionOut)이다. 저장하면 드라이브 자동 올리기를 예약한다. [reading 모듈](../../src/jjabtero/reading.py)의 [router](../../src/jjabtero/reading.py#router)가 처리한다 |
| `GET /api/papers/{id}/annotations`([list_annotations](../../src/jjabtero/reading.py#list_annotations)) | 주석 목록. 쪽 순서, 쪽 안에서는 위에서부터다 |
| `POST /api/papers/{id}/annotations`([create_annotation](../../src/jjabtero/reading.py#create_annotation)), `PATCH`·`DELETE /api/annotations/{id}`([update_annotation](../../src/jjabtero/reading.py#update_annotation), [delete_annotation](../../src/jjabtero/reading.py#delete_annotation)) | 주석을 만들고(입력 [AnnotationIn](../../src/jjabtero/reading.py#AnnotationIn)) 색·메모를 고치고(입력 [AnnotationUpdate](../../src/jjabtero/reading.py#AnnotationUpdate), 보낸 항목만) 지운다. 응답은 [AnnotationOut](../../src/jjabtero/reading.py#AnnotationOut)이다. 앞뒤 공백만인 글과 메모는 비운다. 바꿀 때마다 드라이브 자동 올리기를 예약한다. `/api/annotations`는 [annotations_router](../../src/jjabtero/reading.py#annotations_router)가 처리한다 |

- 모두 로그인이 켜져 있으면 로그인해야 쓴다. PDF도 `/api` 아래라 공개되지 않는다.
- 논문 목록 응답에 PDF가 있는지(`has_pdf`, 화면 타입 [Paper.has_pdf](../../frontend/src/api.ts#Paper.has_pdf))를 더해, 목록과 상세에서 표시한다. PDF의 출처와 출처 주소(`pdf_source`, `pdf_source_url`)도 더한다. 공개판에서 받은 PDF를 알리기 위해서다([이슈 I27](../Issue.md)). 마지막으로 읽은 시각(`last_read_at`, 읽던 위치의 `updated_at`, 연 적이 없으면 담은 시각, 화면 타입 [Paper.last_read_at](../../frontend/src/api.ts#Paper.last_read_at))도 더한다. 서재 목록에서 최근에 연 논문을 찾기 위해서다([이슈 I29](../Issue.md)). 화면의 API 호출은 [listAnnotations](../../frontend/src/api.ts#listAnnotations), [createAnnotation](../../frontend/src/api.ts#createAnnotation), [updateAnnotation](../../frontend/src/api.ts#updateAnnotation), [deleteAnnotation](../../frontend/src/api.ts#deleteAnnotation)(타입 [Annotation](../../frontend/src/api.ts#Annotation), [AnnotationInput](../../frontend/src/api.ts#AnnotationInput)), [fetchPosition](../../frontend/src/api.ts#fetchPosition), [savePosition](../../frontend/src/api.ts#savePosition)(타입 [ReadingPosition](../../frontend/src/api.ts#ReadingPosition)), [fetchOpenPdf](../../frontend/src/api.ts#fetchOpenPdf), [uploadPdf](../../frontend/src/api.ts#uploadPdf), [pdfUrl](../../frontend/src/api.ts#pdfUrl)이고 응답 타입은 [PaperPdf](../../frontend/src/api.ts#PaperPdf)다.
- PDF 내용, 읽던 위치, 주석 목록과 만들기는 `version=<SHA-256>` 질의([VERSION_PATTERN](../../src/jjabtero/pdfs.py#VERSION_PATTERN))로 판을 고른다. 없으면 지금 판이다. 판을 주지 않은 PDF 내용은 판을 고르면 바뀌므로 매번 확인하게 하고(`no-cache`), 판을 준 것만 한 시간 담아 둔다([PDF 판 설계](PdfVersions.md#5-api)).

## 6. 화면

- 논문 상세에 PDF 칸([PdfPanel](../../frontend/src/PdfPanel.vue))을 둔다. PDF가 있으면 "읽기"와 "다른 PDF 올리기"(처음에는 "PDF 바꾸기", 올린 파일은 새 판이 된다)를, 없으면 "PDF 받기"와 "PDF 올리기"를 보여 준다. 받기·올리기 상태는 [createPdfState](../../frontend/src/pdfState.ts#createPdfState)가 가진다.
  - "PDF 받기"가 공개 PDF를 찾지 못하면(404, [NoOpenPdfError](../../frontend/src/api.ts#NoOpenPdfError)) 비슷한 공개판을 찾는다([fetchPdfAlternatives](../../frontend/src/api.ts#fetchPdfAlternatives), 타입 [OpenVersion](../../frontend/src/api.ts#OpenVersion)). 있으면 "공개된 PDF가 없습니다. 비슷한 공개판이 있습니다. 이 PDF를 받을까요?"와 함께 후보마다 제목(PDF 링크), 저자·연도·게재처, "이 PDF 받기"를 보이고, 맨 아래에 "받지 않기"를 둔다. 고르면 그 공개판으로 받는다([fetchOpenPdf](../../frontend/src/api.ts#fetchOpenPdf)의 두 번째 인자). 없으면 지금처럼 오류를 보인다.
  - 공개판에서 받은 PDF는 "비슷한 공개판에서 받은 PDF입니다"와 출처 주소를 보인다. 판이 달라 쪽 번호나 내용이 다를 수 있음을 알리기 위해서다. 화면 타입에 [Paper.pdf_source](../../frontend/src/api.ts#Paper.pdf_source)를 더한다. "새 탭에서 열기"로 브라우저의 PDF 뷰어로도 열 수 있다.
- "읽기"를 누르면 리더 화면([ReaderView](../../frontend/src/ReaderView.vue))이 열린다. 리더는 왼쪽 목록을 남기고 가운데와 오른쪽 칸을 합친 넓은 칸을 쓴다. 위에 닫기, 제목, 쪽 이동(이전·다음, 쪽 번호 입력), 확대·축소(50~300%, [ZOOM_STEPS](../../frontend/src/readerState.ts#ZOOM_STEPS)), 너비 맞춤을 둔다. 처음에는 너비에 맞추되 150%를 넘지 않는다. 왼쪽 목록에서 다른 화면을 고르면 리더가 닫힌다.
- 쪽 배치와 위치 계산은 [readerState 모듈](../../frontend/src/readerState.ts)의 순수 함수다. [pageTops](../../frontend/src/readerState.ts#pageTops)는 쪽마다 위쪽 위치를([PAGE_GAP](../../frontend/src/readerState.ts#PAGE_GAP) 간격), [pageAt](../../frontend/src/readerState.ts#pageAt)은 스크롤 위치의 쪽을, [visiblePages](../../frontend/src/readerState.ts#visiblePages)는 그릴 쪽을, [nextZoom](../../frontend/src/readerState.ts#nextZoom)과 [fitWidthScale](../../frontend/src/readerState.ts#fitWidthScale)은 확대 배율을, [clampPage](../../frontend/src/readerState.ts#clampPage)는 쪽 번호 범위를 맡는다. 읽던 위치에 쓸 [positionAt](../../frontend/src/readerState.ts#positionAt)과 [scrollTopFor](../../frontend/src/readerState.ts#scrollTopFor)는 스크롤 위치와 (쪽, 쪽 안 비율)을 서로 바꾼다. 확대·축소할 때도 이 둘로 보던 자리를 지킨다.
- 하이라이트: 글을 고르면 선택 아래에 색 다섯 개([HIGHLIGHT_COLORS](../../frontend/src/annotations.ts#HIGHLIGHT_COLORS))의 작은 도구 막대가 뜨고, 색을 누르면 하이라이트가 된다. 선택의 화면 사각형은 [normalizeRects](../../frontend/src/annotations.ts#normalizeRects)가 쪽 비율로 바꾸고 같은 줄의 조각을 합친다. 여러 쪽에 걸친 선택은 시작한 쪽 안의 부분만 쓴다.
- 글 선택 도구 막대의 색 옆과 하이라이트 창에는 "AI 대화" 버튼이 있어, 그 글로 Gemini와 대화하는 칸을 리더 오른쪽에 연다([AI 대화 설계](AiChat.md#6-화면)).
- 하이라이트는 캔버스와 글자 층 사이의 층에 반투명 색(곱하기 혼합, [colorFill](../../frontend/src/annotations.ts#colorFill))으로 그린다. 글자 층이 위에 있어 하이라이트 위에서도 글을 고를 수 있다. 그래서 하이라이트를 누른 것은 글자 층의 클릭 위치로 판정한다([hitTest](../../frontend/src/annotations.ts#hitTest), 겹치면 나중 것). 누르면 고른 글, 색 바꾸기, 메모, 삭제가 있는 작은 창이 뜬다. Esc나 다른 곳을 누르면 닫힌다.
- 영역 메모: 머리줄의 "영역 메모"를 켜면 커서가 십자가 되고 글자 층이 선택을 받지 않는다. 쪽 위를 끌면 점선 사각형이 보이고([dragRect](../../frontend/src/annotations.ts#dragRect), 쪽 너비·높이의 1%([MIN_NOTE_SIZE](../../frontend/src/annotations.ts#MIN_NOTE_SIZE))보다 작으면 버림), 놓으면 메모 입력이 열린다. 저장하면 `kind: note` 주석이 되고 영역 메모 모드가 꺼진다. 영역 메모는 노란 테두리 사각형과 말풍선 표시로 그리고, 누르면 하이라이트와 같은 창(색 고르기 없음)이 뜬다.
- 메모 상자(하이라이트 창과 영역 메모 입력)의 너비는 432px([NOTE_BOX_WIDTH](../../frontend/src/readerState.ts#NOTE_BOX_WIDTH))다. 처음 288px에서 사용자 요청으로 1.5배로 늘렸다([이슈 I22](../Issue.md)). 위치는 [notePlacement](../../frontend/src/readerState.ts#notePlacement)가 리더에서 보이는 영역([Viewport](../../frontend/src/readerState.ts#Viewport), 스크롤과 창 크기가 바뀔 때마다 잰다) 안으로 정한다.
  - 기준점(고른 글이나 영역의 아래) 아래 8px에 두고, 오른쪽으로 넘치면 왼쪽으로 당긴다.
  - 상자 아래 끝이 리더 화면 아래를 넘지 않게, 남은 높이를 최대 높이로 한다. 남은 높이가 200px([NOTE_BOX_MIN_HEIGHT](../../frontend/src/readerState.ts#NOTE_BOX_MIN_HEIGHT))보다 작으면 상자를 올려 200px를 확보한다(화면이 그보다 낮으면 화면 위에 붙인다).
  - 메모가 길면 메모 칸 안에서 스크롤하고, 고른 글·색·삭제·저장 버튼은 줄지 않고 늘 보인다.
- 머리줄의 "주석 n"으로 오른쪽 주석 목록을 열고 닫는다. 쪽 순서로 종류, 쪽, 요약([annotationSummary](../../frontend/src/annotations.ts#annotationSummary): 하이라이트는 글과 메모, 영역 메모는 메모)을 보여 주고, 누르면 그 자리로 스크롤하고 주석 창을 연다.

## 7. 태스크 나누기

| 태스크 | 범위 |
| --- | --- |
| M4-T2 | 드라이브 하위 폴더, 로컬 사본, `paper_pdfs`, PDF 받기·올리기·내려주기 API, 논문 상세의 PDF 칸(받기, 올리기) |
| M4-T3 | pdf.js 리더 화면(쪽 그리기, 글자 층, 쪽 이동, 확대·축소, 동적 불러오기) |
| M4-T4 | `reading_positions`, 위치 API, 이어 읽기 |
| M4-T5 | `annotations`의 하이라이트, 주석 API, 글 선택 도구 막대 |
| M4-T6 | 영역 메모와 주석 목록 |

## 8. 테스트

- 비슷한 공개판([이슈 I27](../Issue.md)): [test_pdfs](../../tests/test_pdfs.py)는 제목 비슷함(표기가 다른 판, 같은 저자의 다른 논문, 한 낱말 본제목, 낱말 겹침), 후보 고르기(같은 첫 저자, 5년 안, 공개 PDF, 자기 자신과 같은 DOI 빼기, 저자 없음, 없는 논문), 공개판으로 받기(출처 `alternate`, 논문 응답의 출처, 잘못된 ID 422)를 확인한다. [pdfState.test](../../frontend/src/pdfState.test.ts)와 [referencePreview.test](../../frontend/src/referencePreview.test.ts)는 공개 PDF가 없을 때 공개판을 묻고 받기·받지 않기, 다른 실패에는 찾지 않기를, [api.test](../../frontend/src/api.test.ts)는 `NoOpenPdfError`와 요청 모양을 확인한다.

- [test_pdfs](../../tests/test_pdfs.py): 공개 PDF 받기(OpenAlex, arXiv DOI, 없음, PDF가 아님), 로컬 사본과 드라이브 `pdfs/` 폴더 보관, 올리기(바꾸기, PDF 아님 415, 너무 큼 413), 로컬 사본이 없을 때 드라이브에서 받기, 드라이브 없이 로컬만, 없는 논문 404, 논문을 지우면 연결만 지우기.
- [test_reading](../../tests/test_reading.py): 읽던 위치가 없을 때 204, 저장과 바꾸기, 논문 응답의 마지막으로 읽은 시각(연 적 없으면 담은 시각, 저장하면 바뀜), 범위 밖 422, 없는 논문 404, 논문을 지우면 함께 지우기, 저장마다 드라이브 올리기 예약.
- [test_reading](../../tests/test_reading.py)의 주석 부분: 만들기, 쪽·위치 순 목록, 색·메모 고치기(빈 메모는 비움), 지우기, 잘못된 종류·쪽·사각형·색 422, 없는 논문·주석 404, 논문을 지우면 함께 지우기.
- [annotations.test](../../frontend/src/annotations.test.ts): 화면 사각형의 쪽 비율 변환과 같은 줄 합치기, 쪽 밖 버리기·자르기, 누른 위치 판정, 색, 끈 영역의 사각형(뒤집힌 방향, 쪽 밖 자르기, 너무 작음), 목록 요약.
- [pdfState.test](../../frontend/src/pdfState.test.ts): 받기·올리기 성공과 실패.
- [readerState.test](../../frontend/src/readerState.test.ts): 확대 단계, 너비 맞춤, 쪽 위치, 보이는 쪽, 쪽 번호 범위, 읽던 위치와 스크롤 위치 변환, 위치 저장 지연(2초, 마지막 값만, 닫을 때 바로, 실패 무시).
- 리더 화면 자체(pdf.js 그리기)는 단위 테스트 대신 브라우저에서 실제 PDF로 확인한다.
- [api.test](../../frontend/src/api.test.ts): PDF API 호출과 오류 메시지.

