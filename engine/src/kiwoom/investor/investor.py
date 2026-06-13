"""종목별 투자자·기관 순매수금액 추이 단일 파일 모듈 (키움 ka10059).

특정 종목의 외국인투자자·기관계·개인투자자 일별 순매수금액을 가장 최근부터
N 거래일분 취득해 마크다운 리포트로 저장한다.

API 정보 (PDF p.156~158):
    - TR ID: ka10059 (종목별투자자기관별요청)
    - URL: ``/api/dostk/stkinfo``
    - Body 필수 5개:
        * ``dt``         기준일자 YYYYMMDD
        * ``stk_cd``     종목코드
        * ``amt_qty_tp`` 1=금액 / 2=수량  → **본 모듈 고정 "1"(금액)**
        * ``trde_tp``    0=순매수 / 1=매수 / 2=매도 → **고정 "0"(순매수)**
        * ``unit_tp``    1000=천주 / 1=단주 → **고정 "1000"** (금액모드에선 백만원 단위)
    - 응답 리스트 키: ``stk_invsr_orgn``
    - 1행 = 1 거래일 (주말·휴장 자동 스킵, 응답 정렬: 최신 → 과거)

본 모듈은 ``etc.foreigner`` 패턴을 그대로 따른다. 공용 인프라
(:mod:`src.kiwoom.auth`, :mod:`src.kiwoom.config`) 만 재사용하며 chart 패키지에
의존하지 않는다.

사용 예::

    import asyncio
    from src.kiwoom.investor.investor import (
        get_investor_flow,
        save_investor_markdown,
    )

    df = asyncio.run(get_investor_flow("005930", bars=16))
    path = save_investor_markdown(df, stk_cd="005930", stk_name="삼성전자")
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Final, Protocol

import httpx
import pandas as pd
from loguru import logger
from pydantic import BaseModel, ConfigDict, field_validator

from src.kiwoom._exchange import DEFAULT_EXCHANGE as _DEFAULT_EXCHANGE
from src.kiwoom._exchange import normalize_stk_cd as _normalize_stk_cd
from src.kiwoom.auth import KiwoomAuth
from src.kiwoom.auth import auth as default_auth
from src.kiwoom.config import KiwoomConfig, config as default_config

# ─────────────────────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────────────────────

_API_ID: Final[str] = "ka10059"
_API_PATH: Final[str] = "/api/dostk/stkinfo"
_LIST_KEY: Final[str] = "stk_invsr_orgn"

# 요청 조건 고정 (계획서 6번 항목 — 금액·순매수·천주).
_AMT_QTY_TP: Final[str] = "1"      # 1=금액
_TRDE_TP: Final[str] = "0"         # 0=순매수
_UNIT_TP: Final[str] = "1000"      # 1000=천주 (금액모드에서 사실상 백만원 단위)

# 거래소 정규화는 src.kiwoom._exchange 공용 유틸 사용 (chart60/chartDay/foreigner 도 동일).
# HTS [0995] 종목별투자자 (통합) 탭과 일치시키기 위해 기본값 SOR(통합).
# (예: 005930 20260508 외국인 KRX -2,545,520 vs SOR 통합 -3,049,426)

_PAGE_DELAY_SEC: Final[float] = 0.2
_MAX_PAGES: Final[int] = 20
_MAX_RETRY: Final[int] = 3
_REQUEST_TIMEOUT_SEC: Final[float] = 15.0
_RATE_LIMIT_CODE: Final[int] = 1700
_TOKEN_INVALID_CODE: Final[int] = 8005

_DEFAULT_BARS: Final[int] = 16
_DEFAULT_FETCH_MARGIN: Final[int] = 4

_DEFAULT_OUTPUT_ROOT: Final[Path] = Path("reports")
_DEFAULT_FILENAME: Final[str] = "investor.md"


# ─────────────────────────────────────────────────────────────────────────────
# 예외
# ─────────────────────────────────────────────────────────────────────────────


class KiwoomApiError(RuntimeError):
    """ka10059 호출 실패 예외.

    Attributes:
        code: 키움 ``return_code`` 또는 HTTP 상태코드 등의 식별값.
        msg: 키움 ``return_msg`` 본문 또는 진단용 메시지.
        api_id: 호출한 TR ID.
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


