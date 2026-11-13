# 진행 중

이 문서는 지금 진행 중인 작업의 상세 내역을 적는다. 작업을 시작하면 항목을 추가하고, 끝나면 항목을 [완료](Done.md)로 옮기고 이 문서에서 지운다. 기록 형식과 흐름은 [작업 관리 규칙](TaskRule.md#4-작업-흐름)을 따르며, 할 일 목록은 [로드맵](Roadmap.md)과 [이슈](Issue.md)에 있다. 전체 문서 목록은 [문서 인덱스](index.md)에서 확인한다.

## M2-T6 `main` 첫 배포와 배포 확인(서비스, 비밀 파일, 도메인, 로그인·서재)

- 시작일: 2026-11-13
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

### 결정 사항
- 없음
