"""외국인 보유 동향 단일 파일 모듈 (키움 ka10008).

특정 종목의 외국인 보유주식수·비중·한도 소진률 등 일별 동향을
가장 최근부터 N 거래일분 취득해 마크다운 리포트로 저장한다.

API 정보 (PDF p.39~41):
    - TR ID: ka10008 (주식외국인종목별매매동향)
    - URL: ``/api/dostk/frgnistt``
    - Body: ``{"stk_cd": "<6자리>"}`` 만 필수 (base_dt 없음)
    - 응답 리스트 키: ``stk_frgnr``
    - 응답 단위: 1행 = 1 거래일 (주말·공휴일은 자동 스킵)
    - 응답 순서: 최신 → 과거

본 모듈은 chartDay 모듈의 패턴을 복제했으나, **chart60/chartDay 패키지에는
의존하지 않는다**. 공용 인프라(:mod:`src.kiwoom.auth`, :mod:`src.kiwoom.config`)
만 재사용한다.

사용 예::

    import asyncio
    from src.kiwoom.etc.foreigner import (
        get_foreign_holding,
        save_foreigner_markdown,
    )

    df = asyncio.run(get_foreign_holding("005930", bars=16))
    path = save_foreigner_markdown(df, stk_cd="005930", stk_name="삼성전자")
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

from src.kiwoom._exchange import DEFAULT_EXCHANGE, normalize_stk_cd
from src.kiwoom.auth import KiwoomAuth
from src.kiwoom.auth import auth as default_auth
from src.kiwoom.config import KiwoomConfig, config as default_config

# ─────────────────────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────────────────────

_API_ID: Final[str] = "ka10008"
_API_PATH: Final[str] = "/api/dostk/frgnistt"
_LIST_KEY: Final[str] = "stk_frgnr"

_PAGE_DELAY_SEC: Final[float] = 0.2
_MAX_PAGES: Final[int] = 20
_MAX_RETRY: Final[int] = 3
_REQUEST_TIMEOUT_SEC: Final[float] = 15.0
_RATE_LIMIT_CODE: Final[int] = 1700
_TOKEN_INVALID_CODE: Final[int] = 8005

_DEFAULT_BARS: Final[int] = 16
_DEFAULT_FETCH_MARGIN: Final[int] = 4

_DEFAULT_OUTPUT_ROOT: Final[Path] = Path("reports")
_DEFAULT_FILENAME: Final[str] = "foreigner.md"


# ─────────────────────────────────────────────────────────────────────────────
# 예외
# ─────────────────────────────────────────────────────────────────────────────


class KiwoomApiError(RuntimeError):
    """ka10008 호출 실패 예외.

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


def _strip_sign_to_int(value: object) -> int:
    """``"+78800"`` / ``"-78800"`` / ``""`` / ``None`` → ``int`` (절댓값).

    상승/하락 prefix(``+``/``-``)를 제거한 절댓값 정수로 반환한다. 누락/공백/
    변환실패는 0으로 정규화한다. 가격·수량처럼 부호가 표시 indicator인 필드용.
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
    """``"+1000"`` → 1000, ``"-3441"`` → -3441 (부호 보존).

    변동량처럼 부호 자체가 의미를 갖는 필드(예: ``chg_qty``, ``frgnr_limit_irds``)
    에 사용한다. 누락/공백/변환실패는 0으로 정규화.
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


def _strip_sign_to_float(value: object) -> float:
    """``"+26.10"`` / ``"-22.31"`` / ``""`` → ``float`` (절댓값).

    비중·소진률 등 백분율 필드용(prefix는 증감 표시이므로 제거).
    """
    if value is None or value == "":
        return 0.0
    if isinstance(value, (int, float)):
        return float(abs(value))
    s = str(value).strip().lstrip("+-")
    if not s:
        return 0.0
    try:
        return float(s)
    except ValueError:
        return 0.0


# ─────────────────────────────────────────────────────────────────────────────
# 모델
# ─────────────────────────────────────────────────────────────────────────────


