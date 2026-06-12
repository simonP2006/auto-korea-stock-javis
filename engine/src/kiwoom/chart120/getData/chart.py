"""ka10080(분봉) / ka10081(일봉) 도메인 메서드.

:class:`KiwoomChartClient` 의 페이징 헬퍼 위에 ``stk_cd`` / ``base_dt`` /
``upd_stkpc_tp`` 등 차트 호출에 특화된 파라미터 정리, 종료조건, 그리고
모델 검증을 얹은 얇은 서비스 레이어.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Final

from src.kiwoom._exchange import DEFAULT_EXCHANGE, normalize_stk_cd
from src.kiwoom.chart120.getData.client import KiwoomChartClient
from src.kiwoom.chart120.getData.models import DailyCandle, MinuteCandle

_API_DAILY: Final[str] = "ka10081"
_API_MINUTE: Final[str] = "ka10080"
_LIST_DAILY: Final[str] = "stk_dt_pole_chart_qry"
_LIST_MINUTE: Final[str] = "stk_min_pole_chart_qry"
_BARS_PER_DAY_120M: Final[int] = 4  # 정규장 6.5h 기준 120분봉 ≈ 3~4봉, 여유 포함
_DAILY_MIN_ROWS_DEFAULT: Final[int] = 330  # MA306 산출 + 휴장일 마진
_MINUTE_BARS_DEFAULT: Final[int] = 16  # 가장 최근 120분봉 행 수 기본 (= 4거래일 × 4봉)
_MINUTE_BARS_MARGIN: Final[int] = 4  # 경계 페이지 잘림 방지용 추가 페치


def _today_yyyymmdd() -> str:
    return date.today().strftime("%Y%m%d")


class ChartService:
    """차트 도메인 메서드 묶음.

    Attributes:
        client: 공용 HTTP 클라이언트. 미지정 시 기본 인스턴스 생성.
    """

    def __init__(self, client: KiwoomChartClient | None = None) -> None:
        self.client = client or KiwoomChartClient()

    async def fetch_daily(
        self,
        stk_cd: str,
        base_dt: str | None = None,
        *,
        min_rows: int = _DAILY_MIN_ROWS_DEFAULT,
        exchange: str = DEFAULT_EXCHANGE,
    ) -> list[DailyCandle]:
        """ka10081 일봉을 ``min_rows`` 행 이상 누적 조회.

        Args:
            stk_cd: 종목코드. 평문(``"005930"``) 또는 거래소 접미사 포함.
            base_dt: 기준일자 ``YYYYMMDD``. 미지정 시 오늘 날짜.
            min_rows: 누적 종료 임계값(MA306 + 마진을 고려해 기본 330).
            exchange: 거래소 — ``"sor"`` 통합(기본) / ``"krx"`` / ``"nxt"``.
                HTS 차트(통합) 와 일치시키려면 SOR 사용. ``stk_cd`` 에 이미
                접미사가 있으면 그것이 우선한다.

        Returns:
            ``DailyCandle`` 리스트(API 반환 순서 그대로, 일반적으로 최신→과거).
        """
        api_stk_cd, _ = normalize_stk_cd(stk_cd, exchange)
        body: dict[str, Any] = {
            "stk_cd": api_stk_cd,
            "base_dt": base_dt or _today_yyyymmdd(),
            "upd_stkpc_tp": "1",
        }
        raw = await self.client.post_paged(
            _API_DAILY,
            body,
            _LIST_DAILY,
            stop_when=lambda rows: len(rows) >= min_rows,
        )
        return [DailyCandle.model_validate(r) for r in raw]

    async def fetch_minute_120(
        self,
        stk_cd: str,
        base_dt: str | None = None,
        *,
        days: int | None = None,
        bars: int | None = None,
        exchange: str = DEFAULT_EXCHANGE,
    ) -> list[MinuteCandle]:
        """ka10080 120분봉을 누적 조회.

        ``days`` 또는 ``bars`` 중 하나로 종료 조건을 지정한다. 둘 다 ``None``
        이면 ``bars=16`` (가장 최근 120분봉 16개 = 4거래일분)이 적용된다.
        둘 다 지정하면 ``ValueError`` 를 발생시킨다.

        Args:
            stk_cd: 종목코드.
            base_dt: 기준일자 ``YYYYMMDD``. 미지정 시 오늘.
            days: 확보하려는 거래일 수.
            bars: 확보하려는 120분봉 행 수(가장 최근 기준).

        Returns:
            ``MinuteCandle`` 리스트(API 반환 순서 그대로, 일반적으로 최신→과거).
            ``bars`` 모드의 경우에도 ``bars`` 행보다 다소 많이 반환될 수 있으며
            (페이징 1단위 + 마진), 호출자가 head/tail 로 정확히 잘라 사용한다.

        Raises:
            ValueError: ``days`` 와 ``bars`` 가 동시에 지정된 경우.
        """
        if days is not None and bars is not None:
            raise ValueError("days 와 bars 는 동시에 지정할 수 없습니다")
        if days is None and bars is None:
            bars = _MINUTE_BARS_DEFAULT

        api_stk_cd, _ = normalize_stk_cd(stk_cd, exchange)
        body: dict[str, Any] = {
            "stk_cd": api_stk_cd,
            "tic_scope": "120",
            "upd_stkpc_tp": "1",
            "base_dt": base_dt or _today_yyyymmdd(),
        }

        if bars is not None:
            target_rows = bars + _MINUTE_BARS_MARGIN

            def _stop(rows: list[dict[str, Any]]) -> bool:
                return len(rows) >= target_rows
        else:
            assert days is not None  # for type checkers
            target_rows = days * _BARS_PER_DAY_120M

            def _stop(rows: list[dict[str, Any]]) -> bool:
                # 1차 임계: 누적 행수가 산정치를 넘었는지.
                if len(rows) < target_rows:
                    return False
                # 2차 확정: 거래일 수가 목표를 넘었는지(경계일 완전 수집 보장).
                distinct_dates = {
                    str(r.get("cntr_tm", ""))[:8] for r in rows if r.get("cntr_tm")
                }
                distinct_dates.discard("")
                return len(distinct_dates) > days

        raw = await self.client.post_paged(
            _API_MINUTE,
            body,
            _LIST_MINUTE,
            stop_when=_stop,
        )
        return [MinuteCandle.model_validate(r) for r in raw]
