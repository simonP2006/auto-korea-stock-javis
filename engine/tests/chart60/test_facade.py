"""60분봉 + 60분봉 MA 퍼사드 통합 테스트.

``ChartService`` 를 가짜로 주입하여 네트워크 없이 결합 로직만 검증한다.
MA 는 60분봉 종가의 N 기간 단순이동평균(HTS [0600] 60분봉 MA 와 동일).
"""

from __future__ import annotations

import math

import pandas as pd
import pytest

from src.kiwoom.chart60.getData.facade import (
    get_60min_with_daily_ma,  # 하위 호환 alias 검증용
    get_60min_with_ma,
)
from src.kiwoom.chart60.getData.models import MinuteCandle


class _FakeChart:
    def __init__(self, minute: list[MinuteCandle]) -> None:
        self._minute = minute
        self.minute_calls: list[dict] = []

    async def fetch_minute_60(
        self,
        stk_cd: str,
        base_dt: str | None = None,
        *,
        days: int | None = None,
        bars: int | None = None,
        exchange: str = "sor",
    ) -> list[MinuteCandle]:
        self.minute_calls.append(
            {
                "stk_cd": stk_cd, "base_dt": base_dt,
                "days": days, "bars": bars, "exchange": exchange,
            }
        )
        return self._minute


def _make_minute_series(
    n: int, end_dt: str = "20260509", start_price: int = 1000, step: int = 100,
) -> list[MinuteCandle]:
    """가장 오래된 봉부터 1시간 간격으로 ``n`` 개 60분봉을 만들어 API 순서(최신→과거)로 반환.

    각 봉의 close = ``start_price + i * step`` (i는 가장 오래된 봉부터 0).
    봉의 ts 는 ``end_dt`` 19:00 에서 1시간씩 뒤로 가며 ``n`` 개를 만든다 — 거래시간
    경계는 무시하고 단조 시계열만 보장한다 (MA 검증용 fixture 이므로 충분).
    """
    end_top = pd.Timestamp(f"{end_dt} 19:00:00")
    rows: list[MinuteCandle] = []
    # 가장 오래된 봉(i=0) 부터 시간 오름차순으로 만든 뒤 마지막에 reverse.
    for i in range(n):
        ts = end_top - pd.Timedelta(hours=n - 1 - i)
        rows.append(
            MinuteCandle.model_validate(
                {
                    "cntr_tm": ts.strftime("%Y%m%d%H%M%S"),
                    "cur_prc": str(start_price + i * step),
                }
            )
        )
    rows.reverse()  # API 는 최신→과거 순으로 반환한다고 가정.
    return rows


def _make_minute_for_date(dt: str, hours: list[int], base_price: int = 50000) -> list[MinuteCandle]:
    return [
        MinuteCandle.model_validate(
            {"cntr_tm": f"{dt}{h:02d}0000", "cur_prc": str(base_price + h * 100)}
        )
        for h in hours
    ]


# ─────────────────────────────────────────────────────────────────────────────
# MA 계산 정확성
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_ma10_equals_mean_of_last_10_minute_closes() -> None:
    """HTS 와 일치 — 마지막 봉의 MA10 = 직전 10개 60분봉 종가 평균."""
    # 40봉, 시간 오름차순으로 close = 1000, 1100, ..., 4900 (가장 최신이 4900).
    minute = _make_minute_series(40, end_dt="20260509", start_price=1000, step=100)
    chart = _FakeChart(minute)
    df = await get_60min_with_ma(
        "005930", "20260509", bars=16, ma_windows=(10,), chart=chart,
    )
    # df 는 시간 오름차순 정렬·tail(16). 마지막 봉의 close = 4900.
    assert int(df["close"].iloc[-1]) == 4900
    # 마지막 봉의 MA10 = chronological 마지막 10개 close 평균 = 4000~4900 평균 = 4450.
    expected_ma10 = sum(range(4000, 5000, 100)) / 10
    assert df["ma10"].iloc[-1] == pytest.approx(expected_ma10)
    assert df["ma10"].iloc[-1] == pytest.approx(4450.0)


@pytest.mark.asyncio
async def test_facade_uses_minute_close_for_ma_not_daily() -> None:
    """일봉 fetch 를 호출하지 않는다 (60분봉 종가만 사용)."""
    minute = _make_minute_series(50, end_dt="20260509")
    chart = _FakeChart(minute)
    await get_60min_with_ma(
        "005930", "20260509", bars=4, ma_windows=(10,), chart=chart,
    )
    # 일봉 호출이 없어야 함 (속성 자체가 부재).
    assert not hasattr(chart, "daily_calls")
    # 60분봉 호출은 정확히 1번.
    assert len(chart.minute_calls) == 1