class ForeignHoldingRecord(BaseModel):
    """ka10008 ``stk_frgnr`` 한 행.

    Attributes:
        dt: 일자, ``YYYYMMDD`` 문자열 (1행 = 1 거래일).
        close_pric: 종가(원, 절댓값).
        trde_qty: 거래량(주, 절댓값).
        chg_qty: 외국인 변동수량(주, **부호 보존** — 양수=순매수증가, 음수=순매도).
        poss_stkcnt: 외국인 보유주식수(주).
        wght: 외국인 비중(%, 0~100).
        gain_pos_stkcnt: 외국인 취득가능주식수(주).
        frgnr_limit: 외국인 한도(주).
        frgnr_limit_irds: 외국인 한도 증감(주, **부호 보존**).
        limit_exh_rt: 한도 소진률(%, 0~100).
    """

    model_config = ConfigDict(extra="ignore")

    dt: str
    close_pric: int = 0
    trde_qty: int = 0
    chg_qty: int = 0
    poss_stkcnt: int = 0
    wght: float = 0.0
    gain_pos_stkcnt: int = 0
    frgnr_limit: int = 0
    frgnr_limit_irds: int = 0
    limit_exh_rt: float = 0.0

    @field_validator(
        "close_pric",
        "trde_qty",
        "poss_stkcnt",
        "gain_pos_stkcnt",
        "frgnr_limit",
        mode="before",
    )
    @classmethod
    def _abs_int(cls, v: object) -> int:
        return _strip_sign_to_int(v)

    @field_validator("chg_qty", "frgnr_limit_irds", mode="before")
    @classmethod
    def _signed_int(cls, v: object) -> int:
        return _to_signed_int(v)

    @field_validator("wght", "limit_exh_rt", mode="before")
    @classmethod
    def _percent(cls, v: object) -> float:
        return _strip_sign_to_float(v)


# ─────────────────────────────────────────────────────────────────────────────
# HTTP 클라이언트 (ka10008 전용)
# ─────────────────────────────────────────────────────────────────────────────


class _TokenProvider(Protocol):
    async def get_access_token(self, *, force_refresh: bool = False) -> str: ...
    def invalidate(self) -> None: ...


class _ConfigLike(Protocol):
    @property
    def base_url(self) -> str: ...


