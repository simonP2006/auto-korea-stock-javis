"""조건검색 ka10171/ka10172 도메인 모델 및 응답 파서.

- ``ConditionItem`` : ka10171 응답의 ``(seq, name)`` 한 건.
- ``MatchedStock`` : ka10172 응답 데이터(필드코드 9001/302/10/...) 한 건을
  사람이 읽기 쉬운 컬럼으로 정규화한 모델.
- ``ConditionResult`` : 단일 조건식 1회 실행 누적 결과.
- ``CompositeResult`` : 9개 조건을 순차 누적 제외(전략 A) 적용 후 통합 결과.

가격 필드 변환 규칙(문서 p.246 기준):
    - 9001 ``"A005930"``  → ``"005930"`` ('A'/'a' prefix 제거)
    - 10 (현재가) ``"000075000"``      → 75000 (양수 정수)
    - 11 (전일대비) ``"-00000100"``    → -100 (부호 정수)
    - 12 (등락율) ``"-00000130"``      → -1.30 (부호×1/100, 단위 %)
    - 13 (누적거래량) ``"010386116"``  → 10386116
    - 16/17/18 (시·고·저가)           → int

매칭이 없는 빈 행(필드 11/12/13 등이 ``"000000000"``)은 0으로 정규화한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Final

from pydantic import BaseModel, ConfigDict, Field, field_validator


class KiwoomConditionError(RuntimeError):
    """조건검색 WebSocket 호출 실패 예외.

    Attributes:
        code: 키움 ``return_code`` 또는 진단용 코드 문자열.
        msg: 키움 ``return_msg`` 또는 자체 메시지.
        api_id: 호출한 TR ID(``ka10171``/``ka10172``).
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


# ---- 파서 헬퍼 -------------------------------------------------------------

def _strip_a_prefix(code: str) -> str:
    """``"A005930"`` → ``"005930"`` (앞 'A'/'a' 한 글자만 제거)."""
    if not code:
        return ""
    if code[0] in ("A", "a"):
        return code[1:]
    return code


def _to_signed_int(value: object) -> int:
    """``"+/-NNNNNNNNN"`` / ``""`` / ``None`` → 부호 정수.

    공백·None·변환실패는 0.
    """
    if value is None or value == "":
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    if not s:
        return 0
    sign = 1
    if s[0] in ("+", "-"):
        if s[0] == "-":
            sign = -1
        s = s[1:]
    if not s:
        return 0
    try:
        return sign * int(s)
    except ValueError:
        try:
            return int(sign * float(s))
        except ValueError:
            return 0


def _to_unsigned_int(value: object) -> int:
    """부호 떼고 절댓값 정수로. 빈값/변환실패는 0."""
    return abs(_to_signed_int(value))


def _to_pct(value: object) -> float:
    """ka10172 등락율 raw → ``float`` (% 단위, 부호 보존).

    응답 필드 12 의 raw 정수는 percent×1000 스케일이다(실측 기준).
    예: ``"+00029990"`` → ``29990 / 1000`` = ``+29.99`` (한국 상한가).
    이전엔 /100으로 보정했으나 실거래 데이터에서 상한가 종목이 +299.90% 로
    찍히는 10× 오차가 발견되어 /1000으로 정정함.
    """
    n = _to_signed_int(value)
    return n / 1000.0


# ---- 모델 ------------------------------------------------------------------

class ConditionItem(BaseModel):
    """ka10171 응답의 ``(seq, name)`` 한 건."""

    model_config = ConfigDict(extra="ignore")

    seq: str
    name: str

    @field_validator("seq", "name", mode="before")
    @classmethod
    def _strip(cls, v: object) -> str:
        return "" if v is None else str(v).strip()


_PRICE_FIELDS_FILTER: Final[tuple[str, ...]] = (
    "cur_prc",
    "open_pric",
    "high_pric",
    "low_pric",
    "trde_qty",
)


