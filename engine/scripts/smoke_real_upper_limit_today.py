"""실전 서버 스모크 — 오늘자 상하한가 종목 스크리너 (ka10017).

기본 필터 (HTS [0162] 상한가/하한가 (통합) 화면 프리셋):
    - 시장: 전체(000)
    - 상하한구분: 상승(2)
    - 정렬: 등락률순(3)
    - 종목조건: ETF+ETN+스팩 제외(2)
    - 거래량: 만주이상(00010)
    - 신용: 전체(0)
    - 매매금: 1천원이상(8)
    - 거래소: 통합(3)

실행::

    python -m scripts.smoke_real_upper_limit_today

결과는 ``reports/<오늘 YYYYMMDD>/upperLowerPrice.md`` 로 저장된다.
"""

from __future__ import annotations

import asyncio

from loguru import logger

from src.kiwoom.upperLowerPrice.upperLowerPrice import (
    UpperLowerPriceFilters,
    get_upper_lower_price,
    save_upper_lower_price_markdown,
)


async def main() -> int:
    filters = UpperLowerPriceFilters()
    logger.info(
        "실전 호출 시작 mrkt={m} updown={u} sort={s} stk_cnd={c}",
        m=filters.mrkt_tp, u=filters.updown_tp, s=filters.sort_tp, c=filters.stk_cnd,
    )

    df = await get_upper_lower_price(filters=filters)
    logger.info("응답 종목 수: {n}", n=len(df))

    if df.empty:
        logger.warning("빈 결과 — 조건 부합 종목 없음")
        out_path = save_upper_lower_price_markdown(df, filters=filters)
        logger.info("빈 리포트 저장: {p}", p=out_path)
        return 0

    out_path = save_upper_lower_price_markdown(df, filters=filters)
    logger.info("저장 완료: {p}", p=out_path)

    print(
        df[
            [
                "stk_cd",
                "stk_nm",
                "cur_prc",
                "flu_rt",
                "pred_pre",
                "trde_qty",
                "cnt",
            ]
        ].to_string(index=False)
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
