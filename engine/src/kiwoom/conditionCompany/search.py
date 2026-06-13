"""ka10172: 조건검색 요청 일반.

단일 조건식(``seq``) 1개에 대해 매칭 종목 리스트를 받아온다. 응답의
``cont_yn == "Y"`` 인 동안 ``next_key`` 를 따라 페이징 누적한다.

거래소 구분(``stex_tp``)은 KRX(``"K"``) 고정. 모의투자 도메인은 KRX만
지원한다(문서 p.245).
"""

from __future__ import annotations

import asyncio
from typing import Final

from loguru import logger

from src.kiwoom.conditionCompany.models import (
    ConditionResult,
    KiwoomConditionError,
    MatchedStock,
)
from src.kiwoom.conditionCompany.ws_client import KiwoomConditionWebSocket

_API_ID: Final[str] = "ka10172"
_TRNM: Final[str] = "CNSRREQ"
_PAGE_DELAY_SEC: Final[float] = 0.2
_MAX_PAGES: Final[int] = 50


async def search_condition(
    ws: KiwoomConditionWebSocket,
    *,
    seq: str,
    name: str,
    stex_tp: str = "K",
) -> ConditionResult:
    """단일 조건식 검색 + 페이징 누적.

    Args:
        ws: 활성 WebSocket 세션.
        seq: ka10171에서 얻은 조건식 일련번호.
        name: 조건식 명(결과 모델에 그대로 보존).
        stex_tp: 거래소 구분(``"K"`` KRX 고정).

    Returns:
        ``ConditionResult`` — 누적된 매칭 종목 포함.

    Raises:
        KiwoomConditionError: API 오류 응답 또는 응답 형식 이상.
    """
    seq = str(seq).strip()
    stocks: list[MatchedStock] = []
    cont_yn = "N"
    next_key = ""

    for page in range(_MAX_PAGES):
        payload = {
            "trnm": _TRNM,
            "seq": seq,
            "search_type": "0",
            "stex_tp": stex_tp,
            "cont_yn": cont_yn,
            "next_key": next_key,
        }
        msg = await ws.request(
            payload,
            expected_trnm=_TRNM,
            match_seq=seq,
        )

        data = msg.get("data") or []
        if not isinstance(data, list):
            raise KiwoomConditionError(
                code="SHAPE",
                msg=f"data 가 리스트가 아님: {type(data).__name__}",
                api_id=_API_ID,
            )
        for raw in data:
            if isinstance(raw, dict):
                stocks.append(MatchedStock.from_raw(raw))

        cont_yn = str(msg.get("cont_yn", "N")).strip() or "N"
        next_key = str(msg.get("next_key", "")).strip()

        logger.debug(
            "ka10172 page={p} name={n} seq={s} got={g} total={t} cont_yn={c}",
            p=page + 1, n=name, s=seq, g=len(data), t=len(stocks), c=cont_yn,
        )

        if cont_yn != "Y" or not next_key:
            break

        await asyncio.sleep(_PAGE_DELAY_SEC)
    else:
        logger.warning(
            "ka10172 페이징 한계({m}) 도달 name={n} seq={s} total={t}",
            m=_MAX_PAGES, n=name, s=seq, t=len(stocks),
        )

    logger.info(
        "ka10172 완료 name={n} seq={s} 매칭 {t}건",
        n=name, s=seq, t=len(stocks),
    )
    return ConditionResult(seq=seq, name=name, stocks=stocks)
