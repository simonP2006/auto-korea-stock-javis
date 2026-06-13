"""키움 조건검색 전용 WebSocket 클라이언트.

키움 OpenAPI의 조건검색 카테고리(ka10171/ka10172/ka10173/ka10174)는
REST가 아닌 WebSocket(``wss://api.kiwoom.com:10000/api/dostk/websocket``)으로
제공된다. 본 클라이언트는 단일 연결 위에서 LOGIN → CNSRLST → CNSRREQ ...
순서로 TR을 멀티플렉싱한다.

프로토콜 요약:
    1. ``wss://...`` 연결
    2. LOGIN 프레임 송신: ``{"trnm":"LOGIN","token":"<access_token>"}``
       (Bearer prefix 없이 평문 토큰 그대로 — 키움 공개 샘플 표준)
    3. ``{"trnm":"LOGIN","return_code":0,...}`` 수신 시 인증 성공
    4. 이후 임의의 TR(``CNSRLST``/``CNSRREQ`` 등) 송신 가능
    5. 서버 PING 프레임 수신 시 같은 페이로드를 echo 송신(keepalive)

오류 처리:
    - ``return_code == 8005`` (토큰 무효) → 토큰 캐시 무효화 + 재연결 1회 재시도
    - ``return_code == 1700`` (요청수 초과) → 지수 백오프 후 재시도
    - 그 외 ``return_code != 0`` → :class:`KiwoomConditionError`
"""

from __future__ import annotations

import asyncio
import json
from typing import Any, Final, Protocol

import websockets
from loguru import logger
from websockets.asyncio.client import ClientConnection
from websockets.exceptions import ConnectionClosed, WebSocketException
from websockets.protocol import State

from src.kiwoom.auth import KiwoomAuth
from src.kiwoom.auth import auth as default_auth
from src.kiwoom.conditionCompany.models import KiwoomConditionError
from src.kiwoom.config import KiwoomConfig
from src.kiwoom.config import config as default_config

_WS_PATH: Final[str] = "/api/dostk/websocket"
_OPEN_TIMEOUT_SEC: Final[float] = 20.0
_LOGIN_TIMEOUT_SEC: Final[float] = 10.0
_RECV_TIMEOUT_SEC: Final[float] = 30.0
_MAX_RETRY: Final[int] = 5
_RATE_LIMIT_CODES: Final[frozenset[int]] = frozenset({1700, 105110})
_TOKEN_INVALID_CODE: Final[int] = 8005


class _TokenProvider(Protocol):
    """토큰 발급기 프로토콜 (테스트 격리용 duck-typing)."""

    async def get_access_token(self, *, force_refresh: bool = False) -> str: ...

    def invalidate(self) -> None: ...


def _ws_url(base_url: str) -> str:
    """``https://api.kiwoom.com`` → ``wss://api.kiwoom.com:10000/api/dostk/websocket``."""
    if base_url.startswith("https://"):
        host = base_url[len("https://"):]
    elif base_url.startswith("http://"):
        host = base_url[len("http://"):]
    else:
        host = base_url
    return f"wss://{host}:10000{_WS_PATH}"


