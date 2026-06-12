"""상하한가요청 단일 파일 모듈 (키움 ka10017).

시장 전체에서 상한·상승·보합·하락·하한·전일상한·전일하한 조건에 부합하는
종목을 일괄 수집해 마크다운 리포트로 저장한다. chartDay/foreigner 와 달리
**종목별 시계열이 아닌 시점 스냅샷 종목 리스트**를 반환하는 스크리너 TR
이므로 출력 파일은 종목별 leaf 디렉터리 없이 ``reports/<YYYYMMDD>/
upperLowerPrice.md`` 에 직접 저장된다.

API 정보 (PDF p.61~63):
    - TR ID: ka10017 (상하한가요청)
    - URL: ``/api/dostk/stkinfo``
    - Body: 8개 필수 필터 (mrkt_tp, updown_tp, sort_tp, stk_cnd,
      trde_qty_tp, crd_cnd, trde_gold_tp, stex_tp)
    - 응답 리스트 키: ``updown_pric``
    - 정렬: API 의 ``sort_tp`` 결과 그대로 (시계열이 아니므로 추가 정렬 안 함)

본 모듈은 etc/foreigner.py 와 동일한 단일 파일 패턴을 사용하며, chart60/
chartDay/etc 패키지에는 의존하지 않는다. 공용 인프라
(:mod:`src.kiwoom.auth`, :mod:`src.kiwoom.config`) 만 재사용한다.

사용 예::

    import asyncio
    from src.kiwoom.upperLowerPrice.upperLowerPrice import (
        UpperLowerPriceFilters,
        get_upper_lower_price,
        save_upper_lower_price_markdown,
    )

    df = asyncio.run(get_upper_lower_price())
    path = save_upper_lower_price_markdown(df, filters=UpperLowerPriceFilters())
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Final, Literal, Protocol

import httpx
import pandas as pd
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.kiwoom.auth import KiwoomAuth
from src.kiwoom.auth import auth as default_auth
from src.kiwoom.config import KiwoomConfig
from src.kiwoom.config import config as default_config

# ─────────────────────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────────────────────

_API_ID: Final[str] = "ka10017"
_API_PATH: Final[str] = "/api/dostk/stkinfo"
_LIST_KEY: Final[str] = "updown_pric"

_PAGE_DELAY_SEC: Final[float] = 0.2
# 페이지 수 안전망. 페이지당 응답 100건이므로 50 = 5,000행 = 한국시장 전체
# 종목 수(~2,800) 의 약 2배. 무한루프 방지용이며 정상 사용에서는 도달하지 않음.
_MAX_PAGES: Final[int] = 50
_MAX_RETRY: Final[int] = 3
_REQUEST_TIMEOUT_SEC: Final[float] = 15.0
_RATE_LIMIT_CODE: Final[int] = 1700
_TOKEN_INVALID_CODE: Final[int] = 8005

# max_rows 디폴트는 ``None`` (무제한). 응답 헤더 ``cont-yn`` 이 ``N`` 이 될
# 때까지(또는 _MAX_PAGES 안전망까지) 모든 페이지를 누적한다.
_DEFAULT_MAX_ROWS: Final[int | None] = None

_DEFAULT_OUTPUT_ROOT: Final[Path] = Path("reports")
_DEFAULT_FILENAME: Final[str] = "upperLowerPrice.md"


# ─────────────────────────────────────────────────────────────────────────────
# ETF / ETN / SPAC 클라이언트측 필터 — 키워드/마커
#
# 키움 ka10017 의 ``stk_cnd="2"`` 가 HTS UI 라벨("ETF+ETN+스팩 제외")과 달리
# 실전 응답에서 ETF/ETN 종목이 그대로 포함됨이 확인됨(2026-05-10). 향후
# 키움 측 defect 가 수정될 가능성을 대비해 ``stk_cnd="2"`` 자체는 유지하고,
# 응답을 받은 뒤 종목명 기반으로 클라이언트가 직접 추가 필터링한다.
#
# ETF: 한국 ETF는 항상 ``<운용사 브랜드> <기초자산>`` 포맷 (브랜드 + 공백).
# ETN: 한국 ETN은 종목명에 반드시 "ETN" 토큰을 포함.
# SPAC: 한국 SPAC은 종목명에 반드시 "스팩" 을 포함.
# ─────────────────────────────────────────────────────────────────────────────

_ETF_BRAND_PREFIXES: Final[tuple[str, ...]] = (
    "KODEX",        # 삼성자산운용
    "TIGER",        # 미래에셋자산운용
    "PLUS",         # 한화자산운용 (구 ARIRANG 리브랜딩)
    "RISE",         # KB자산운용 (구 KBSTAR 리브랜딩)
    "KBSTAR",       # KB자산운용 (구 브랜드, 일부 잔존)
    "ARIRANG",      # 한화자산운용 (구 브랜드, 일부 잔존)
    "ACE",          # 한국투자신탁운용 (구 KINDEX)
    "KINDEX",       # 한국투자신탁운용 (구 브랜드)
    "SOL",          # 신한자산운용
    "HANARO",       # NH-Amundi
    "KOSEF",        # 키움투자자산운용
    "KIWOOM",       # 키움투자자산운용 (영문 브랜드)
    "KoAct",        # 한국투자신탁운용 액티브 ETF 브랜드
    "TIMEFOLIO",    # 타임폴리오자산운용
    "BNK",          # BNK자산운용
    "WOORI",        # 우리자산운용
    "WON",          # 우리자산운용 (구 브랜드)
    "FOCUS",        # 포커스자산운용
    "TREX",         # 유리자산운용
    "마이다스",      # 마이다스에셋자산운용
    "파워",          # KB(구 파워)
)

# 종목명 어디든 등장하면 ETF/ETN 등 금융상품으로 판정하는 키워드.
# brand prefix 매칭에서 누락된 발행사·신규 운용사·합성형 등을 보완 캡쳐.
_ETF_KEYWORD_MARKERS: Final[tuple[str, ...]] = (
    "채권",          # 채권형 ETF/ETN
    "혼합",          # 혼합형 ETF/ETN
    "액티브",        # 액티브 ETF
    "ITF",          # 인덱스 트래킹 펀드 마커
    "배당",          # 배당 ETF
    "합성",          # 합성 ETF (총수익스왑 기반)
    "나스닥",        # 나스닥 추종 ETF
    "다우존스",      # 다우존스 추종 ETF
)

_ETN_MARKERS: Final[tuple[str, ...]] = ("ETN",)
_SPAC_MARKERS: Final[tuple[str, ...]] = ("스팩",)


# ─────────────────────────────────────────────────────────────────────────────
# 한글 라벨 (리포트 헤더에서 코드값을 사람이 읽을 수 있는 라벨로 변환)
# ─────────────────────────────────────────────────────────────────────────────

_LABEL_MRKT: Final[dict[str, str]] = {
    "000": "전체",
    "001": "코스피",
    "101": "코스닥",
}

_LABEL_UPDOWN: Final[dict[str, str]] = {
    "1": "상한",
    "2": "상승",
    "3": "보합",
    "4": "하한",
    "5": "하락",
    "6": "전일상한",
    "7": "전일하한",
}

_LABEL_SORT: Final[dict[str, str]] = {
    "1": "종목코드순",
    "2": "연속횟수순(상위100개)",
    "3": "등락률순",
}

_LABEL_STK_CND: Final[dict[str, str]] = {
    "0": "전체조회",
    "1": "관리종목제외",
    "2": "ETF+ETN+스팩 제외",  # 공식 PDF 누락 — HTS 캡처로 확인
    "3": "우선주제외",
    "4": "우선주+관리종목제외",
    "5": "증100제외",
    "6": "증100만 보기",
    "7": "증40만 보기",
    "8": "증30만 보기",
    "9": "증20만 보기",
    "10": "우선주+관리종목+환기종목제외",
}

_LABEL_TRDE_QTY: Final[dict[str, str]] = {
    "00000": "전체조회",
    "00010": "만주이상",
    "00050": "5만주이상",
    "00100": "10만주이상",
    "00150": "15만주이상",
    "00200": "20만주이상",
    "00300": "30만주이상",
    "00500": "50만주이상",
    "01000": "백만주이상",
}

_LABEL_CRD_CND: Final[dict[str, str]] = {
    "0": "전체조회",
    "1": "신용융자A군",
    "2": "신용융자B군",
    "3": "신용융자C군",
    "4": "신용융자D군",
    "7": "신용융자E군",
    "9": "신용융자전체",
}

_LABEL_TRDE_GOLD: Final[dict[str, str]] = {
    "0": "전체조회",
    "1": "1천원미만",
    "2": "1천원~2천원",
    "3": "2천원~3천원",
    "4": "5천원~1만원",
    "5": "1만원이상",
    "8": "1천원이상",
}

_LABEL_STEX: Final[dict[str, str]] = {
    "1": "KRX",
    "2": "NXT",
    "3": "통합",
}


# ─────────────────────────────────────────────────────────────────────────────
# 예외
# ─────────────────────────────────────────────────────────────────────────────


class KiwoomApiError(RuntimeError):
    """ka10017 호출 실패 예외.

    Attributes:
        code: 키움 ``return_code`` 또는 HTTP 상태코드 등의 식별값.
        msg: 키움 ``return_msg`` 본문 또는 진단용 메시지.
        api_id: 호출한 TR ID (기본 ``ka10017``).
    """

    def __init__(
        self,
        code: int | str,
        msg: str,
        *,
        api_id: str | None = _API_ID,
    ) -> None:
        self.code = code
        self.msg = msg
        self.api_id = api_id
        super().__init__(f"[{api_id}] return_code={code} return_msg={msg}")


# ─────────────────────────────────────────────────────────────────────────────
# 값 변환 헬퍼
# ─────────────────────────────────────────────────────────────────────────────


def _strip_sign_to_int(value: object) -> int:
    """``"+235500"`` / ``"-10060"`` / ``""`` / ``None`` → ``int`` (절댓값).

    가격·호가처럼 ``+``/``-`` prefix 가 상승/하락 표시 indicator인 필드용
    (실제 부호는 ``pred_pre_sig`` 등 별도 필드가 표현). 누락/공백/변환실패는
    0으로 정규화.
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


