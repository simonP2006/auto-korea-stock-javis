"""단순이동평균(SMA) 계산 유틸.

별도 의존(예: ``ta`` 라이브러리)을 도입하지 않고 pandas의 ``rolling`` 만으로
충분하므로 얇은 함수 한 개만 노출한다.
"""

from __future__ import annotations

import pandas as pd


def compute_sma(closes: pd.Series, window: int) -> pd.Series:
    """오래된→최신 정렬된 종가 시리즈의 단순이동평균을 반환한다.

    윈도우 미만 구간은 NaN(``min_periods=window``)으로 채워 정확성을
    우선한다. MA306 같은 장기 이평이 데이터 부족으로 손상되는 것을 막기
    위함.

    Args:
        closes: 종가 시리즈. 인덱스/순서는 호출자 책임으로 오래→최신이어야 함.
        window: 이동평균 구간(거래일 수).

    Returns:
        같은 길이의 SMA 시리즈. 앞쪽 ``window-1`` 행은 NaN.

    Raises:
        ValueError: ``window < 1`` 일 때.
    """
    if window < 1:
        raise ValueError(f"window must be >= 1, got {window}")
    return closes.rolling(window=window, min_periods=window).mean()
