"""종목 재무 기본정보 단일 파일 모듈 (키움 ka10001).

특정 종목의 PER·EPS·ROE·PBR·당기순이익을 단발 조회해 마크다운 리포트로
저장한다. ka10001 은 시계열이 아닌 **단일 스냅샷** 이며 응답 필드가 body
루트에 평면 배치된다(리스트 키·페이징 없음).

API 정보 (PDF p.15~17):
    - TR ID: ka10001 (주식기본정보요청)
    - URL: ``/api/dostk/stkinfo``
    - Body 필수 1개:
        * ``stk_cd``  종목코드 (거래소 접미사 지원: ``_AL``/``_NX``)
    - 응답: 단일 객체(루트 평면). 본 모듈이 추출하는 필드:
        * ``stk_nm``   종목명
        * ``per``      PER     ← 외부 벤더 데이터, 주1회/실적시즌 갱신
        * ``eps``      EPS
        * ``roe``      ROE     ← 외부 벤더 데이터(per 와 동일 주의)
        * ``pbr``      PBR
        * ``cup_nga``  당기순이익 (단위: 억원 — 005930 스모크로 확인)

주의 (PDF 명시):
    - per/eps/roe/pbr 은 외부 벤더 제공값으로 비정기 갱신 → **빈 문자열**로
      오는 케이스 정상. 누락은 ``None`` 으로 정규화한다.
    - 모든 값이 String 타입. 부호·콤마 포함 가능.

본 모듈은 ``investor`` 패턴을 그대로 따른다. 공용 인프라
(:mod:`src.kiwoom.auth`, :mod:`src.kiwoom.config`, :mod:`src.kiwoom._exchange`)
만 재사용하며 다른 도메인 모듈에 의존하지 않는다.

사용 예::

    import asyncio
    from src.kiwoom.finance.finance import (
        get_finance_snapshot,
        save_finance_markdown,
    )

    snap = asyncio.run(get_finance_snapshot("005930"))
    path = save_finance_markdown(snap, stk_cd="005930", stk_name="삼성전자")
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Any, Final, Protocol

import httpx
from loguru import logger
from pydantic import BaseModel, ConfigDict, Field, field_validator

from src.kiwoom._exchange import DEFAULT_EXCHANGE as _DEFAULT_EXCHANGE
from src.kiwoom._exchange import normalize_stk_cd as _normalize_stk_cd
from src.kiwoom.auth import KiwoomAuth
from src.kiwoom.auth import auth as default_auth
from src.kiwoom.config import KiwoomConfig, config as default_config

# ─────────────────────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────────────────────

_API_ID: Final[str] = "ka10001"
_API_PATH: Final[str] = "/api/dostk/stkinfo"

# 추출 대상 필드 (응답 루트). raw 원문 보존용 키 목록.
_RAW_FIELDS: Final[tuple[str, ...]] = ("per", "eps", "roe", "pbr", "cup_nga")

_MAX_RETRY: Final[int] = 3
_REQUEST_TIMEOUT_SEC: Final[float] = 15.0
_RATE_LIMIT_CODE: Final[int] = 1700
_TOKEN_INVALID_CODE: Final[int] = 8005

_DEFAULT_OUTPUT_ROOT: Final[Path] = Path("reports")
_DEFAULT_FILENAME: Final[str] = "finance.md"


# ─────────────────────────────────────────────────────────────────────────────
# 예외
# ─────────────────────────────────────────────────────────────────────────────


class KiwoomApiError(RuntimeError):
    """ka10001 호출 실패 예외.

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