def _to_signed_int(value: object) -> int:
    """``"+1584"`` → 1584, ``"-61779"`` → -61779 (부호 보존).

    순매수금액처럼 부호 자체가 의미를 갖는 필드용. 누락/공백/변환실패는 0 으로
    정규화한다.
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


# ─────────────────────────────────────────────────────────────────────────────
# 모델
# ─────────────────────────────────────────────────────────────────────────────


class InvestorFlowRecord(BaseModel):
    """ka10059 ``stk_invsr_orgn`` 한 행 — 외국인·기관·개인 순매수금액.

    응답에 포함된 ``cur_prc``, ``pre_sig``, ``pred_pre``, ``flu_rt``,
    ``acc_trde_qty``, ``acc_trde_prica``, 그리고 기관 세분류
    (``fnnc_invt``, ``insrnc``, ``invtrt``, ``etc_fnnc``, ``bank``,
    ``penfnd_etc``, ``samo_fund``, ``natn``, ``etc_corp``, ``natfor``) 는
    본 리포트 범위 밖이므로 ``extra="ignore"`` 로 자동 폐기한다.

    Attributes:
        dt: 일자, ``YYYYMMDD`` 문자열 (1행 = 1 거래일).
        ind_invsr: 개인투자자 순매수금액 (백만원, **부호 보존**).
        frgnr_invsr: 외국인투자자 순매수금액 (백만원, **부호 보존**).
        orgn: 기관계 순매수금액 (백만원, **부호 보존**).
    """

    model_config = ConfigDict(extra="ignore")

    dt: str
    ind_invsr: int = 0
    frgnr_invsr: int = 0
    orgn: int = 0

    @field_validator("ind_invsr", "frgnr_invsr", "orgn", mode="before")
    @classmethod
    def _signed(cls, v: object) -> int:
        return _to_signed_int(v)


# ─────────────────────────────────────────────────────────────────────────────
# HTTP 클라이언트 (ka10059 전용)
# ─────────────────────────────────────────────────────────────────────────────


class _TokenProvider(Protocol):
    async def get_access_token(self, *, force_refresh: bool = False) -> str: ...
    def invalidate(self) -> None: ...


class _ConfigLike(Protocol):
    @property
    def base_url(self) -> str: ...


class InvestorFlowClient:
    """ka10059 (종목별투자자기관별요청) 호출 전용 클라이언트.

    ``etc.foreigner.ForeignHoldingClient`` 와 동형. URL(``_API_PATH``) ·
    TR ID(``_API_ID``) · 응답 리스트 키(``_LIST_KEY``) 만 본 모듈 안에 고정한다.

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

    async def fetch_records(
        self,
        stk_cd: str,
        *,
        base_dt: str,
        min_rows: int,
        exchange: str = _DEFAULT_EXCHANGE,
        stop_when: Callable[[list[dict[str, Any]]], bool] | None = None,
    ) -> list[dict[str, Any]]:
        """``cont-yn`` 헤더 페이징으로 ``stk_invsr_orgn`` 누적 조회.

        Args:
            stk_cd: 종목코드. 평문(``"005930"``) 또는 거래소 접미사 포함
                (``"005930_AL"`` 등) 모두 허용.
            base_dt: 기준일자 YYYYMMDD (``dt`` 필드 값).
            min_rows: 누적 행수가 이 값 이상이면 조기 종료.
            exchange: 거래소 — ``"sor"``(통합, 기본) / ``"krx"`` / ``"nxt"``.
                ``stk_cd`` 에 이미 접미사가 있으면 그것이 우선한다.
            stop_when: 추가 종료 조건 함수(rows → bool).

        Returns:
            누적된 raw dict 리스트(원본 응답 그대로, 모델 검증 전).
        """
        api_stk_cd, _label = _normalize_stk_cd(stk_cd, exchange)
        body: dict[str, Any] = {
            "dt": base_dt,
            "stk_cd": api_stk_cd,
            "amt_qty_tp": _AMT_QTY_TP,
            "trde_tp": _TRDE_TP,
            "unit_tp": _UNIT_TP,
        }
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
                "ka10059 page={p} got={g} total={t} cont-yn={c}",
                p=page + 1, g=len(chunk), t=len(rows), c=cont_yn,
            )

            if len(rows) >= min_rows:
                break
            if stop_when is not None and stop_when(rows):
                break
            if cont_yn != "Y" or not next_key:
                break

            await asyncio.sleep(_PAGE_DELAY_SEC)

        return rows


# ─────────────────────────────────────────────────────────────────────────────
# 파사드
# ─────────────────────────────────────────────────────────────────────────────