def _to_signed_int(value: object) -> int:
    """``"+54200"`` → 54200, ``"-1790"`` → -1790 (부호 보존).

    전일대비 절대값처럼 부호 자체가 의미를 갖는 정수 필드용. 누락/공백/
    변환실패는 0으로 정규화.
    """
    if value is None or value == "":
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    if not s:
        return 0
    try:
        return int(s)
    except ValueError:
        return int(float(s))


def _to_signed_float(value: object) -> float:
    """``"+29.90"`` → 29.90, ``"-15.11"`` → -15.11 (부호 보존).

    등락률처럼 부호 자체가 가격 변화 방향을 나타내는 백분율 필드용.
    누락/공백/변환실패는 0.0 으로 정규화.
    """
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip()
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


def _to_int(value: object) -> int:
    """단순 정수 변환. 부호/prefix 없는 거래량·횟수·잔량 필드용."""
    if value is None or value == "":
        return 0
    if isinstance(value, (int, float)):
        return int(value)
    s = str(value).strip()
    if not s:
        return 0
    try:
        return int(s)
    except ValueError:
        return int(float(s))


# ─────────────────────────────────────────────────────────────────────────────
# 모델
# ─────────────────────────────────────────────────────────────────────────────


class UpperLowerPriceRow(BaseModel):
    """ka10017 ``updown_pric`` 한 행.

    Attributes:
        stk_cd: 종목코드.
        stk_nm: 종목명.
        stk_infr: 종목정보(관리/투자주의 등 표시 — API 응답 그대로 보존).
        cur_prc: 현재가(원, 절댓값. ``+`` prefix 는 상승 indicator).
        pred_pre_sig: 전일대비기호(API 코드 그대로 — 표시 매핑은 호출측 책임).
        pred_pre: 전일대비(원, 부호 보존 — +상승 / −하락).
        flu_rt: 등락률(%, 부호 보존 — +상승 / −하락).
        trde_qty: 거래량(주).
        pred_trde_qty: 전일거래량(주).
        sel_req: 매도잔량(주).
        sel_bid: 매도호가(원, 절댓값).
        buy_bid: 매수호가(원, 절댓값).
        buy_req: 매수잔량(주).
        cnt: 연속횟수 (``sort_tp=2`` 일 때 의미가 큼).
    """

    model_config = ConfigDict(extra="ignore")

    stk_cd: str
    stk_nm: str = ""
    stk_infr: str = ""
    cur_prc: int = 0
    pred_pre_sig: str = ""
    pred_pre: int = 0
    flu_rt: float = 0.0
    trde_qty: int = 0
    pred_trde_qty: int = 0
    sel_req: int = 0
    sel_bid: int = 0
    buy_bid: int = 0
    buy_req: int = 0
    cnt: int = 0

    @field_validator("cur_prc", "sel_bid", "buy_bid", mode="before")
    @classmethod
    def _abs_int(cls, v: object) -> int:
        return _strip_sign_to_int(v)

    @field_validator("pred_pre", mode="before")
    @classmethod
    def _signed_int(cls, v: object) -> int:
        return _to_signed_int(v)

    @field_validator("flu_rt", mode="before")
    @classmethod
    def _signed_float(cls, v: object) -> float:
        return _to_signed_float(v)

    @field_validator(
        "trde_qty",
        "pred_trde_qty",
        "sel_req",
        "buy_req",
        "cnt",
        mode="before",
    )
    @classmethod
    def _plain_int(cls, v: object) -> int:
        return _to_int(v)


