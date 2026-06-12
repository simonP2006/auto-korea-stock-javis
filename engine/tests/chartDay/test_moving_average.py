"""chartDay SMA 계산 검증 (chart60과 동일 알고리즘 확인)."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.kiwoom.chartDay.getData.moving_average import compute_sma


def test_compute_sma_basic_window_3() -> None:
    s = pd.Series([10, 20, 30, 40, 50])
    out = compute_sma(s, 3)
    assert math.isnan(out.iloc[0])
    assert math.isnan(out.iloc[1])
    assert out.iloc[2] == 20.0
    assert out.iloc[3] == 30.0
    assert out.iloc[4] == 40.0


def test_compute_sma_window_larger_than_data_returns_all_nan() -> None:
    s = pd.Series([1, 2, 3])
    out = compute_sma(s, 10)
    assert out.isna().all()


def test_compute_sma_invalid_window_raises() -> None:
    s = pd.Series([1, 2, 3])
    with pytest.raises(ValueError):
        compute_sma(s, 0)
