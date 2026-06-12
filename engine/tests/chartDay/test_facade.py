"""chartDay get_daily_with_ma() 결정성 검증.

``ChartService`` 를 가짜로 주입하여 네트워크 없이 MA 계산/tail 로직만 검증.
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.kiwoom.chartDay.getData.facade import get_daily_with_ma
from src.kiwoom.chartDay.getData.models import DailyCandle


class _FakeChart:
    def __init__(self, daily: list[DailyCandle]) -> None:
        self._daily = daily
        self.calls: list[dict] = []

    async def fetch_daily(
        self,
        stk_cd: str,
        base_dt: str | None = None,
        *,
        min_rows: int = 660,
        exchange: str = "sor",
    ) -> list[DailyCandle]:
        self.calls.append(
            {
                "stk_cd": stk_cd, "base_dt": base_dt,
                "min_rows": min_rows, "exchange": exchange,
            }
        )
        return self._daily


def _make_daily(n: int, end: str = "20260509", step: int = 100) -> list[DailyCandle]:
    """``end`` 기준 과거 방향 ``n``개 일봉. close 단조증가."""
    end_ts = pd.Timestamp(end)
    rows: list[DailyCandle] = []
    for i in range(n):
        d = (end_ts - pd.Timedelta(days=n - 1 - i)).strftime("%Y%m%d")
        rows.append(
            DailyCandle.model_validate({"dt": d, "cur_prc": str(1000 + i * step)})
        )
    rows.reverse()  # API는 최신→과거 순으로 반환한다고 가정.
    return rows


@pytest.mark.asyncio
async def test_facade_returns_exact_n_bars_in_ascending_order() -> None:
    daily = _make_daily(700, end="20260509")
    chart = _FakeChart(daily)
    df = await get_daily_with_ma(
        "005930", "20260509", bars=16,
        ma_windows=(10, 20, 60, 306, 612), chart=chart,
    )
    assert len(df) == 16
    # 시간 오름차순 검증.
    assert list(df["dt"]) == sorted(df["dt"])
    # 마지막 행이 최신.
    assert df["dt"].iloc[-1] == "20260509"
    # 모든 MA 컬럼 부착.
    for col in ("ma10", "ma20", "ma60", "ma306", "ma612"):
        assert col in df.columns
    # 700행이면 MA612까지 모두 채워짐.
    for col in ("ma10", "ma20", "ma60", "ma306", "ma612"):
        assert df[col].notna().all()


@pytest.mark.asyncio
async def test_facade_min_rows_includes_max_ma_plus_bars_plus_margin() -> None:
    daily = _make_daily(700, end="20260509")
    chart = _FakeChart(daily)
    await get_daily_with_ma(
        "005930", "20260509", bars=16,
        ma_windows=(10, 20, 60, 306, 612), chart=chart,
    )
    # min_rows = max(MA) + bars + 마진(24) = 612 + 16 + 24 = 652
    assert chart.calls[0]["min_rows"] == 652


@pytest.mark.asyncio
async def test_facade_ma612_nan_when_history_short() -> None:
    # 100일짜리 짧은 히스토리: MA612는 모두 NaN, MA60은 채워짐.
    daily = _make_daily(100, end="20260509")
    chart = _FakeChart(daily)
    df = await get_daily_with_ma(
        "005930", "20260509", bars=16,
        ma_windows=(60, 612), chart=chart,
    )
    assert df["ma60"].notna().all()
    assert df["ma612"].isna().all()
    assert all(math.isnan(v) for v in df["ma612"])


@pytest.mark.asyncio
async def test_facade_default_bars_16_and_default_windows() -> None:
    daily = _make_daily(700, end="20260509")
    chart = _FakeChart(daily)
    df = await get_daily_with_ma("005930", "20260509", chart=chart)
    assert len(df) == 16
    for col in ("ma10", "ma20", "ma60", "ma306", "ma612"):
        assert col in df.columns


@pytest.mark.asyncio
async def test_facade_returns_empty_when_no_data() -> None:
    chart = _FakeChart([])
    df = await get_daily_with_ma("005930", "20260509", chart=chart)
    assert df.empty


@pytest.mark.asyncio
async def test_facade_default_exchange_is_sor() -> None:
    daily = _make_daily(700, end="20260509")
    chart = _FakeChart(daily)
    df = await get_daily_with_ma("005930", "20260509", chart=chart)
    assert chart.calls[0]["exchange"] == "sor"
    assert df.attrs["exchange_label"] == "SOR(통합)"
    assert df.attrs["api_stk_cd"] == "005930_AL"


@pytest.mark.asyncio
async def test_facade_explicit_krx_exchange() -> None:
    daily = _make_daily(700, end="20260509")
    chart = _FakeChart(daily)
    df = await get_daily_with_ma(
        "005930", "20260509", exchange="krx", chart=chart,
    )
    assert chart.calls[0]["exchange"] == "krx"
    assert df.attrs["exchange_label"] == "KRX"
    assert df.attrs["api_stk_cd"] == "005930"