# ─────────────────────────────────────────────────────────────────────────────
# 종목명 기반 분류·필터 (ETF / ETN / SPAC)
# ─────────────────────────────────────────────────────────────────────────────


def is_etf(stk_nm: str) -> bool:
    """종목명이 ETF 명명규칙을 따르면 True.

    두 가지 검출 규칙을 OR 결합한다:

    1. **브랜드 prefix + 공백** — ``KODEX 200``/``TIGER 화장품``/
       ``ACE MSCI인도네시아(합성)`` 처럼 ``_ETF_BRAND_PREFIXES`` 에 등록된
       운용사 브랜드 + 공백으로 시작.
    2. **상품 키워드 substring** — 종목명 아무 위치에 ``_ETF_KEYWORD_MARKERS``
       (채권/혼합/액티브/ITF/배당/합성/나스닥/다우존스) 중 하나가 포함.
       brand prefix 에 등록되지 않은 신규 발행사·합성형·외국지수 추종 ETF 를
       보완 캡쳐.

    Args:
        stk_nm: 종목명 문자열.

    Returns:
        둘 중 하나라도 매칭되면 True. 빈 문자열은 False.
    """
    if not stk_nm:
        return False
    for prefix in _ETF_BRAND_PREFIXES:
        if stk_nm.startswith(prefix + " "):
            return True
    for kw in _ETF_KEYWORD_MARKERS:
        if kw in stk_nm:
            return True
    return False