class ForeignHoldingClient:
    """ka10008 (주식외국인종목별매매동향) 호출 전용 클라이언트.

    chart60/chartDay 의 ``KiwoomChartClient`` 와 동일한 패턴이지만,
    URL(``_API_PATH``)·TR ID(``_API_ID``)·응답 리스트 키(``_LIST_KEY``) 를
    이 모듈 안에 고정한다. chart 패키지에 의존하지 않는다.

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
        min_rows: int,
        exchange: str = DEFAULT_EXCHANGE,
        stop_when: Callable[[list[dict[str, Any]]], bool] | None = None,
    ) -> list[dict[str, Any]]:
        """``cont-yn`` 헤더 페이징으로 ``stk_frgnr`` 누적 조회.

        Args:
            stk_cd: 종목코드. 평문 또는 거래소 접미사 포함.
            min_rows: 누적 행수가 이 값 이상이면 조기 종료.
            exchange: 거래소 — ``"sor"`` 통합(기본) / ``"krx"`` / ``"nxt"``.
            stop_when: 추가 종료 조건 함수(rows → bool).

        Returns:
            누적된 raw dict 리스트(원본 응답 그대로, 모델 검증 전).
        """
        api_stk_cd, _ = normalize_stk_cd(stk_cd, exchange)
        body: dict[str, Any] = {"stk_cd": api_stk_cd}
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
                "ka10008 page={p} got={g} total={t} cont-yn={c}",
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


async def get_foreign_holding(
    stk_cd: str,
    *,
    bars: int = _DEFAULT_BARS,
    exchange: str = DEFAULT_EXCHANGE,
    client: ForeignHoldingClient | None = None,
) -> pd.DataFrame:
    """특정 종목의 외국인 보유 동향을 가장 최근 ``bars`` 거래일분 반환.

    Args:
        stk_cd: 종목코드(예: ``"005930"``). 평문 또는 거래소 접미사 포함.
        bars: 결과에 포함할 최근 거래일 수(기본 16).
        exchange: 거래소 — ``"sor"`` 통합(기본) / ``"krx"`` / ``"nxt"``.
        client: 주입용 :class:`ForeignHoldingClient` (테스트/모킹용).

    Returns:
        DataFrame. 컬럼:
            ``dt``, ``close_pric``, ``trde_qty``, ``chg_qty``, ``poss_stkcnt``,
            ``wght``, ``gain_pos_stkcnt``, ``frgnr_limit``,
            ``frgnr_limit_irds``, ``limit_exh_rt``.

        시간 오름차순(과거 → 최신). 행 수는 정확히 ``bars`` (또는 응답이
        부족하면 그 미만). DataFrame ``attrs`` 에 ``exchange_label``/
        ``api_stk_cd`` 가 보존된다.
    """
    client = client or ForeignHoldingClient()
    api_stk_cd, exchange_label = normalize_stk_cd(stk_cd, exchange)

    raw = await client.fetch_records(
        stk_cd, min_rows=bars + _DEFAULT_FETCH_MARGIN, exchange=exchange,
    )
    logger.info(
        "stk_cd={s} api_code={a} exchange={e} fetched={n}",
        s=stk_cd, a=api_stk_cd, e=exchange_label, n=len(raw),
    )

    if not raw:
        logger.warning("외국인 동향 응답 없음 stk_cd={s}", s=stk_cd)
        empty = pd.DataFrame()
        empty.attrs["exchange_label"] = exchange_label
        empty.attrs["api_stk_cd"] = api_stk_cd
        return empty

    records = [ForeignHoldingRecord.model_validate(r) for r in raw]
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


def _fmt_pct(v: object) -> str:
    if pd.isna(v):
        return "—"
    return f"{float(v):.2f}"


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
    """외국인 보유 일별 데이터를 마크다운 문자열로 렌더링한다.

    Args:
        df: ``get_foreign_holding()`` 반환 DataFrame.
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
        return f"# {title_name} 외국인 보유 동향\n\n응답 데이터 없음.\n"

    last = df.iloc[-1]
    first = df.iloc[0]

    lines: list[str] = [
        f"# {title_name} 외국인 보유 동향",
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
        "- **데이터 단위**: 1회 = 1거래일 (주말·공휴일 자동 스킵)",
        "",
        "## 최근 거래일 스냅샷",
        f"- **최근 거래일**: {_fmt_dt(last['dt'])}",
        f"- **종가**: {_fmt_int(last['close_pric'])} 원",
        f"- **외국인 보유주식수**: {_fmt_int(last['poss_stkcnt'])} 주",
        f"- **외국인 비중**: {_fmt_pct(last['wght'])} %",
        f"- **외국인 한도**: {_fmt_int(last['frgnr_limit'])} 주",
        f"- **한도 소진률**: {_fmt_pct(last['limit_exh_rt'])} %",
        f"- **당일 변동수량**: {_fmt_signed_int(last['chg_qty'])} 주",
        "",
        "## 일별 외국인 보유 내역 (날짜 오름차순)",
        "",
        "| 날짜 | 종가 | 거래량 | 변동수량 | 보유주식수 | 비중% | 한도 | 한도소진% |",
        "|---|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for _, r in df.iterrows():
        lines.append(
            "| {dt} | {c} | {v} | {chg} | {hold} | {w} | {lim} | {ex} |".format(
                dt=_fmt_dt(r["dt"]),
                c=_fmt_int(r["close_pric"]),
                v=_fmt_int(r["trde_qty"]),
                chg=_fmt_signed_int(r["chg_qty"]),
                hold=_fmt_int(r["poss_stkcnt"]),
                w=_fmt_pct(r["wght"]),
                lim=_fmt_int(r["frgnr_limit"]),
                ex=_fmt_pct(r["limit_exh_rt"]),
            )
        )
    lines += [
        "",
        "## 비고",
        "- 단위: 주식수=주, 종가=원, 비중/소진률=%",
        "- 변동수량은 부호 보존(+ 순매수 증가, − 순매도 또는 보유감소)",
        "- 데이터 출처: 키움 OpenAPI ka10008(주식외국인종목별매매동향)",
        "- 본 리포트는 분석 보조 자료이며, 매매 신호로 단정해서는 안 됩니다",
        "",
    ]
    return "\n".join(lines)


def save_foreigner_markdown(
    df: pd.DataFrame,
    *,
    stk_cd: str,
    stk_name: str = "",
    output_root: Path = _DEFAULT_OUTPUT_ROOT,
    now: datetime | None = None,
) -> Path:
    """마크다운 렌더 후 ``<output_root>/<오늘 YYYYMMDD>/foreigner.md`` 에 저장.

    Args:
        df: ``get_foreign_holding()`` 반환 DataFrame.
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
    "ForeignHoldingClient",
    "ForeignHoldingRecord",
    "KiwoomApiError",
    "get_foreign_holding",
    "render_markdown",
    "save_foreigner_markdown",
]
