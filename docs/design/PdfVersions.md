# PDF 판 설계

이 문서는 서재 논문 하나에 PDF를 여러 판(arXiv 개정판, 학술지·학회 출판판, 올린 파일) 두고, 판을 골라 받고 읽는 방법을 정한다. 판마다 하이라이트·영역 메모·읽던 위치를 따로 둔다. PDF 가져오기와 보관의 바탕은 [PDF 리더 설계](Reader.md#2-pdf-가져오기)에, 서재 데이터 모델은 [서재 데이터 설계](Library.md#1-데이터-모델)에 있다. 이슈는 [I30](../Issue.md)이다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 정한 것

사용자가 2026-11-18에 정했다.

- 논문 상세와 리더에 판 선택 드롭다운을 둔다. 서재에 받아 둔 판과, 아직 받지 않았지만 받을 수 있는 판을 함께 보인다.
- 받은 판은 모두 남긴다. 하이라이트·영역 메모·읽던 위치는 판마다 따로 둔다. 판마다 쪽과 글 위치가 달라 한 판의 주석을 다른 판에 그리면 엉뚱한 곳에 놓이기 때문이다.

## 2. 판을 찾는 곳

조사 결과(2026-11-18, 로컬 서재):

- arXiv 논문은 개정판이 여럿이다. 'Attention Is All You Need'는 v7까지, 'Darwin Gödel Machine'은 v1(2025-05-29), v2(2025-09-26), v3(2026-03-12)이 있다.
- OpenAlex 작업의 `locations`에는 판마다 출처(`source.display_name`), 판 종류(`version`: `publishedVersion` 출판판, `acceptedVersion` 수락판, `submittedVersion` 제출판), 공개 PDF 주소(`pdf_url`)가 있다. 'Gödel Agent'는 ACL 출판판과 arXiv 제출판이, 'Darwin Gödel Machine'은 학술지(s-rsa.com) 출판판과 arXiv 제출판이 있었다. NeurIPS 출판판처럼 공개 PDF 주소가 없는 위치도 있다.

받을 수 있는 판은 다음 두 곳에서 모은다([available_versions](../../src/jjabtero/pdf_versions.py#available_versions)).

- **arXiv 개정판**: 논문의 arXiv 번호는 DOI(`10.48550/arxiv.<번호>`)에서, 없으면 OpenAlex 위치의 arXiv 주소(`arxiv.org/abs/<번호>`, `arxiv.org/pdf/<번호>`)에서 얻는다. 개정판 목록과 날짜는 arXiv의 공식 메타데이터 API(OAI-PMH, `https://export.arxiv.org/oai2?verb=GetRecord&identifier=oai:arXiv.org:<번호>&metadataPrefix=arXivRaw`)의 `<version version="vN"><date>…</date>`에서 읽는다([arxiv_versions](../../src/jjabtero/pdf_versions.py#arxiv_versions)). 검색 API(`export.arxiv.org/api/query`)는 마지막 판의 번호와 첫·마지막 날짜만 주어 쓰지 않는다. 판마다 주소는 `https://arxiv.org/pdf/<번호>v<N>`이다.
- **OpenAlex 위치**: 서재 논문이 OpenAlex에 연결되어 있으면 작업의 `locations`에서 공개 PDF 주소가 있는 것을 쓴다. arXiv 위치는 위의 개정판 목록이 대신하므로 뺀다. 같은 주소는 한 번만 쓴다.

판 이름([PdfVersionOut](../../src/jjabtero/pdf_versions.py#PdfVersionOut)의 `label`):

- arXiv 개정판: `arXiv v3`, 날짜는 `date`로 따로 준다. 가장 늦은 판에는 `latest`를 붙인다.
- OpenAlex 위치: 출처 이름과 판 종류(`출판판`, `수락판`, `제출판`, 모르면 종류 없이). 예: `SuperIntelligence - Robotics - Safety & Alignment · 출판판`.
- 받아 둔 판([saved_label](../../src/jjabtero/pdf_versions.py#saved_label)): 출처 주소가 arXiv 판 주소이면 `arXiv vN`, 판 번호 없는 arXiv 주소이면 `arXiv`, 올린 파일은 `올린 PDF`, 비슷한 공개판은 `비슷한 공개판`, 그 밖에는 출처 주소의 호스트 이름이다. 받아 둔 판이 받을 수 있는 판과 출처 주소가 같으면 그 이름을 쓴다.

찾기에 실패해도(네트워크, OpenAlex 한도) 받아 둔 판은 고를 수 있다. 실패는 드롭다운 아래에 안내한다.

## 3. 데이터

마이그레이션 0008([0008_pdf_versions](../../src/jjabtero/migrations/versions/0008_pdf_versions.py))이 바꾼다. 서재 통계 설계에서 0008로 적었던 다 읽은 시각은 0009가 된다.

- `paper_pdfs`([PaperPdf](../../src/jjabtero/models.py#PaperPdf)): 주 키를 (`paper_id`, `sha256`)으로 바꿔 한 논문에 판 여러 개를 둔다. `selected_at`(고른 시각)을 더하고, 있던 행은 `added_at`으로 채운다. 지금 판은 `selected_at`이 가장 늦은 판이다([Paper.pdf](../../src/jjabtero/models.py#Paper.pdf)). 고른 판을 논문 행이 아니라 판 행의 시각으로 두는 것은, 드라이브 합치기에서 판 행마다 따로 합쳐도 지금 판이 하나로 정해지게 하기 위해서다.
- `reading_positions`([ReadingPosition](../../src/jjabtero/models.py#ReadingPosition)): `pdf_sha256`을 더하고 주 키를 (`paper_id`, `pdf_sha256`)으로 바꾼다. 있던 행은 그 논문의 PDF로 채우고, PDF가 없는 논문의 위치는 지운다(쓸 곳이 없다).
- `annotations`([Annotation](../../src/jjabtero/models.py#Annotation)): `pdf_sha256`을 더한다. 있던 행은 그 논문의 PDF로 채우고, PDF가 없으면 빈 글자로 둔다.
- 판 행을 지우지 않으므로 판에 딸린 위치·주석을 판과 잇는 외래 키는 두지 않는다. 논문을 지우면 모두 함께 지운다.
- 마지막으로 읽은 시각(`last_read_at`, [이슈 I29](../Issue.md), [Paper.last_read_at](../../src/jjabtero/models.py#Paper.last_read_at))은 판마다의 위치 가운데 가장 늦은 저장 시각이다.
- 드라이브 합치기([구글 드라이브 동기화 설계](DriveSync.md#10-자동-합치기))의 규칙: `paper_pdfs`는 키 (`paper_id`, `sha256`)와 시각 `selected_at`, `reading_positions`는 키 (`paper_id`, `pdf_sha256`)와 시각 `updated_at`이다. 세 사본을 먼저 최신 스키마로 올리므로 옛 기준 사본도 같은 키로 합친다.

## 4. 저장

- 받거나 올린 PDF는 판으로 더하고 지금 판으로 고른다([PdfStore.save](../../src/jjabtero/pdfs.py#PdfStore.save)). 같은 내용(SHA-256)이 이미 있으면 새 행을 만들지 않고 출처와 고른 시각만 바꾼다. 예전에는 새 PDF가 옛 연결을 바꿨다.
- 판을 고르면 그 판의 `selected_at`을 지금 시각으로 바꾸고 드라이브 올리기를 예약한다.
- 판 지우기는 하지 않는다(8절).

## 5. API

[pdf_versions 모듈](../../src/jjabtero/pdf_versions.py)의 [router](../../src/jjabtero/pdf_versions.py#router)가 처리한다.

| API | 내용 |
| --- | --- |
| `GET /api/papers/{id}/pdf/versions`([saved_versions](../../src/jjabtero/pdf_versions.py#saved_versions)) | 받아 둔 판 목록([SavedVersionOut](../../src/jjabtero/pdf_versions.py#SavedVersionOut): `sha256`, `label`, `source`, `source_url`, `added_at`, `selected`), 지금 판이 먼저다. 바깥 요청을 하지 않는다 |
| `GET /api/papers/{id}/pdf/versions/available`([remote_versions](../../src/jjabtero/pdf_versions.py#remote_versions)) | 받을 수 있는 판 목록([PdfVersionOut](../../src/jjabtero/pdf_versions.py#PdfVersionOut): `key`, `label`, `date`, `url`, `latest`, `saved_sha256`). 받아 둔 판과 주소가 같으면 `saved_sha256`에 그 판을 적는다. 찾기에 실패하면 502다 |
| `POST /api/papers/{id}/pdf/fetch` 본문 `{"version": key}`([FetchIn](../../src/jjabtero/pdfs.py#FetchIn)) | 받을 수 있는 판 하나를 받아 지금 판으로 둔다. 서버가 판 목록을 다시 찾아 그 `key`의 주소만 받는다. 사용자가 준 주소를 서버가 그대로 받지 않기 위해서다. 목록에 없는 `key`는 404다 |
| `PUT /api/papers/{id}/pdf/selected` 본문 `{"sha256": …}`([select_version](../../src/jjabtero/pdf_versions.py#select_version)) | 받아 둔 판을 지금 판으로 고른다. 없는 판은 404다 |

- `key`는 arXiv 개정판이면 `arxiv:v3`, OpenAlex 위치이면 `url:<PDF 주소>`다.
- PDF 내용(`GET /api/papers/{id}/pdf`, [read_pdf](../../src/jjabtero/pdfs.py#read_pdf)), 읽던 위치(`GET`, `PUT …/position`, [read_position](../../src/jjabtero/reading.py#read_position), [save_position](../../src/jjabtero/reading.py#save_position)), 주석 목록과 만들기(`GET`, `POST …/annotations`, [list_annotations](../../src/jjabtero/reading.py#list_annotations), [create_annotation](../../src/jjabtero/reading.py#create_annotation))는 `version=<sha256>` 질의([VERSION_PATTERN](../../src/jjabtero/pdfs.py#VERSION_PATTERN))를 받는다. 없으면 지금 판이다([Paper.pdf_version](../../src/jjabtero/models.py#Paper.pdf_version)). 받아 두지 않은 판은 404다. PDF가 없는 논문의 주석 목록은 비어 있고, 만들기는 404다.

## 6. 화면

- 판 선택 드롭다운([PdfVersionSelect](../../frontend/src/PdfVersionSelect.vue))은 "받은 판"과 "받을 수 있는 판" 두 묶음을 보인다. 받은 판은 이름과 받은 날, 받을 수 있는 판은 이름과 공개일(arXiv 판의 날짜)과 "최신" 표시다. 받을 수 있는 판 가운데 이미 받은 것은 받은 판 쪽에만 보인다.
  - 받은 판 목록은 드롭다운이 처음 보일 때 불러온다. 받을 수 있는 판은 드롭다운을 열 때 한 번 찾는다. 논문을 고를 때마다 OpenAlex·arXiv에 묻지 않기 위해서다.
  - 받은 판을 고르면 지금 판으로 바꾸고, 받을 수 있는 판을 고르면 받아서 지금 판으로 둔다. 받는 동안 드롭다운을 막는다.
- 논문 상세의 PDF 칸([PdfPanel](../../frontend/src/PdfPanel.vue)): PDF가 있으면 "읽기" 옆에 드롭다운을 둔다. PDF가 없어도 드롭다운을 두어 받을 판을 고를 수 있다. "PDF 바꾸기"는 "다른 PDF 올리기"가 되고, 올린 파일은 새 판이 된다.
- 리더([ReaderView](../../frontend/src/ReaderView.vue)): 머리줄 제목 옆에 같은 드롭다운을 둔다. 리더는 열 때 받아 둔 판 목록에서 지금 판을 정하고, 그 판의 PDF·읽던 위치·주석을 `version`으로 청한다. 판을 바꾸면 리더를 그 판으로 다시 연다(앱이 리더를 새로 만든다).
- 상태는 [createPdfVersionState](../../frontend/src/pdfVersionState.ts#createPdfVersionState)가 가진다. 드롭다운 묶음은 [versionGroups](../../frontend/src/pdfVersionState.ts#versionGroups)가 만든다(항목 [VersionOption](../../frontend/src/pdfVersionState.ts#VersionOption), 묶음 [VersionGroup](../../frontend/src/pdfVersionState.ts#VersionGroup)).
- API 호출은 [listPdfVersions](../../frontend/src/api.ts#listPdfVersions), [listAvailablePdfVersions](../../frontend/src/api.ts#listAvailablePdfVersions), [fetchPdfVersion](../../frontend/src/api.ts#fetchPdfVersion), [selectPdfVersion](../../frontend/src/api.ts#selectPdfVersion)이고, 타입은 [SavedPdfVersion](../../frontend/src/api.ts#SavedPdfVersion), [AvailablePdfVersion](../../frontend/src/api.ts#AvailablePdfVersion)이다. [pdfUrl](../../frontend/src/api.ts#pdfUrl)과 위치·주석 호출은 판을 두 번째(만들기는 세 번째) 인자로 받는다.

## 7. 테스트

- 백엔드([test_pdf_versions](../../tests/test_pdf_versions.py)): arXiv 메타데이터 읽기(판과 날짜, 판 없음), arXiv 번호 찾기(DOI, OpenAlex 위치), OpenAlex 위치 고르기(공개 PDF 없음·arXiv 빼기·같은 주소), 판 이름, 받은 판 목록과 지금 판, 판 고르기, 판 받기(목록에 없는 키 404), 같은 내용을 다시 받으면 행을 늘리지 않음, 판마다 따로인 위치·주석, 마지막으로 읽은 시각.
- 마이그레이션([test_db](../../tests/test_db.py)): 0008이 있던 PDF·위치·주석을 판과 잇는다.
- 드라이브 합치기([test_drive_merge](../../tests/test_drive_merge.py)): 판 행과 판마다의 위치가 따로 합쳐진다.
- 프론트엔드([pdfVersionState.test](../../frontend/src/pdfVersionState.test.ts)): 받은 판 불러오기, 열 때 한 번만 찾기, 받은 판 고르기, 받을 판 받기, 찾기 실패 안내. [api.test](../../frontend/src/api.test.ts): 요청 모양과 `version` 질의.
- 브라우저: 로컬 서재 사본에서 DGM 논문의 arXiv v1과 학술지판을 받아 판을 바꿔 가며 주석이 판마다 따로인지 확인한다.

## 8. 미결정 사항

- 받은 판 지우기. 드라이브의 파일은 지금도 지우지 않으므로([PDF 리더 설계](Reader.md#3-보관)), 필요해지면 쓰지 않는 파일 정리와 함께 다룬다.
- 한 판의 주석을 다른 판으로 옮기기(글로 찾아 옮기기).
