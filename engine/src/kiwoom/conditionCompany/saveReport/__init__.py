"""조건검색 결과 마크다운 저장 서브패키지.

저장 위치: ``reports/<오늘 YYYYMMDD>/conditionResearch.md`` (단일 파일).

사용 예::

    from src.kiwoom.conditionCompany.saveReport import save_condition_research

    path = save_condition_research(composite_result)
"""

from src.kiwoom.conditionCompany.saveReport.markdown import (
    render_markdown,
    save_condition_research,
)

__all__ = [
    "render_markdown",
    "save_condition_research",
]