async def get_investor_flow(
    stk_cd: str,
    *,
    bars: int = _DEFAULT_BARS,
    base_dt: str | None = None,
    exchange: str = _DEFAULT_EXCHANGE,
    client: InvestorFlowClient | None = None,
) -> pd.DataFrame:
    """특정 종목의 투자자·기관 순매수금액 추이를 최근 ``bars`` 거래일분 반환.

    호출 조건은 모듈 상수로 고정: ``amt_qty_tp="1"`` (금액),
    ``trde_tp="0"`` (순매수), ``unit_tp="1000"`` (천주). 금액모드에서
    투자자별 값은 사실상 **백만원** 단위로 떨어진다.

    거래소 기본값은 SOR(통합) 으로, HTS [0995] 종목별투자자 (통합) 탭과 일치하는
    KRX+NXT 합산 데이터를 반환한다.

    Args:
        stk_cd: 종목코드(예: ``"005930"``). 평문 또는 접미사(``_AL``/``_NX``) 포함.
        bars: 결과에 포함할 최근 거래일 수(기본 16).
        base_dt: 기준일자 ``YYYYMMDD``. ``None`` 이면 오늘 날짜.
        exchange: 거래소 — ``"sor"`` 통합(기본) / ``"krx"`` / ``"nxt"``.
        client: 주입용 :class:`InvestorFlowClient` (테스트/모킹용).

    Returns:
        DataFrame. 컬럼: ``dt``, ``ind_invsr``, ``frgnr_invsr``, ``orgn``.
        시간 오름차순(과거 → 최신). 행 수는 정확히 ``bars`` (또는 응답이
        부족하면 그 미만). DataFrame 의 ``attrs`` 에 ``exchange_label``
        ("SOR(통합)"/"KRX"/"NXT") 가 보존된다.
    """
    client = client or InvestorFlowClient()
    base_dt = base_dt or datetime.now().strftime("%Y%m%d")
    api_stk_cd, exchange_label = _normalize_stk_cd(stk_cd, exchange)

    raw = await client.fetch_records(
        stk_cd, base_dt=base_dt, exchange=exchange,
        min_rows=bars + _DEFAULT_FETCH_MARGIN,
    )
    logger.info(
        "stk_cd={s} api_code={a} exchange={e} base_dt={b} fetched={n}",
        s=stk_cd, a=api_stk_cd, e=exchange_label, b=base_dt, n=len(raw),
    )

    if not raw:
        logger.warning("투자자 동향 응답 없음 stk_cd={s}", s=stk_cd)
        empty = pd.DataFrame()
        empty.attrs["exchange_label"] = exchange_label
        empty.attrs["api_stk_cd"] = api_stk_cd
        return empty

    records = [InvestorFlowRecord.model_validate(r) for r in raw]
    df = pd.DataFrame([r.model_dump() for r in records])
    df["dt"] = df["dt"].astype(str)
    df = df.sort_values("dt").reset_index(drop=True)
    df = df.tail(bars).reset_index(drop=True)
    df.attrs["exchange_label"] = exchange_label
    df.attrs["api_stk_cd"] = api_stk_cd
    return df


# ─────────────────────────────────────────────────────────────────────────────
# 마크다운 리포트
# ─────────────────────────────────────────────────────────────────────────────


def _fmt_signed_int(v: object) -> str:
    if pd.isna(v):
        return "—"
    n = int(v)
    if n > 0:
        return f"+{n:,}"
    return f"{n:,}"


def _fmt_dt(s: str) -> str:
    """``YYYYMMDD`` → ``YYYY-MM-DD``."""
    return f"{s[0:4]}-{s[4:6]}-{s[6:8]}"


