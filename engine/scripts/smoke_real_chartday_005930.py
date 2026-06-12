"""실전 서버 스모크 — 삼성전자(005930) 일봉 + MA(10/20/60/306/612) × 16봉.

실행::

    python -m scripts.smoke_real_chartday_005930 [base_dt]

결과는 :func:`src.kiwoom.chartDay.saveReport.save_chartday_markdown` 을 통해
``reports/<오늘 YYYYMMDD>/chartDay.md`` 로 저장된다.
"""

from __future__ import annotations

import asyncio
import sys

from loguru import logger

from src.kiwoom.chartDay import get_daily_with_ma
from src.kiwoom.chartDay.saveReport import save_chartday_markdown

_STK_CD = "005930"
_STK_NAME = "삼성전자"
_BARS = 16


async def main() -> int:
    base_dt_arg = sys.argv[1] if len(sys.argv) > 1 else None
    logger.info("실전 호출 시작 stk_cd={s} base_dt={b}", s=_STK_CD, b=base_dt_arg)

    df = await get_daily_with_ma(_STK_CD, base_dt_arg, bars=_BARS)
    logger.info("응답 행 수: {n}", n=len(df))

    if df.empty:
        logger.warning("빈 결과")
        return 1

    out_path = save_chartday_markdown(df, stk_cd=_STK_CD, stk_name=_STK_NAME)
    logger.info("저장 완료: {p}", p=out_path)

    print(
        df[
            [
                "dt",
                "open_pric",
                "high_pric",
                "low_pric",
                "cur_prc",
                "ma10",
                "ma20",
                "ma60",
                "ma306",
                "ma612",
            ]
        ].to_string(index=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
