"""실행 명령 `jjabtero`.

@doc: docs/design/AppSkeleton.md#2-실행-명령
"""

import argparse
from collections.abc import Sequence

import uvicorn

from jjabtero.app import create_app


def main(argv: Sequence[str] | None = None) -> None:
    """앱 서버를 띄운다.

    @doc: docs/design/AppSkeleton.md#2-실행-명령
    """
    parser = argparse.ArgumentParser(prog="jjabtero", description="Jjabtero 서버를 띄운다.")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args(argv)
    uvicorn.run(create_app(), host=args.host, port=args.port)
