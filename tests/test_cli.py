"""실행 명령을 검증한다.

@doc: docs/design/AppSkeleton.md#4-테스트
@doc: docs/design/Auth.md#7-테스트
"""

from pathlib import Path
from typing import Any

import pytest

from jjabtero import cli


@pytest.fixture
def uvicorn_calls(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[dict[str, Any]]:
    """실제 서버 대신 uvicorn.run 호출 인자를 모은다. 데이터베이스는 임시 파일을 쓴다.

    @doc: docs/design/AppSkeleton.md#4-테스트
    """
    monkeypatch.setenv("JJABTERO_DB", str(tmp_path / "library.db"))
    calls: list[dict[str, Any]] = []
    monkeypatch.setattr(cli.uvicorn, "run", lambda app, **kwargs: calls.append(kwargs))
    return calls


def test_main_uses_local_defaults(uvicorn_calls: list[dict[str, Any]]) -> None:
    """옵션이 없으면 127.0.0.1:8000으로 띄운다.

    @doc: docs/design/AppSkeleton.md#4-테스트
    """
    cli.main([])
    assert uvicorn_calls == [{"host": "127.0.0.1", "port": 8000}]


def test_main_uses_given_host_and_port(
    uvicorn_calls: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """로그인을 켜면 지정한 외부 호스트와 포트로 띄운다.

    @doc: docs/design/AppSkeleton.md#4-테스트
    @doc: docs/design/Auth.md#7-테스트
    """
    monkeypatch.setenv("JJABTERO_ALLOWED_EMAIL", "me@example.com")
    monkeypatch.setenv("JJABTERO_SESSION_SECRET", "s" * 40)
    cli.main(["--host", "0.0.0.0", "--port", "9000"])
    assert uvicorn_calls == [{"host": "0.0.0.0", "port": 9000}]


def test_main_rejects_invalid_port(uvicorn_calls: list[dict[str, Any]]) -> None:
    """포트가 숫자가 아니면 오류로 끝나고 서버를 띄우지 않는다.

    @doc: docs/design/AppSkeleton.md#4-테스트
    """
    with pytest.raises(SystemExit):
        cli.main(["--port", "abc"])
    assert uvicorn_calls == []


def test_main_refuses_external_host_without_login(uvicorn_calls: list[dict[str, Any]]) -> None:
    """로그인이 꺼진 채 외부 주소로 띄우려 하면 오류로 끝난다.

    @doc: docs/design/Auth.md#7-테스트
    """
    with pytest.raises(SystemExit):
        cli.main(["--host", "0.0.0.0"])
    assert uvicorn_calls == []


def test_main_refuses_short_session_secret(
    uvicorn_calls: list[dict[str, Any]], monkeypatch: pytest.MonkeyPatch
) -> None:
    """로그인을 켰는데 서명 키가 짧으면 오류로 끝난다.

    @doc: docs/design/Auth.md#7-테스트
    """
    monkeypatch.setenv("JJABTERO_ALLOWED_EMAIL", "me@example.com")
    monkeypatch.setenv("JJABTERO_SESSION_SECRET", "short")
    with pytest.raises(SystemExit):
        cli.main([])
    assert uvicorn_calls == []

