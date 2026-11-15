"""사용자 설정의 항목, 저장, API.

@doc: docs/design/Settings.md#1-항목
"""

from collections.abc import Iterator
from dataclasses import dataclass
from typing import Annotated, Any

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from jjabtero.models import Setting


@dataclass(frozen=True)
class SettingSpec:
    """설정 항목 하나의 정의. 지금 설정은 모두 정수다.

    @doc: docs/design/Settings.md#1-항목
    """

    key: str
    label: str
    description: str
    default: int
    minimum: int
    maximum: int


# @doc: docs/design/Settings.md#1-항목
SETTINGS: tuple[SettingSpec, ...] = (
    SettingSpec(
        key="citing_limit",
        label="가져올 피인용 수",
        description="서재 논문마다 가져올 피인용의 최대 건수입니다. 논문 공개 후 1년 안에 인용한 논문 가운데 피인용 많은 순으로 고릅니다.",
        default=10,
        minimum=1,
        maximum=1000,
    ),
)

_SPECS = {spec.key: spec for spec in SETTINGS}


class SettingError(ValueError):
    """모르는 키이거나 허용 범위를 벗어난 값이다.

    @doc: docs/design/Settings.md#2-저장
    """


def _valid(spec: SettingSpec, value: Any) -> bool:
    return (
        isinstance(value, int)
        and not isinstance(value, bool)
        and spec.minimum <= value <= spec.maximum
    )


def read_settings(session: Session) -> dict[str, int]:
    """모든 항목의 현재 값을 돌려준다. 저장된 값이 깨졌으면 기본값을 쓴다.

    @doc: docs/design/Settings.md#2-저장
    """
    stored = {row.key: row.value for row in session.query(Setting)}
    values: dict[str, int] = {}
    for spec in SETTINGS:
        try:
            value = int(stored[spec.key])
        except (KeyError, ValueError):
            value = spec.default
        values[spec.key] = value if _valid(spec, value) else spec.default
    return values


def update_settings(session: Session, changes: dict[str, Any]) -> dict[str, int]:
    """바꿀 항목을 모두 검사한 뒤 저장하고 현재 값을 돌려준다.

    @doc: docs/design/Settings.md#2-저장
    """
    for key, value in changes.items():
        spec = _SPECS.get(key)
        if spec is None:
            raise SettingError(f"모르는 설정입니다: {key}")
        if not _valid(spec, value):
            raise SettingError(
                f"{spec.label}은(는) {spec.minimum}~{spec.maximum} 사이의 정수여야 합니다."
            )
    for key, value in changes.items():
        session.merge(Setting(key=key, value=str(value)))
    session.commit()
    return read_settings(session)


# @doc: docs/design/Settings.md#3-api
router = APIRouter(prefix="/api")


class SettingOut(BaseModel):
    """설정 항목 하나의 응답.

    @doc: docs/design/Settings.md#3-api
    """

    key: str
    label: str
    description: str
    value: int
    default: int
    minimum: int
    maximum: int


def _session(request: Request) -> Iterator[Session]:
    with Session(request.app.state.engine) as session:
        yield session


def _out(values: dict[str, int]) -> list[SettingOut]:
    return [
        SettingOut(
            key=spec.key,
            label=spec.label,
            description=spec.description,
            value=values[spec.key],
            default=spec.default,
            minimum=spec.minimum,
            maximum=spec.maximum,
        )
        for spec in SETTINGS
    ]


@router.get("/settings")
def read_settings_api(session: Annotated[Session, Depends(_session)]) -> list[SettingOut]:
    """`GET /api/settings`를 처리한다.

    @doc: docs/design/Settings.md#3-api
    """
    return _out(read_settings(session))


@router.put("/settings")
def update_settings_api(
    request: Request,
    session: Annotated[Session, Depends(_session)],
    changes: Annotated[dict[str, Any], Body()],
) -> list[SettingOut]:
    """`PUT /api/settings`를 처리한다.

    @doc: docs/design/Settings.md#3-api
    """
    try:
        values = update_settings(session, changes)
    except SettingError as error:
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(error)) from error
    request.app.state.drive.schedule_push()
    return _out(values)
