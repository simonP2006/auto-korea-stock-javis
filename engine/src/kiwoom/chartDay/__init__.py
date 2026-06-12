"""키움 일봉 차트 + MA 모듈 (네임스페이스 패키지).

실제 구현은 :mod:`src.kiwoom.chartDay.getData` 에 있으며, 이 모듈은
하위 호환을 위한 re-export shim 이다.

사용 예::

    import asyncio
    from src.kiwoom.chartDay import get_daily_with_ma

    df = asyncio.run(get_daily_with_ma("005930"))
"""

from src.kiwoom.chartDay.getData import (
    ChartService,
    DailyCandle,
    KiwoomApiError,
    KiwoomChartClient,
    compute_sma,
    get_daily_with_ma,
)

__all__ = [
    "ChartService",
    "DailyCandle",
    "KiwoomApiError",
    "KiwoomChartClient",
    "compute_sma",
    "get_daily_with_ma",
]
