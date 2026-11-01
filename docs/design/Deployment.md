# 배포 설계

이 문서는 Jjabtero를 Render에 배포할 때의 주소, 공개 범위, 데이터와 비밀 값, OAuth 동의 화면 게시를 정한다. 로드맵은 [M2 Render 배포](../Roadmap.md#m2-render-배포)에, 실행 형태는 [시스템 구조](../Architecture.md#1-실행-형태)에 있다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 주소와 도메인

- 앱은 Render 무료 웹 서비스 하나로 띄우고, 사용자가 가진 도메인의 서브도메인 `jjabtero.qazcde.kr`로 연결한다.
- `qazcde.kr`의 DNS는 호스팅케이알에서 관리한다. `jjabtero` 호스트에 Render 서비스 주소(`<서비스>.onrender.com`)를 가리키는 CNAME 레코드를 더하고, Render의 Custom Domains에 같은 이름을 등록해 HTTPS 인증서를 받는다.
- `qazcde.kr` 자체는 사용자의 개인 홈페이지(GitHub Pages)이며, 이 배포와 무관하다. 홈페이지에는 Jjabtero를 소개하거나 링크하지 않는다. 사용자가 원했다.

## 2. 공개 범위

- 사용자는 본인 한 명이다([제품 비전](../ProductVision.md#4-범위)).
- 로그인 없이 열리는 것은 앱 소개(`/about`)와 개인정보처리방침(`/privacy`) 두 페이지뿐이다. OAuth 동의 화면 게시에 필요하기 때문이다(4절). 두 페이지는 검색 엔진이 색인하지 않도록 `noindex`를 붙인다.
- 그 밖의 화면과 모든 `/api`는 본인 로그인을 거쳐야 쓸 수 있다. 로그인 방식은 M2-T2에서 정한다.
- 서브도메인 이름은 공개 인증서 기록(Certificate Transparency)에 남아 숨길 수 없다. 그래서 보호는 주소를 숨기는 것이 아니라 로그인이 맡는다.

## 3. 데이터와 비밀 값

- Render 무료 플랜은 재시작·재배포·유휴 정지 때 파일 시스템이 지워진다. 서버에서는 구글 드라이브 사본을 서재의 원본으로 삼고, 서버의 SQLite 파일은 그때그때의 작업 사본이다([구글 드라이브 동기화 설계](DriveSync.md)). 서버가 시작할 때 받고 바뀌면 올리는 방식은 M2-T3에서 정한다.
- 비밀 값(OAuth 클라이언트, 드라이브 갱신 토큰, 로그인에 쓰는 값)은 저장소에 두지 않고 Render의 환경 변수나 비밀 파일로 넣는다. 서버의 파일 시스템이 지워져도 드라이브 연결이 유지되도록 갱신 토큰을 어디에 둘지는 M2-T3에서 정한다.
- OAuth 클라이언트에는 리디렉션 URI `https://jjabtero.qazcde.kr/api/drive/callback`을 더한다. 로컬용 URI는 그대로 둔다.

## 4. OAuth 동의 화면 게시

- 동의 화면은 M2-T5까지 "테스트" 상태로 둔다. 그동안은 7일마다 드라이브를 다시 연결한다.
- M2-T5에서 홈페이지 주소 `https://jjabtero.qazcde.kr/about`, 개인정보처리방침 주소 `https://jjabtero.qazcde.kr/privacy`, 승인된 도메인 `qazcde.kr`을 브랜딩에 넣고 "프로덕션"으로 게시한다. `qazcde.kr`의 소유는 Google Search Console에서 DNS TXT 레코드로 이미 확인했다.

## 5. 미결정 사항

- 로그인 방식(예: 구글 로그인으로 본인 계정만 허용, 비밀번호). M2-T2에서 정한다.
- 서버 시작·종료 때의 동기화와 갱신 토큰 보관. M2-T3에서 정한다.
- Render 빌드 방식(Python과 Node를 함께 쓰는 기본 환경, 또는 Docker)과 실행 명령. M2-T4에서 정한다.
