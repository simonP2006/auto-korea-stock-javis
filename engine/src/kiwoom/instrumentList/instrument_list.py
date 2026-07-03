"""키움 종목정보 리스트 (ka10099) — 전체 상장종목 코드↔이름 마스터.

시장(코스피/코스닥)별로 전체 상장 종목의 (단축코드, 종목명) 마스터를 조회한다.
과거일 백필의 종목명→코드 해석에서 디스크 스캔(reports/*)으로 못 찾은 이름을
보완하는 **fallback 소스**다.

:mod:`src.kiwoom.upperLowerPrice.upperLowerPrice` 와 동일한 공용 인프라
(:mod:`src.kiwoom.auth`, :mod:`src.kiwoom.config`) 와 httpx 페이징·재시도 패턴을
그대로 재사용한다.

API 정보 (PDF ka10099, p.228~):
    - TR ID: ka10099 (종목정보 리스트)
    - URL: ``/api/dostk/stkinfo`` (POST)
    - Body: ``{"mrkt_tp": "0"}`` — 시장구분(0=코스피 / 10=코스닥 / 30=K-OTC /
      50=코넥스 / 60=ETN / 8=ETF ...). 유일한 필수 필드.
    - 응답 리스트 키: ``list`` — 항목 필드 ``code``(단축코드)·``name``(종목명)·
      ``listCount``(상장주식수)·``auditInfo``(감리구분) 등.
    - 페이징: 응답 헤더 ``cont-yn=Y`` 이면 ``next-key`` 로 다음 페이지 요청.

사용 예::

    import asyncio
    from src.kiwoom.instrumentList import get_instrument_name_to_code

    name_to_code = asyncio.run(get_instrument_name_to_code())  # 코스피+코스닥
"""

from __future__ import annotations

import asyncio
import re
from typing import Any, Final, Protocol

import httpx
from loguru import logger

from src.kiwoom.auth import KiwoomAuth
from src.kiwoom.auth import auth as default_auth
from src.kiwoom.config import KiwoomConfig
from src.kiwoom.config import config as default_config

_API_ID: Final[str] = "ka10099"
_API_PATH: Final[str] = "/api/dostk/stkinfo"
_LIST_KEY: Final[str] = "list"

MARKET_KOSPI: Final[str] = "0"
MARKET_KOSDAQ: Final[str] = "10"
_DEFAULT_MARKETS: Final[tuple[str, ...]] = (MARKET_KOSPI, MARKET_KOSDAQ)

_PAGE_DELAY_SEC: Final[float] = 0.2
# 페이지 수 안전망. 페이지당 ~100건, 코스피+코스닥 전체 ~2,800종목 → ~28페이지.
# 200 은 그 7배로 넉넉한 무한루프 방지선(정상 사용에서는 도달하지 않음).
_MAX_PAGES: Final[int] = 200
_MAX_RETRY: Final[int] = 3
_REQUEST_TIMEOUT_SEC: Final[float] = 15.0
_RATE_LIMIT_CODE: Final[int] = 1700
_TOKEN_INVALID_CODE: Final[int] = 8005

# 단축코드 정규화 — 선두 4~6자리 숫자만(거래소 접미사·특수클래스 문자 제거).
_CODE_DIGITS: Final[re.Pattern[str]] = re.compile(r"(\d{4,6})")