class KiwoomConditionWebSocket:
    """조건검색 카테고리 전용 WebSocket 세션.

    ``async with`` 컨텍스트 매니저로 사용한다.

    사용 예::

        async with KiwoomConditionWebSocket() as ws:
            data = await ws.request({"trnm": "CNSRLST"}, expected_trnm="CNSRLST")

    Attributes:
        auth: 토큰 제공자(기본: 모듈 싱글톤 ``KiwoomAuth``).
        config: 환경설정(기본: 모듈 싱글톤 ``KiwoomConfig``).
    """

    def __init__(
        self,
        auth: _TokenProvider | KiwoomAuth | None = None,
        config: KiwoomConfig | None = None,
    ) -> None:
        self.auth: _TokenProvider = auth or default_auth
        self.config: KiwoomConfig = config or default_config
        self._ws: ClientConnection | None = None
        self._url: str = _ws_url(self.config.base_url)

    async def __aenter__(self) -> "KiwoomConditionWebSocket":
        await self._connect_and_login()
        return self

    async def __aexit__(self, exc_type: object, exc: object, tb: object) -> None:
        await self.close()

    async def close(self) -> None:
        """WebSocket 연결 종료."""
        if self._ws is not None:
            try:
                await self._ws.close()
            except Exception:
                pass
            self._ws = None

    async def request(
        self,
        payload: dict[str, Any],
        *,
        expected_trnm: str,
        match_seq: str | None = None,
    ) -> dict[str, Any]:
        """단발 TR 송신 후 매칭되는 응답을 받아 반환한다.

        PING은 자동 echo 처리하며, 8005/1700 오류는 자동 재시도한다.

        Args:
            payload: 송신 JSON body (``{"trnm": ..., ...}``).
            expected_trnm: 기다릴 응답 ``trnm`` 값.
            match_seq: ``trnm`` 외에 ``seq`` 까지 일치를 요구할 때 지정.

        Returns:
            응답 JSON dict (``return_code`` 검증 통과 시).

        Raises:
            KiwoomConditionError: ``return_code != 0`` 이고 자동 복구 불가능한 경우.
        """
        api_id = str(payload.get("trnm", "?"))

        for attempt in range(_MAX_RETRY):
            await self._ensure_connected()
            assert self._ws is not None

            try:
                await self._ws.send(json.dumps(payload, ensure_ascii=False))
                msg = await self._recv_until(expected_trnm, match_seq=match_seq)
            except (ConnectionClosed, WebSocketException, asyncio.TimeoutError) as exc:
                logger.warning(
                    "ws transport error trnm={a} attempt={n}/{m} err={e}",
                    a=api_id, n=attempt + 1, m=_MAX_RETRY, e=exc,
                )
                await self.close()
                if attempt < _MAX_RETRY - 1:
                    await asyncio.sleep(2**attempt)
                    continue
                raise KiwoomConditionError(
                    code="WS",
                    msg=f"transport error: {exc}",
                    api_id=api_id,
                ) from exc

            rc = msg.get("return_code")
            if rc in (None, 0):
                return msg

            if rc in _RATE_LIMIT_CODES and attempt < _MAX_RETRY - 1:
                wait = 2**attempt
                logger.warning(
                    "rate limit (rc={rc}) trnm={a} attempt={n}/{m} sleep={s}s",
                    rc=rc, a=api_id, n=attempt + 1, m=_MAX_RETRY, s=wait,
                )
                await asyncio.sleep(wait)
                continue

            if rc == _TOKEN_INVALID_CODE and attempt < _MAX_RETRY - 1:
                logger.warning(
                    "token invalid (8005) trnm={a}, 토큰 재발급 + 재연결 후 재시도",
                    a=api_id,
                )
                self.auth.invalidate()
                await self.close()
                continue

            raise KiwoomConditionError(
                code=rc,
                msg=str(msg.get("return_msg", "")),
                api_id=api_id,
            )

        raise KiwoomConditionError(
            code="RETRY",
            msg=f"재시도 {_MAX_RETRY}회 초과",
            api_id=api_id,
        )

    # ---- 내부 -------------------------------------------------------------

    async def _ensure_connected(self) -> None:
        if self._ws is not None and self._ws.state == State.OPEN:
            return
        await self._connect_and_login()

    async def _connect_and_login(self) -> None:
        token = await self.auth.get_access_token()
        logger.debug("ws connect url={u} mode={m}", u=self._url, m=self.config.mode)
        self._ws = await websockets.connect(
            self._url,
            open_timeout=_OPEN_TIMEOUT_SEC,
            ping_interval=20,
            ping_timeout=20,
            close_timeout=5,
            max_size=2**24,  # 매칭 종목이 많을 수 있어 16MB 허용
        )

        login_payload = {"trnm": "LOGIN", "token": token}
        await self._ws.send(json.dumps(login_payload, ensure_ascii=False))
        try:
            msg = await asyncio.wait_for(
                self._recv_until("LOGIN"),
                timeout=_LOGIN_TIMEOUT_SEC,
            )
        except asyncio.TimeoutError as exc:
            await self.close()
            raise KiwoomConditionError(
                code="LOGIN_TIMEOUT",
                msg=f"LOGIN 응답 {_LOGIN_TIMEOUT_SEC}초 초과",
                api_id="LOGIN",
            ) from exc

        rc = msg.get("return_code")
        if rc not in (None, 0):
            await self.close()
            raise KiwoomConditionError(
                code=rc,
                msg=str(msg.get("return_msg", "")),
                api_id="LOGIN",
            )
        logger.info("ws login ok url={u}", u=self._url)

    async def _recv_until(
        self,
        expected_trnm: str,
        *,
        match_seq: str | None = None,
    ) -> dict[str, Any]:
        """``expected_trnm`` 응답이 올 때까지 받는다. PING은 자동 echo."""
        assert self._ws is not None
        while True:
            raw = await asyncio.wait_for(self._ws.recv(), timeout=_RECV_TIMEOUT_SEC)
            try:
                msg: dict[str, Any] = json.loads(raw)
            except (TypeError, ValueError) as exc:
                logger.warning("ws non-json msg ignored: {r!r}", r=raw[:200])
                continue

            trnm = msg.get("trnm")
            if trnm == "PING":
                # 서버 keepalive — 같은 페이로드를 그대로 echo
                await self._ws.send(json.dumps(msg, ensure_ascii=False))
                continue

            if trnm == expected_trnm:
                if match_seq is None:
                    return msg
                seq_in_msg = str(msg.get("seq", "")).strip()
                # 서버가 seq를 비워서 응답하는 케이스가 있어 빈 값은 일치로 간주.
                # 본 클라이언트는 단일 요청-응답을 순차로 처리하므로 trnm 일치만으로
                # 충분히 안전함.
                if not seq_in_msg or seq_in_msg == match_seq.strip():
                    return msg
                logger.debug(
                    "ws seq mismatch want={w} got={g} — 계속 대기",
                    w=match_seq, g=seq_in_msg,
                )
                continue

            logger.debug("ws unexpected trnm={t} skipped", t=trnm)