def render_markdown(
    df: pd.DataFrame,
    *,
    stk_cd: str,
    stk_name: str = "",
    fetched_at: str = "",
) -> str:
    """투자자·기관 순매수금액 추이를 마크다운 문자열로 렌더링한다.

    Args:
        df: ``get_investor_flow()`` 반환 DataFrame.
        stk_cd: 종목코드.
        stk_name: 종목명(표시용).
        fetched_at: 취득 시각 표기.

    Returns:
        마크다운 본문. 빈 ``df`` 면 그 사실을 표기하는 짧은 문서.
    """
    title_name = f"{stk_name}({stk_cd})" if stk_name else stk_cd
    exchange_label = df.attrs.get("exchange_label", "SOR(통합)")
    api_stk_cd = df.attrs.get("api_stk_cd", stk_cd)
    if df.empty:
        return f"# {title_name} 투자자·기관 순매수금액 추이\n\n응답 데이터 없음.\n"

    last = df.iloc[-1]
    first = df.iloc[0]

    lines: list[str] = [
        f"# {title_name} 투자자·기관 순매수금액 추이",
        "",
        "## 기본 정보",
        f"- **종목코드**: {stk_cd} (API 호출 코드: `{api_stk_cd}`)",
    ]
    if stk_name:
        lines.append(f"- **종목명**: {stk_name}")
    lines += [
        f"- **거래소**: {exchange_label}",
        f"- **데이터 모드**: {default_config.mode} ({default_config.base_url})",
        f"- **취득 시각**: {fetched_at}" if fetched_at else "- **취득 시각**: —",
        f"- **거래일 행 수**: {len(df)}회",
        f"- **날짜 범위**: {_fmt_dt(first['dt'])} ~ {_fmt_dt(last['dt'])}",
        "- **호출 조건**: 금액 · 순매수 · 천주 (단위: 백만원)",
        "",
        "## 최근 거래일 스냅샷",
        f"- **최근 거래일**: {_fmt_dt(last['dt'])}",
        f"- **외국인**: {_fmt_signed_int(last['frgnr_invsr'])} 백만원",
        f"- **기관계**: {_fmt_signed_int(last['orgn'])} 백만원",
        f"- **개인**:    {_fmt_signed_int(last['ind_invsr'])} 백만원",
        "",
        "## 일별 순매수금액 추이 (날짜 오름차순, 단위: 백만원)",
        "",
        "| 날짜 | 개인 | 외국인 | 기관계 |",
        "|---|---:|---:|---:|",
    ]
    for _, r in df.iterrows():
        lines.append(
            "| {dt} | {ind} | {frg} | {org} |".format(
                dt=_fmt_dt(r["dt"]),
                ind=_fmt_signed_int(r["ind_invsr"]),
                frg=_fmt_signed_int(r["frgnr_invsr"]),
                org=_fmt_signed_int(r["orgn"]),
            )
        )
    lines += [
        "",
        "## 비고",
        "- 호출 조건: amt_qty_tp=1(금액), trde_tp=0(순매수), unit_tp=1000(천주)",
        f"- 거래소: {exchange_label} — KRX 단독 조회 시 NXT 거래분 누락으로 HTS 통합값과 차이 발생",
        "- 단위: 백만원 / 부호 보존 (+ 매수우위, − 매도우위)",
        "- 데이터 출처: 키움 OpenAPI ka10059(종목별투자자기관별요청)",
        "- 본 리포트는 분석 보조 자료이며, 매매 신호로 단정해서는 안 됩니다",
        "",
    ]
    return "\n".join(lines)


def save_investor_markdown(
    df: pd.DataFrame,
    *,
    stk_cd: str,
    stk_name: str = "",
    output_root: Path = _DEFAULT_OUTPUT_ROOT,
    now: datetime | None = None,
) -> Path:
    """마크다운 렌더 후 ``<output_root>/<오늘 YYYYMMDD>/<종목명(코드)>/investor.md`` 에 저장.

    Args:
        df: ``get_investor_flow()`` 반환 DataFrame.
        stk_cd: 종목코드.
        stk_name: 종목명(표시용).
        output_root: 리포트 루트 디렉터리(기본 ``reports``).
        now: 실행 시각. ``None`` 이면 ``datetime.now()`` 사용.

    Returns:
        저장된 파일의 ``Path``.
    """
    current = now or datetime.now()
    today_dir = current.strftime("%Y%m%d")
    fetched_at = current.strftime("%Y-%m-%d %H:%M:%S")

    md = render_markdown(df, stk_cd=stk_cd, stk_name=stk_name, fetched_at=fetched_at)

    stock_leaf = f"{stk_name}({stk_cd})" if stk_name else stk_cd
    out_dir = output_root / today_dir / stock_leaf
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / _DEFAULT_FILENAME
    out_path.write_text(md, encoding="utf-8")
    logger.info("리포트 저장: {p}", p=out_path)
    return out_path


__all__ = [
    "InvestorFlowClient",
    "InvestorFlowRecord",
    "KiwoomApiError",
    "get_investor_flow",
    "render_markdown",
    "save_investor_markdown",
]
