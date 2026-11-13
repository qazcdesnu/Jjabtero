# 완료

이 문서는 끝난 작업의 상세 기록이다. 최신 기록이 맨 위에 온다. 기록 형식은 [작업 관리 규칙](TaskRule.md#5-기록-형식)을 따르며, 할 일 목록은 [로드맵](Roadmap.md)과 [이슈](Issue.md)에 있다. 닫힌 마일스톤의 기록은 [작업 관리 규칙](TaskRule.md#47-완료-기록-보관)에 따라 보관 문서로 옮긴다. 보관 문서: [M0 시작](Done-M0.md), [M1 기본 서재](Done-M1.md). 전체 문서 목록은 [문서 인덱스](index.md)에서 확인한다.

## M2-T5 홈페이지·개인정보처리방침 페이지 구현

- 시작일: 2026-11-14
- 완료일: 2026-11-14
- 근거 문서: [배포 설계](design/Deployment.md#4-oauth-동의-화면-게시), [공개 페이지 설계](design/PublicPages.md)
- 참고 자료: 없음

### 계획
- 공개 페이지 설계를 쓰고 배포 설계·로그인 설계·인덱스와 잇는다.
- 서버가 `/about`, `/privacy`를 로그인 없이 `noindex`로 제공하게 구현하고 테스트한다.
- 동의 화면 게시와 드라이브 재연결은 페이지가 배포된 뒤에야 할 수 있으므로 M2-T7로 나눈다.

### 진행 기록
- 2026-11-14: 사용자가 M2-T5를 진행하기로 했다. 테스트 상태의 갱신 토큰이 7일 뒤 만료되면 Render 서버가 재시작 때 서재를 받지 못하기 때문이다. PR #22(M2-T6)가 아직 병합되지 않아 그 브랜치에서 작업 브랜치를 만들었다.
- 2026-11-14: 공개 페이지 설계를 쓰고 배포 설계, 로그인 설계, 인덱스에서 링크했다. 서버가 `/about`, `/privacy`를 완성된 HTML로 돌려주게 구현하고 테스트를 더했다. 개인정보처리방침에는 이메일은 허용 계정 확인에만 쓰고 세션 쿠키에만 담는다는 것, `drive.file`로 앱이 만든 파일만 다룬다는 것, 제한적 사용(Limited Use) 문장, 삭제 방법을 적었다.
- 2026-11-14: 동의 화면 게시는 두 페이지가 `jjabtero.qazcde.kr`에 배포된 뒤에야 할 수 있고, Render는 `main`만 배포한다. 그래서 이 태스크는 페이지 구현까지로 완료하고, 게시와 서버 드라이브 재연결은 새 태스크 M2-T7로 로드맵에 더했다. 배포 설계의 M2-T5 언급도 M2-T7로 고쳤다.

### 결정 사항
- 개인정보처리방침의 연락처는 GitHub 저장소의 이슈 페이지로 한다. 공개 페이지에 이메일을 적지 않기 위해 사용자가 골랐다.
- 두 페이지는 한국어 아래에 같은 내용을 영어로 붙인다. 구글 심사자가 읽을 수 있게 하기 위해서다([공개 페이지 설계](design/PublicPages.md#3-내용)).
- 페이지 구현과 동의 화면 게시를 나눈다. 게시는 배포된 페이지가 있어야 하고 배포는 `main` 병합 뒤에만 일어나기 때문이다.

### 변경 파일
- `docs/design/PublicPages.md`
- `docs/design/Deployment.md`
- `docs/design/Auth.md`
- `docs/index.md`
- `src/jjabtero/public_pages.py`
- `src/jjabtero/app.py`
- `tests/test_public_pages.py`
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`

### 결과
- 로그인을 켠 서버에서도 `/about`, `/privacy`가 로그인 없이 열린다. 두 페이지는 `noindex` 메타 태그와 `X-Robots-Tag` 헤더로 검색 색인을 막고, 외부 스크립트나 추적 코드가 없다. 병합되어 배포되면 M2-T7에서 동의 화면 브랜딩에 이 주소를 넣을 수 있다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과(새 테스트 `tests/test_public_pages.py` 4개 포함).

## M2-T6 `main` 첫 배포와 배포 확인(서비스, 비밀 파일, 도메인, 로그인·서재)

- 시작일: 2026-11-13
- 완료일: 2026-11-14
- 근거 문서: [배포 설계](design/Deployment.md)
- 참고 자료: 없음

### 계획
- 사용자가 Render Blueprint로 `main`을 배포하고, 비밀 파일과 환경 변수, 호스팅케이알 CNAME, OAuth 리디렉션 URI를 넣는다.
- 서비스 상태, 로그인, 드라이브에서 받은 서재, 커스텀 도메인 인증서를 확인한다.

### 진행 기록
- 2026-11-13: PR #21(M2-T4)이 병합되었다. 사용자가 Render Blueprint로 `main`을 배포했다. 서비스 주소는 `https://jjabtero.onrender.com`이다. `/api/health`가 200이고 `/api/auth/me`가 로그인 켜짐이었다.
- 2026-11-13: 사용자가 호스팅케이알에 CNAME `jjabtero` → `jjabtero.onrender.com`을 저장했다. ns1·ns3에는 보였으나 ns2·ns4와 구글 공용 DNS에는 보이지 않았다.
- 2026-11-13: 로그인을 누르자 "OAuth 클라이언트 파일이 없습니다: /etc/secrets/google_client_secret.json"이 나왔다. 비밀 파일이 없던 것이다. 사용자가 비밀 파일을 저장했고 재배포가 끝난 16:28부터 로그인 요청이 구글 로그인으로 302 이동했으며, 리디렉션 주소가 `https://jjabtero.onrender.com/api/auth/callback`으로 `https`였다. 전달 헤더 설정이 Render에서도 동작함을 확인했다.
- 2026-11-13: 작업 기록을 시작했다. 최신 `main`에서 작업 브랜치를 만들었다. CNAME은 여전히 ns2·ns4에 없다.
- 2026-11-14: CNAME이 네 네임서버와 구글·클라우드플레어 공용 DNS에 모두 퍼졌다. `https://jjabtero.qazcde.kr/api/health`가 200이고, 인증서는 `jjabtero.qazcde.kr`용(Google Trust Services, 2027-02-11 만료)으로 발급되었다. 로그인 요청의 리디렉션 주소가 `https://jjabtero.qazcde.kr/api/auth/callback`이었다.
- 2026-11-14: 사용자가 `https://jjabtero.qazcde.kr`에서 개인 Gmail로 로그인했다.
- 2026-11-14: 사용자가 서재에 'Attention Is All You Need'가 보이고 드라이브 상태가 "드라이브 동기화됨"인 것을 확인했다. 서버가 시작할 때 드라이브에서 서재를 받아 왔다.

### 결정 사항
- 없음

### 변경 파일
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`

### 결과
- `main`이 Render에 배포되어 `https://jjabtero.qazcde.kr`에서 HTTPS로 열린다. 본인 계정으로만 로그인되고, 서버가 드라이브에서 받은 서재가 보이며 동기화 상태가 정상이다. 코드 변경은 없었다.
- 동의 화면은 아직 테스트 상태라 드라이브 연결이 7일마다 만료된다(현재 연결은 2026-11-20쯤 만료). M2-T5에서 프로덕션 게시한다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기와 백엔드·프론트엔드 테스트 통과.
- 배포 확인: `dig`로 네 네임서버와 공용 DNS의 CNAME, `curl`로 `/api/health` 200과 로그인 리디렉션 주소, `openssl`로 인증서를 확인했다. 로그인, 서재, 동기화 상태는 사용자가 브라우저에서 확인했다.

## M2-T4 Render 빌드·실행 설정과 첫 배포

- 시작일: 2026-11-02
- 완료일: 2026-11-13
- 근거 문서: [배포 설계](design/Deployment.md)
- 참고 자료: 없음

### 계획
- 빌드 방식을 정하고 Docker 빌드 파일과 Render 설정 파일(`render.yaml`)을 만든다.
- Render 앞단이 HTTPS를 끝내고 앱에는 `http`로 넘기므로, 앱이 `X-Forwarded-Proto`를 믿도록 실행 명령을 고친다. 그러지 않으면 OAuth 리디렉션 주소가 `http`로 만들어진다.
- 로컬에 Docker가 없으므로 깨끗한 사본에서 같은 빌드 단계를 손으로 밟아 확인한다.
- 사용자가 할 일(Render 서비스 만들기, 비밀 파일과 환경 변수, DNS CNAME, OAuth 리디렉션 URI)을 단계별로 안내하고, 첫 배포를 확인한다.

### 진행 기록
- 2026-11-02: 작업을 시작했다. PR #20까지 병합되어 최신 `main`에서 작업 브랜치를 만들었다.
- 2026-11-02: Render 문서를 확인했다. Python 기본 환경은 `uv.lock`이 있으면 uv를 쓰지만, Node.js가 함께 있는지는 확인하지 못했다. 이 컴퓨터에는 Docker가 없다.
- 2026-11-02: Render 앞단이 HTTPS를 끝내고 `http`로 넘겨, 지금대로면 OAuth 리디렉션 주소가 `http://jjabtero.qazcde.kr/...`로 만들어지는 문제를 찾았다. 실행 명령이 uvicorn의 전달 헤더 처리를 켜고 믿을 주소를 `JJABTERO_FORWARDED_ALLOW_IPS`(기본 `127.0.0.1`)로 받게 했다. 앱 골격 설계와 배포 설계에 적었다.
- 2026-11-02: `Dockerfile`(Node로 프론트엔드 빌드, uv Python 3.14 이미지에 `uv sync --locked --no-dev`), `.dockerignore`, `render.yaml`(Docker, 무료, 싱가포르, 상태 확인 `/api/health`, 도메인, 환경 변수)을 만들었다. 시스템 구조의 디렉터리 표에 더하고 배포 설계의 미결정 사항을 빌드와 실행 절로 바꿨다. 백엔드 테스트는 134개다.
- 2026-11-02: Docker가 없어 저장소의 커밋 대상 파일을 깨끗한 폴더에 복사해 Dockerfile의 단계를 손으로 밟았다. `npm ci`·빌드, `uv sync --locked --no-dev`가 되고 개발 의존성(pytest)은 빠졌으며, 앱의 기본 화면 경로가 빌드 결과를 가리켰다. 배포와 같은 환경 변수로 띄우자 `/api/health` 200, `/` 화면, 로그인 전 `/api/papers` 401, `Host: jjabtero.qazcde.kr`·`X-Forwarded-Proto: https` 요청의 로그인 리디렉션 주소가 `https://jjabtero.qazcde.kr/api/auth/callback`, 세션 쿠키가 Secure·HttpOnly·SameSite=Lax였다.
- 2026-11-13: 사용자가 로드맵 진행 상황을 물었다. M2-T4는 사용자의 Render 작업을 기다리는 중이었고, 동의 화면이 테스트 상태라 11-01에 받은 드라이브 갱신 토큰이 만료되었을 것으로 보았다. 제품 비전의 인용 기반 연결·추천과 서재 통계·시각화가 어느 마일스톤에도 없다는 점을 알렸다.
- 2026-11-13: 사용자가 드라이브를 다시 연결하려 했으나 8000번 포트를 다른 프로젝트(`TrainingSWhigh`)의 데모 서버가 쓰고 있었다. 사용자가 그 서버를 끄고 Jjabtero를 띄워 다시 연결했다. 토큰이 15:11에 새로 받아졌고 수동 동기화가 오류 없이 맞춤 상태였다.
- 2026-11-13: 프론트엔드 빌드에서 "500kB보다 큰 묶음" 경고가 나온다고 사용자가 알렸다. 앱 코드 묶음이 약 935KB(gzip 약 206KB)이며 M1-T10부터 나던 경고다. 그동안 빌드 출력에서 오류와 성공 줄만 골라 보느라 알리지 못했다. 기능에는 영향이 없고, 서버가 응답을 압축하지 않아 배포 뒤 첫 로딩이 느릴 수 있어 이슈 I11로 등록했다.
- 2026-11-13: 사용자가 작업 브랜치 대신 `main`을 배포하고, 그러려면 `main`에 병합하는 PR을 올리는 것이 맞다고 했다. 이 태스크는 빌드·실행 설정까지로 끝내고 로컬 빌드 재현으로 확인한 상태로 완료하며, 첫 배포와 확인은 로드맵에 새 태스크 M2-T6으로 더했다.

### 결정 사항
- 빌드는 Docker로 한다. 프론트엔드(Node)와 백엔드(Python)를 한 이미지에서 같은 방식으로 빌드할 수 있고, 기본 환경의 Node 유무에 기대지 않기 때문이다.
- 앞단 프록시 헤더는 Render에서 `*`로 믿는다. Render 프록시의 주소가 정해져 있지 않고, 앱은 컨테이너 안에서 프록시를 거쳐서만 닿기 때문이다. 로컬 기본값은 `127.0.0.1`이다.
- 지역은 사용자와 가까운 싱가포르로 한다.
- 첫 배포는 이 작업 브랜치로 하고, 확인한 뒤 PR을 병합하고 Render 서비스의 브랜치를 `main`으로 바꾼다. 배포를 확인해야 작업을 완료할 수 있기 때문이다.
- 위 결정을 바꾼다. 사용자 지시대로 `main`을 배포한다. 이 태스크는 빌드·실행 설정으로 끝내고, `main` 첫 배포와 확인은 M2-T6에서 한다. 아직 확인하지 않은 배포를 이 태스크의 결과로 적지 않기 위해서다.

### 변경 파일
- `Dockerfile`
- `.dockerignore`
- `render.yaml`
- `src/jjabtero/cli.py`
- `tests/test_cli.py`
- `tests/conftest.py`
- `docs/design/Deployment.md`
- `docs/design/AppSkeleton.md`
- `docs/Architecture.md`
- `docs/Roadmap.md`
- `docs/Issue.md`
- `docs/Ongoing.md`
- `docs/Done.md`

### 결과
- 저장소에 Render용 Docker 빌드와 Blueprint 설정이 생겼다. 앱은 Render 앞단이 넘기는 `https` 정보를 믿어 OAuth 리디렉션 주소를 올바르게 만든다.
- 실제 Render 배포와 확인은 M2-T6에서 한다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기, `uv run pytest`(테스트 134개), 프론트엔드 `npm test` 통과.
- 깨끗한 사본에서 Dockerfile 단계(`npm ci`·빌드, `uv sync --locked --no-dev`)를 재현했고, 배포와 같은 환경 변수로 띄워 상태 확인, 로그인 차단, `https` 리디렉션 주소, Secure 쿠키를 확인했다. Docker 이미지 빌드 자체는 이 컴퓨터에 Docker가 없어 확인하지 못했다.

## M2-T3 서버 환경의 서재 보존(시작할 때 드라이브에서 받기, 바뀔 때 올리기) 구현

- 시작일: 2026-11-01
- 완료일: 2026-11-01
- 근거 문서: [배포 설계](design/Deployment.md#3-데이터와-비밀-값), [구글 드라이브 동기화 설계](design/DriveSync.md)
- 참고 자료: 없음

### 계획
- Render의 비밀 파일, 배포 때 종료 신호 동작을 확인하고 서버 환경 동작을 구글 드라이브 동기화 설계에 적는다.
- 갱신 토큰을 환경 변수에서 받아 토큰 파일을 만드는 기능, 시작할 때 동기화를 끝내고 요청을 받는 설정, 종료할 때 대기 중인 올리기를 바로 하는 기능, 로컬 갱신 토큰을 꺼내는 명령을 만든다.
- 테스트하고, 실제 드라이브로 "빈 서버가 시작할 때 서재를 받는" 흐름을 확인한다.

### 진행 기록
- 2026-11-01: 작업을 시작했다. PR #19까지 병합되어 최신 `main`에서 작업 브랜치를 만들었다.
- 2026-11-01: Render 문서를 확인했다. 비밀 파일은 실행 중 `/etc/secrets/<파일 이름>`에 있고 재배포에도 남는다. 배포 때는 새 인스턴스가 먼저 뜨고 트래픽이 옮겨진 뒤 60초 뒤에 옛 인스턴스에 SIGTERM을 보내며, 기본 30초 뒤 SIGKILL한다.
- 2026-11-01: 구글 드라이브 동기화 설계에 서버 환경 절(8절)을 더하고 테스트 절 번호가 9로 밀려, 코드의 `#8-테스트` 포인터를 `#9-테스트`로 고쳤다. 배포 설계와 시스템 구조의 미결정 사항을 고쳤다.
- 2026-11-01: `seed_token_from_env`, `DriveSync.start(wait)`(전의 `start_background_sync`를 바꿈), `DriveSync.flush`, 앱 종료 때 `flush`를 부르는 lifespan, `JJABTERO_INITIAL_SYNC=wait`, 실행 명령 `--print-drive-token`을 만들었다. 테스트 격리에 새 환경 변수 두 개를 더했다. 백엔드 테스트는 134개다.
- 2026-11-01: 실제 드라이브로 빈 서버를 흉내 냈다. 빈 데이터 폴더와 빈 데이터베이스, 환경 변수로 넘긴 갱신 토큰(값은 출력하지 않음), `JJABTERO_INITIAL_SYNC=wait`으로 서버를 띄우자 토큰 파일이 만들어지고, 첫 요청부터 서재(논문 1편)가 보였으며, 상태는 맞춤(`data_version` 1)이었다. 서재를 고치지 않아 드라이브는 바뀌지 않았다. 종료도 정상이었다.
- 2026-11-01: 포인터 검사기가 `test_cli.py`의 동기화 설계 포인터를 받아 주는 문서 포인터가 없다고 알려, 테스트 절에 서버 환경 테스트 목록을 적었다.

### 결정 사항
- 없음
- 위 "없음"은 시작할 때 적은 줄이다. 아래 결정을 작업 중에 내렸다.
- OAuth 클라이언트 JSON은 Render 비밀 파일로 두고 기존 경로 환경 변수로 가리킨다. 재배포에도 남기 때문이다.
- 드라이브 갱신 토큰은 환경 변수 `JJABTERO_GOOGLE_REFRESH_TOKEN`으로 넣는다. 유료 영구 디스크 없이 재시작을 견디는 가장 단순한 방법이다. 로컬에서 연결해 `--print-drive-token`으로 꺼낸다. 동의 화면이 테스트 상태인 동안은 7일마다 새 값이 필요하다.
- 서버는 `JJABTERO_INITIAL_SYNC=wait`으로 시작할 때 받기를 끝낸 뒤 요청을 받는다. 빈 서재가 보이는 동안 논문을 넣어 충돌이 나는 일을 막기 위해서다.
- 앱이 끝날 때 대기 중인 올리기를 바로 한다. 고친 직후 재배포·정지로 변경을 잃지 않기 위해서다.

### 변경 파일
- `docs/design/DriveSync.md`
- `docs/design/Deployment.md`
- `docs/Architecture.md`
- `src/jjabtero/drive_sync.py`
- `src/jjabtero/app.py`
- `src/jjabtero/cli.py`
- `tests/conftest.py`
- `tests/test_drive_sync.py`
- `tests/test_drive_api.py`
- `tests/test_cli.py`
- `tests/fakes.py`
- `tests/test_drive.py`
- `tests/test_google_auth.py`
- `frontend/src/driveState.test.ts`
- `frontend/src/api.test.ts`
- `docs/Roadmap.md`
- `docs/Ongoing.md`
- `docs/Done.md`

### 결과
- 파일 시스템이 지워지는 서버에서도 환경 변수의 갱신 토큰으로 드라이브에 연결되고, 시작할 때 서재를 받은 뒤 요청을 받으며, 끝날 때 대기 중인 변경을 올린다.

### 검증
- `uvx --from git+https://github.com/qazcdesnu/ProjInit@v0.2.0 projinit check`: 모든 검사기, `uv run pytest`(테스트 134개), 프론트엔드 `npm test` 통과.
- 실제 드라이브로 빈 서버가 시작할 때 서재를 받는 것을 확인했다.

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
