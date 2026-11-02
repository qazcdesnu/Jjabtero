# 진행 중

이 문서는 지금 진행 중인 작업의 상세 내역을 적는다. 작업을 시작하면 항목을 추가하고, 끝나면 항목을 [완료](Done.md)로 옮기고 이 문서에서 지운다. 기록 형식과 흐름은 [작업 관리 규칙](TaskRule.md#4-작업-흐름)을 따르며, 할 일 목록은 [로드맵](Roadmap.md)과 [이슈](Issue.md)에 있다. 전체 문서 목록은 [문서 인덱스](index.md)에서 확인한다.

## M2-T4 Render 빌드·실행 설정과 첫 배포

- 시작일: 2026-11-02
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

### 결정 사항
- 빌드는 Docker로 한다. 프론트엔드(Node)와 백엔드(Python)를 한 이미지에서 같은 방식으로 빌드할 수 있고, 기본 환경의 Node 유무에 기대지 않기 때문이다.
- 앞단 프록시 헤더는 Render에서 `*`로 믿는다. Render 프록시의 주소가 정해져 있지 않고, 앱은 컨테이너 안에서 프록시를 거쳐서만 닿기 때문이다. 로컬 기본값은 `127.0.0.1`이다.
- 지역은 사용자와 가까운 싱가포르로 한다.
- 첫 배포는 이 작업 브랜치로 하고, 확인한 뒤 PR을 병합하고 Render 서비스의 브랜치를 `main`으로 바꾼다. 배포를 확인해야 작업을 완료할 수 있기 때문이다.
