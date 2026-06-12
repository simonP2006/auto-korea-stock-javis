"""240분 차트 분석 결과의 리포트 저장 서브패키지.

저장 위치는 함수 호출 시점의 시스템 일자(``YYYYMMDD``) 디렉터리이며,
파일명은 ``chart240.md`` 로 고정된다.

사용 예::

    from src.kiwoom.chart240.saveReport import save_chart240_markdown

    path = save_chart240_markdown(df, stk_cd="005930", stk_name="삼성전자")
"""

from src.kiwoom.chart240.saveReport.markdown import (
    render_markdown,
    save_chart240_markdown,
)

__all__ = [
    "render_markdown",
    "save_chart240_markdown",
]
