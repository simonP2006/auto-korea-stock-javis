"""키움 보고서 통합 모듈 — conditionResearch + upperLowerPrice 합치기.

오늘자 두 보고서를 읽어 종목명 기준으로 중복 제거하고 등락률 내림차순으로
정렬한 단순 텍스트 리스트를 ``reports/<YYYYMMDD>/organizedCompany.md`` 에
저장한다.

사용 예::

    from src.kiwoom.organizedCompany import organize_today
    from src.kiwoom.organizedCompany.saveReport import save_organized_company

    stocks = organize_today()                 # 오늘
    path = save_organized_company(stocks)
"""

from src.kiwoom.organizedCompany.facade import OrganizeError, organize_today
from src.kiwoom.organizedCompany.models import OrganizedStock, SourceLabel
from src.kiwoom.organizedCompany.parsers import (
    parse_condition_research,
    parse_upper_lower_price,
)

__all__ = [
    "OrganizeError",
    "OrganizedStock",
    "SourceLabel",
    "organize_today",
    "parse_condition_research",
    "parse_upper_lower_price",
]
