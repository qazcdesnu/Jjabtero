"""논문 제목과 참고문헌 글을 맞추기 위한 글 다듬기.

@doc: docs/design/ReaderCitations.md#4-논문-찾기
"""

import re
import unicodedata

_NOT_WORD = re.compile(r"[^0-9a-z]+")


def normalize(text: str) -> str:
    """소문자로 바꾸고 악센트를 떼고, 글자·숫자가 아닌 것을 빈칸 하나로 바꾼다.

    @doc: docs/design/ReaderCitations.md#4-논문-찾기
    @doc: docs/design/Citations.md#9-semantic-scholar-참고문헌
    """
    plain = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii").lower()
    return _NOT_WORD.sub(" ", plain).strip()