def _to_float(value: object) -> float | None:
    """``"+12.34"`` / ``"-3,400"`` / ``"1,234.56"`` → float (부호 보존).

    외부 벤더 미갱신 등으로 빈 문자열·공백·변환불가가 오면 ``None``.
    """
    if value is None:
        return None
    if isinstance(value, (int, float)):
        return float(value)
    s = str(value).strip().replace(",", "")
    if not s or s in {"+", "-"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


# ─────────────────────────────────────────────────────────────────────────────
# 모델
# ─────────────────────────────────────────────────────────────────────────────


class FinanceSnapshot(BaseModel):
    """ka10001 재무 기본정보 단일 스냅샷.

    응답의 다른 모든 필드(시가총액·현재가·52주 최고/최저 등)는 본 리포트
    범위 밖이므로 ``extra="ignore"`` 로 자동 폐기한다.

    Attributes:
        stk_cd: 종목코드.
        stk_nm: 종목명.
        per: PER (벤더 미갱신 시 ``None``).
        eps: EPS (적자 시 음수, 미갱신 시 ``None``).
        roe: ROE (%) (벤더 미갱신 시 ``None``).
        pbr: PBR (미갱신 시 ``None``).
        cup_nga: 당기순이익 (억원, 적자 시 음수, 미제공 시 ``None``).
        raw: per/eps/roe/pbr/cup_nga 응답 원문 문자열 보존(감사용).
    """

    model_config = ConfigDict(extra="ignore")

    stk_cd: str = ""
    stk_nm: str = ""
    per: float | None = None
    eps: float | None = None
    roe: float | None = None
    pbr: float | None = None
    cup_nga: float | None = None
    raw: dict[str, str] = Field(default_factory=dict)

    @field_validator("per", "eps", "roe", "pbr", "cup_nga", mode="before")
    @classmethod
    def _num(cls, v: object) -> float | None:
        return _to_float(v)

    @property
    def is_empty(self) -> bool:
        """유효 종목 응답이 아님(종목명 없음 + 5지표 전부 결측)."""
        return not self.stk_nm and all(
            getattr(self, f) is None for f in _RAW_FIELDS
        )


# ─────────────────────────────────────────────────────────────────────────────
# HTTP 클라이언트 (ka10001 전용)
# ─────────────────────────────────────────────────────────────────────────────


class _TokenProvider(Protocol):
    async def get_access_token(self, *, force_refresh: bool = False) -> str: ...
    def invalidate(self) -> None: ...


class _ConfigLike(Protocol):
    @property
    def base_url(self) -> str: ...


class FinanceInfoClient:
    """ka10001 (주식기본정보요청) 호출 전용 클라이언트.

    ``investor.InvestorFlowClient`` 와 동형이나 ka10001 은 단발 조회이므로
    페이징(cont-yn)·리스트 키가 없다. URL(``_API_PATH``) · TR ID(``_API_ID``)
    만 본 모듈 안에 고정한다.

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

    async def post(self, body: dict[str, Any]) -> dict[str, Any]:
        """단발 POST. 반환: 응답 JSON body(루트 평면).

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
                return data

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


# ─────────────────────────────────────────────────────────────────────────────
# 파사드
# ─────────────────────────────────────────────────────────────────────────────


async def get_finance_snapshot(
    stk_cd: str,
    *,
    exchange: str = _DEFAULT_EXCHANGE,
    client: FinanceInfoClient | None = None,
) -> FinanceSnapshot:
    """특정 종목의 PER·EPS·ROE·PBR·당기순이익 스냅샷을 반환.

    ka10001 은 날짜 파라미터가 없는 단발 조회이므로 ``base_dt`` 인자가 없다.
    펀더멘털 값은 거래소(SOR/KRX/NXT)와 무관하며 ``exchange`` 는 전송 코드
    문자열에만 영향을 준다(기본 SOR — 다른 도메인 모듈과 일관).

    Args:
        stk_cd: 종목코드(예 ``"005930"``). 평문 또는 접미사(``_AL``/``_NX``).
        exchange: 거래소 — ``"sor"`` 통합(기본) / ``"krx"`` / ``"nxt"``.
        client: 주입용 :class:`FinanceInfoClient` (테스트/모킹용).

    Returns:
        :class:`FinanceSnapshot`. 응답이 비정상이면 ``is_empty`` 가 True.
    """
    client = client or FinanceInfoClient()
    api_stk_cd, exchange_label = _normalize_stk_cd(stk_cd, exchange)

    data = await client.post({"stk_cd": api_stk_cd})

    raw = {k: str(data.get(k, "")) for k in _RAW_FIELDS}
    snap = FinanceSnapshot.model_validate(
        {
            "stk_cd": str(data.get("stk_cd", "") or stk_cd),
            "stk_nm": str(data.get("stk_nm", "")),
            "per": data.get("per"),
            "eps": data.get("eps"),
            "roe": data.get("roe"),
            "pbr": data.get("pbr"),
            "cup_nga": data.get("cup_nga"),
            "raw": raw,
        }
    )
    logger.info(
        "stk_cd={s} api_code={a} exchange={e} per={p} eps={ep} roe={r} "
        "pbr={pb} 당기순이익={c}",
        s=stk_cd, a=api_stk_cd, e=exchange_label,
        p=snap.per, ep=snap.eps, r=snap.roe, pb=snap.pbr, c=snap.cup_nga,
    )
    if snap.is_empty:
        logger.warning("재무 기본정보 응답 없음/무효 stk_cd={s}", s=stk_cd)
    return snap


# ─────────────────────────────────────────────────────────────────────────────
# 마크다운 리포트
# ─────────────────────────────────────────────────────────────────────────────


def _fmt_num(v: float | None, *, decimals: int = 2) -> str:
    """결측은 ``—``. 정수면 콤마 정수, 소수면 지정 자릿수."""
    if v is None:
        return "—"
    if float(v).is_integer():
        return f"{int(v):,}"
    return f"{v:,.{decimals}f}"


def render_markdown(
    snap: FinanceSnapshot,
    *,
    stk_cd: str,
    stk_name: str = "",
    fetched_at: str = "",
) -> str:
    """재무 기본정보를 마크다운 문자열로 렌더링한다.

    Args:
        snap: ``get_finance_snapshot()`` 반환 스냅샷.
        stk_cd: 종목코드.
        stk_name: 종목명(표시용).
        fetched_at: 취득 시각 표기.

    Returns:
        마크다운 본문. 무효 응답이면 그 사실을 표기하는 짧은 문서.
    """
    title_name = f"{stk_name}({stk_cd})" if stk_name else stk_cd
    if snap.is_empty:
        return (
            f"# {title_name} 재무 기본정보 (ka10001)\n\n"
            "응답 데이터 없음 / 무효.\n"
        )

    lines: list[str] = [
        f"# {title_name} 재무 기본정보 (ka10001)",
        "",
        "## 기본 정보",
        f"- **종목코드**: {stk_cd}",
    ]
    if stk_name or snap.stk_nm:
        lines.append(f"- **종목명**: {stk_name or snap.stk_nm}")
    lines += [
        f"- **데이터 모드**: {default_config.mode} ({default_config.base_url})",
        f"- **취득 시각**: {fetched_at}" if fetched_at else "- **취득 시각**: —",
        "",
        "## 핵심 지표",
        "",
        "| 지표 | 값 |",
        "|---|---:|",
        f"| PER | {_fmt_num(snap.per)} |",
        f"| EPS | {_fmt_num(snap.eps)} |",
        f"| ROE | {_fmt_num(snap.roe)} |",
        f"| PBR | {_fmt_num(snap.pbr)} |",
        f"| 당기순이익 (억원) | {_fmt_num(snap.cup_nga)} |",
        "",
        "## 비고",
        "- 데이터 출처: 키움 OpenAPI ka10001(주식기본정보요청)",
        "- PER·ROE 는 외부 벤더 제공값으로 주1회 또는 실적발표 시즌에만 갱신됨",
        "- 빈 값(`—`)은 벤더 미갱신/미제공 — 결측이며 0 이 아님",
        "- 당기순이익 단위: **억원** (005930 검증: 452,068 ≈ 45.2조원)",
        "- 본 리포트는 분석 보조 자료이며, 매매 신호로 단정해서는 안 됩니다",
        "",
    ]
    return "\n".join(lines)


def save_finance_markdown(
    snap: FinanceSnapshot,
    *,
    stk_cd: str,
    stk_name: str = "",
    output_root: Path = _DEFAULT_OUTPUT_ROOT,
    now: datetime | None = None,
) -> Path:
    """마크다운 렌더 후 ``<output_root>/<오늘 YYYYMMDD>/<종목명(코드)>/finance.md`` 저장.

    Args:
        snap: ``get_finance_snapshot()`` 반환 스냅샷.
        stk_cd: 종목코드.
        stk_name: 종목명(표시용).
        output_root: 리포트 루트 디렉터리(기본 ``reports``).
        now: 실행 시각. ``None`` 이면 ``datetime.now()``.

    Returns:
        저장된 파일의 ``Path``.
    """
    current = now or datetime.now()
    today_dir = current.strftime("%Y%m%d")
    fetched_at = current.strftime("%Y-%m-%d %H:%M:%S")

    md = render_markdown(
        snap, stk_cd=stk_cd, stk_name=stk_name, fetched_at=fetched_at,
    )

    stock_leaf = f"{stk_name}({stk_cd})" if stk_name else stk_cd
    out_dir = output_root / today_dir / stock_leaf
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / _DEFAULT_FILENAME
    out_path.write_text(md, encoding="utf-8")
    logger.info("리포트 저장: {p}", p=out_path)
    return out_path


__all__ = [
    "FinanceInfoClient",
    "FinanceSnapshot",
    "KiwoomApiError",
    "get_finance_snapshot",
    "render_markdown",
    "save_finance_markdown",
]
