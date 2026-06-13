"""ka10081(주식일봉차트) 도메인 메서드.

:class:`KiwoomChartClient` 의 페이징 헬퍼 위에 ``stk_cd`` / ``base_dt`` /
``upd_stkpc_tp`` 등 일봉 호출 파라미터 정리, 종료조건, 모델 검증을 얹은
얇은 서비스 레이어.
"""

from __future__ import annotations

from datetime import date
from typing import Any, Final

from src.kiwoom._exchange import DEFAULT_EXCHANGE, normalize_stk_cd
from src.kiwoom.chartDay.getData.client import KiwoomChartClient
from src.kiwoom.chartDay.getData.models import DailyCandle

_API_DAILY: Final[str] = "ka10081"
_LIST_DAILY: Final[str] = "stk_dt_pole_chart_qry"
_DAILY_MIN_ROWS_DEFAULT: Final[int] = 660  # MA612 + 16봉 + 휴장일 마진


def _today_yyyymmdd() -> str:
    return date.today().strftime("%Y%m%d")


class ChartService:
    """일봉 차트 도메인 메서드.

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
            stk_cd: 종목코드. 평문 또는 거래소 접미사 포함.
            base_dt: 기준일자 ``YYYYMMDD``. 미지정 시 오늘 날짜.
            min_rows: 누적 종료 임계값(MA612 + 결과 16봉 + 마진을 고려해 기본 660).
            exchange: 거래소 — ``"sor"`` 통합(기본) / ``"krx"`` / ``"nxt"``.
                HTS 차트(통합) 와 일치시키려면 SOR 사용.

        Returns:
            ``DailyCandle`` 리스트(API 반환 순서, 일반적으로 최신→과거).
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
