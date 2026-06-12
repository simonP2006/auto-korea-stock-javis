"""키움 조건검색 모듈 — ka10171/ka10172 (WebSocket).

영웅문4에 사전 등록된 조건검색식 9개를 사용자가 정한 순서대로 호출하여
매칭 종목을 수집하고, 전략 A(순차 누적 제외)를 적용한 통합 결과를
``reports/<YYYYMMDD>/conditionResearch.md`` 한 파일에 저장한다.

사용 예::

    import asyncio
    from src.kiwoom.conditionCompany import run_all_conditions
    from src.kiwoom.conditionCompany.saveReport import save_condition_research

    composite = asyncio.run(run_all_conditions())
    save_condition_research(composite)

기본 실행 순서는 :data:`src.kiwoom.conditionCompany.formulas.EXECUTION_ORDER` 참조.
"""

from src.kiwoom.conditionCompany.conditions import (
    build_name_to_seq,
    fetch_condition_list,
)
from src.kiwoom.conditionCompany.facade import run_all_conditions
from src.kiwoom.conditionCompany.formulas import (
    COMMON_UNIVERSE_NOTE,
    EXECUTION_ORDER,
    FORMULA_DEFINITIONS,
)
from src.kiwoom.conditionCompany.models import (
    CompositeResult,
    ConditionItem,
    ConditionResult,
    FilteredConditionResult,
    KiwoomConditionError,
    MatchedStock,
)
from src.kiwoom.conditionCompany.search import search_condition
from src.kiwoom.conditionCompany.ws_client import KiwoomConditionWebSocket

__all__ = [
    "COMMON_UNIVERSE_NOTE",
    "CompositeResult",
    "ConditionItem",
    "ConditionResult",
    "EXECUTION_ORDER",
    "FORMULA_DEFINITIONS",
    "FilteredConditionResult",
    "KiwoomConditionError",
    "KiwoomConditionWebSocket",
    "MatchedStock",
    "build_name_to_seq",
    "fetch_condition_list",
    "run_all_conditions",
    "search_condition",
]
