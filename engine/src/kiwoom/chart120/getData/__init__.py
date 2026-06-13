"""키움 120분 차트 + 120분봉 MA — 데이터 취득 서브패키지.

ka10080(주식분봉차트, tic_scope=120)을 호출해 120분봉 종가 기반
MA(10/20/60/306)를 결합한 DataFrame 을 반환한다.

사용 예::

    import asyncio
    from src.kiwoom.chart120.getData import get_120min_with_ma

    df = asyncio.run(get_120min_with_ma("005930", "20260509"))
    print(df.tail())
"""

from src.kiwoom.chart120.getData.chart import ChartService
from src.kiwoom.chart120.getData.client import KiwoomChartClient
from src.kiwoom.chart120.getData.facade import (
    get_120min_with_daily_ma,  # deprecated alias
    get_120min_with_ma,
)
from src.kiwoom.chart120.getData.models import (
    DailyCandle,
    KiwoomApiError,
    MinuteCandle,
)
from src.kiwoom.chart120.getData.moving_average import compute_sma

__all__ = [
    "ChartService",
    "DailyCandle",
    "KiwoomApiError",
    "KiwoomChartClient",
    "MinuteCandle",
    "compute_sma",
    "get_120min_with_daily_ma",  # deprecated
    "get_120min_with_ma",
]
