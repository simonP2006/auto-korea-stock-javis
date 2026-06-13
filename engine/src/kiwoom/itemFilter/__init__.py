"""종목 필터 모듈.

기존 ``reports/<YYYYMMDD>/<종목명(종목코드)>/`` 하위 리포트를 입력으로 받아
조건에 부합하는 종목을 선별한다.

서브모듈:
    - :mod:`chart60Filter`     — chart60.md (60분봉 MA) 기반 필터
    - :mod:`chart60_120Filter` — chart60.md + chart120.md 결합 (4 Type) 필터
    - :mod:`chart240Filter`    — chart240.md (240분봉 장기추세) 기반 필터
    - :mod:`chartDayPreFilter` — chartDay.md (금일 일봉 급상승 제외) 사전 필터
    - :mod:`chartDayFilter`    — chartDay.md (일봉 MA) 기반 필터
    - :mod:`investorFilter`    — investor.md (투자자 수급) 기반 필터
    - :mod:`financeFilter`     — finance.md (당기순이익 적자 제외) 기반 필터

이름 충돌 방지를 위해 ``filter_stock``/``filter_all_stocks`` 등 모듈별 함수는
별칭으로 re-export 한다::

    from src.kiwoom.itemFilter import (
        chart60_filter_stock,     chart60_filter_all_stocks,
        chart60_120_filter_stock, chart60_120_filter_all_stocks,
        chart240_filter_stock,    chart240_filter_all_stocks,
        chartday_filter_stock,    chartday_filter_all_stocks,
        investor_filter_stock,    investor_filter_all_stocks,
        finance_filter_stock,     finance_filter_all_stocks,
    )

또는 서브모듈을 직접 import 해도 된다::

    from src.kiwoom.itemFilter.investorFilter import filter_stock
    r = filter_stock("005930")
"""

from src.kiwoom.itemFilter.chart60Filter import (
    Chart60Bar,
    Chart60FilterResult,
    evaluate_chart60,
)
from src.kiwoom.itemFilter.chart60Filter import (
    filter_all_stocks as chart60_filter_all_stocks,
)
from src.kiwoom.itemFilter.chart60Filter import (
    filter_stock as chart60_filter_stock,
)
from src.kiwoom.itemFilter.chart60Filter import (
    parse_chart60_md,
    save_chart60_filter_markdown,
)
from src.kiwoom.itemFilter.chart60_120Filter import (
    Chart120Bar,
    Chart60_120FilterResult,
    evaluate_chart60_120,
)
from src.kiwoom.itemFilter.chart60_120Filter import (
    filter_all_stocks as chart60_120_filter_all_stocks,
)
from src.kiwoom.itemFilter.chart60_120Filter import (
    filter_stock as chart60_120_filter_stock,
)
from src.kiwoom.itemFilter.chart60_120Filter import (
    parse_chart120_md,
    save_chart60_120_filter_markdown,
)
from src.kiwoom.itemFilter.chart240Filter import (
    Chart240Bar,
    Chart240FilterResult,
    evaluate_chart240,
)
from src.kiwoom.itemFilter.chart240Filter import (
    filter_all_stocks as chart240_filter_all_stocks,
)
from src.kiwoom.itemFilter.chart240Filter import (
    filter_stock as chart240_filter_stock,
)
from src.kiwoom.itemFilter.chart240Filter import (
    parse_chart240_md,
    save_chart240_filter_markdown,
)
from src.kiwoom.itemFilter.chartDayFilter import (
    ChartDayBar,
    ChartDayFilterResult,
    evaluate_chartday,
)
from src.kiwoom.itemFilter.chartDayFilter import (
    filter_all_stocks as chartday_filter_all_stocks,
)
from src.kiwoom.itemFilter.chartDayFilter import (
    filter_stock as chartday_filter_stock,
)
from src.kiwoom.itemFilter.chartDayFilter import (
    parse_chartday_md,
    save_chartday_filter_markdown,
)
from src.kiwoom.itemFilter.chartDayPreFilter import (
    ChartDayPreFilterResult,
    evaluate_chartday_pre,
)
from src.kiwoom.itemFilter.chartDayPreFilter import (
    filter_all_stocks as chartday_pre_filter_all_stocks,
)
from src.kiwoom.itemFilter.chartDayPreFilter import (
    filter_stock as chartday_pre_filter_stock,
)
from src.kiwoom.itemFilter.chartDayPreFilter import (
    save_chartday_pre_filter_markdown,
)
from src.kiwoom.itemFilter.investorFilter import (
    InvestorBar,
    InvestorFilterResult,
    evaluate_investor,
)
from src.kiwoom.itemFilter.investorFilter import (
    filter_all_stocks as investor_filter_all_stocks,
)
from src.kiwoom.itemFilter.investorFilter import (
    filter_stock as investor_filter_stock,
)
from src.kiwoom.itemFilter.investorFilter import (
    parse_investor_md,
    save_investor_filter_markdown,
)
from src.kiwoom.itemFilter.financeFilter import (
    FinanceFilterResult,
    evaluate_finance,
)
from src.kiwoom.itemFilter.financeFilter import (
    filter_all_stocks as finance_filter_all_stocks,
)
from src.kiwoom.itemFilter.financeFilter import (
    filter_stock as finance_filter_stock,
)
from src.kiwoom.itemFilter.financeFilter import (
    parse_finance_md,
    save_finance_filter_markdown,
)

__all__ = [
    "Chart120Bar",
    "Chart240Bar",
    "Chart240FilterResult",
    "Chart60Bar",
    "Chart60FilterResult",
    "Chart60_120FilterResult",
    "ChartDayBar",
    "ChartDayFilterResult",
    "ChartDayPreFilterResult",
    "FinanceFilterResult",
    "InvestorBar",
    "InvestorFilterResult",
    "chart240_filter_all_stocks",
    "chart240_filter_stock",
    "chart60_120_filter_all_stocks",
    "chart60_120_filter_stock",
    "chart60_filter_all_stocks",
    "chart60_filter_stock",
    "chartday_filter_all_stocks",
    "chartday_filter_stock",
    "chartday_pre_filter_all_stocks",
    "chartday_pre_filter_stock",
    "evaluate_chart240",
    "evaluate_chart60",
    "evaluate_chart60_120",
    "evaluate_chartday",
    "evaluate_chartday_pre",
    "evaluate_finance",
    "evaluate_investor",
    "finance_filter_all_stocks",
    "finance_filter_stock",
    "investor_filter_all_stocks",
    "investor_filter_stock",
    "parse_chart120_md",
    "parse_chart240_md",
    "parse_chart60_md",
    "parse_chartday_md",
    "parse_finance_md",
    "parse_investor_md",
    "save_chart240_filter_markdown",
    "save_chart60_120_filter_markdown",
    "save_chart60_filter_markdown",
    "save_chartday_filter_markdown",
    "save_chartday_pre_filter_markdown",
    "save_finance_filter_markdown",
    "save_investor_filter_markdown",
]
