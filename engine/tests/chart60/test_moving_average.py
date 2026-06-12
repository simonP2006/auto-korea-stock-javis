"""SMA 계산 정확성 및 경계값 검증."""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.kiwoom.chart60.getData.moving_average import compute_sma


def test_compute_sma_basic_window_3() -> None:
    s = pd.Series([10, 20, 30, 40, 50])
    out = compute_sma(s, 3)

    # 처음 두 값은 NaN, 그 다음부터 (10+20+30)/3, (20+30+40)/3, (30+40+50)/3
    assert math.isnan(out.iloc[0])
    assert math.isnan(out.iloc[1])
    assert out.iloc[2] == 20.0
    assert out.iloc[3] == 30.0
    assert out.iloc[4] == 40.0


def test_compute_sma_window_equals_length() -> None:
    s = pd.Series([1, 2, 3, 4])
    out = compute_sma(s, 4)
    assert math.isnan(out.iloc[2])
    assert out.iloc[3] == 2.5


def test_compute_sma_window_larger_than_data_returns_all_nan() -> None:
    s = pd.Series([1, 2, 3])
    out = compute_sma(s, 10)
    assert out.isna().all()


def test_compute_sma_invalid_window_raises() -> None:
    s = pd.Series([1, 2, 3])
    with pytest.raises(ValueError):
        compute_sma(s, 0)
    with pytest.raises(ValueError):
        compute_sma(s, -1)
