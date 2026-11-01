# 완료

이 문서는 끝난 작업의 상세 기록이다. 최신 기록이 맨 위에 온다. 기록 형식은 [작업 관리 규칙](TaskRule.md#5-기록-형식)을 따르며, 할 일 목록은 [로드맵](Roadmap.md)과 [이슈](Issue.md)에 있다. 닫힌 마일스톤의 기록은 [작업 관리 규칙](TaskRule.md#47-완료-기록-보관)에 따라 보관 문서로 옮긴다. 보관 문서: [M0 시작](Done-M0.md), [M1 기본 서재](Done-M1.md). 전체 문서 목록은 [문서 인덱스](index.md)에서 확인한다.

## M2-T2 본인 전용 로그인 구현

- 시작일: 2026-11-01
- 완료일: 2026-11-01
- 근거 문서: [배포 설계](design/Deployment.md#2-공개-범위)
- 참고 자료: 없음

### 계획
- 로그인 설계 문서를 쓰고 인덱스에서 링크한다. 배포 설계의 미결정 사항을 고친다.
- 구글 로그인(OpenID Connect)으로 이메일을 확인하고, 허용한 계정만 들여보낸다. 로그인 상태는 서명된 세션 쿠키로 유지한다.
- 로그인이 켜져 있으면 공개 경로 밖의 `/api`를 막고, 화면은 로그인 전에 로그인 화면을 보여 준다.
- 테스트하고, 실제 구글 계정으로 확인한다.

### 진행 기록
- 2026-11-01: 사용자가 로그인 방식으로 추천안(구글 로그인으로 본인 계정만 허용)을 골랐다. 작업을 시작했다. PR #18이 병합되지 않아 `m2-t1-deploy-scope` 위에 작업 브랜치를 만들었다.
- 2026-11-01: 로그인 설계를 쓰고 인덱스에 링크했다. 배포 설계와 시스템 구조의 미결정 사항에서 로그인 방식을 지웠다. 세션용 `itsdangerous`를 더했다.
- 2026-11-01: `google_auth`의 동의 주소 만들기를 범위·오프라인·`prompt`를 받게 일반화하고, 접근 토큰만 받는 `exchange_code_for_access`를 더했다. `auth` 모듈(설정, 로그인 검사 미들웨어, `/api/auth` 라우터)을 만들고 앱과 실행 명령에 연결했다. 실행 명령은 로그인이 꺼진 채 외부 주소로 띄우면 거부한다. 기존 테스트 하나가 `0.0.0.0`으로 띄우고 있어 로그인을 켜도록 고쳤다. 백엔드 테스트는 128개다.
- 2026-11-01: 프론트엔드에 `auth.ts`(상태, 401 감시), `LoginView.vue`, 머리줄 이메일·로그아웃을 더했다. 프론트엔드 테스트는 61개다. 로그인을 켠 서버에서 로그인 전 `/api/papers`가 401이고 화면이 로그인 화면만 보이는 것을 Playwright로 확인했다.
- 2026-11-01: 포인터 검사기가 `app.py`의 로그인 설계 포인터를 받아 주는 문서 포인터가 없다고 알려, 로그인 설계에 `create_app`이 세션과 로그인 검사를 다는 내용을 적었다. `JJABTERO_SECURE_COOKIE`를 설계 표에 더했다.
- 2026-11-01: 사용자가 로그인을 켜고 실제 구글 계정으로 로그인하자 `redirect_uri_mismatch`가 났다. 서버가 보내는 주소(`http://127.0.0.1:8000/api/auth/callback`, `http://localhost:8000/api/auth/callback`)는 맞았고, 콘솔 클라이언트에 이 주소가 아직 없었다. 사용자가 두 주소를 등록한 뒤 로그인이 잘 된다고 알려 왔다.

### 결정 사항
- 로그인은 구글 로그인으로 하고, 허용한 이메일 하나만 들여보낸다. 사용자가 골랐다.
- 로그인은 `JJABTERO_ALLOWED_EMAIL`이 있을 때만 켠다. 내 컴퓨터에서 쓸 때는 지금처럼 로그인 없이 쓰기 위해서다. 대신 로그인 없이 외부 주소로 띄우는 것은 실행 명령이 막는다.
- 신원 확인은 ID 토큰 서명 검증 대신 접근 토큰으로 구글 사용자 정보 API를 불러 `email`, `email_verified`를 받는다. 서명 검증 라이브러리를 더하지 않고, 구글 서버가 직접 답한 값이기 때문이다.
- 화면 파일은 로그인 없이 주고, 서재 데이터가 나가는 `/api`만 막는다.

### 변경 파일
- `docs/design/Auth.md`
- `docs/design/Deployment.md`
- `docs/Architecture.md`
- `docs/index.md`
- `README.md`
- `pyproject.toml`
- `uv.lock`
- `src/jjabtero/auth.py`
- `src/jjabtero/google_auth.py`
- `src/jjabtero/app.py`
- `src/jjabtero/cli.py`
- `tests/conftest.py`
- `tests/test_auth.py`
- `tests/test_cli.py`
- `frontend/src/auth.ts`
- `frontend/src/auth.test.ts`
- `frontend/src/LoginView.vue`
- `frontend/src/App.vue`
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`

### 결과
- `JJABTERO_ALLOWED_EMAIL`과 `JJABTERO_SESSION_SECRET`을 넣으면 허용한 구글 계정만 로그인해 쓸 수 있다. 로그인하지 않으면 `/api`가 막히고 로그인 화면만 보인다. 넣지 않으면 지금처럼 로그인 없이 쓰며, 그 상태로 외부 주소로 띄우는 것은 거부된다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기, `uv run pytest`(테스트 128개), 프론트엔드 `npm test`(테스트 61개) 통과.
- `npm run build`: 타입 검사와 빌드 통과.
- 로그인을 켠 서버에서 로그인 전 401과 로그인 화면을 Playwright로 확인했다. 사용자가 실제 구글 계정으로 로그인이 되는 것을 확인했다. 다른 계정 거부는 자동 테스트로 확인했다.

## M2-T1 배포 범위 결정과 제품 비전·시스템 구조 갱신

- 시작일: 2026-11-01
- 완료일: 2026-11-01
- 근거 문서: [제품 비전](ProductVision.md#4-범위), [시스템 구조](Architecture.md#1-실행-형태)
- 참고 자료: 없음

### 계획
- 배포 주소, 공개 범위, 데이터와 비밀 값, 동의 화면 게시를 사용자와 정한 대로 배포 설계 문서에 적고 인덱스에서 링크한다.
- 제품 비전, 시스템 구조, 구글 드라이브 동기화 설계를 맞춘다.
- 로그인 방식, 서버 동기화, 빌드 방식은 각 태스크의 미결정 사항으로 남긴다.

### 진행 기록
- 2026-11-01: 사용자가 가진 도메인 `qazcde.kr`을 쓰기로 했다. 네임서버는 호스팅케이알이다. 동의 화면 게시용 도메인 소유 확인을 위해 사용자가 Google Search Console에 `qazcde.kr`을 도메인 속성으로 추가하고 DNS TXT 레코드를 넣었다. 네 네임서버와 구글 공용 DNS에서 레코드가 보이는 것을 확인했다.
- 2026-11-01: 사용자가 개인 홈페이지 저장소(`qazcde-homepage`, Hugo, GitHub Pages)를 `qazcde.kr`로 옮겼다. Vercel에서 도메인을 빼고 DNS를 GitHub Pages로 바꿨다. 호스팅케이알 ns1이 한동안 옛 A 레코드를 내보내 인증서 발급이 `bad_authz`로 멈췄고, 사용자가 Custom domain을 지우고 다시 저장해 인증서가 발급됐다. 홈페이지 배포가 옛 주소를 `baseURL`로 넘겨 CSS 경로가 깨져 있어, 배포 작업을 다시 실행해 고쳤다. 이 작업은 Jjabtero 저장소 밖의 일이다.
- 2026-11-01: 홈페이지에 Jjabtero 소개·개인정보처리방침 페이지를 올려 지금 프로덕션 게시하는 안과, M2 배포 때 `jjabtero.qazcde.kr`에서 앱이 직접 그 페이지를 띄우는 안을 제시했다. 사용자는 홈페이지에 소개하지 않고 `jjabtero.qazcde.kr`로 조용히 쓰기를 원해 뒤의 안을 골랐다. 그때까지는 테스트 상태로 7일마다 다시 연결한다.
- 2026-11-01: 작업을 시작했다. PR #17까지 병합되어 최신 `main`에서 작업 브랜치를 만들었다. 배포 설계를 쓰고 인덱스에 링크했으며 제품 비전, 시스템 구조, 구글 드라이브 동기화 설계를 맞췄다.
- 2026-11-01: README의 서재 데이터 문단에 M1-T9에서 고치지 못한 "구글 드라이브 동기화는 아직 없다"가 남아 있어 고쳤다.

### 결정 사항
- 배포 주소는 `jjabtero.qazcde.kr`이다. 개인 홈페이지 `qazcde.kr`에는 소개하거나 링크하지 않는다. 사용자가 골랐다.
- 로그인 없이 열리는 것은 `/about`, `/privacy` 두 페이지뿐이고 `noindex`를 붙인다. 동의 화면 게시에 필요하기 때문이다.
- 서브도메인은 공개 인증서 기록에 남아 숨길 수 없으므로, 보호는 로그인(M2-T2)이 맡는다.
- 동의 화면은 M2-T5까지 테스트 상태로 두고, 그때 `jjabtero.qazcde.kr`의 두 페이지 주소로 프로덕션 게시한다.

### 변경 파일
- `docs/design/Deployment.md`
- `docs/ProductVision.md`
- `docs/Architecture.md`
- `docs/design/DriveSync.md`
- `docs/index.md`
- `README.md`
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`

### 결과
- 배포 주소(`jjabtero.qazcde.kr`), 공개 범위(소개·개인정보처리방침만 공개, 나머지는 로그인), 서버의 데이터와 비밀 값 원칙, 동의 화면 게시 시점이 배포 설계에 정해졌다. 로그인 방식, 서버 동기화, 빌드 방식은 M2-T2~T4의 미결정 사항이다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