def is_etn(stk_nm: str) -> bool:
    """종목명에 ``ETN`` 토큰이 포함되면 True.

    한국 상장 ETN 은 모두 종목명에 ``ETN`` 을 포함한다(예:
    ``메리츠 인버스 2X WTI원유 선물 ETN(H)``). 일반 회사명에 ``ETN``
    부분문자열이 들어갈 가능성은 사실상 없어 안전한 마커.
    """
    if not stk_nm:
        return False
    return any(m in stk_nm for m in _ETN_MARKERS)


def is_spac(stk_nm: str) -> bool:
    """종목명에 ``스팩`` 이 포함되면 True.

    한국 상장 SPAC 은 모두 종목명에 ``스팩`` 을 포함한다(예:
    ``신한스팩7호``, ``하나금융스팩28호``).
    """
    if not stk_nm:
        return False
    return any(m in stk_nm for m in _SPAC_MARKERS)


def filter_out_etf_etn_spac(df: pd.DataFrame) -> pd.DataFrame:
    """ETF/ETN/SPAC 종목 행을 제거한 새 DataFrame 반환.

    Args:
        df: ``stk_nm`` 컬럼을 포함하는 DataFrame.

    Returns:
        제외 후 행만 남긴 DataFrame. ``attrs`` 는 원본에서 복제되며 추가로
        ``filter_stats`` 키에 다음 카운트가 기록된다::

            {
                "input_rows": 원본 행 수,
                "etf_excluded": ETF 로 판정된 행 수,
                "etn_excluded": ETN 으로 판정된 행 수,
                "spac_excluded": SPAC 으로 판정된 행 수,
                "kept_rows": 최종 잔존 행 수,
            }

        한 행이 여러 카테고리에 동시 매칭되면 카테고리별 카운트는 중복
        반영되지만 행 자체는 한 번만 제외된다.
    """
    if df.empty:
        out = df.copy()
        out.attrs = dict(df.attrs)
        out.attrs["filter_stats"] = {
            "input_rows": 0,
            "etf_excluded": 0,
            "etn_excluded": 0,
            "spac_excluded": 0,
            "kept_rows": 0,
        }
        return out

    nm = df["stk_nm"].fillna("")
    is_e = nm.apply(is_etf)
    is_n = nm.apply(is_etn)
    is_s = nm.apply(is_spac)
    keep_mask = ~(is_e | is_n | is_s)
    out = df.loc[keep_mask].reset_index(drop=True)
    out.attrs = dict(df.attrs)
    out.attrs["filter_stats"] = {
        "input_rows": int(len(df)),
        "etf_excluded": int(is_e.sum()),
        "etn_excluded": int(is_n.sum()),
        "spac_excluded": int(is_s.sum()),
        "kept_rows": int(len(out)),
    }
    return out


# ─────────────────────────────────────────────────────────────────────────────
# 필터 (요청 body)
# ─────────────────────────────────────────────────────────────────────────────


