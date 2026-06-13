"""키움 일봉 차트 + MA — 데이터 취득 서브패키지.

ka10081(주식일봉차트조회)을 호출해 일봉 + MA(10/20/60/306/612)를 결합한
DataFrame을 반환한다.

사용 예::

    import asyncio
    from src.kiwoom.chartDay.getData import get_daily_with_ma

    df = asyncio.run(get_daily_with_ma("005930", "20260509"))
    print(df.tail())
"""

from src.kiwoom.chartDay.getData.chart import ChartService
from src.kiwoom.chartDay.getData.client import KiwoomChartClient
from src.kiwoom.chartDay.getData.facade import get_daily_with_ma
from src.kiwoom.chartDay.getData.models import (
    DailyCandle,
    KiwoomApiError,
)
from src.kiwoom.chartDay.getData.moving_average import compute_sma

__all__ = [
    "ChartService",
    "DailyCandle",
    "KiwoomApiError",
    "KiwoomChartClient",
    "compute_sma",
    "get_daily_with_ma",
]