class InstrumentListError(RuntimeError):
    """ka10099 호출 실패 예외.

    Attributes:
        code: 키움 ``return_code`` 또는 HTTP 상태코드 등의 식별값.
        msg: 키움 ``return_msg`` 본문 또는 진단용 메시지.
        api_id: 호출한 TR ID (기본 ``ka10099``).
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


class _TokenProvider(Protocol):
    async def get_access_token(self, *, force_refresh: bool = False) -> str: ...
    def invalidate(self) -> None: ...


class _ConfigLike(Protocol):
    @property
    def base_url(self) -> str: ...


def _normalize_code(code: str) -> str:
    """``"005930"`` / ``"005930_AL"`` → ``"005930"`` (선두 4~6자리). 실패 시 빈 문자열."""
    m = _CODE_DIGITS.match(code.strip())
    return m.group(1) if m else ""


class InstrumentListClient:
    """ka10099 (종목정보 리스트) 호출 전용 클라이언트.

    upperLowerPrice/chartDay 와 동일한 페이징·재시도 패턴.

    오류 코드 자동 처리:
        - ``1700`` (요청수 초과): 지수 백오프 후 재시도
        - ``8005`` (토큰 무효): 토큰 캐시 무효화 후 재발급하여 재시도
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
            InstrumentListError: HTTP 비정상, JSON 파싱 실패, 또는
                ``return_code != 0`` (1700/8005 자동 재시도 후에도 실패 포함).
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
                raise InstrumentListError(
                    code="HTTP", msg=f"transport error: {exc}",
                ) from exc

            if resp.status_code != 200:
                raise InstrumentListError(
                    code=resp.status_code,
                    msg=f"non-200 body={resp.text[:300]}",
                )

            try:
                data: dict[str, Any] = resp.json()
            except ValueError as exc:
                raise InstrumentListError(
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
                    "ka10099 rate limit (1700) attempt={n}/{m} sleep={s}s",
                    n=attempt + 1, m=_MAX_RETRY, s=wait,
                )
                await asyncio.sleep(wait)
                continue

            if rc == _TOKEN_INVALID_CODE and attempt < _MAX_RETRY - 1:
                logger.warning("ka10099 token invalid (8005), 재발급 후 재시도")
                self.auth.invalidate()
                continue

            raise InstrumentListError(
                code=rc, msg=str(data.get("return_msg", "")),
            )

        raise InstrumentListError(code="RETRY", msg=f"재시도 {_MAX_RETRY}회 초과")

    async def fetch_market(self, mrkt_tp: str) -> list[dict[str, Any]]:
        """한 시장의 전체 종목 리스트를 ``cont-yn`` 페이징으로 누적 조회.

        Args:
            mrkt_tp: 시장구분 (``"0"`` 코스피 / ``"10"`` 코스닥 등).

        Returns:
            누적된 raw dict 리스트(원본 응답 그대로).
        """
        body = {"mrkt_tp": mrkt_tp}
        rows: list[dict[str, Any]] = []
        cont_yn: str | None = None
        next_key: str | None = None

        for page in range(_MAX_PAGES):
            data, cont_yn, next_key = await self.post(
                body, cont_yn=cont_yn, next_key=next_key,
            )
            chunk = data.get(_LIST_KEY) or []
            if not isinstance(chunk, list):
                raise InstrumentListError(
                    code="SHAPE",
                    msg=f"{_LIST_KEY} 가 리스트가 아님: {type(chunk).__name__}",
                )
            rows.extend(chunk)
            logger.debug(
                "ka10099 mrkt={mk} page={p} got={g} total={t} cont-yn={c}",
                mk=mrkt_tp, p=page + 1, g=len(chunk), t=len(rows), c=cont_yn,
            )

            if cont_yn != "Y" or not next_key:
                break
            await asyncio.sleep(_PAGE_DELAY_SEC)
        else:
            logger.warning(
                "ka10099 _MAX_PAGES={m} 안전망 도달 (mrkt={mk} 누적 {t}건, "
                "마지막 cont-yn={c})",
                m=_MAX_PAGES, mk=mrkt_tp, t=len(rows), c=cont_yn,
            )

        return rows


async def get_instrument_name_to_code(
    markets: tuple[str, ...] = _DEFAULT_MARKETS,
    *,
    client: InstrumentListClient | None = None,
) -> dict[str, str]:
    """시장별 ka10099 를 조회해 ``{종목명: 단축코드}`` 매핑을 만든다.

    Args:
        markets: 조회할 시장구분 튜플(기본 코스피+코스닥).
        client: 주입용 :class:`InstrumentListClient` (테스트/모킹용).

    Returns:
        ``{종목명: 6자리 단축코드}`` dict. 같은 이름이 여러 행/시장에 나오면
        **첫 등장 우선**(setdefault). 이름 또는 코드가 빈 행은 건너뛴다.
    """
    client = client or InstrumentListClient()
    out: dict[str, str] = {}
    for mrkt in markets:
        rows = await client.fetch_market(mrkt)
        added = 0
        for r in rows:
            name = str(r.get("name", "")).strip()
            code = _normalize_code(str(r.get("code", "")))
            if not name or not code:
                continue
            if name not in out:
                out[name] = code
                added += 1
        logger.info(
            "ka10099 mrkt={mk} rows={n} names+={a} total={t}",
            mk=mrkt, n=len(rows), a=added, t=len(out),
        )
    return out


__all__ = [
    "MARKET_KOSDAQ",
    "MARKET_KOSPI",
    "InstrumentListClient",
    "InstrumentListError",
    "get_instrument_name_to_code",
]