class UpperLowerPriceFilters(BaseModel):
    """ka10017 요청 body 필터.

    기본값은 사용자의 HTS [0162] 상한가/하한가 (통합) 화면에서 자주 쓰는
    프리셋: 시장 전체 / 상승 / 등락률순 / ETF+ETN+스팩 제외 / 만주이상 /
    1천원이상 / 통합 거래소.

    Attributes:
        mrkt_tp: 시장구분 — ``"000"``/``"001"``/``"101"``.
        updown_tp: 상하한구분 — ``"1"``~``"7"``.
        sort_tp: 정렬구분 — ``"1"``/``"2"``/``"3"``.
        stk_cnd: 종목조건 — 문자열 코드. ``"2"``(ETF+ETN+스팩 제외) 는 공식
            PDF 에 누락되어 있으나 HTS 와 동일하게 동작.
        trde_qty_tp: 거래량구분 — ``"00000"``~``"01000"``.
        crd_cnd: 신용조건 — ``"0"``~``"9"``.
        trde_gold_tp: 매매금구분 — ``"0"``/``"1"``..``"5"``/``"8"``.
        stex_tp: 거래소구분 — ``"1"``(KRX)/``"2"``(NXT)/``"3"``(통합).
    """

    mrkt_tp: Literal["000", "001", "101"] = "000"
    updown_tp: Literal["1", "2", "3", "4", "5", "6", "7"] = "2"
    sort_tp: Literal["1", "2", "3"] = "3"
    stk_cnd: str = Field(default="2")
    trde_qty_tp: str = Field(default="00010")
    crd_cnd: str = Field(default="0")
    trde_gold_tp: str = Field(default="8")
    stex_tp: Literal["1", "2", "3"] = "3"

    def to_body(self) -> dict[str, str]:
        """API 요청 body dict 로 변환.

        Returns:
            ka10017 가 요구하는 8개 키-값 dict (모두 문자열).
        """
        return self.model_dump()


# ─────────────────────────────────────────────────────────────────────────────
# HTTP 클라이언트 (ka10017 전용)
# ─────────────────────────────────────────────────────────────────────────────


class _TokenProvider(Protocol):
    async def get_access_token(self, *, force_refresh: bool = False) -> str: ...
    def invalidate(self) -> None: ...


class _ConfigLike(Protocol):
    @property
    def base_url(self) -> str: ...


class UpperLowerPriceClient:
    """ka10017 (상하한가요청) 호출 전용 클라이언트.

    chart60/chartDay/foreigner 와 동일한 페이징·재시도 패턴을 사용한다.

    오류 코드 자동 처리:
        - ``1700`` (요청수 초과): 지수 백오프 후 재시도
        - ``8005`` (토큰 무효): 토큰 캐시 무효화 후 재발급하여 재시도

    Attributes:
        auth: 토큰 제공자(기본: 모듈 싱글톤 ``KiwoomAuth``).
        config: 환경설정(기본: 모듈 싱글톤 ``KiwoomConfig``).
    """

    def __init__(
        self,
        auth: _TokenProvider | KiwoomAuth | None = None,
        config: _ConfigLike | KiwoomConfig | None = None,
        *,
        transport: httpx.AsyncBaseTransport | None = None,
    ) -> None:
        self.auth: _TokenProvider = auth or default_auth
        self.config: _ConfigLike = config or default_config
        self._transport = transport

    async def post(
        self,
        body: dict[str, Any],
        *,
        cont_yn: str | None = None,
        next_key: str | None = None,
    ) -> tuple[dict[str, Any], str | None, str | None]:
        """단발 POST. 반환: ``(json_body, cont-yn, next-key)``.

        Raises:
            KiwoomApiError: HTTP 비정상, JSON 파싱 실패, 또는 ``return_code != 0``
                (1700/8005 자동 재시도 후에도 실패한 경우 포함).
        """
        url = f"{self.config.base_url}{_API_PATH}"

        for attempt in range(_MAX_RETRY):
            token = await self.auth.get_access_token()
            headers = {
                "authorization": f"Bearer {token}",
                "api-id": _API_ID,
                "Content-Type": "application/json;charset=UTF-8",
            }
            if cont_yn:
                headers["cont-yn"] = cont_yn
            if next_key:
                headers["next-key"] = next_key

            try:
                async with httpx.AsyncClient(
                    timeout=_REQUEST_TIMEOUT_SEC,
                    transport=self._transport,
                ) as client:
                    resp = await client.post(url, json=body, headers=headers)
            except httpx.HTTPError as exc:
                raise KiwoomApiError(
                    code="HTTP", msg=f"transport error: {exc}",
                ) from exc

            if resp.status_code != 200:
                raise KiwoomApiError(
                    code=resp.status_code,
                    msg=f"non-200 body={resp.text[:300]}",
                )

            try:
                data: dict[str, Any] = resp.json()
            except ValueError as exc:
                raise KiwoomApiError(
                    code="JSON",
                    msg=f"응답이 JSON이 아님: {resp.text[:300]}",
                ) from exc

            rc = data.get("return_code")

            if rc in (None, 0):
                return (
                    data,
                    resp.headers.get("cont-yn"),
                    resp.headers.get("next-key"),
                )

            if rc == _RATE_LIMIT_CODE and attempt < _MAX_RETRY - 1:
                wait = 2**attempt
                logger.warning(
                    "rate limit (1700) attempt={n}/{m} sleep={s}s",
                    n=attempt + 1, m=_MAX_RETRY, s=wait,
                )
                await asyncio.sleep(wait)
                continue

            if rc == _TOKEN_INVALID_CODE and attempt < _MAX_RETRY - 1:
                logger.warning("token invalid (8005), 토큰 재발급 후 재시도")
                self.auth.invalidate()
                continue

            raise KiwoomApiError(code=rc, msg=str(data.get("return_msg", "")))

        raise KiwoomApiError(code="RETRY", msg=f"재시도 {_MAX_RETRY}회 초과")

    async def fetch_rows(
        self,
        body: dict[str, Any],
        *,
        max_rows: int | None = _DEFAULT_MAX_ROWS,
    ) -> list[dict[str, Any]]:
        """``cont-yn`` 헤더 페이징으로 ``updown_pric`` 누적 조회.

        Args:
            body: 8개 필터 dict (UpperLowerPriceFilters.to_body() 결과).
            max_rows: 누적 행수가 이 값 이상이면 조기 종료. ``None`` 이면
                상한 없음(기본) — 응답 헤더 ``cont-yn`` 이 ``N`` 이 될 때까지
                또는 ``_MAX_PAGES`` 안전망까지 모든 페이지를 누적한다.

        Returns:
            누적된 raw dict 리스트(원본 응답 그대로, 모델 검증 전).
        """
        rows: list[dict[str, Any]] = []
        cont_yn: str | None = None
        next_key: str | None = None

        for page in range(_MAX_PAGES):
            data, cont_yn, next_key = await self.post(
                body, cont_yn=cont_yn, next_key=next_key,
            )
            chunk = data.get(_LIST_KEY) or []
            if not isinstance(chunk, list):
                raise KiwoomApiError(
                    code="SHAPE",
                    msg=f"{_LIST_KEY} 가 리스트가 아님: {type(chunk).__name__}",
                )
            rows.extend(chunk)
            logger.debug(
                "ka10017 page={p} got={g} total={t} cont-yn={c}",
                p=page + 1, g=len(chunk), t=len(rows), c=cont_yn,
            )

            if max_rows is not None and len(rows) >= max_rows:
                break
            if cont_yn != "Y" or not next_key:
                break

            await asyncio.sleep(_PAGE_DELAY_SEC)
        else:
            logger.warning(
                "ka10017 _MAX_PAGES={m} 안전망 도달 — 응답이 더 있을 수 있음 "
                "(누적 {t}건, 마지막 cont-yn={c})",
                m=_MAX_PAGES, t=len(rows), c=cont_yn,
            )

        return rows


