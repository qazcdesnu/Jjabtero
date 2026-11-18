"""Gemini API 무료 등급 모델 목록: 구글 가격표에서 읽고 매일 자정(한국 시각)에 갱신한다.

@doc: docs/design/AiChat.md#4-gemini-호출
"""

import html
import json
import re
import threading
from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import httpx2

# @doc: docs/design/AiChat.md#4-gemini-호출
PRICING_URL = "https://ai.google.dev/gemini-api/docs/pricing"
# 한국은 일광 절약 시간이 없어 고정 시차로 둔다. 서버(Render)에 시간대 자료가 없어도 같게 돈다.
# @doc: docs/design/AiChat.md#4-gemini-호출
SEOUL = timezone(timedelta(hours=9), "Asia/Seoul")
# @doc: docs/design/AiChat.md#4-gemini-호출
FREE_MODELS_FILE = "gemini_free_models.json"

_SECTION = re.compile(r"(?m)^## ")
_MODEL_ID = re.compile(r"`([a-z0-9][a-z0-9.\-]*)`")
_STANDARD_TAB = re.compile(r'\{%\s*tab title="Standard"\s*%\}(.*?)\{%\s*/tab\s*%\}', re.S)
_TABLE = re.compile(r"\{%\s*table\s*%\}(.*?)\{%\s*/table\s*%\}", re.S)


@dataclass(frozen=True)
class ModelPrice:
    """유료 등급의 100만 토큰당 가격(가격표 글 그대로). 무료 등급은 한도 안에서 무료다.

    @doc: docs/design/AiChat.md#4-gemini-호출
    """

    input: str
    output: str


def _cells(row: str) -> list[str]:
    """표 행 하나의 칸들. `* `로 시작하지 않는 줄은 앞 칸에 이어 붙인다(여러 줄 가격)."""
    cells: list[str] = []
    for line in row.splitlines():
        stripped = line.strip()
        if stripped.startswith("* "):
            cells.append(stripped[2:].strip())
        elif stripped and cells:
            cells[-1] = f"{cells[-1]}; {stripped}"
    return [re.sub(r"\s+", " ", cell).replace(".;", ";").rstrip(".").strip() for cell in cells]


def parse_free_prices(page: str) -> dict[str, ModelPrice]:
    """가격표 페이지에서 표준 요금의 입력 가격 무료 등급이 "Free of charge"인 모델과 그 유료 등급 가격을 모은다.

    @doc: docs/design/AiChat.md#4-gemini-호출
    """
    text = html.unescape(page)
    free: dict[str, ModelPrice] = {}
    for section in _SECTION.split(text)[1:]:
        head, _, rest = section.partition("{% hr /%}")
        ids = _MODEL_ID.findall(head)
        if not ids:
            continue
        tab = _STANDARD_TAB.search(rest)
        table = _TABLE.search(tab.group(1) if tab else rest)
        if table is None:
            continue
        rows = [_cells(row) for row in table.group(1).split("---")[1:]]
        prices = {cells[0].lower(): cells for cells in rows if len(cells) >= 3}
        input_row = next((cells for key, cells in prices.items() if key.startswith("input price")), None)
        if input_row is None or not input_row[1].lower().startswith("free of charge"):
            continue
        output_row = next((cells for key, cells in prices.items() if key.startswith("output price")), None)
        price = ModelPrice(input=input_row[2], output=output_row[2] if output_row else "")
        for model_id in ids:
            free[model_id] = price
    return free


def parse_free_models(page: str) -> set[str]:
    """가격표 페이지에서 무료 등급 모델 ID를 모은다.

    @doc: docs/design/AiChat.md#4-gemini-호출
    """
    return set(parse_free_prices(page))


@dataclass(frozen=True)
class FreeModels:
    """무료 등급 모델 ID와 가격표를 읽은 시각. `stale`이면 오늘 갱신에 실패해 지난 목록을 쓰는 중이다.

    @doc: docs/design/AiChat.md#4-gemini-호출
    """

    prices: dict[str, ModelPrice]
    checked_at: datetime
    stale: bool = False

    @property
    def names(self) -> frozenset[str]:
        """무료 등급 모델 ID.

        @doc: docs/design/AiChat.md#4-gemini-호출
        """
        return frozenset(self.prices)


