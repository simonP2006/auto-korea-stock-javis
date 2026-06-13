"""키움 240분 차트 + 240분봉 MA 모듈 (네임스페이스 패키지).

실제 구현은 :mod:`src.kiwoom.chart240.getData` 에 있으며, 이 모듈은
하위 호환을 위한 re-export shim 이다.

사용 예::

    import asyncio
    from src.kiwoom.chart240 import get_240min_with_ma   # 권장
    # 또는
    from src.kiwoom.chart240.getData import get_240min_with_ma

    df = asyncio.run(get_240min_with_ma("005930"))
"""

from src.kiwoom.chart240.getData import (
    ChartService,
    DailyCandle,
    KiwoomApiError,
    KiwoomChartClient,
    MinuteCandle,
    compute_sma,
    get_240min_with_daily_ma,  # deprecated alias
    get_240min_with_ma,
)

__all__ = [
    "ChartService",
    "DailyCandle",
    "KiwoomApiError",
    "KiwoomChartClient",
    "MinuteCandle",
    "compute_sma",
    "get_240min_with_daily_ma",  # deprecated
    "get_240min_with_ma",
]
