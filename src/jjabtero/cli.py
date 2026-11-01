"""실행 명령 `jjabtero`.

@doc: docs/design/AppSkeleton.md#2-실행-명령
@doc: docs/design/Auth.md#2-켜고-끄기
@doc: docs/design/DriveSync.md#8-서버-환경
"""

import argparse
from collections.abc import Sequence

import uvicorn

from jjabtero.app import create_app
from jjabtero.auth import AuthConfigError, auth_settings_from_env
from jjabtero.db import default_db_path
from jjabtero.drive_sync import default_drive_paths
from jjabtero.google_auth import TokenStore

_LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")


def main(argv: Sequence[str] | None = None) -> None:
    """앱 서버를 띄운다.

    @doc: docs/design/AppSkeleton.md#2-실행-명령
    @doc: docs/design/Auth.md#2-켜고-끄기
    @doc: docs/design/DriveSync.md#8-서버-환경
    """
    parser = argparse.ArgumentParser(prog="jjabtero", description="Jjabtero 서버를 띄운다.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--print-drive-token",
        action="store_true",
        help="로컬 드라이브 연결의 갱신 토큰을 출력하고 끝낸다(서버 환경 변수에 넣을 값).",
    )
    args = parser.parse_args(argv)
    if args.print_drive_token:
        token = TokenStore(default_drive_paths(default_db_path()).token).load()
        if token is None:
            parser.error("드라이브에 연결되어 있지 않습니다. 앱에서 먼저 드라이브를 연결하세요.")
        print(token.refresh_token)
        return
    settings = auth_settings_from_env()
    if args.host not in _LOCAL_HOSTS and not settings.enabled:
        parser.error(
            f"{args.host}로 열려면 JJABTERO_ALLOWED_EMAIL과 JJABTERO_SESSION_SECRET으로 로그인을 켜야 합니다."
        )
    try:
        app = create_app(auth=settings)
    except AuthConfigError as error:
        parser.error(str(error))
    uvicorn.run(app, host=args.host, port=args.port)
