"""120분봉 + 120분봉 종가 기준 MA 퍼사드.

흐름:
    1. ``KiwoomAuth`` 토큰 확보 (``ChartService`` 내부에서 자동).
    2. ``ka10080`` 120분봉을 ``max(ma_windows) + bars + 마진`` 만큼 누적 조회.
    3. 120분봉 종가 시리즈로 MA10/20/60/306 등 SMA 계산.
    4. 가장 최근 ``bars`` 행을 시간 오름차순 DataFrame 으로 반환.
"""

from __future__ import annotations

from typing import Final

import pandas as pd
from loguru import logger

from src.kiwoom._exchange import DEFAULT_EXCHANGE, normalize_stk_cd
from src.kiwoom.chart120.getData.chart import ChartService
from src.kiwoom.chart120.getData.models import MinuteCandle
from src.kiwoom.chart120.getData.moving_average import compute_sma

_DEFAULT_MA_WINDOWS: Final[tuple[int, ...]] = (10, 20, 60, 306)
_DEFAULT_BARS: Final[int] = 16  # 기본 16봉 = 4거래일분 (120분봉 × 4봉/일)
_HISTORY_MARGIN: Final[int] = 24  # 거래소 경계 페이지 잘림·휴장 마진


def _minute_to_df(rows: list[MinuteCandle]) -> pd.DataFrame:
    """분봉 모델 리스트 → 시간 오름차순 DataFrame. ``ts``, ``date``, ``close`` 추가."""
    if not rows:
        return pd.DataFrame(
            columns=[
                "cntr_tm", "ts", "date", "close",
                "cur_prc", "open_pric", "high_pric", "low_pric", "trde_qty",
            ]
        )
    df = pd.DataFrame([r.model_dump() for r in rows])
    df["cntr_tm"] = df["cntr_tm"].astype(str)
    df["ts"] = pd.to_datetime(df["cntr_tm"], format="%Y%m%d%H%M%S")
    df["date"] = df["cntr_tm"].str[:8]
    df = df.sort_values("ts").reset_index(drop=True)
    df["close"] = df["cur_prc"]
    return df


async def get_120min_with_ma(
    stk_cd: str,
    base_dt: str | None = None,
    *,
    days: int | None = None,
    bars: int | None = None,
    ma_windows: tuple[int, ...] = _DEFAULT_MA_WINDOWS,
    exchange: str = DEFAULT_EXCHANGE,
    chart: ChartService | None = None,
) -> pd.DataFrame:
    """특정 종목의 120분봉 + 120분봉 종가 기준 MA 결합 결과를 반환한다.

    ``days`` 또는 ``bars`` 중 하나로 결과 범위를 지정한다. 둘 다 ``None`` 이면
    ``bars=16`` 이 적용되어 가장 최근 120분봉 16개(= 4거래일분)를 반환한다.
    둘 다 지정하면 ``ValueError`` 가 발생한다.

    MA 는 120분봉 종가의 N 기간 단순이동평균(SMA) 이다 (예: ma10 = 직전
    10개 120분봉 종가의 평균).

    Args:
        stk_cd: 종목코드(예: ``"005930"``). 평문 또는 거래소 접미사 포함.
        base_dt: 기준일자 ``YYYYMMDD``. ``None`` 이면 오늘 날짜.
        days: 결과에 포함할 최근 거래일 수.
        bars: 결과에 포함할 최근 120분봉 행 수(기본 모드).
        ma_windows: 120분봉 종가 기준 MA 윈도우 튜플(기본 ``(10,20,60,306)``).
        exchange: 거래소 — ``"sor"`` 통합(기본) / ``"krx"`` / ``"nxt"``.
        chart: 주입용 :class:`ChartService` (테스트/모킹용).

    Returns:
        DataFrame. 컬럼:
            ``cntr_tm``, ``ts``, ``date``, ``close``,
            ``cur_prc``(종가), ``open_pric``, ``high_pric``, ``low_pric``,
            ``trde_qty``,
            ``ma10``, ``ma20``, ``ma60``, ``ma306`` (윈도우 미충족 시 NaN).

        시간 오름차순. ``bars`` 모드에선 정확히 ``bars`` 행. ``attrs`` 에
        ``exchange_label``/``api_stk_cd`` 보존.

    Raises:
        ValueError: ``days`` 와 ``bars`` 가 동시에 지정된 경우.
    """
    if days is not None and bars is not None:
        raise ValueError("days 와 bars 는 동시에 지정할 수 없습니다")
    if days is None and bars is None:
        bars = _DEFAULT_BARS

    chart = chart or ChartService()
    api_stk_cd, exchange_label = normalize_stk_cd(stk_cd, exchange)

    # 가장 큰 MA 윈도우만큼 충분한 봉을 확보 (+ 결과 봉 + 마진).
    if bars is not None:
        target_bars = bars
    else:
        # days 모드는 거래일 단위라 120분봉 단위로 환산할 때 정확하지 않으므로
        # 풍부하게 잡는다.
        assert days is not None
        target_bars = days * 16  # NXT 포함 1거래일 약 3~4봉이지만 여유 확보
    fetch_bars = max(ma_windows) + target_bars + _HISTORY_MARGIN

    minute_rows = await chart.fetch_minute_120(
        stk_cd, base_dt, bars=fetch_bars, exchange=exchange,
    )
    logger.info(
        "stk_cd={s} api_code={a} exchange={e} base_dt={b} mode={mode} fetched minute={m}",
        s=stk_cd, a=api_stk_cd, e=exchange_label, b=base_dt,
        mode=f"bars={bars}" if bars is not None else f"days={days}",
        m=len(minute_rows),
    )

    minute_df = _minute_to_df(minute_rows)
    if minute_df.empty:
        logger.warning("120분봉 응답 없음 stk_cd={s}", s=stk_cd)
        minute_df.attrs["exchange_label"] = exchange_label
        minute_df.attrs["api_stk_cd"] = api_stk_cd
        return minute_df

    # 전체 시리즈에 SMA 적용 (rolling) 후 결과 잘라내기.
    for w in ma_windows:
        minute_df[f"ma{w}"] = compute_sma(minute_df["close"], w)

    if bars is not None:
        result = minute_df.tail(bars)
    else:
        cutoff_dates = sorted(minute_df["date"].unique())[-days:]
        result = minute_df[minute_df["date"].isin(cutoff_dates)]

    result = result.reset_index(drop=True)
    result.attrs["exchange_label"] = exchange_label
    result.attrs["api_stk_cd"] = api_stk_cd
    return result


# 하위 호환 — 이전 이름 유지 (deprecated). 신규 코드는 get_120min_with_ma 사용.
get_120min_with_daily_ma = get_120min_with_ma
