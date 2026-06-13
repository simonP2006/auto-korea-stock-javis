"""일봉 차트 + MA(10/20/60/306/612) 결합 퍼사드.

흐름:
    1. ``ChartService.fetch_daily`` 로 ``max(ma_windows) + bars + 마진``
       이상의 일봉을 페이징 누적.
    2. 일봉 종가 시리즈로 MA10/20/60/306/612 계산.
    3. 가장 최근 ``bars`` 행을 시간 오름차순(과거→최신)으로 반환.

(표시 정렬을 내림차순으로 바꾸는 것은 :mod:`src.kiwoom.chartDay.saveReport`
영역의 책임이며, facade 자체는 표준적인 시계열 오름차순을 유지한다.)
"""

from __future__ import annotations

from typing import Final

import pandas as pd
from loguru import logger

from src.kiwoom._exchange import DEFAULT_EXCHANGE, normalize_stk_cd
from src.kiwoom.chartDay.getData.chart import ChartService
from src.kiwoom.chartDay.getData.moving_average import compute_sma

_DEFAULT_MA_WINDOWS: Final[tuple[int, ...]] = (10, 20, 60, 306, 612)
_DEFAULT_BARS: Final[int] = 16
_HISTORY_MARGIN: Final[int] = 24  # 휴장일/거래정지 등 마진


async def get_daily_with_ma(
    stk_cd: str,
    base_dt: str | None = None,
    *,
    bars: int = _DEFAULT_BARS,
    ma_windows: tuple[int, ...] = _DEFAULT_MA_WINDOWS,
    exchange: str = DEFAULT_EXCHANGE,
    chart: ChartService | None = None,
) -> pd.DataFrame:
    """특정 종목의 일봉 차트 + 일봉 종가 기준 MA 결합 결과를 반환한다.

    Args:
        stk_cd: 종목코드(예: ``"005930"``).
        base_dt: 기준일자 ``YYYYMMDD``. ``None`` 이면 오늘 날짜.
        bars: 결과에 포함할 최근 일봉 수(기본 16).
        ma_windows: 일봉 종가 기준 MA 윈도우 튜플(기본 ``(10,20,60,306,612)``).
        chart: 주입용 :class:`ChartService` (테스트/모킹용).

    Returns:
        DataFrame. 컬럼:
            ``dt``, ``open_pric``, ``high_pric``, ``low_pric``, ``cur_prc``,
            ``trde_qty``, ``trde_prica``, ``close``,
            ``ma10``, ``ma20``, ``ma60``, ``ma306``, ``ma612`` (윈도우 미충족 시 NaN).

        시간 오름차순(과거→최신). 행 수는 정확히 ``bars``.
    """
    chart = chart or ChartService()
    api_stk_cd, exchange_label = normalize_stk_cd(stk_cd, exchange)

    min_rows = max(ma_windows) + bars + _HISTORY_MARGIN

    rows = await chart.fetch_daily(stk_cd, base_dt, min_rows=min_rows, exchange=exchange)
    logger.info(
        "stk_cd={s} api_code={a} exchange={e} base_dt={b} fetched daily={d}",
        s=stk_cd, a=api_stk_cd, e=exchange_label, b=base_dt, d=len(rows),
    )

    if not rows:
        logger.warning("일봉 응답 없음 stk_cd={s}", s=stk_cd)
        empty = pd.DataFrame()
        empty.attrs["exchange_label"] = exchange_label
        empty.attrs["api_stk_cd"] = api_stk_cd
        return empty

    df = pd.DataFrame([r.model_dump() for r in rows])
    df["dt"] = df["dt"].astype(str)
    df = df.sort_values("dt").reset_index(drop=True)
    df["close"] = df["cur_prc"]

    for w in ma_windows:
        df[f"ma{w}"] = compute_sma(df["close"], w)

    df = df.tail(bars).reset_index(drop=True)
    df.attrs["exchange_label"] = exchange_label
    df.attrs["api_stk_cd"] = api_stk_cd
    return df
