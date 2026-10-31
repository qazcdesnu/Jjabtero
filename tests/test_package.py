"""패키지 골격을 검증한다.

@doc: docs/Architecture.md#5-테스트
"""

from importlib.metadata import version

import jjabtero


def test_version_matches_installed_package() -> None:
    """`__version__`이 설치된 패키지 버전과 같다.

    @doc: docs/Architecture.md#5-테스트
    """
    assert jjabtero.__version__ == version("jjabtero")


def test_version_is_not_empty() -> None:
    """`__version__`이 빈 문자열이 아니다.

    @doc: docs/Architecture.md#5-테스트
    """
    assert jjabtero.__version__
