"""키움 일봉 차트 API(ka10081) 응답 도메인 모델.

가격 필드의 ``+``/``-`` prefix(상승/하락 표시)를 제거하고 정수로 변환한다.
누락/공백은 0으로 정규화한다.
"""

from __future__ import annotations

from typing import Final

from pydantic import BaseModel, ConfigDict, field_validator

_PRICE_FIELDS_DAILY: Final[tuple[str, ...]] = (
    "cur_prc",
    "open_pric",
    "high_pric",
    "low_pric",
    "trde_qty",
    "trde_prica",
)


class KiwoomApiError(RuntimeError):
    """키움 차트 API 호출 실패 예외.

    Attributes:
        code: 키움 ``return_code`` 또는 HTTP 상태코드 등의 식별값.
        msg: 키움 ``return_msg`` 본문 또는 진단용 메시지.
        api_id: 호출한 TR ID(예: ``ka10081``).
    """

    def __init__(
        self,
        code: int | str,
        msg: str,
        *,
        api_id: str | None = None,
    ) -> None:
        self.code = code
        self.msg = msg
        self.api_id = api_id
        super().__init__(f"[{api_id}] return_code={code} return_msg={msg}")


def _strip_sign_to_int(value: object) -> int:
    """``"+78800"`` / ``"-78800"`` / ``""`` / ``None`` → ``int``.

    상승/하락 prefix(``+``/``-``)를 제거한 절댓값 정수로 반환한다.
    빈 문자열, ``None``, 변환 실패는 모두 0으로 정규화한다.
    """
    if value is None or value == "":
        return 0
    if isinstance(value, (int, float)):
        return int(abs(value))
    s = str(value).strip().lstrip("+-")
    if not s:
        return 0
    try:
        return int(s)
    except ValueError:
        return int(float(s))


class DailyCandle(BaseModel):
    """ka10081 ``stk_dt_pole_chart_qry`` 한 건.

    Attributes:
        dt: 일자, ``YYYYMMDD`` 문자열.
        cur_prc: 종가(부호 제거된 절댓값).
        open_pric: 시가.
        high_pric: 고가.
        low_pric: 저가.
        trde_qty: 거래량.
        trde_prica: 거래대금.
    """

    model_config = ConfigDict(extra="ignore")

    dt: str
    cur_prc: int
    open_pric: int = 0
    high_pric: int = 0
    low_pric: int = 0
    trde_qty: int = 0
    trde_prica: int = 0

    @field_validator(*_PRICE_FIELDS_DAILY, mode="before")
    @classmethod
    def _strip(cls, v: object) -> int:
        return _strip_sign_to_int(v)
