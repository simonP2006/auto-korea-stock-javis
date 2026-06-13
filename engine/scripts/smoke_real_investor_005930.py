"""실전 서버 스모크 — 삼성전자(005930) 투자자·기관 순매수금액 × 16 거래일.

호출 조건: 금액 · 순매수 · 천주 (백만원 단위).

실행::

    python -m scripts.smoke_real_investor_005930

결과는 ``reports/<오늘 YYYYMMDD>/삼성전자(005930)/investor.md`` 로 저장된다.
"""

from __future__ import annotations

import asyncio

from loguru import logger

from src.kiwoom.investor.investor import (
    get_investor_flow,
    save_investor_markdown,
)

_STK_CD = "005930"
_STK_NAME = "삼성전자"
_BARS = 16


async def main() -> int:
    logger.info("실전 호출 시작 stk_cd={s} bars={b}", s=_STK_CD, b=_BARS)

    df = await get_investor_flow(_STK_CD, bars=_BARS)
    logger.info("응답 행 수: {n}", n=len(df))

    if df.empty:
        logger.warning("빈 결과")
        return 1

    out_path = save_investor_markdown(df, stk_cd=_STK_CD, stk_name=_STK_NAME)
    logger.info("저장 완료: {p}", p=out_path)

    print(
        df[["dt", "ind_invsr", "frgnr_invsr", "orgn"]].to_string(index=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
