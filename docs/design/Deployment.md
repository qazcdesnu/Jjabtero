# 배포 설계

이 문서는 Jjabtero를 Render에 배포할 때의 주소, 공개 범위, 데이터와 비밀 값, OAuth 동의 화면 게시를 정한다. 로드맵은 [M2 Render 배포](../Roadmap.md#m2-render-배포)에, 실행 형태는 [시스템 구조](../Architecture.md#1-실행-형태)에 있다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 주소와 도메인

- 앱은 Render 무료 웹 서비스 하나로 띄우고, 사용자가 가진 도메인의 서브도메인 `jjabtero.qazcde.kr`로 연결한다.
- `qazcde.kr`의 DNS는 호스팅케이알에서 관리한다. `jjabtero` 호스트에 Render 서비스 주소(`<서비스>.onrender.com`)를 가리키는 CNAME 레코드를 더하고, Render의 Custom Domains에 같은 이름을 등록해 HTTPS 인증서를 받는다.
- `qazcde.kr` 자체는 사용자의 개인 홈페이지(GitHub Pages)이며, 이 배포와 무관하다. 홈페이지에는 Jjabtero를 소개하거나 링크하지 않는다. 사용자가 원했다.

## 2. 공개 범위

- 사용자는 본인 한 명이다([제품 비전](../ProductVision.md#4-범위)).
- 로그인 없이 열리는 것은 앱 소개(`/about`)와 개인정보처리방침(`/privacy`) 두 페이지뿐이다. OAuth 동의 화면 게시에 필요하기 때문이다(4절). 두 페이지는 검색 엔진이 색인하지 않도록 `noindex`를 붙인다. 내용과 제공 방식은 [공개 페이지 설계](PublicPages.md)에 있다.
- 그 밖의 `/api`는 본인 로그인을 거쳐야 쓸 수 있다. 로그인은 구글 로그인으로 본인 계정만 허용한다([로그인 설계](Auth.md)).
- 서브도메인 이름은 공개 인증서 기록(Certificate Transparency)에 남아 숨길 수 없다. 그래서 보호는 주소를 숨기는 것이 아니라 로그인이 맡는다.

## 3. 데이터와 비밀 값

- Render 무료 플랜은 재시작·재배포·유휴 정지 때 파일 시스템이 지워진다. 서버에서는 구글 드라이브 사본을 서재의 원본으로 삼고, 서버의 SQLite 파일은 그때그때의 작업 사본이다. 서버는 시작할 때 드라이브에서 받기를 끝낸 뒤 요청을 받고, 끝날 때 대기 중인 변경을 올린다([구글 드라이브 동기화 설계의 서버 환경](DriveSync.md#8-서버-환경)).
- 비밀 값은 저장소에 두지 않는다. OAuth 클라이언트 JSON은 Render 비밀 파일로, 드라이브 갱신 토큰(`JJABTERO_GOOGLE_REFRESH_TOKEN`)과 로그인 값(`JJABTERO_ALLOWED_EMAIL`, `JJABTERO_SESSION_SECRET`)은 환경 변수로 넣는다. 갱신 토큰은 로컬에서 드라이브를 연결한 뒤 `jjabtero --print-drive-token`으로 꺼낸다. 동의 화면이 테스트 상태인 동안에는 갱신 토큰이 7일 뒤 만료되므로, M2-T7에서 프로덕션으로 게시하기 전까지는 그때마다 새 값을 넣어야 한다.
- OAuth 클라이언트에는 리디렉션 URI `https://jjabtero.qazcde.kr/api/drive/callback`과 `https://jjabtero.qazcde.kr/api/auth/callback`을 더한다. 로컬용 URI는 그대로 둔다.

## 4. OAuth 동의 화면 게시

- 동의 화면은 M2-T7까지 "테스트" 상태로 둔다. 그동안은 7일마다 드라이브를 다시 연결한다.
- M2-T7에서 홈페이지 주소 `https://jjabtero.qazcde.kr/about`, 개인정보처리방침 주소 `https://jjabtero.qazcde.kr/privacy`([공개 페이지 설계](PublicPages.md), M2-T5), 승인된 도메인 `qazcde.kr`을 브랜딩에 넣고 "프로덕션"으로 게시한다. `qazcde.kr`의 소유는 Google Search Console에서 DNS TXT 레코드로 이미 확인했다.
- 게시한 뒤 로컬에서 드라이브를 다시 연결하고, `jjabtero --print-drive-token`으로 꺼낸 새 갱신 토큰을 서버 환경 변수에 넣는다. 테스트 상태에서 받은 토큰은 게시한 뒤에도 7일이 지나면 만료되기 때문이다.

## 5. 빌드와 실행

- Docker로 빌드한다. Render의 Python 기본 환경에 Node.js가 있는지 확인할 수 없었고, Docker는 프론트엔드와 백엔드를 한 이미지에서 같은 방식으로 빌드하기 때문이다.
- [Dockerfile](../../Dockerfile)은 두 단계다.
  1. Node 이미지에서 `frontend/`를 `npm ci`, `npm run build`로 빌드한다.
  2. uv가 든 Python 3.14 이미지에서 `uv sync --locked --no-dev`로 의존성과 패키지를 설치하고, 1단계의 `frontend/dist`를 `/app/frontend/dist`로 복사한다. 패키지는 편집 가능 설치(`src/` 그대로)라 앱의 기본 화면 경로(`frontend/dist`)가 맞는다.
  - 실행 명령은 `jjabtero --host 0.0.0.0 --port $PORT`다. Render는 `PORT` 환경 변수로 받을 포트를 알려 준다.
  - [.dockerignore](../../.dockerignore)는 가상 환경, `node_modules`, 빌드 결과, 데이터베이스, 비밀 파일, `private/`를 이미지에 넣지 않는다.
- [render.yaml](../../render.yaml)은 Render Blueprint다. 서비스 하나(Docker, 무료 플랜, 싱가포르 지역), 상태 확인 경로 `/api/health`, 도메인 `jjabtero.qazcde.kr`, 환경 변수를 적는다.
  - 값을 저장소에 둘 수 있는 것: `JJABTERO_INITIAL_SYNC=wait`, `JJABTERO_SECURE_COOKIE=1`, `JJABTERO_FORWARDED_ALLOW_IPS=*`, `JJABTERO_DB`·`JJABTERO_DATA_DIR`(컨테이너 안 `/app/data`), `JJABTERO_GOOGLE_CLIENT_SECRET=/etc/secrets/google_client_secret.json`.
  - `JJABTERO_SESSION_SECRET`은 Render가 임의 값을 만든다(`generateValue`).
  - 사용자가 대시보드에서 넣는 것(`sync: false`): `JJABTERO_ALLOWED_EMAIL`, `JJABTERO_GOOGLE_REFRESH_TOKEN`, `OPENALEX_API_KEY`(선택).
  - 비밀 파일 `google_client_secret.json`은 Blueprint에 적을 수 없어 대시보드에서 올린다.
- Render 앞단이 HTTPS를 끝내고 앱에는 `http`로 넘긴다. 앱이 원래 주소를 알아야 OAuth 리디렉션 주소를 `https://jjabtero.qazcde.kr/...`로 만들 수 있으므로, 실행 명령은 `X-Forwarded-Proto`·`X-Forwarded-For`를 믿을 주소를 `JJABTERO_FORWARDED_ALLOW_IPS`로 받는다([앱 골격 설계의 실행 명령](AppSkeleton.md#2-실행-명령)). Render에서는 앱 앞의 프록시 주소가 정해져 있지 않아 `*`로 둔다. 앱은 컨테이너 안에서 Render 프록시를 거쳐서만 닿으므로 위조된 헤더를 직접 보낼 길이 없다.
