"""키움 차트 계열 TR 공용 HTTP 클라이언트.

``ka10080`` / ``ka10081`` 등 ``/api/dostk/chart`` 엔드포인트를 호출하고
응답 헤더의 ``cont-yn`` / ``next-key`` 를 활용한 연속조회(페이징)를
공통 처리한다. 다음 오류 코드를 자동 처리한다:

- ``1700`` (요청수 초과): 지수 백오프 후 재시도
- ``8005`` (토큰 무효): 토큰 캐시 무효화 후 재발급하여 1회 재시도

그 외 ``return_code != 0`` 응답은 :class:`KiwoomApiError` 로 raise.
"""

from __future__ import annotations

import asyncio
from typing import Any, Callable, Final, Protocol

import httpx
from loguru import logger

from src.kiwoom.auth import KiwoomAuth
from src.kiwoom.auth import auth as default_auth
from src.kiwoom.chart120.getData.models import KiwoomApiError
from src.kiwoom.config import KiwoomConfig
from src.kiwoom.config import config as default_config

_CHART_PATH: Final[str] = "/api/dostk/chart"
_PAGE_DELAY_SEC: Final[float] = 0.2
_MAX_PAGES: Final[int] = 20
_MAX_RETRY: Final[int] = 3
_REQUEST_TIMEOUT_SEC: Final[float] = 15.0
_RATE_LIMIT_CODE: Final[int] = 1700
_TOKEN_INVALID_CODE: Final[int] = 8005


class _TokenProvider(Protocol):
    """토큰 발급기 프로토콜 (테스트 격리용 duck-typing)."""

    async def get_access_token(self, *, force_refresh: bool = False) -> str: ...

    def invalidate(self) -> None: ...


class _ConfigLike(Protocol):
    """``base_url`` 만 노출하는 설정 프로토콜."""

    @property
    def base_url(self) -> str: ...


class KiwoomChartClient:
    """차트 TR 호출 클라이언트.

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
        api_id: str,
        body: dict[str, Any],
        *,
        cont_yn: str | None = None,
        next_key: str | None = None,
    ) -> tuple[dict[str, Any], str | None, str | None]:
        """단발 POST. 반환: ``(json_body, cont-yn, next-key)``.

        Args:
            api_id: 키움 TR ID(``ka10080`` 등).
            body: 요청 JSON body.
            cont_yn: 연속조회 여부 헤더값(이전 응답의 cont-yn).
            next_key: 연속조회 키 헤더값(이전 응답의 next-key).

        Returns:
            응답 JSON dict, 응답 헤더 ``cont-yn``, 응답 헤더 ``next-key``.

        Raises:
            KiwoomApiError: HTTP 비정상, JSON 파싱 실패, 또는 ``return_code != 0``.
        """
        url = f"{self.config.base_url}{_CHART_PATH}"

        for attempt in range(_MAX_RETRY):
            token = await self.auth.get_access_token()
            headers = {
                "authorization": f"Bearer {token}",
                "api-id": api_id,
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
                    code="HTTP",
                    msg=f"transport error: {exc}",
                    api_id=api_id,
                ) from exc

            if resp.status_code != 200:
                raise KiwoomApiError(
                    code=resp.status_code,
                    msg=f"non-200 body={resp.text[:300]}",
                    api_id=api_id,
                )

            try:
                data: dict[str, Any] = resp.json()
            except ValueError as exc:
                raise KiwoomApiError(
                    code="JSON",
                    msg=f"응답이 JSON이 아님: {resp.text[:300]}",
                    api_id=api_id,
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
                    "rate limit (1700) api_id={a} attempt={n}/{m} sleep={s}s",
                    a=api_id,
                    n=attempt + 1,
                    m=_MAX_RETRY,
                    s=wait,
                )
                await asyncio.sleep(wait)
                continue

            if rc == _TOKEN_INVALID_CODE and attempt < _MAX_RETRY - 1:
                logger.warning(
                    "token invalid (8005) api_id={a}, 토큰 재발급 후 재시도",
                    a=api_id,
                )
                self.auth.invalidate()
                # 다음 루프에서 force_refresh 효과를 내기 위해 캐시를 비움.
                continue

            raise KiwoomApiError(
                code=rc,
                msg=str(data.get("return_msg", "")),
                api_id=api_id,
            )

        raise KiwoomApiError(
            code="RETRY",
            msg=f"재시도 {_MAX_RETRY}회 초과",
            api_id=api_id,
        )

    async def post_paged(
        self,
        api_id: str,
        body: dict[str, Any],
        list_key: str,
        *,
        stop_when: Callable[[list[dict[str, Any]]], bool] | None = None,
        max_pages: int = _MAX_PAGES,
    ) -> list[dict[str, Any]]:
        """``cont-yn`` 헤더 기반 페이징 누적 조회.

        Args:
            api_id: TR ID.
            body: 요청 body (페이징 사이에 동일하게 사용).
            list_key: 응답 본문에서 누적 대상이 되는 리스트 키
                (예: ``stk_dt_pole_chart_qry``).
            stop_when: 누적 행 리스트를 받아 더 이상 페이징할 필요가 없을 때
                ``True`` 를 반환하는 종료 판정 함수. ``None`` 이면 ``cont-yn``
                이 ``Y`` 가 아닐 때까지 진행한다.
            max_pages: 안전 상한 페이지 수.

        Returns:
            누적된 raw dict 리스트(원본 응답 그대로, 모델 검증 전).
        """
        rows: list[dict[str, Any]] = []
        cont_yn: str | None = None
        next_key: str | None = None

        for page in range(max_pages):
            data, cont_yn, next_key = await self.post(
                api_id, body, cont_yn=cont_yn, next_key=next_key,
            )
            chunk = data.get(list_key) or []
            if not isinstance(chunk, list):
                raise KiwoomApiError(
                    code="SHAPE",
                    msg=f"{list_key} 가 리스트가 아님: {type(chunk).__name__}",
                    api_id=api_id,
                )
            rows.extend(chunk)
            logger.debug(
                "paged api_id={a} page={p} got={g} total={t} cont-yn={c}",
                a=api_id,
                p=page + 1,
                g=len(chunk),
                t=len(rows),
                c=cont_yn,
            )

            if stop_when is not None and stop_when(rows):
                break
            if cont_yn != "Y" or not next_key:
                break

            await asyncio.sleep(_PAGE_DELAY_SEC)

        return rows
