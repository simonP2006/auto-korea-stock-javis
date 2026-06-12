"""키움 차트 API 응답 도메인 모델.

ka10080(주식분봉차트), ka10081(주식일봉차트) 응답의 가격 필드에는
상승/하락 표시용 ``+``/``-`` 부호가 prefix로 붙어 있다(예: ``"-78800"``은
78,800원의 하락 표시이지 음수가 아님). pydantic v2 ``field_validator``로
부호를 제거하고 정수로 변환한다. 누락/공백 값은 0으로 정규화한다.
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

_PRICE_FIELDS_MINUTE: Final[tuple[str, ...]] = (
    "cur_prc",
    "open_pric",
    "high_pric",
    "low_pric",
    "trde_qty",
)


class KiwoomApiError(RuntimeError):
    """키움 차트 API 호출 실패 예외.

    Attributes:
        code: 키움 ``return_code`` 또는 HTTP 상태코드 등의 식별값.
        msg: 키움 ``return_msg`` 본문 또는 진단용 메시지.
        api_id: 호출한 TR ID(예: ``ka10080``).
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
        # 키움이 드물게 "1.5" 등 소수점을 보낼 가능성에 대비한 폴백.
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


class MinuteCandle(BaseModel):
    """ka10080 ``stk_min_pole_chart_qry`` 한 건.

    Attributes:
        cntr_tm: 체결시간, ``YYYYMMDDHHMMSS`` 문자열.
        cur_prc: 종가(부호 제거된 절댓값).
        open_pric: 시가.
        high_pric: 고가.
        low_pric: 저가.
        trde_qty: 거래량(해당 분봉 체결량).
    """

    model_config = ConfigDict(extra="ignore")

    cntr_tm: str
    cur_prc: int
    open_pric: int = 0
    high_pric: int = 0
    low_pric: int = 0
    trde_qty: int = 0

    @field_validator(*_PRICE_FIELDS_MINUTE, mode="before")
    @classmethod
    def _strip(cls, v: object) -> int:
        return _strip_sign_to_int(v)