# ─────────────────────────────────────────────────────────────────────────────
# 파사드
# ─────────────────────────────────────────────────────────────────────────────


async def get_upper_lower_price(
    filters: UpperLowerPriceFilters | None = None,
    *,
    max_rows: int | None = _DEFAULT_MAX_ROWS,
    exclude_etf_etn_spac: bool = True,
    client: UpperLowerPriceClient | None = None,
) -> pd.DataFrame:
    """ka10017 호출하여 조건 부합 종목 리스트를 DataFrame 으로 반환.

    Args:
        filters: 8개 필터. ``None`` 이면 :class:`UpperLowerPriceFilters` 기본값.
        max_rows: 응답 누적 상한. ``None``(기본) 이면 상한 없음 —
            ``cont-yn=N`` 또는 ``_MAX_PAGES`` 안전망까지 전체 수집.
            정수 지정 시 그 값에서 조기 종료.
        exclude_etf_etn_spac: True 이면 응답을 받은 뒤 종목명 기반으로
            ETF/ETN/SPAC 행을 추가 제외한다(기본 True). 키움 ka10017 의
            ``stk_cnd="2"`` 가 실전에서 ETF/ETN 을 거르지 못하는 문제를
            클라이언트측에서 보완하기 위한 안전장치.
        client: 주입용 :class:`UpperLowerPriceClient` (테스트/모킹용).

    Returns:
        DataFrame. 컬럼: ``stk_cd``, ``stk_nm``, ``stk_infr``, ``cur_prc``,
        ``pred_pre_sig``, ``pred_pre``, ``flu_rt``, ``trde_qty``,
        ``pred_trde_qty``, ``sel_req``, ``sel_bid``, ``buy_bid``,
        ``buy_req``, ``cnt``.

        정렬은 API 의 ``sort_tp`` 결과 그대로 보존(시계열 아님).
        DataFrame ``attrs["filters"]`` 에 사용된 필터 dict 가 보존되며,
        ``exclude_etf_etn_spac=True`` 일 때 ``attrs["filter_stats"]`` 에
        제외 카운트가 기록된다.
    """
    filters = filters or UpperLowerPriceFilters()
    client = client or UpperLowerPriceClient()

    body = filters.to_body()
    raw = await client.fetch_rows(body, max_rows=max_rows)
    logger.info(
        "ka10017 mrkt={m} updown={u} sort={s} fetched={n}",
        m=filters.mrkt_tp, u=filters.updown_tp, s=filters.sort_tp, n=len(raw),
    )

    if not raw:
        empty = pd.DataFrame()
        empty.attrs["filters"] = body
        if exclude_etf_etn_spac:
            empty = filter_out_etf_etn_spac(empty)
            empty.attrs["filters"] = body
        return empty

    records = [UpperLowerPriceRow.model_validate(r) for r in raw]
    df = pd.DataFrame([r.model_dump() for r in records])
    df.attrs["filters"] = body

    if exclude_etf_etn_spac:
        df = filter_out_etf_etn_spac(df)
        df.attrs["filters"] = body
        stats = df.attrs.get("filter_stats", {})
        logger.info(
            "client filter ETF/ETN/SPAC: input={i} etf={e} etn={n} spac={s} kept={k}",
            i=stats.get("input_rows"), e=stats.get("etf_excluded"),
            n=stats.get("etn_excluded"), s=stats.get("spac_excluded"),
            k=stats.get("kept_rows"),
        )

    return df


