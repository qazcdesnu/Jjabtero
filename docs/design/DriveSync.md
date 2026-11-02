# 구글 드라이브 동기화 설계

이 문서는 서재 데이터베이스 파일을 사용자의 구글 드라이브 `Jjabtero` 폴더와 동기화하는 기능을 정한다. 로컬 데이터베이스 파일은 [서재 데이터 설계](Library.md#2-데이터베이스-파일과-연결)에 있다. 전체 문서 목록은 [문서 인덱스](../index.md)에서 확인한다.

## 1. 방식

- 로컬 SQLite 파일이 작업 사본이고, 드라이브 `Jjabtero` 폴더의 `library.db`가 다른 컴퓨터·서버와 나누는 사본이다. 파일 전체를 받고 올린다. 서재가 작아(수 MB 이하) 행 단위 동기화보다 단순하고 안전하기 때문이다.
- 드라이브 접근은 Google Drive API v3와 OAuth 2.0 웹 서버 흐름으로 한다. 범위는 `https://www.googleapis.com/auth/drive.file` 하나다. 이 범위로는 앱이 만든 파일만 볼 수 있으므로 `Jjabtero` 폴더와 `library.db`는 앱이 만든다. 사용자가 손으로 만든 같은 이름의 폴더는 보이지 않는다.
- Google 클라이언트 라이브러리를 쓰지 않고 HTTP 요청(httpx2)으로 직접 부른다. 쓰는 요청이 몇 개뿐이고, 기존 외부 API 코드와 같은 방식으로 가짜 응답을 넣어 테스트할 수 있기 때문이다.
- 동의 화면은 지금 "테스트" 게시 상태다. 테스트 상태에서는 갱신 토큰이 7일 뒤 만료되므로, 만료되면 앱이 "연결 안 됨"으로 바뀌고 다시 연결하게 한다. "프로덕션"으로 게시하면 만료가 없어지지만 홈페이지와 개인정보처리방침 주소가 필요해, M2 배포 때 `jjabtero.qazcde.kr`에 그 페이지를 만들면서 게시한다([배포 설계](Deployment.md#4-oauth-동의-화면-게시)). `drive.file`은 민감하지 않은 범위라 게시할 때 검수가 필요 없다.

## 2. 로컬 파일

동기화가 쓰는 파일은 모두 저장소 밖에 둔다. 경로는 [DrivePaths](../../src/jjabtero/drive_sync.py#DrivePaths)가 가지며, [default_drive_paths](../../src/jjabtero/drive_sync.py#default_drive_paths)가 데이터베이스 경로를 받아 기본 경로를 만든다.

| 파일 | 위치 | 내용 |
| --- | --- | --- |
| OAuth 클라이언트 | 사용자 데이터 폴더의 `google_client_secret.json` | Google Cloud 콘솔에서 받은 웹 애플리케이션 클라이언트 JSON. 환경 변수 `JJABTERO_GOOGLE_CLIENT_SECRET`로 경로를 바꿀 수 있다. |
| 토큰 | 사용자 데이터 폴더의 `google_token.json` | 접근 토큰, 갱신 토큰, 만료 시각 |
| 동기화 상태 | 데이터베이스 파일과 같은 폴더의 `drive_sync.json` | 드라이브 폴더·파일 ID, 마지막으로 맞춘 드라이브 파일의 내용 체크섬, 그때의 로컬 내용 해시, 마지막 동기화 시각 |
| 백업 | 데이터베이스 파일과 같은 폴더의 `backups/library-<시각>-<쪽>.db` | 충돌을 풀 때 버린 쪽 사본 |

- 사용자 데이터 폴더는 [user_data_dir](../../src/jjabtero/drive_sync.py#user_data_dir)가 돌려준다. 운영체제의 앱 데이터 폴더 아래 `Jjabtero`이며(macOS: `~/Library/Application Support/Jjabtero`), 환경 변수 `JJABTERO_DATA_DIR`로 바꿀 수 있다. 기본 데이터베이스도 여기 있다.
- 동기화 상태와 백업을 데이터베이스 옆에 두는 것은 상태가 그 데이터베이스에 묶이기 때문이다. `JJABTERO_DB`로 다른 데이터베이스를 쓰면 그 데이터베이스의 상태가 따로 생긴다.

- 토큰 파일과 동기화 상태 파일은 소유자만 읽고 쓰게(600) 만든다.
- 클라이언트 파일이 없으면 동기화 기능은 "설정 안 됨"이고, 나머지 앱은 그대로 동작한다.

## 3. 인증

[google_auth 모듈](../../src/jjabtero/google_auth.py)이 맡는다.

- [load_client](../../src/jjabtero/google_auth.py#load_client)는 클라이언트 JSON의 `web` 항목에서 클라이언트 ID, 보안 비밀, 인증·토큰 주소, 리디렉션 URI를 읽어 [OAuthClient](../../src/jjabtero/google_auth.py#OAuthClient)로 돌려준다. 파일이 없거나 `web` 항목이 없으면 [DriveNotConfiguredError](../../src/jjabtero/google_auth.py#DriveNotConfiguredError)다.
- [authorization_url](../../src/jjabtero/google_auth.py#authorization_url)은 동의 화면 주소를 만든다. `response_type=code`, `scope`, `access_type=offline`, `prompt=consent`(갱신 토큰을 늘 받기 위해), `state`, PKCE(`code_challenge`, `S256`)를 붙인다.
- [exchange_code](../../src/jjabtero/google_auth.py#exchange_code)는 인증 코드를 토큰으로 바꾸고, [refresh_token](../../src/jjabtero/google_auth.py#refresh_token)은 갱신 토큰으로 새 접근 토큰을 받는다. 결과는 [Token](../../src/jjabtero/google_auth.py#Token)(접근 토큰, 갱신 토큰, 만료 시각)이다. 갱신 응답에 갱신 토큰이 없으면 전의 것을 그대로 쓴다.
- [TokenStore](../../src/jjabtero/google_auth.py#TokenStore)는 토큰 파일을 읽고(`load`), 쓰고(`save`, 권한 600), 지운다(`clear`).
- [access_token](../../src/jjabtero/google_auth.py#access_token)은 저장된 토큰을 돌려주되, 만료 60초 전부터는 갱신해 저장한 뒤 돌려준다. 토큰이 없으면, 또는 갱신이 `invalid_grant`로 거부되면(연결이 해제·취소됨) 토큰을 지우고 [DriveAuthError](../../src/jjabtero/google_auth.py#DriveAuthError)를 던진다.

## 4. 드라이브 파일

[drive 모듈](../../src/jjabtero/drive.py)의 [DriveFiles](../../src/jjabtero/drive.py#DriveFiles)가 드라이브 요청을 맡는다. 요청마다 접근 토큰을 얻는 함수를 받는다.

- `find_folder(name)`, `create_folder(name)`: 내 드라이브 맨 위에서 휴지통에 없는 폴더를 찾거나 만든다.
- `find_file(folder_id, name)`: 폴더 안에서 휴지통에 없는 파일을 찾는다.
- `get(file_id)`: 파일 정보를 돌려준다. 없거나 휴지통에 있으면 `None`이다.
- `download(file_id)`: 내용을 받는다.
- `create(folder_id, name, data)`, `update(file_id, data)`: 새 파일을 올리거나 내용을 바꾼다.
- 동기화 쪽은 이 요청들을 [FilesLike](../../src/jjabtero/drive_sync.py#FilesLike) 모양으로만 쓴다. 테스트는 같은 모양의 가짜 드라이브를 넘긴다.
- 파일 정보는 [RemoteFile](../../src/jjabtero/drive.py#RemoteFile)(ID, `checksum`)이다. `checksum`은 드라이브가 파일 내용으로 계산한 `md5Checksum`이며(폴더는 빈 문자열), 드라이브 쪽 변경 감지에 쓴다. 드라이브의 `version` 필드는 내용이 그대로여도 올라가는 것을 실제 드라이브에서 확인했으므로(올린 직전 1, 잠시 뒤 2, 리비전 하나) 쓰지 않는다.
- 드라이브 API 오류(4xx, 5xx)는 [DriveApiError](../../src/jjabtero/drive.py#DriveApiError)다.

## 5. 동기화

[drive_sync 모듈](../../src/jjabtero/drive_sync.py)이 맡는다.

**로컬 사본**

- [snapshot_db](../../src/jjabtero/drive_sync.py#snapshot_db)는 SQLite 백업 기능으로 실행 중인 데이터베이스의 일관된 사본을 바이트로 만든다. 쓰는 도중의 파일을 복사하면 깨질 수 있기 때문이다.
- [restore_db](../../src/jjabtero/drive_sync.py#restore_db)는 받은 사본을 먼저 임시 파일에서 열어 무결성 검사(`PRAGMA integrity_check`)를 하고, 통과하면 SQLite 백업 기능으로 실행 중인 데이터베이스에 덮어쓴다. 그다음 스키마를 최신으로 올린다. 다른 컴퓨터의 사본이 옛 스키마일 수 있기 때문이다. 검사에 실패하면 로컬은 그대로 두고 오류를 낸다.
- [content_hash](../../src/jjabtero/drive_sync.py#content_hash)는 데이터베이스의 SQL 덤프로 만든 해시다. 파일 바이트는 내용이 같아도 달라질 수 있어, 내용이 바뀌었는지는 이 해시로 판단한다.

**판단**

[DriveSync.sync](../../src/jjabtero/drive_sync.py#DriveSync.sync)는 다음 순서로 한다. 로컬이 바뀌었는지는 지금 해시와 상태 파일의 해시가 다른지로, 드라이브가 바뀌었는지는 드라이브 파일의 `checksum`과 상태 파일의 체크섬이 다른지로 판단한다.

1. `Jjabtero` 폴더를 찾고 없으면 만든다. 상태 파일의 파일 ID로 `library.db`를 찾고, 없으면 폴더에서 이름으로 찾는다.
2. 드라이브에 파일이 없으면 로컬을 올린다.
3. 상태 파일이 없거나 다른 파일을 가리키면(이 컴퓨터에서 처음 연결): 로컬 서재가 비었으면 드라이브 것을 받고, 아니면 충돌이다.
4. 둘 다 안 바뀌었으면 아무것도 하지 않는다.
5. 로컬만 바뀌었으면 올린다. 올리기 직전에 드라이브 `checksum`을 다시 읽어 그새 바뀌었으면 충돌로 바꾼다.
6. 드라이브만 바뀌었으면 받아서 로컬에 덮어쓴다.
7. 둘 다 바뀌었으면 충돌이다. 아무것도 덮어쓰지 않는다.

받거나 올린 뒤에는 상태 파일에 그때의 드라이브 `checksum`, 로컬 해시, 시각을 적는다.

**충돌 풀기**

- [DriveSync.resolve](../../src/jjabtero/drive_sync.py#DriveSync.resolve)는 사용자가 고른 쪽으로 맞춘다. `remote`면 로컬 사본을 백업한 뒤 드라이브 것을 받고, `local`이면 드라이브 사본을 백업한 뒤 로컬을 올린다. 충돌 상태가 아닐 때 부르면 아무것도 하지 않는다.
- 충돌 동안에는 자동 올리기를 하지 않는다.

**상태와 자동 동기화**

- [DriveSync](../../src/jjabtero/drive_sync.py#DriveSync)는 앱마다 하나이며 현재 상태 [SyncStatus](../../src/jjabtero/drive_sync.py#SyncStatus)를 가진다. 상태 값은 `not_configured`(클라이언트 파일 없음), `disconnected`(토큰 없음), `idle`(맞춤), `syncing`, `conflict`, `error`다. 그 밖에 메시지, 마지막 동기화 시각, 자동 올리기 대기 여부, 로컬을 드라이브 것으로 바꾼 횟수(`data_version`)를 가진다. 화면은 `data_version`이 바뀌면 서재를 다시 불러온다.
- 동기화와 충돌 풀기는 한 번에 하나만 돈다(잠금).
- 앱이 시작되면 연결되어 있을 때 한 번 동기화한다. 기본은 백그라운드이고, 서버에서는 끝날 때까지 기다릴 수 있다(8절).
- 논문을 넣고, 고치고, 지우는 API가 성공하면 [DriveSync.schedule_push](../../src/jjabtero/drive_sync.py#DriveSync.schedule_push)를 부른다. 5초 동안 더 바뀌지 않으면 백그라운드에서 동기화한다. 연달아 고칠 때 매번 올리지 않기 위해서다.
- 인증 오류(`DriveAuthError`)가 나면 상태를 `disconnected`로 바꾸고 다시 연결하라고 알린다.

## 6. API

[drive_api 모듈](../../src/jjabtero/drive_api.py)의 라우터다. 앱은 [create_app](../../src/jjabtero/app.py#create_app)에서 `DriveSync`를 만들어 둔다. 테스트는 경로와 가짜 드라이브를 넘긴다.

- `GET /api/drive/status`: 현재 [SyncStatus](../../src/jjabtero/drive_sync.py#SyncStatus).
- `GET /api/drive/connect?return_to=<주소>`: `state`와 PKCE 값을 만들어 기억하고 동의 화면으로 보낸다(302). `return_to`는 `http://127.0.0.1`이나 `http://localhost`로 시작하는 주소만 받고, 아니면 `/`로 한다. 클라이언트 파일이 없으면 409.
- `GET /api/drive/callback?code=&state=`: 기억한 `state`와 맞으면 코드를 토큰으로 바꿔 저장하고, 동기화한 뒤 `return_to`로 보낸다(302). `state`가 맞지 않거나 `error`가 오면 400.
- 리디렉션 URI는 요청이 들어온 호스트와 포트로 만든 `<scheme>://<host>/api/drive/callback`이다. 콘솔에 등록한 주소와 같아야 한다.
- `POST /api/drive/sync`: 지금 동기화하고 상태를 돌려준다.
- `POST /api/drive/resolve`: 본문 `{"choice": "remote" | "local"}`로 충돌을 풀고 상태를 돌려준다. 다른 값은 422.
- `POST /api/drive/disconnect`: 토큰을 지우고 상태를 돌려준다. 동기화 상태 파일은 남긴다.

## 7. 화면

- API 함수는 [api 모듈](../../frontend/src/api.ts)의 [fetchDriveStatus](../../frontend/src/api.ts#fetchDriveStatus), [syncDrive](../../frontend/src/api.ts#syncDrive), [resolveDrive](../../frontend/src/api.ts#resolveDrive), [disconnectDrive](../../frontend/src/api.ts#disconnectDrive), [driveConnectUrl](../../frontend/src/api.ts#driveConnectUrl)이다.
- [driveState 모듈](../../frontend/src/driveState.ts)의 [createDriveState](../../frontend/src/driveState.ts#createDriveState)가 상태를 가진다. 처음에 상태를 불러오고, 그 뒤 10초마다(동기화 중이거나 대기 중이면 2초마다) 다시 불러온다. `data_version`이 바뀌면 받은 콜백을 부른다. [syncedLabel](../../frontend/src/driveState.ts#syncedLabel)은 맞춤 상태의 문구(마지막 동기화 시각 또는 "올릴 변경 있음")를 만든다.
- 머리줄의 `DriveStatus.vue`가 상태를 보여 준다.
  - 설정 안 됨: 회색 "드라이브 설정 안 됨"(마우스를 올리면 클라이언트 파일 위치 안내).
  - 연결 안 됨: "드라이브 연결" 단추. 누르면 `driveConnectUrl`로 이동한다.
  - 맞춤: 초록 "드라이브 동기화됨"과 마지막 시각. 대기 중이면 "올릴 변경 있음".
  - 동기화 중: 도는 아이콘.
  - 오류: 빨강 "동기화 오류"와 메시지, "다시 시도".
  - 충돌: 주황 "충돌". 누르면 대화 상자에서 "드라이브 것 쓰기"와 "이 컴퓨터 것 쓰기"를 고른다. 버린 쪽은 백업된다고 알린다.
  - 연결되어 있으면 메뉴에 "지금 동기화", "연결 해제"가 있다.
- 앱(`App.vue`)은 `data_version`이 바뀌면 서재를 다시 불러온다. 머리줄의 서버 상태는 버전만 짧게 보여 주고, 드라이브 상태를 그 왼쪽에 둔다.

## 8. 서버 환경

Render처럼 파일 시스템이 재시작마다 지워지는 서버에서도 서재와 드라이브 연결을 잃지 않게 한다([배포 설계](Deployment.md#3-데이터와-비밀-값)).

- **클라이언트 JSON**: 서버의 비밀 파일로 올리고, `JJABTERO_GOOGLE_CLIENT_SECRET`에 그 경로(Render는 `/etc/secrets/<파일 이름>`)를 적는다. 기존 경로 설정을 그대로 쓴다.
- **갱신 토큰**: 환경 변수 `JJABTERO_GOOGLE_REFRESH_TOKEN`에 넣는다. [seed_token_from_env](../../src/jjabtero/drive_sync.py#seed_token_from_env)는 앱이 만들어질 때, 토큰 파일이 없고 이 환경 변수가 있으면 갱신 토큰만 든 토큰 파일(접근 토큰은 비고 만료 시각은 0)을 만든다. 처음 요청에서 [access_token](../../src/jjabtero/google_auth.py#access_token)이 갱신한다. 토큰 파일이 이미 있으면 건드리지 않는다.
- **갱신 토큰 꺼내기**: 실행 명령 `jjabtero --print-drive-token`([main](../../src/jjabtero/cli.py#main))은 로컬 토큰 파일의 갱신 토큰을 출력하고 끝난다. 로컬에서 드라이브를 연결한 뒤 이 값을 서버 환경 변수에 한 번 넣는다. 토큰 파일이 없으면 오류로 끝난다. 갱신 토큰은 비밀이므로 사용자가 직접 실행해 복사한다.
- **시작할 때 받기**: `JJABTERO_INITIAL_SYNC=wait`이면 [create_app](../../src/jjabtero/app.py#create_app)이 앱을 돌려주기 전에 동기화를 끝낸다([DriveSync.start](../../src/jjabtero/drive_sync.py#DriveSync.start)). 서버의 새 데이터베이스는 비어 있고 동기화 상태 파일도 없으므로, 5절의 "처음 연결이고 로컬이 비었으면 받는다"가 서재를 받는다. 기다리지 않으면 받기 전의 빈 서재가 보이고, 그때 논문을 넣으면 충돌이 되기 때문이다. 이 설정이 없으면 지금처럼 백그라운드에서 동기화한다.
- **끝날 때 올리기**: 앱이 종료될 때(서버가 SIGTERM을 받아 uvicorn이 앱을 끝낼 때) [DriveSync.flush](../../src/jjabtero/drive_sync.py#DriveSync.flush)가 대기 중인 자동 올리기가 있으면 예약을 취소하고 바로 동기화한다. 고친 지 5초가 안 되어 서버가 꺼져도 변경을 잃지 않기 위해서다.
- **배포가 겹칠 때**: 배포 때 새 인스턴스와 옛 인스턴스가 60초쯤 함께 돈다. 옛 인스턴스가 그사이 올리면 새 인스턴스는 드라이브가 바뀐 것을 알아채 다음 동기화에서 받거나, 자기도 바뀌었으면 충돌로 멈춘다. 덮어쓰지 않으므로 데이터를 잃지 않는다.
- **서버에서 드라이브를 다시 연결하면**: 새 토큰은 서버의 토큰 파일에만 있어 재시작하면 사라진다. 다시 연결했으면 `--print-drive-token`과 같은 값을 서버에서 꺼낼 수 없으므로, 로컬에서 연결해 꺼낸 값을 환경 변수에 넣는다.

## 9. 테스트

실제 Google 서버는 부르지 않는다. [conftest](../../tests/conftest.py)는 모든 테스트에서 사용자 데이터 폴더, 데이터베이스, 클라이언트 경로를 임시 폴더로 바꿔, 테스트가 실제 토큰이나 서재를 건드리지 않게 한다. 가짜 드라이브와 가짜 OAuth 응답은 [fakes](../../tests/fakes.py)에 둔다.

- [test_google_auth](../../tests/test_google_auth.py): 클라이언트 읽기와 오류, 동의 주소의 인자, 코드 교환과 갱신(가짜 응답), 갱신 토큰 유지, 만료 전 갱신, `invalid_grant`로 토큰 지우기, 토큰 파일 권한.
- [test_drive](../../tests/test_drive.py): `DriveFiles`의 요청 모양(검색 질의, 업로드 형식)과 응답 해석, 오류.
- [test_drive_sync](../../tests/test_drive_sync.py): 메모리 안의 가짜 드라이브로 `sync`의 모든 경우(처음 올리기, 처음 받기, 처음 연결 충돌, 변경 없음, 로컬만, 드라이브만, 둘 다, 올리기 직전 충돌, 드라이브 파일이 지워짐), `resolve` 두 쪽과 백업, 사본 만들기·되살리기와 깨진 사본 거부, 인증 오류, 자동 올리기 대기.
- [test_drive_api](../../tests/test_drive_api.py): 상태, 연결 주소와 `return_to` 검사, 콜백의 `state` 검사, 동기화·충돌 풀기·연결 해제, 논문 API가 자동 올리기를 예약하는지.
- 서버 환경(8절): [test_drive_sync](../../tests/test_drive_sync.py)는 환경 변수로 토큰 파일 만들기, 빈 서버가 기다려 받기, 대기 중인 올리기를 바로 하기를, [test_drive_api](../../tests/test_drive_api.py)는 앱이 시작할 때 받고 끝날 때 올리기를, [test_cli](../../tests/test_cli.py)는 갱신 토큰 꺼내기와 연결이 없을 때의 오류를 확인한다.
- 프론트엔드는 드라이브 API 함수([api.test](../../frontend/src/api.test.ts))와 [driveState.test](../../frontend/src/driveState.test.ts)(불러오기, `data_version` 콜백, 동작 뒤 상태 갱신, 오류)를 확인한다.
- 실제 드라이브 확인은 사용자가 브라우저에서 연결한 뒤 한다.
