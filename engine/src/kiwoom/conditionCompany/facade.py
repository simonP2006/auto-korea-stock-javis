"""9개 조건검색식 일괄 실행 + 전략 A(순차 누적 제외).

흐름:
    1. WebSocket 연결 + LOGIN
    2. ka10171 → ``{name: seq}`` 매핑 획득 (9개 이름 모두 있는지 검증)
    3. ``EXECUTION_ORDER`` 순서대로 ka10172 호출
    4. 누적 본 종목 코드 set을 유지하면서, 매 조건식의 결과에서
       이미 본 종목을 제거(=전략 A: 먼저 잡힌 자가 임자)
    5. ``CompositeResult`` 반환

전략 A 정의(사용자 확정):
    - 기본1 → 매칭 전부 채택
    - 기본2 → 기본1에 등장한 종목 제외
    - 기본3 → 기본1∪기본2 에 등장한 종목 제외
    - ... (이하 동일)
    - ZONE1 → 다른 8개 조건에 한 번도 등장하지 않은 종목만
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Final

from loguru import logger

from src.kiwoom.conditionCompany.conditions import build_name_to_seq
from src.kiwoom.conditionCompany.formulas import EXECUTION_ORDER
from src.kiwoom.conditionCompany.models import (
    CompositeResult,
    FilteredConditionResult,
    KiwoomConditionError,
)
from src.kiwoom.conditionCompany.search import search_condition
from src.kiwoom.conditionCompany.ws_client import KiwoomConditionWebSocket

# 키움은 CNSRREQ TR에 짧은 간격 호출 제한(코드 105110)을 둔다.
# 9개 조건식을 순차 호출 시 호출 간 최소 간격 확보를 위한 슬리프.
_INTER_REQUEST_DELAY_SEC: Final[float] = 1.0


async def run_all_conditions(
    *,
    execution_order: tuple[str, ...] | list[str] = EXECUTION_ORDER,
    stex_tp: str = "K",
    ws: KiwoomConditionWebSocket | None = None,
) -> CompositeResult:
    """9개 조건식을 순차 실행하고 전략 A를 적용해 통합 결과를 반환한다.

    Args:
        execution_order: 실행 순서 조건명 리스트(기본: 사용자 확정 9개).
        stex_tp: 거래소 구분(``"K"`` KRX 고정).
        ws: 외부에서 주입할 WebSocket 세션. ``None`` 이면 내부에서 생성/종료.

    Returns:
        :class:`CompositeResult` — 조건별 raw_count/kept stocks 누적, missing 포함.

    Raises:
        KiwoomConditionError: ka10171 결과에 필수 조건명이 없거나 호출 실패.
    """
    order = list(execution_order)
    fetched_at = datetime.now()

    if ws is not None:
        return await _run(ws, order, stex_tp, fetched_at)

    async with KiwoomConditionWebSocket() as session:
        return await _run(session, order, stex_tp, fetched_at)


async def _run(
    ws: KiwoomConditionWebSocket,
    order: list[str],
    stex_tp: str,
    fetched_at: datetime,
) -> CompositeResult:
    name_to_seq = await build_name_to_seq(ws, required_names=order)

    seen: set[str] = set()
    results: list[FilteredConditionResult] = []
    missing: list[str] = []

    for idx, name in enumerate(order, 1):
        seq = name_to_seq.get(name)
        if seq is None:
            # build_name_to_seq 에서 사전 검증되지만 안전망으로 한번 더
            missing.append(name)
            logger.error("실행 불가(서버 목록에 없음): {n}", n=name)
            continue

        # 첫 호출이 아니면 키움 CNSRREQ rate limit 회피용 슬리프
        if idx > 1:
            await asyncio.sleep(_INTER_REQUEST_DELAY_SEC)

        logger.info(
            "[{i}/{t}] {n} 실행 (seq={s})",
            i=idx, t=len(order), n=name, s=seq,
        )

        try:
            result = await search_condition(
                ws, seq=seq, name=name, stex_tp=stex_tp,
            )
        except KiwoomConditionError as exc:
            logger.error("조건식 실행 실패 name={n} seq={s} err={e}", n=name, s=seq, e=exc)
            raise

        # 전략 A: 이미 본 종목은 제외, 새 종목만 남김
        kept = []
        for stock in result.stocks:
            if stock.stk_cd in seen:
                continue
            seen.add(stock.stk_cd)
            kept.append(stock)

        filtered = FilteredConditionResult(
            seq=seq,
            name=name,
            raw_count=result.count,
            stocks=kept,
        )
        results.append(filtered)

        logger.info(
            "[{i}/{t}] {n} raw={r} → 누적후 {k}건 (제외 {x}건)",
            i=idx, t=len(order), n=name,
            r=filtered.raw_count, k=filtered.kept_count, x=filtered.excluded_count,
        )

    logger.info(
        "전체 완료: {c}개 조건, 고유 누적 종목 {u}건, 누락 {m}건",
        c=len(results), u=len(seen), m=len(missing),
    )

    return CompositeResult(
        fetched_at=fetched_at,
        execution_order=order,
        results=results,
        missing=missing,
    )