# ─────────────────────────────────────────────────────────────────────────────
# 마크다운 리포트
# ─────────────────────────────────────────────────────────────────────────────


def _fmt_int(v: object) -> str:
    if pd.isna(v):
        return "—"
    return f"{int(v):,}"


def _fmt_signed_int(v: object) -> str:
    if pd.isna(v):
        return "—"
    n = int(v)
    if n > 0:
        return f"+{n:,}"
    return f"{n:,}"


def _fmt_signed_pct(v: object) -> str:
    if pd.isna(v):
        return "—"
    f = float(v)
    if f > 0:
        return f"+{f:.2f}"
    return f"{f:.2f}"


def _label(table: dict[str, str], code: str) -> str:
    return f"{table.get(code, '?')}({code})"


def render_markdown(
    df: pd.DataFrame,
    *,
    filters: UpperLowerPriceFilters | dict[str, str] | None = None,
    fetched_at: str = "",
) -> str:
    """ka10017 결과를 마크다운 문자열로 렌더링한다.

    Args:
        df: ``get_upper_lower_price()`` 반환 DataFrame.
        filters: 사용된 필터. ``None`` 이면 ``df.attrs["filters"]`` 에서 복원.
        fetched_at: 취득 시각 표기.

    Returns:
        마크다운 본문. 빈 ``df`` 면 그 사실을 표기하는 짧은 문서.
    """
    if isinstance(filters, UpperLowerPriceFilters):
        f = filters.to_body()
    elif isinstance(filters, dict):
        f = filters
    else:
        f = df.attrs.get("filters", {})

    title_label = (
        _LABEL_UPDOWN.get(f.get("updown_tp", ""), "상하한") if f else "상하한"
    )

    lines: list[str] = [
        f"# 상하한가 종목 리포트 — {title_label} (ka10017)",
        "",
        "## 조회 조건",
    ]
    if f:
        lines += [
            f"- **시장구분**: {_label(_LABEL_MRKT, f.get('mrkt_tp', ''))}",
            f"- **상하한구분**: {_label(_LABEL_UPDOWN, f.get('updown_tp', ''))}",
            f"- **정렬구분**: {_label(_LABEL_SORT, f.get('sort_tp', ''))}",
            f"- **종목조건**: {_label(_LABEL_STK_CND, f.get('stk_cnd', ''))}",
            f"- **거래량구분**: {_label(_LABEL_TRDE_QTY, f.get('trde_qty_tp', ''))}",
            f"- **신용조건**: {_label(_LABEL_CRD_CND, f.get('crd_cnd', ''))}",
            f"- **매매금구분**: {_label(_LABEL_TRDE_GOLD, f.get('trde_gold_tp', ''))}",
            f"- **거래소구분**: {_label(_LABEL_STEX, f.get('stex_tp', ''))}",
        ]
    lines += [
        f"- **데이터 모드**: {default_config.mode} ({default_config.base_url})",
        f"- **취득 시각**: {fetched_at}" if fetched_at else "- **취득 시각**: —",
        f"- **수집 종목 수**: {len(df)}건",
    ]

    stats = df.attrs.get("filter_stats")
    if stats:
        lines.append(
            "- **클라이언트 필터링**: ETF/ETN/스팩 제외 — "
            f"원본 {stats.get('input_rows', 0)}건 → "
            f"ETF {stats.get('etf_excluded', 0)} / "
            f"ETN {stats.get('etn_excluded', 0)} / "
            f"스팩 {stats.get('spac_excluded', 0)} 제외 → "
            f"최종 {stats.get('kept_rows', 0)}건"
        )
    lines.append("")

    if df.empty:
        lines += ["응답 데이터 없음.", ""]
        return "\n".join(lines)

    sort_label = _LABEL_SORT.get(f.get("sort_tp", ""), "API 기본") if f else "API 기본"
    lines += [
        f"## 종목 목록 (정렬: {sort_label} — API 응답 순서 보존)",
        "",
        "| # | 종목코드 | 종목명 | 종목정보 | 현재가 | 등락률 | 전일대비 | 거래량 | 전일거래량 | 매도잔량 | 매도호가 | 매수호가 | 매수잔량 | 연속횟수 |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for i, r in enumerate(df.itertuples(index=False), start=1):
        lines.append(
            "| {n} | {cd} | {nm} | {info} | {cur} | {flu} | {pre} | {q} | {pq} | {sr} | {sb} | {bb} | {br} | {cnt} |".format(
                n=i,
                cd=str(r.stk_cd),
                nm=str(r.stk_nm),
                info=str(r.stk_infr),
                cur=_fmt_int(r.cur_prc),
                flu=_fmt_signed_pct(r.flu_rt),
                pre=_fmt_signed_int(r.pred_pre),
                q=_fmt_int(r.trde_qty),
                pq=_fmt_int(r.pred_trde_qty),
                sr=_fmt_int(r.sel_req),
                sb=_fmt_int(r.sel_bid),
                bb=_fmt_int(r.buy_bid),
                br=_fmt_int(r.buy_req),
                cnt=_fmt_int(r.cnt),
            )
        )

    lines += [
        "",
        "## 비고",
        "- 가격 단위: 원, 거래량/잔량 단위: 주, 등락률 단위: %",
        "- `등락률`·`전일대비` 는 부호 보존 (+상승 / −하락)",
        "- `현재가`·`매도호가`·`매수호가` 는 절댓값 (응답의 ``+``/``-`` prefix 는 상승/하락 표시 indicator라 제거)",
        "- `종목정보` 는 관리/투자주의/거래정지 등 표시 — 빈 값이면 일반종목",
        "- `연속횟수` 는 ``sort_tp=2`` (연속횟수순) 일 때 의미가 큼",
        "- 데이터 출처: 키움 OpenAPI ka10017(상하한가요청)",
        "- 본 리포트는 분석 보조 자료이며, 매매 신호로 단정해서는 안 됩니다",
        "",
    ]
    return "\n".join(lines)


def save_upper_lower_price_markdown(
    df: pd.DataFrame,
    *,
    filters: UpperLowerPriceFilters | dict[str, str] | None = None,
    output_root: Path = _DEFAULT_OUTPUT_ROOT,
    now: datetime | None = None,
) -> Path:
    """마크다운 렌더 후 ``<output_root>/<오늘 YYYYMMDD>/upperLowerPrice.md`` 에 저장.

    chart60/chartDay/foreigner 와 달리 **종목별 leaf 디렉터리 없이** 날짜
    디렉터리 직속으로 저장한다 (스크리너 결과는 단일 파일이 자연스러움).

    Args:
        df: ``get_upper_lower_price()`` 반환 DataFrame.
        filters: 사용된 필터(헤더 표시용). ``None`` 이면 ``df.attrs["filters"]``.
        output_root: 리포트 루트 디렉터리(기본 ``reports``).
        now: 실행 시각. ``None`` 이면 ``datetime.now()`` 사용.

    Returns:
        저장된 파일의 ``Path``.
    """
    current = now or datetime.now()
    today_dir = current.strftime("%Y%m%d")
    fetched_at = current.strftime("%Y-%m-%d %H:%M:%S")

    md = render_markdown(df, filters=filters, fetched_at=fetched_at)

    out_dir = output_root / today_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / _DEFAULT_FILENAME
    out_path.write_text(md, encoding="utf-8")
    logger.info("리포트 저장: {p}", p=out_path)
    return out_path


__all__ = [
    "KiwoomApiError",
    "UpperLowerPriceClient",
    "UpperLowerPriceFilters",
    "UpperLowerPriceRow",
    "filter_out_etf_etn_spac",
    "get_upper_lower_price",
    "is_etf",
    "is_etn",
    "is_spac",
    "render_markdown",
    "save_upper_lower_price_markdown",
]
