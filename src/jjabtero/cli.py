"""실행 명령 `jjabtero`.

@doc: docs/design/AppSkeleton.md#2-실행-명령
@doc: docs/design/Auth.md#2-켜고-끄기
"""

import argparse
from collections.abc import Sequence

import uvicorn

from jjabtero.app import create_app
from jjabtero.auth import AuthConfigError, auth_settings_from_env

_LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")


def main(argv: Sequence[str] | None = None) -> None:
    """앱 서버를 띄운다.

    @doc: docs/design/AppSkeleton.md#2-실행-명령
    @doc: docs/design/Auth.md#2-켜고-끄기
    """
    parser = argparse.ArgumentParser(prog="jjabtero", description="Jjabtero 서버를 띄운다.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
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
