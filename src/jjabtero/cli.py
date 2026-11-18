"""실행 명령 `jjabtero`.

@doc: docs/design/AppSkeleton.md#2-실행-명령
@doc: docs/design/Auth.md#2-켜고-끄기
@doc: docs/design/DriveSync.md#8-서버-환경
@doc: docs/design/AiChat.md#2-키-암호화
"""

import argparse
import os
from collections.abc import Sequence
from pathlib import Path

import uvicorn
from dotenv import load_dotenv

from jjabtero.ai import master_key_text
from jjabtero.app import create_app
from jjabtero.auth import AuthConfigError, auth_settings_from_env
from jjabtero.db import default_db_path
from jjabtero.drive_sync import default_drive_paths
from jjabtero.google_auth import TokenStore

_LOCAL_HOSTS = ("127.0.0.1", "localhost", "::1")
ENV_FILE = ".env"


def load_env_file() -> None:
    """현재 디렉터리의 `.env`를 환경 변수로 읽는다. 이미 있는 값은 덮어쓰지 않는다.

    @doc: docs/design/AppSkeleton.md#2-실행-명령
    """
    load_dotenv(Path.cwd() / ENV_FILE, override=False)


def main(argv: Sequence[str] | None = None) -> None:
    """앱 서버를 띄운다.

    @doc: docs/design/AppSkeleton.md#2-실행-명령
    @doc: docs/design/Auth.md#2-켜고-끄기
    @doc: docs/design/DriveSync.md#8-서버-환경
    @doc: docs/design/AiChat.md#2-키-암호화
    """
    load_env_file()
    parser = argparse.ArgumentParser(prog="jjabtero", description="Jjabtero 서버를 띄운다.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument(
        "--print-drive-token",
        action="store_true",
        help="로컬 드라이브 연결의 갱신 토큰을 출력하고 끝낸다(서버 환경 변수에 넣을 값).",
    )
    parser.add_argument(
        "--print-secret-key",
        action="store_true",
        help="API 키 암호화에 쓰는 마스터 키를 출력하고 끝낸다(서버 환경 변수 JJABTERO_SECRET_KEY에 넣을 값).",
    )
    args = parser.parse_args(argv)
    if args.print_secret_key:
        secret = master_key_text(default_db_path().parent)
        if secret is None:
            parser.error("마스터 키가 없습니다. 앱의 프로필에서 Google AI API 키를 먼저 등록하세요.")
        print(secret)
        return
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
        app = create_app(auth=settings, run_citations=True, run_model_refresh=True)
    except AuthConfigError as error:
        parser.error(str(error))
    uvicorn.run(
        app,
        host=args.host,
        port=args.port,
        proxy_headers=True,
        forwarded_allow_ips=os.environ.get("JJABTERO_FORWARDED_ALLOW_IPS", "127.0.0.1"),
    )
