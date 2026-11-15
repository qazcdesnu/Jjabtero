# 완료

이 문서는 끝난 작업의 상세 기록이다. 최신 기록이 맨 위에 온다. 기록 형식은 [작업 관리 규칙](TaskRule.md#5-기록-형식)을 따르며, 할 일 목록은 [로드맵](Roadmap.md)과 [이슈](Issue.md)에 있다. 닫힌 마일스톤의 기록은 [작업 관리 규칙](TaskRule.md#47-완료-기록-보관)에 따라 보관 문서로 옮긴다. 보관 문서: [M0 시작](Done-M0.md), [M1 기본 서재](Done-M1.md), [M2 Render 배포](Done-M2.md). 전체 문서 목록은 [문서 인덱스](index.md)에서 확인한다.

## M4-T4 읽던 위치 저장과 이어 읽기

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [PDF 리더 설계](design/Reader.md#4-데이터)
- 참고 자료: 없음

### 계획
- `reading_positions`(마이그레이션 0006)와 위치 API를 만들고, 리더가 스크롤이 멈추면 위치를 저장하고 다시 열면 그 자리를 보여 주게 한다.

### 진행 기록
- 2026-11-15: M4-T3을 마치고 권장 순서대로 시작했다. PR #34(M4-T3)가 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-15: 모델, 마이그레이션 0006, 위치 API(읽기 204/쓰기, 범위 검사, 드라이브 올리기 예약)를 구현하고 테스트를 더했다. 화면에 위치 API 함수와 2초 지연 저장기를 더하고, 리더가 열 때 위치를 되살리고 스크롤·확대 때 저장하며 닫을 때 남은 것을 저장하게 했다.
- 2026-11-15: 임시 서버의 브라우저 시험에서 5쪽으로 가서 닫았다 다시 열면 5쪽이 보였다. 다만 저장값이 "4쪽 끝"(offset 1.0)이었다. 쪽 머리 바로 위로 이동한 위치를 스크롤 위치 그대로 셌기 때문이다. 쪽 번호와 같은 기준(쪽 간격만큼 아래)으로 세도록 고쳐 "5쪽, 0.007"로 저장되는 것을 확인했다.
- 2026-11-15: PDF 리더 설계와 서재 데이터 설계에 위치 데이터, API, 마이그레이션, 테스트를 더했다.

### 결정 사항
- 저장한 위치가 없으면 `GET`이 204를 돌려준다. 없음이 오류가 아니기 때문이다.
- 위치 저장 실패는 화면에 알리지 않고 다음 저장 때 다시 보낸다. 읽기를 방해하지 않기 위해서다.

### 변경 파일
- `src/jjabtero/reading.py`
- `src/jjabtero/models.py`
- `src/jjabtero/migrations/versions/0006_reading_positions.py`
- `src/jjabtero/app.py`
- `tests/test_reading.py`
- `frontend/src/api.ts`
- `frontend/src/api.test.ts`
- `frontend/src/readerState.ts`
- `frontend/src/readerState.test.ts`
- `frontend/src/ReaderView.vue`
- `docs/design/Reader.md`
- `docs/design/Library.md`
- `docs/Roadmap.md`
- `docs/Done.md`

### 결과
- 리더를 닫았다 다시 열면, 다른 컴퓨터에서 열어도(서재 동기화 뒤) 읽던 쪽과 확대 배율로 이어 읽는다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과(백엔드 새 테스트 5개, 프론트엔드 새 테스트 4개 포함).
- `vue-tsc` 타입 검사와 `npm run build` 통과. 브라우저에서 이어 읽기를 확인했다.

## M4-T3 리더 화면(서재 논문의 PDF 열람) 구현

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [PDF 리더 설계](design/Reader.md#6-화면)
- 참고 자료: 없음

### 계획
- pdf.js로 쪽 그리기, 글자 층, 쪽 이동, 확대·축소를 하는 리더 화면을 만들고, 처음 열 때만 불러오게 한다.

### 진행 기록
- 2026-11-15: M4-T2를 마치고 권장 순서대로 시작했다. PR #33(M4-T2)이 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-15: `pdfjs-dist` 6.4.299를 고정 버전으로 설치했다. 쪽 배치·위치 계산을 순수 함수 모듈로 만들어 테스트하고, 리더 화면을 만들어 `App.vue`에서 비동기 컴포넌트로 불러오게 했다. 논문 상세의 "읽기"가 리더를 연다.
- 2026-11-15: 빌드에서 리더가 따로 묶이고(약 435KB) 첫 화면 번들 크기는 그대로임을 확인했다.
- 2026-11-15: 임시 데이터 폴더로 띄운 서버에서 받은 arXiv PDF(15쪽)를 브라우저로 열었다. 쪽과 글자 층(첫 쪽 240조각)이 그려지고 콘솔 오류가 없었다. "다음 쪽"을 눌렀을 때 쪽 번호가 1로 남는 문제를 찾았다. 쪽 머리 8px 위로 이동하는데 쪽을 스크롤 위치에서 세었기 때문이다. 쪽 간격만큼 아래를 보고 세도록 고쳐 2로 바뀌는 것을 확인했다.
- 2026-11-15: PDF 리더 설계에 코드 링크, 그리기 방식, 테스트를, 시스템 구조에 pdf.js를 더했다.

### 결정 사항
- 리더 화면의 그리기는 단위 테스트 대신 실제 PDF로 브라우저에서 확인한다. pdf.js가 캔버스와 작업자를 쓰므로 테스트 환경에서 흉내 내기 어렵기 때문이다. 계산은 순수 함수로 빼서 테스트한다.
- 글자 층 스타일은 pdf.js의 `pdf_viewer.css`를 리더에서만 불러온다. 첫 화면 CSS를 키우지 않기 위해서다.

### 변경 파일
- `frontend/package.json`
- `frontend/package-lock.json`
- `frontend/src/ReaderView.vue`
- `frontend/src/readerState.ts`
- `frontend/src/readerState.test.ts`
- `frontend/src/App.vue`
- `frontend/src/PaperDetail.vue`
- `docs/design/Reader.md`
- `docs/Architecture.md`
- `docs/Roadmap.md`
- `docs/Done.md`

### 결과
- 서재 논문의 PDF를 Jjabtero 안에서 읽을 수 있다. 글을 고를 수 있고, 쪽 이동과 확대·축소가 된다. 하이라이트·영역 메모·읽던 위치가 이 위에 쌓인다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과(프론트엔드 새 테스트 6개 포함).
- `vue-tsc` 타입 검사와 `npm run build` 통과. 브라우저에서 실제 PDF 열람을 확인했다.

## M4-T2 PDF 가져오기(공개 PDF 자동 받기, 직접 올리기)와 드라이브 보관 구현

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [PDF 리더 설계](design/Reader.md#2-pdf-가져오기)
- 참고 자료: 없음

### 계획
- 드라이브 하위 폴더, 로컬 사본, `paper_pdfs`(마이그레이션 0005), PDF 받기·올리기·내려주기 API, 논문 상세의 PDF 칸을 구현한다.

### 진행 기록
- 2026-11-15: M4-T1을 마치고 권장 순서대로 시작했다. PR #32(M4-T1)가 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-15: 드라이브 폴더 찾기·만들기에 부모 폴더 인자를 더하고, 하위 폴더에 파일을 올리고 ID로 받는 `put_file`, `download_file`을 더했다. `PaperPdf` 모델과 마이그레이션 0005, PDF 모듈(공개 PDF 주소 찾기, 받기, 검사, 로컬·드라이브 보관, API)을 구현하고 테스트를 더했다. 논문 응답에 `has_pdf`를 더했다.
- 2026-11-15: 화면에 PDF 칸(받기, 올리기·바꾸기, 읽기)을 더했다. 리더가 생기기 전이라 "읽기"는 PDF를 새 탭에서 연다.
- 2026-11-15: 임시 데이터 폴더로 띄운 서버에 'Attention Is All You Need'(arXiv DOI)를 넣고 브라우저에서 "PDF 받기"를 눌렀다. arXiv에서 2.2MB PDF를 받아 로컬 `pdfs/<SHA-256>.pdf`에 저장하고 목록의 `has_pdf`가 참이 되는 것을 확인했다.
- 2026-11-15: 문서를 구현에 맞췄다. PDF 리더 설계에 코드 링크와 테스트 절을, 서재 데이터 설계에 `paper_pdfs`와 마이그레이션 0005를, 구글 드라이브 동기화 설계에 하위 폴더 파일을 더했다.

### 결정 사항
- 드라이브의 같은 이름(같은 내용 해시) 파일은 다시 올리지 않는다. 이름이 내용 해시이기 때문이다.
- 올리기는 본문 전체를 PDF 내용으로 받는 `PUT`이다. 여러 부분(multipart) 양식 처리 의존성을 더하지 않기 위해서다.

### 변경 파일
- `docs/design/Reader.md`
- `docs/design/Library.md`
- `docs/design/DriveSync.md`
- `src/jjabtero/pdfs.py`
- `src/jjabtero/models.py`
- `src/jjabtero/migrations/versions/0005_paper_pdfs.py`
- `src/jjabtero/drive.py`
- `src/jjabtero/drive_sync.py`
- `src/jjabtero/papers_api.py`
- `src/jjabtero/app.py`
- `tests/test_pdfs.py`
- `tests/fakes.py`
- `frontend/src/api.ts`
- `frontend/src/api.test.ts`
- `frontend/src/pdfState.ts`
- `frontend/src/pdfState.test.ts`
- `frontend/src/PdfPanel.vue`
- `frontend/src/PaperDetail.vue`
- `docs/Roadmap.md`
- `docs/Done.md`

### 결과
- 논문 상세에서 공개 PDF를 받거나 PDF를 올릴 수 있다. PDF는 로컬 사본과 드라이브 `Jjabtero/pdfs/`에 보관되고, 다른 컴퓨터나 재시작한 서버는 드라이브에서 받는다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과(백엔드 새 테스트 11개, 프론트엔드 새 테스트 5개 포함).
- `vue-tsc` 타입 검사와 `npm run build` 통과. 브라우저에서 실제 arXiv PDF 받기를 확인했다.

## M4-T1 PDF 리더 설계(뷰어 라이브러리, PDF 가져오기와 드라이브 보관, 서버 전달, 주석 데이터)

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [제품 비전](ProductVision.md#7-pdf-리더)
- 참고 자료: 없음

### 계획
- 뷰어 라이브러리, PDF 가져오기와 보관, 서버 전달, 읽던 위치·하이라이트·영역 메모 데이터를 PDF 리더 설계로 쓴다.
- M4-T2~T6이 같은 바탕 위에 쌓이도록 데이터와 API를 미리 정한다.

### 진행 기록
- 2026-11-15: M3-T8을 마치고 권장 순서대로 M4-T1을 시작했다. PR #31(M3-T8)이 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-15: npm에서 `pdfjs-dist`를 확인했다. 최신 6.5.438은 2026-11-01 배포라 2주가 막 지났고, 6.4.299는 2026-10-03 배포다. 라이선스는 Apache-2.0이다. OpenAlex에서 'Attention Is All You Need'의 `best_oa_location.pdf_url`이 `https://arxiv.org/pdf/1706.03762`임을 확인했다.
- 2026-11-15: PDF 리더 설계를 쓰고 인덱스와 제품 비전에서 링크했다.

### 결정 사항
- 뷰어는 pdf.js(`pdfjs-dist` 6.4.299 고정)이고 컴포넌트는 직접 만든다. 주석 층을 우리 데이터에 맞게 얹기 위해서다. 리더를 열 때만 불러온다([PDF 리더 설계](design/Reader.md#1-뷰어-라이브러리)).
- 공개 PDF는 사용자가 "PDF 받기"를 누를 때 받는다. 담을 때마다 받으면 쓰지 않을 PDF가 드라이브를 채우기 때문이다([PDF 리더 설계](design/Reader.md#2-pdf-가져오기)).
- PDF는 드라이브 `Jjabtero/pdfs/<SHA-256>.pdf`와 로컬 사본에 두고, 서재 파일에는 연결만 둔다. 지울 때 드라이브 파일은 남긴다([PDF 리더 설계](design/Reader.md#3-보관)).
- 읽던 위치와 주석은 서재 파일에 두고, 좌표는 쪽 크기에 대한 비율로 저장한다. 주석은 PDF가 아니라 논문에 묶는다([PDF 리더 설계](design/Reader.md#4-데이터)).

### 변경 파일
- `docs/design/Reader.md`
- `docs/index.md`
- `docs/ProductVision.md`
- `docs/Roadmap.md`
- `docs/Done.md`

### 결과
- PDF 리더의 뷰어, 가져오기, 보관, 데이터, API, 화면, 태스크별 범위가 정해졌다. M4-T2부터 이 설계대로 구현한다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.

## M3-T8 서재 논문의 OpenAlex 연결과 인용 데이터 가져오기·갱신 구현

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [인용 데이터 설계](design/Citations.md)
- 참고 자료: 없음

### 계획
- 인용 데이터 설계를 구현 수준(모듈, 갱신 순서, 드라이브 보관, API, 테스트)으로 고친다.
- 마이그레이션 0004(`openalex_id`), 연결, 가져오기, 캐시 파일, 백그라운드 갱신, 드라이브 보관, 상태 API와 설정 페이지의 인용 데이터 칸을 구현한다.

### 진행 기록
- 2026-11-15: 사용자가 앞으로 태스크가 끝날 때마다 다음 태스크를 정해 권장안대로 이어서 진행하고, PR 10개까지 연속으로 하며, 사용자가 할 일은 이슈로 남기라고 했다. PR #30(I14)이 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-15: 인용 데이터 설계를 구현 수준으로 고쳤다. 구글 드라이브 동기화 설계에 캐시 파일 보관을, 서재 데이터 설계에 `openalex_id`와 마이그레이션 0004를, 사용자 설정 설계에 인용 데이터 칸을 더했다.
- 2026-11-15: 마이그레이션 0004와 `PaperData.openalex_id`, 드라이브 캐시 파일 올리기·받기, 인용 데이터 모듈(연결, 가져오기, 캐시 파일, 백그라운드 갱신, 상태 API)을 구현했다. 실행 명령이 만든 앱만 갱신 스레드를 띄우게 했다. 화면은 검색 결과의 OpenAlex ID를 함께 보내고, 설정 페이지에 인용 데이터 칸을 더했다.
- 2026-11-15: 공동 인용 수가 같은 논문의 순서가 실행마다 달라 테스트가 가끔 실패했다. 같은 수는 ID 순으로 정렬해 고쳤다.
- 2026-11-15: 임시 서재에 'Attention Is All You Need'를 DOI로 넣고 실제 OpenAlex로 갱신을 한 번 돌렸다. W2626778328로 연결되고, 참고문헌 35건과 피인용 10건이 저장되었으며, 피인용 많은 순 첫 세 건이 조사 때와 같았다.
- 2026-11-15: 사용자가 해야 할 일인 Render의 `OPENALEX_API_KEY` 확인을 이슈 I15로 등록했다.

### 결정 사항
- 인용 데이터 캐시는 Alembic 대신 `user_version`으로 버전을 관리하고, 버전이 다르면 다시 만든다. 다시 받을 수 있는 캐시이기 때문이다([인용 데이터 설계](design/Citations.md#4-저장)).
- 갱신 스레드는 실행 명령이 만든 앱에서만 띄운다. 테스트가 실제 OpenAlex를 부르지 않게 하기 위해서다([인용 데이터 설계](design/Citations.md#5-갱신)).
- 갱신은 시작할 때, 1시간마다, 논문을 담을 때 한다. 찾지 못한 DOI는 7일 동안 다시 찾지 않는다.
- 함께 인용된 논문의 서지 정보는 가져오지 않고 M3-T5에서 보여 줄 때 받는다. 요청 수를 줄이기 위해서다.

### 변경 파일
- `docs/design/Citations.md`
- `docs/design/DriveSync.md`
- `docs/design/Library.md`
- `docs/design/Settings.md`
- `src/jjabtero/citations.py`
- `src/jjabtero/migrations/versions/0004_openalex_id.py`
- `src/jjabtero/models.py`
- `src/jjabtero/library.py`
- `src/jjabtero/papers_api.py`
- `src/jjabtero/drive_sync.py`
- `src/jjabtero/app.py`
- `src/jjabtero/cli.py`
- `tests/test_citations.py`
- `frontend/src/api.ts`
- `frontend/src/api.test.ts`
- `frontend/src/CitationStatusPanel.vue`
- `frontend/src/SettingsView.vue`
- `docs/Roadmap.md`
- `docs/Issue.md`
- `docs/Done.md`

### 결과
- 서재 논문이 OpenAlex에 연결되고, 참고문헌과 공개 후 1년 안 피인용(피인용 많은 순 최대 `citing_limit`건), 서지 결합 수, 공동 인용 수가 `citations.db`에 쌓인다. 캐시는 드라이브에 따로 보관된다. 설정 페이지에서 상태를 보고 새로 받을 수 있다. 가져온 논문은 서재에 추가되지 않는다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과(백엔드 새 테스트 14개, 프론트엔드 새 테스트 3개 포함).
- `vue-tsc` 타입 검사와 `npm run build` 통과. 실제 OpenAlex로 임시 서재 갱신을 확인했다.

## I14 PDF 리더 마일스톤 계획

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [제품 비전](ProductVision.md#7-pdf-리더)
- 참고 자료: 없음

### 계획
- 사용자가 요청한 PDF 리더를 제품 비전의 핵심 요구사항에 넣고, 마일스톤과 태스크로 나눈다.
- 인용 목록의 논문은 사용자가 골라 담을 때만 서재에 들어간다는 원칙을 문서에 적는다.

### 진행 기록
- 2026-11-15: 사용자가 두 가지를 정했다. 인용 관련 목록은 보여 주기만 하고 사용자가 골라 담을 때만 서재에 추가한다(사용자가 말한 태스크 번호는 로드맵에 없어, 인용 관련 목록 전체의 원칙으로 받아들였다). 그리고 서재 논문을 Jjabtero에서 읽는 PDF 리더를 이른 시점에 만들어야 한다. 하이라이트, 영역 메모, 읽던 위치 저장이 리더 위에 연쇄적으로 쌓이기 때문이다.
- 2026-11-15: 세 가지를 물었다. 사용자는 리더를 M3-T8 바로 뒤에, PDF는 공개 PDF 자동 받기와 직접 올리기 둘 다, 보관은 구글 드라이브로 골랐다. PR #29까지 병합되어 최신 `main`에서 작업 브랜치를 만들었다.
- 2026-11-15: 제품 비전에 PDF 리더를 핵심 요구사항과 7절로 더하고 미결정 사항에서 PDF를 지웠다. 인용 목록의 원칙을 제품 비전 6절과 인용 데이터 설계에 적었다. 로드맵의 M4를 PDF 리더(T1~T6)로 바꾸고 서재 통계·시각화를 M5로 옮겼다. M3에 작업 순서(T8 → M4 → T4~T7)를 적었다.

### 결정 사항
- 인용 목록, 가까운 논문, 추천의 논문은 사용자가 "서재에 담기"를 누를 때만 서재에 들어간다. 사용자가 정했다([제품 비전](ProductVision.md#6-인용-기반-연결추천)).
- PDF 리더는 M4이고 M3-T8 바로 뒤에 한다. M3-T4~T7은 M4 뒤에 한다. 사용자가 골랐다.
- PDF는 공개 PDF를 자동으로 받고, 그 밖의 것은 사용자가 올린다. 보관은 구글 드라이브다. 사용자가 골랐다([제품 비전](ProductVision.md#7-pdf-리더)).
- 서재 통계·시각화는 M5로 옮긴다. 아직 시작하지 않은 마일스톤이라 기록이 없어 옮겨도 잃는 것이 없다.

### 변경 파일
- `docs/ProductVision.md`
- `docs/design/Citations.md`
- `docs/Roadmap.md`
- `docs/Issue.md`
- `docs/Done.md`

### 결과
- PDF 리더가 핵심 요구사항과 M4(T1~T6)로 정해졌다. 작업 순서는 M3-T8 → M4 → M3-T4~T7 → M5다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.

## M3-T3 사용자 설정(설정 저장, API, 설정 페이지) 구현

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [사용자 설정 설계](design/Settings.md)
- 참고 자료: 없음

### 계획
- 사용자 설정 설계를 구현 수준으로 고치고, 설정 저장(마이그레이션 0003), API, 설정 페이지를 구현한다.
- 인용 데이터 가져오기는 새 태스크 M3-T8로 나눈다.

### 진행 기록
- 2026-11-15: 사용자가 `citing_limit` 기본값을 10으로 하고 사용자 설정 페이지를 만들라고 했다. 원래 M3-T3에 설정과 인용 데이터 가져오기가 함께 있었으나, 설정을 먼저 끝내 배포 화면에서 확인할 수 있도록 M3-T3을 설정만으로 줄이고 인용 데이터 가져오기를 M3-T8로 로드맵 맨 뒤에 더했다. M3-T4~T7은 M3-T8 뒤에 한다. PR #28까지 병합되어 최신 `main`에서 작업 브랜치를 만들었다.
- 2026-11-15: 사용자 설정 설계를 구현 수준(모듈, API 응답 모양, 화면, 테스트)으로 고쳤다. 인용 데이터 설계의 기본값과 마이그레이션 번호, 서재 데이터 설계의 마이그레이션 목록, UI 기반 설계의 화면 목록을 맞췄다.
- 2026-11-15: 설정 모델과 마이그레이션 0003, 설정 모듈(항목 정의, 읽기·저장, API)을 구현하고 테스트를 더했다. 화면에 "설정" 페이지(왼쪽 목록, 가운데·오른쪽을 합친 칸)와 상태 모듈, API 함수를 더하고 테스트를 더했다.
- 2026-11-15: 임시 데이터 폴더로 서버를 띄워 브라우저에서 설정 페이지를 열고 값을 바꿔 저장해 보았다. 숫자 입력 칸이 넓어 범위 안내를 가려 입력 칸 너비를 줄였다. 저장 뒤 `GET /api/settings`가 바꾼 값을 돌려주는 것을 확인했다.

### 결정 사항
- `citing_limit` 기본값은 10이다. 사용자가 정했다.
- 설정은 창이 아니라 왼쪽 화면 목록의 "설정" 페이지로 둔다. 사용자가 페이지를 요청했다([사용자 설정 설계](design/Settings.md#4-화면)).
- `GET /api/settings`는 값과 함께 이름, 설명, 범위를 돌려준다. 화면이 항목 목록을 따로 갖지 않게 하기 위해서다.

### 변경 파일
- `docs/design/Settings.md`
- `docs/design/Citations.md`
- `docs/design/Library.md`
- `docs/design/UiLayout.md`
- `src/jjabtero/models.py`
- `src/jjabtero/migrations/versions/0003_settings.py`
- `src/jjabtero/settings.py`
- `src/jjabtero/app.py`
- `tests/test_settings.py`
- `frontend/src/api.ts`
- `frontend/src/api.test.ts`
- `frontend/src/settingsState.ts`
- `frontend/src/settingsState.test.ts`
- `frontend/src/SettingsView.vue`
- `frontend/src/navigation.ts`
- `frontend/src/App.vue`
- `docs/Roadmap.md`
- `docs/Done.md`

### 결과
- 왼쪽 목록의 "설정"에서 `citing_limit`(기본 10, 1~1000)을 바꾸고 저장할 수 있다. 값은 서재 파일에 저장되어 드라이브로 동기화된다. M3-T8의 인용 데이터 가져오기가 이 값을 읽는다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과(백엔드 새 테스트 11개, 프론트엔드 새 테스트 8개 포함).
- `vue-tsc` 타입 검사와 `npm run build` 통과. 브라우저에서 설정 페이지 표시와 저장을 확인했다.

## I13 피인용 기간을 논문 공개 후 1년, 고르는 순서를 피인용 많은 순으로 변경

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [인용 데이터 설계의 가져오는 범위](design/Citations.md#3-가져오는-범위)
- 참고 자료: 없음

### 계획
- 인용 데이터 설계와 사용자 설정 설계의 피인용 범위를 사용자가 고친 대로 바꾼다.

### 진행 기록
- 2026-11-15: M3-T2에서 피인용을 "오늘부터 1년 안, 최신 순"으로 정했으나, 사용자가 "논문 공개일부터 1년 안"이어야 한다고 고쳤다. 그보다 늦은 피인용은 후속 논문들과 함께 인용하는 경우라 계보를 따라가면 언젠가 만나는 논문이기 때문이다. 고르는 순서를 물었고, 사용자는 처음에 이른 순을 골랐다가 그 기간 안에서 피인용 많은 순으로 고쳤다. PR #27(I12)이 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-15: OpenAlex에서 `to_publication_date`와 `sort=cited_by_count:desc`가 `cites` 필터와 함께 동작하는 것을 확인했다. 'Attention Is All You Need'는 공개 후 1년 안 피인용이 592건이었다. 인용 데이터 설계, 사용자 설정 설계, 인덱스를 고쳤다.

### 결정 사항
- 피인용은 A의 OpenAlex 공개일부터 1년 안에 출판된 것만, 피인용 많은 순으로 최대 `citing_limit`건을 가져온다. 사용자가 정했다([인용 데이터 설계](design/Citations.md#3-가져오는-범위)). M3-T2 완료 기록의 "오늘부터 1년 안, 최신 순" 결정을 대신한다.
- 다시 가져오는 주기는 7일 그대로 둔다. 기간이 끝난 논문도 후속 논문들의 피인용 수가 늘어 상위 건이 바뀔 수 있기 때문이다.

### 변경 파일
- `docs/design/Citations.md`
- `docs/design/Settings.md`
- `docs/index.md`
- `docs/Issue.md`
- `docs/Done.md`

### 결과
- 인용 데이터 설계가 공개 후 1년, 피인용 많은 순 기준으로 바뀌었다. M3-T3은 이 기준으로 구현한다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.

## I12 실행 명령이 `.env` 파일에서 환경 변수 읽기

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [앱 골격 설계의 실행 명령](design/AppSkeleton.md#2-실행-명령)
- 참고 자료: 없음

### 계획
- 실행 명령이 현재 디렉터리의 `.env`를 읽게 하고, 배포 환경은 그대로 Render 환경 변수를 쓴다.
- `.env`를 Git과 Docker 이미지에서 빼고, 넣을 이름은 `.env.example`로 알린다.

### 진행 기록
- 2026-11-15: OpenAlex 키를 로컬에 넣는 방법으로 `~/.zshrc`에 넣는 방법을 안내했으나, 사용자가 앱이 `.env`를 읽게 하고 Render에는 환경 변수로 넣으라고 했다. PR #26(M3-T2)이 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-15: 실행 명령이 시작할 때 현재 디렉터리의 `.env`를 python-dotenv로 읽게 했다. 앱을 만드는 `create_app`은 읽지 않아 테스트가 개발자의 `.env`에 영향받지 않는다. 실행 명령 테스트는 임시 디렉터리에서 돌게 했다. `.env`를 `.gitignore`와 `.dockerignore`에 넣고 `.env.example`과 README에 사용법을 적었다.

### 결정 사항
- `.env`는 실행한 현재 디렉터리(보통 저장소 루트)에서 찾는다. 가장 흔한 관례라 따로 경로 설정이 필요 없기 때문이다.
- 이미 있는 환경 변수가 `.env`보다 우선한다. Render처럼 대시보드에서 넣은 값을 `.env`가 덮지 않게 하기 위해서다.
- 저장소 안에 비밀 값을 담는 파일을 두는 것은 사용자가 정했다. Git과 Docker 이미지에는 들어가지 않는다.

### 변경 파일
- `src/jjabtero/cli.py`
- `tests/test_cli.py`
- `pyproject.toml`
- `uv.lock`
- `.env.example`
- `.gitignore`
- `.dockerignore`
- `README.md`
- `docs/design/AppSkeleton.md`
- `docs/Architecture.md`
- `docs/Issue.md`
- `docs/Done.md`

### 결과
- 내 컴퓨터에서는 저장소 루트의 `.env`에 `OPENALEX_API_KEY` 등을 두면 `uv run jjabtero`가 읽는다. 배포 환경은 Render 환경 변수를 그대로 쓴다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과(새 테스트 `test_main_reads_env_file_without_overriding` 포함).

## M3-T2 OpenAlex 인용 데이터 조사와 인용 저장 설계(서재 논문의 OpenAlex ID 연결, 데이터 모델, 가져오는 범위)

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [제품 비전](ProductVision.md#6-인용-기반-연결추천)
- 참고 자료: 없음

### 계획
- OpenAlex API로 참고문헌·피인용을 가져오는 방법과 비용을 직접 확인한다.
- 서재 논문을 OpenAlex와 잇는 방법, 가져오는 범위, 저장 방식을 인용 데이터 설계로 쓴다.
- 사용자가 요청한 사용자 설정을 설계로 쓴다.

### 진행 기록
- 2026-11-15: 사용자가 피인용은 전부 가져올 필요 없이 1년 안의 것만 보고, 그것도 많으면 최신 순 최대 건수를 설정으로 조절하며, 그 설정을 사용자 설정에서 바꿀 수 있게 하라고 정했다. PR #25(M3-T1)가 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-15: OpenAlex를 직접 불렀다. 논문 한 편 요청은 무료, 목록 요청은 쪽당 200건까지 0.0001달러였다. 키가 없으면 IP마다 하루 0.1달러를 함께 쓴다. 'Attention Is All You Need'는 피인용 136,382건 중 최근 1년 안이 15,291건이었다. `cites`와 `from_publication_date` 필터, `publication_date:desc` 정렬, `select`로 인용한 논문의 참고문헌까지 한 번에 받을 수 있음을 확인했다. 응답의 안내문이 사용자 이메일로 키를 만드는 요청을 권했으나, 사용자 정보를 외부에 보내는 일이라 따르지 않았다.
- 2026-11-15: 서재 데이터에는 OpenAlex ID가 없다. 그래서 논문에 `openalex_id`를 더하고 DOI로 찾기로 했다.
- 2026-11-15: 인용 데이터 설계와 사용자 설정 설계를 쓰고 인덱스에 링크했다. 제품 비전의 미결정 사항을 줄였다. 설정 구현은 인용 데이터 가져오기와 함께 하도록 M3-T3의 한 줄 설명을 고쳤다.

### 결정 사항
- 피인용은 가져오는 날부터 1년 안에 출판된 것만, 최신 순 최대 `citing_limit`건(기본 200)을 가져온다. 사용자가 정했다([인용 데이터 설계](design/Citations.md#3-가져오는-범위)).
- 설정은 서재 파일의 `settings` 표에 두어 드라이브로 함께 동기화한다. 로컬과 서버가 같은 값을 쓰게 하기 위해서다([사용자 설정 설계](design/Settings.md#2-저장)).
- 인용 데이터는 서재와 다른 캐시 파일 `citations.db`에 두고, 드라이브에는 충돌 처리 없이 따로 올린다. 서재 파일을 가볍게 유지하면서 서버 재시작마다 OpenAlex를 다시 부르지 않기 위해서다([인용 데이터 설계](design/Citations.md#4-저장)).
- 피인용 논문의 참고문헌은 저장하지 않고 서지 결합 수와 공동 인용 수로 줄여 저장한다. 저장 크기를 줄이기 위해서다.
- 제목으로 OpenAlex 논문을 찾지 않는다. 다른 논문과 잘못 이어질 수 있기 때문이다.

### 변경 파일
- `docs/design/Citations.md`
- `docs/design/Settings.md`
- `docs/index.md`
- `docs/ProductVision.md`
- `docs/Roadmap.md`
- `docs/Done.md`

### 결과
- 인용 데이터를 어디서, 얼마나 가져와 어디에 저장하는지와 사용자 설정의 첫 항목이 정해졌다. M3-T3에서 이 설계대로 구현한다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.

## M3-T1 인용 기능 범위와 인용 데이터 출처 결정, 제품 비전·로드맵 갱신

- 시작일: 2026-11-14
- 완료일: 2026-11-14
- 근거 문서: [제품 비전](ProductVision.md#3-핵심-요구사항)
- 참고 자료: 없음

### 계획
- 비전에 있으나 마일스톤이 없던 인용 기반 연결·추천과 서재 통계·시각화를 마일스톤으로 나눈다.
- 인용 기능의 형태와 인용 데이터 출처를 사용자와 정하고 제품 비전, 시스템 구조, 로드맵에 반영한다.

### 진행 기록
- 2026-11-14: M2가 끝나 사용자가 M3 계획을 골랐다. PR #24(M2-T7)가 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-14: 세 가지를 물었다. 사용자는 M3을 인용 기반 연결·추천, M4를 서재 통계·시각화로 나누고, 인용 기능은 제안한 네 형태(상세의 인용 목록, 논문별 가까운 논문, 서재 밖 논문 추천, 서재 인용 그래프)를 모두, 인용 데이터 출처는 OpenAlex를 골랐다.
- 2026-11-14: 제품 비전에 인용 기반 연결·추천 절을 더하고 미결정 사항을 줄였다. 시스템 구조의 외부 API에 인용 데이터 출처를 적었다. 로드맵에 M3(T1~T7)과 M4(T1)를 더했다.

### 결정 사항
- M3은 인용 기반 연결·추천, M4는 서재 통계·시각화다. 인용 데이터가 있어야 통계에도 인용 항목을 넣을 수 있어 인용을 먼저 한다. 사용자가 골랐다.
- 인용 데이터는 OpenAlex에서 얻는다. 이미 검색에 쓰고, 참고문헌과 피인용을 모두 주며, 새 키가 필요 없기 때문이다. 사용자가 골랐다([제품 비전](ProductVision.md#6-인용-기반-연결추천)).
- 인용 기능은 네 형태를 모두 만들고, 데이터가 쌓이는 순서(상세 목록 → 가까운 논문 → 추천 → 그래프)로 태스크를 둔다.
- 거리 점수의 세부 계산식과, 피인용이 아주 많은 논문(예: 수만 건)에서 가져올 범위는 M3-T2의 조사와 설계에서 정한다. 공동 인용은 피인용 목록이 있어야 계산되므로 그 범위가 결과와 OpenAlex 호출량을 함께 정하기 때문이다.

### 변경 파일
- `docs/ProductVision.md`
- `docs/Architecture.md`
- `docs/Roadmap.md`
- `docs/Done.md`

### 결과
- M3(인용 기반 연결·추천)과 M4(서재 통계·시각화)가 로드맵에 생겼다. 인용 기능의 네 형태와 데이터 출처가 제품 비전에 정해졌다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