# ─────────────────────────────────────────────────────────────────────────────
# 결과 형태
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_facade_returns_exact_n_bars_in_bars_mode() -> None:
    minute = _make_minute_series(50, end_dt="20260509")
    chart = _FakeChart(minute)
    df = await get_60min_with_ma(
        "005930", "20260509", bars=16, ma_windows=(10,), chart=chart,
    )
    assert len(df) == 16
    assert df["ts"].is_monotonic_increasing
    for col in ("cntr_tm", "ts", "date", "cur_prc", "close", "ma10"):
        assert col in df.columns


@pytest.mark.asyncio
async def test_facade_default_uses_bars_16() -> None:
    minute = _make_minute_series(40, end_dt="20260509")
    chart = _FakeChart(minute)
    df = await get_60min_with_ma(
        "005930", "20260509", ma_windows=(10,), chart=chart,
    )
    assert len(df) == 16
    # 60분봉 호출 시 bars >= max(window) + bars + 마진 으로 늘어났는지.
    assert chart.minute_calls[0]["bars"] >= 16 + 10
    assert chart.minute_calls[0]["days"] is None


@pytest.mark.asyncio
async def test_facade_leaves_nan_when_history_too_short_for_ma() -> None:
    # 5봉만 줘서 MA306 산출 불가 — NaN 이 채워져야 함.
    minute = _make_minute_for_date("20260509", [9, 10, 11, 12, 13])
    chart = _FakeChart(minute)
    df = await get_60min_with_ma(
        "005930", "20260509", bars=5, ma_windows=(3, 306), chart=chart,
    )
    assert df["ma3"].iloc[-1] is not None and not math.isnan(df["ma3"].iloc[-1])
    assert df["ma306"].isna().all()


@pytest.mark.asyncio
async def test_facade_returns_empty_when_no_minute_data() -> None:
    chart = _FakeChart([])
    df = await get_60min_with_ma(
        "005930", "20260509", bars=16, ma_windows=(10,), chart=chart,
    )
    assert df.empty
    # 빈 결과여도 attrs 보존.
    assert df.attrs.get("exchange_label") == "SOR(통합)"


@pytest.mark.asyncio
async def test_facade_trims_to_last_n_dates_in_days_mode() -> None:
    """days 모드: 누적된 60분봉을 가장 최근 N 거래일만 잘라 반환."""
    minute: list[MinuteCandle] = []
    for d in ["20260501", "20260504", "20260505", "20260506",
              "20260507", "20260508", "20260509"]:
        minute.extend(_make_minute_for_date(d, [9, 10]))
    chart = _FakeChart(minute)
    df = await get_60min_with_ma(
        "005930", "20260509", days=3, ma_windows=(2,), chart=chart,
    )
    assert sorted(df["date"].unique().tolist()) == ["20260507", "20260508", "20260509"]
    assert len(df) == 3 * 2


@pytest.mark.asyncio
async def test_facade_rejects_days_and_bars_together() -> None:
    chart = _FakeChart(_make_minute_for_date("20260509", [9, 10]))
    with pytest.raises(ValueError):
        await get_60min_with_ma(
            "005930", "20260509", days=5, bars=16,
            ma_windows=(10,), chart=chart,
        )


# ─────────────────────────────────────────────────────────────────────────────
# 거래소 분기
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_facade_default_exchange_is_sor() -> None:
    minute = _make_minute_series(40, end_dt="20260509")
    chart = _FakeChart(minute)
    df = await get_60min_with_ma(
        "005930", "20260509", bars=4, ma_windows=(2,), chart=chart,
    )
    assert chart.minute_calls[0]["exchange"] == "sor"
    assert df.attrs["exchange_label"] == "SOR(통합)"
    assert df.attrs["api_stk_cd"] == "005930_AL"


@pytest.mark.asyncio
async def test_facade_explicit_krx_exchange() -> None:
    minute = _make_minute_series(40, end_dt="20260509")
    chart = _FakeChart(minute)
    df = await get_60min_with_ma(
        "005930", "20260509", bars=4, ma_windows=(2,),
        exchange="krx", chart=chart,
    )
    assert chart.minute_calls[0]["exchange"] == "krx"
    assert df.attrs["exchange_label"] == "KRX"
    assert df.attrs["api_stk_cd"] == "005930"


# ─────────────────────────────────────────────────────────────────────────────
# 하위 호환
# ─────────────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_legacy_alias_get_60min_with_daily_ma_still_works() -> None:
    """이전 함수명도 동일한 새 구현을 가리켜야 함."""
    minute = _make_minute_series(40, end_dt="20260509")
    chart = _FakeChart(minute)
    df = await get_60min_with_daily_ma(
        "005930", "20260509", bars=4, ma_windows=(2,), chart=chart,
    )
    assert len(df) == 4
    assert df["ma2"].notna().all()
    # 동일 함수 객체.
    assert get_60min_with_daily_ma is get_60min_with_ma
