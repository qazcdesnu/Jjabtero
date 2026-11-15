# 완료 보관 M4 PDF 리더

이 문서는 닫힌 마일스톤 M4 PDF 리더의 완료 기록과, 그동안 끝난 이슈의 완료 기록을 보관한다. 기록 형식과 순서는 [완료](Done.md)와 같으며, 진행 중인 마일스톤의 기록은 완료 문서에 있다.

## M4-T6 영역 메모

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [PDF 리더 설계](design/Reader.md#6-화면)
- 참고 자료: 없음

### 계획
- 리더에서 영역을 끌어 메모를 달고, 주석 목록에서 하이라이트와 영역 메모를 모아 보고 그 자리로 가게 한다.
- M4가 닫히므로 M4 기록을 보관 문서로 옮긴다.

### 진행 기록
- 2026-11-15: M4-T5를 마치고 권장 순서대로 시작했다. PR #36(M4-T5)이 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다. 주석 표와 API는 M4-T5에서 영역 메모 종류까지 만들어 두었으므로 화면만 더했다.
- 2026-11-15: 끈 영역의 사각형과 목록 요약 함수를 더해 테스트하고, 리더에 영역 메모 모드(십자 커서, 점선 미리 보기, 메모 입력), 영역 메모 그리기, 오른쪽 주석 목록을 더했다.
- 2026-11-15: 빌드에서 템플릿의 닫는 태그가 하나 남아 실패했다. 타입 검사는 통과했으므로 빌드로 찾았다. 남은 태그를 지웠다.
- 2026-11-15: 임시 서버의 브라우저 시험에서 영역 메모 버튼과 메모 입력 칸의 접근성 이름이 같아 구분되지 않았다. 입력 칸을 "영역 메모 내용"으로 바꿨다. 그 뒤 첫 쪽 초록 부분을 끌어 메모를 저장하고, 주석 목록(하이라이트 1, 영역 메모 1)에서 영역 메모를 눌러 그 자리로 가며 창이 열리는 것을 확인했다. 영역 메모 창에서는 쓰지 않는 색 고르기를 숨겼다.
- 2026-11-15: PDF 리더 설계에 영역 메모와 주석 목록 화면, 테스트를 더했다. M4의 모든 태스크가 끝나 M4 기록과 완료 문서에 있던 이슈 기록(I12, I13, I14)을 보관 문서로 옮겼다.

### 결정 사항
- 영역 메모를 저장하면 영역 메모 모드를 끈다. 모드가 켜진 채 남으면 글 선택이 막혀 헷갈리기 때문이다.
- 영역 메모는 색을 쓰지 않는다. 노란 테두리로 하이라이트와 구분한다.

### 변경 파일
- `frontend/src/annotations.ts`
- `frontend/src/annotations.test.ts`
- `frontend/src/ReaderView.vue`
- `docs/design/Reader.md`
- `docs/Roadmap.md`
- `docs/Done.md`
- `docs/Done-M4.md`

### 결과
- 리더에서 영역을 끌어 메모를 달고, 주석 목록에서 모든 하이라이트와 영역 메모를 쪽 순서로 보고 그 자리로 갈 수 있다. M4(PDF 리더)가 닫혔다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과(프론트엔드 새 테스트 2개 포함).
- `vue-tsc` 타입 검사와 `npm run build` 통과. 브라우저에서 영역 메모와 주석 목록을 확인했다.

## M4-T5 하이라이트

- 시작일: 2026-11-15
- 완료일: 2026-11-15
- 근거 문서: [PDF 리더 설계](design/Reader.md#6-화면)
- 참고 자료: 없음

### 계획
- `annotations`(마이그레이션 0007)와 주석 API를 만들고, 리더에서 글을 골라 하이라이트하고 눌러서 색·메모를 고치거나 지우게 한다.

### 진행 기록
- 2026-11-15: M4-T4를 마치고 권장 순서대로 시작했다. PR #35(M4-T4)가 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-15: 모델, 마이그레이션 0007, 주석 API(목록, 만들기, 고치기, 지우기, 검사, 드라이브 올리기 예약)를 구현하고 테스트를 더했다. 영역 메모도 같은 표와 API를 쓰도록 종류를 함께 두었다.
- 2026-11-15: 화면에 사각형 변환·누른 위치 판정·색 함수와 주석 API 함수를 더해 테스트하고, 리더에 하이라이트 층, 선택 도구 막대, 주석 창을 더했다.
- 2026-11-15: 임시 서버의 브라우저 시험에서 첫 쪽 제목을 끌어 골라 초록 하이라이트를 만들고, 눌러서 메모를 저장한 뒤, 리더를 닫았다 다시 열어 하이라이트가 남아 있음을 확인했다. 저장된 사각형은 한 줄로 합쳐진 하나였고 콘솔 오류가 없었다.
- 2026-11-15: PDF 리더 설계와 서재 데이터 설계에 주석 데이터, API, 화면, 테스트를 더했다.

### 결정 사항
- 하이라이트는 글자 층 아래에 그리고, 누름은 클릭 위치로 판정한다. 하이라이트 위의 글도 다시 고를 수 있게 하기 위해서다([PDF 리더 설계](design/Reader.md#6-화면)).
- 색은 다섯 가지로 고정하고 이름으로 저장한다. 화면 색을 나중에 바꿔도 데이터가 그대로이기 때문이다.

### 변경 파일
- `src/jjabtero/reading.py`
- `src/jjabtero/models.py`
- `src/jjabtero/migrations/versions/0007_annotations.py`
- `src/jjabtero/app.py`
- `tests/test_reading.py`
- `frontend/src/annotations.ts`
- `frontend/src/annotations.test.ts`
- `frontend/src/api.ts`
- `frontend/src/api.test.ts`
- `frontend/src/ReaderView.vue`
- `docs/design/Reader.md`
- `docs/design/Library.md`
- `docs/Roadmap.md`
- `docs/Done.md`

### 결과
- 리더에서 글을 골라 다섯 색으로 하이라이트하고, 하이라이트에 메모를 달고, 색을 바꾸거나 지울 수 있다. 하이라이트는 서재와 함께 드라이브로 동기화된다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과(백엔드 새 테스트 8개, 프론트엔드 새 테스트 6개 포함).
- `vue-tsc` 타입 검사와 `npm run build` 통과. 브라우저에서 하이라이트, 메모, 다시 열기를 확인했다.

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
