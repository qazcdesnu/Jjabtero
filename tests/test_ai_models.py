"""Gemini 무료 등급 모델 목록의 가격표 읽기와 매일 갱신을 검증한다.

@doc: docs/design/AiChat.md#7-테스트
"""

from datetime import datetime, timedelta
from pathlib import Path

import httpx2
import pytest

from jjabtero.ai_models import SEOUL, FreeModelCatalog, FreeModelsError, parse_free_models
from test_ai import PRICING

LIVE_TABS = """
## Gemini 3.8 Flash {% id="gemini-3.8-flash" %}
*[`gemini-3.8-flash`](/docs/models/gemini-3.8-flash)*
{% hr /%}
{% tabs %}
  {% tab title="Batch" %}
  {% table %}
  * Feature
  * Free Tier
  * Paid Tier
  ---
  * Input price
  * Not available
  * $0.1
  {% /table %}
  {% /tab %}
  {% tab title="Standard" %}
  {% table %}
  * Feature
  * Free Tier
  * Paid Tier
  ---
  * Input price
  * Free of charge
  * $0.2
  {% /table %}
  {% /tab %}
{% /tabs %}

## Gemini 3.1 Pro Preview {% id="gemini-3.1-pro-preview" %}
*[`gemini-3.1-pro-preview`](/m) [`gemini-3.1-pro-preview-customtools`](/m)*
{% hr /%}
{% table %}
* Feature
* Free Tier
* Paid Tier
---
* Input price
* Not available
* $2
{% /table %}

## Pricing for tools
Some text without models.
"""


def test_parse_reads_standard_tab_input_price() -> None:
    """표준 탭의 입력 가격 무료 등급만 본다. 다른 탭의 값과 모델 없는 절은 무시한다.

    @doc: docs/design/AiChat.md#7-테스트
    """
    assert parse_free_models(PRICING) == {"gemini-2.5-flash"}
    assert parse_free_models(LIVE_TABS) == {"gemini-3.8-flash"}
    assert parse_free_models("<html>바뀐 페이지</html>") == set()


class Pages:
    """가격표 응답을 차례로 주는 가짜 웹. 응답이 정수면 그 상태 코드로 실패한다.

    @doc: docs/design/AiChat.md#7-테스트
    """

    def __init__(self, *pages: str | int) -> None:
        self.pages = list(pages)
        self.calls = 0

    def __call__(self, request: httpx2.Request) -> httpx2.Response:
        page = self.pages[min(self.calls, len(self.pages) - 1)]
        self.calls += 1
        if isinstance(page, int):
            return httpx2.Response(page)
        return httpx2.Response(200, text=page)


class Clock:
    """바꿀 수 있는 한국 시각.

    @doc: docs/design/AiChat.md#7-테스트
    """

    def __init__(self) -> None:
        self.now = datetime(2026, 11, 19, 23, 30, tzinfo=SEOUL)

    def __call__(self) -> datetime:
        return self.now


def _catalog(tmp_path: Path, web: Pages, clock: Clock) -> FreeModelCatalog:
    return FreeModelCatalog(httpx2.Client(transport=httpx2.MockTransport(web)), tmp_path / "free.json", clock)


def test_current_refreshes_once_per_day_and_caches(tmp_path: Path) -> None:
    """같은 날에는 다시 읽지 않고, 날짜가 바뀌면 다시 읽는다. 읽은 목록은 파일에 남아 다시 띄워도 쓴다.

    @doc: docs/design/AiChat.md#7-테스트
    """
    web, clock = Pages(PRICING, LIVE_TABS), Clock()
    catalog = _catalog(tmp_path, web, clock)
    assert catalog.current().names == {"gemini-2.5-flash"}
    clock.now += timedelta(minutes=20)
    assert catalog.current().names == {"gemini-2.5-flash"}
    assert web.calls == 1
    clock.now += timedelta(minutes=20)  # 다음 날 0시 10분
    assert catalog.current().names == {"gemini-3.8-flash"}
    assert web.calls == 2
    reopened = _catalog(tmp_path, Pages(500), clock)
    assert reopened.current().names == {"gemini-3.8-flash"}


def test_failed_refresh_keeps_last_list_as_stale(tmp_path: Path) -> None:
    """가격표를 못 읽거나 무료 모델이 하나도 없으면 지난 목록을 `stale`로 쓰고, 지난 목록도 없으면 오류다.

    @doc: docs/design/AiChat.md#7-테스트
    """
    clock = Clock()
    with pytest.raises(FreeModelsError):
        _catalog(tmp_path, Pages(503), clock).current()
    catalog = _catalog(tmp_path, Pages(PRICING, "<html/>"), clock)
    catalog.current()
    clock.now += timedelta(days=1)
    stale = catalog.current()
    assert stale.names == {"gemini-2.5-flash"}
    assert stale.stale is True


def test_seconds_until_seoul_midnight(tmp_path: Path) -> None:
    """다음 한국 자정까지 남은 초를 센다.

    @doc: docs/design/AiChat.md#7-테스트
    """
    clock = Clock()
    catalog = _catalog(tmp_path, Pages(PRICING), clock)
    assert catalog.seconds_until_midnight() == 30 * 60
    clock.now = datetime(2026, 11, 20, 0, 0, tzinfo=SEOUL)
    assert catalog.seconds_until_midnight() == 24 * 3600