class FreeModelsError(Exception):
    """가격표를 읽지 못했고 지난 목록도 없다.

    @doc: docs/design/AiChat.md#4-gemini-호출
    """


class FreeModelCatalog:
    """무료 등급 모델 목록을 가진다. 매일 자정에 새로 읽고, 날짜가 지난 목록은 쓸 때 다시 읽는다.

    서버가 자정에 잠들어 있었어도(무료 플랜의 유휴 정지) 다음 요청에서 그날 목록을 받게 하기 위해서다.

    @doc: docs/design/AiChat.md#4-gemini-호출
    """

    def __init__(
        self,
        http: httpx2.Client,
        cache_path: Path,
        clock: Callable[[], datetime] = lambda: datetime.now(SEOUL),
    ) -> None:
        self.http = http
        self.cache_path = cache_path
        self.clock = clock
        self._lock = threading.Lock()
        self._wake = threading.Event()
        self._stopped = False
        self._thread: threading.Thread | None = None
        self._current: FreeModels | None = self._load()

    def _load(self) -> FreeModels | None:
        try:
            data = json.loads(self.cache_path.read_text())
            # 가격이 없는 예전 파일은 버리고 다시 읽는다.
            prices = {name: ModelPrice(**price) for name, price in data["prices"].items()}
            return FreeModels(prices, datetime.fromisoformat(data["checked_at"]))
        except (OSError, ValueError, KeyError, TypeError):
            return None

    def _save(self, models: FreeModels) -> None:
        prices = {name: {"input": price.input, "output": price.output} for name, price in sorted(models.prices.items())}
        data = {"checked_at": models.checked_at.isoformat(), "prices": prices}
        self.cache_path.parent.mkdir(parents=True, exist_ok=True)
        self.cache_path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n")

    def _today(self, models: FreeModels | None) -> bool:
        if models is None or models.stale:
            return False
        return models.checked_at.astimezone(SEOUL).date() == self.clock().astimezone(SEOUL).date()

    def refresh(self) -> FreeModels:
        """가격표를 읽어 목록을 바꾼다. 실패하면 지난 목록을 `stale`로 두고, 지난 목록도 없으면 오류다.

        @doc: docs/design/AiChat.md#4-gemini-호출
        """
        with self._lock:
            try:
                response = self.http.get(PRICING_URL, follow_redirects=True, timeout=20)
                response.raise_for_status()
                prices = parse_free_prices(response.text)
                if not prices:
                    raise ValueError("가격표에서 무료 모델을 찾지 못했습니다.")
            except (httpx2.HTTPError, ValueError) as error:
                if self._current is None:
                    raise FreeModelsError("구글 가격표에서 무료 모델 목록을 가져오지 못했습니다.") from error
                self._current = FreeModels(self._current.prices, self._current.checked_at, stale=True)
                return self._current
            self._current = FreeModels(prices, self.clock())
            self._save(self._current)
            return self._current

    def current(self) -> FreeModels:
        """오늘 읽은 목록. 오늘 것이 아니면 먼저 다시 읽는다.

        @doc: docs/design/AiChat.md#4-gemini-호출
        """
        current = self._current
        if self._today(current):
            return current  # type: ignore[return-value]
        return self.refresh()

    def seconds_until_midnight(self) -> float:
        """다음 한국 자정까지 남은 초.

        @doc: docs/design/AiChat.md#4-gemini-호출
        """
        now = self.clock().astimezone(SEOUL)
        midnight = datetime.combine(now.date() + timedelta(days=1), datetime.min.time(), SEOUL)
        return max((midnight - now).total_seconds(), 1.0)

    def _loop(self) -> None:
        while not self._stopped:
            self._wake.wait(self.seconds_until_midnight())
            self._wake.clear()
            if self._stopped:
                return
            try:
                self.refresh()
            except FreeModelsError:
                pass

    def start(self) -> None:
        """자정마다 갱신하는 스레드를 띄운다.

        @doc: docs/design/AiChat.md#4-gemini-호출
        """
        if self._thread is None:
            self._thread = threading.Thread(target=self._loop, daemon=True)
            self._thread.start()

    def stop(self) -> None:
        """갱신 스레드를 멈춘다.

        @doc: docs/design/AiChat.md#4-gemini-호출
        """
        self._stopped = True
        self._wake.set()
