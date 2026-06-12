"""실전 서버 스모크 — 삼성전자(005930) 외국인 보유 동향 × 16 거래일.

실행::

    python -m scripts.smoke_real_foreigner_005930

결과는 ``reports/<오늘 YYYYMMDD>/foreigner.md`` 로 저장된다.
"""

from __future__ import annotations

import asyncio

from loguru import logger

from src.kiwoom.etc.foreigner import (
    get_foreign_holding,
    save_foreigner_markdown,
)

_STK_CD = "005930"
_STK_NAME = "삼성전자"
_BARS = 16


async def main() -> int:
    logger.info("실전 호출 시작 stk_cd={s} bars={b}", s=_STK_CD, b=_BARS)

    df = await get_foreign_holding(_STK_CD, bars=_BARS)
    logger.info("응답 행 수: {n}", n=len(df))

    if df.empty:
        logger.warning("빈 결과")
        return 1

    out_path = save_foreigner_markdown(df, stk_cd=_STK_CD, stk_name=_STK_NAME)
    logger.info("저장 완료: {p}", p=out_path)

    print(
        df[
            [
                "dt",
                "close_pric",
                "trde_qty",
                "chg_qty",
                "poss_stkcnt",
                "wght",
                "frgnr_limit",
                "limit_exh_rt",
            ]
        ].to_string(index=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
