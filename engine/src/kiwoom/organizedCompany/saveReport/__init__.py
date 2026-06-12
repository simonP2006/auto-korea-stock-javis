"""organizedCompany 결과 저장 서브패키지.

저장 위치: ``reports/<YYYYMMDD>/organizedCompany.md`` (단순 텍스트, 종목명만).

사용 예::

    from src.kiwoom.organizedCompany.saveReport import save_organized_company

    path = save_organized_company(stocks, date="20260510")
"""

from src.kiwoom.organizedCompany.saveReport.plain_text import (
    render_plain_text,
    save_organized_company,
)

__all__ = [
    "render_plain_text",
    "save_organized_company",
]