class MatchedStock(BaseModel):
    """ka10172 ``data`` 의 한 건 — 정규화된 종목 행.

    Attributes:
        stk_cd: 종목코드 ('A' prefix 제거됨, 예: ``"005930"``).
        stk_nm: 종목명.
        cur_prc: 현재가 (원, 양수).
        sign: 전일대비기호 (1상한/2상승/3보합/4하한/5하락).
        pred_pre: 전일대비 (원, 부호 보존).
        flu_rt: 등락율 (%, 부호 보존, 소수점 둘째자리).
        trde_qty: 누적거래량 (주).
        open_pric: 시가, high_pric: 고가, low_pric: 저가.
    """

    model_config = ConfigDict(extra="ignore")

    stk_cd: str
    stk_nm: str = ""
    cur_prc: int = 0
    sign: str = ""
    pred_pre: int = 0
    flu_rt: float = 0.0
    trde_qty: int = 0
    open_pric: int = 0
    high_pric: int = 0
    low_pric: int = 0

    @classmethod
    def from_raw(cls, raw: dict[str, object]) -> "MatchedStock":
        """ka10172 응답 한 행(``{"9001":..., "302":..., "10":...}``) → 모델."""
        return cls(
            stk_cd=_strip_a_prefix(str(raw.get("9001", "")).strip()),
            stk_nm=str(raw.get("302", "")).strip(),
            cur_prc=_to_unsigned_int(raw.get("10")),
            sign=str(raw.get("25", "")).strip(),
            pred_pre=_to_signed_int(raw.get("11")),
            flu_rt=_to_pct(raw.get("12")),
            trde_qty=_to_unsigned_int(raw.get("13")),
            open_pric=_to_unsigned_int(raw.get("16")),
            high_pric=_to_unsigned_int(raw.get("17")),
            low_pric=_to_unsigned_int(raw.get("18")),
        )


class ConditionResult(BaseModel):
    """단일 조건식의 1회 실행 결과(원본).

    Attributes:
        seq: 조건식 일련번호.
        name: 조건식 명.
        stocks: 페이징 누적된 매칭 종목 리스트(중복 제거 전).
    """

    model_config = ConfigDict(extra="ignore")

    seq: str
    name: str
    stocks: list[MatchedStock] = Field(default_factory=list)

    @property
    def count(self) -> int:
        return len(self.stocks)


class FilteredConditionResult(BaseModel):
    """전략 A(순차 누적 제외) 적용 후의 단일 조건식 결과.

    Attributes:
        seq, name: 조건식 식별자.
        raw_count: ka10172 원본 응답의 매칭 종목 수.
        stocks: 누적 제외 후 남은 매칭 종목(이 조건이 '처음으로 잡은' 종목들).
    """

    model_config = ConfigDict(extra="ignore")

    seq: str
    name: str
    raw_count: int
    stocks: list[MatchedStock] = Field(default_factory=list)

    @property
    def kept_count(self) -> int:
        return len(self.stocks)

    @property
    def excluded_count(self) -> int:
        return self.raw_count - self.kept_count


class CompositeResult(BaseModel):
    """9개 조건식을 순차 누적 제외(전략 A) 적용 후의 통합 결과.

    Attributes:
        fetched_at: 실행 시각(UTC가 아닌 시스템 로컬).
        execution_order: 실행 순서(조건명 리스트, 길이 9).
        results: ``execution_order`` 와 동일 길이의 ``FilteredConditionResult`` 리스트.
        missing: ka10171 결과에 없어 실행 불가했던 조건명.
    """

    model_config = ConfigDict(extra="ignore")

    fetched_at: datetime
    execution_order: list[str]
    results: list[FilteredConditionResult] = Field(default_factory=list)
    missing: list[str] = Field(default_factory=list)

    @property
    def total_unique(self) -> int:
        """중복 없이 누적된 고유 종목 수."""
        return sum(r.kept_count for r in self.results)
