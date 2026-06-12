"""researchFlow — 데이터 수집 + 6 Stage 필터 통합 파이프라인.

진입점 세 가지:

1. :func:`prefetch_all` — Stage 0. ``organizedCompany.md`` 의 모든 종목에 대해
   6 개 API (chart60·chart120·chart240·chartDay·investor·finance) 를 일괄
   호출/저장.
2. :func:`filter_today` (= :func:`research_today` 별칭) — Stage 1~5 순수 필터.
   API 호출 없이 Stage 0 결과(.md + prefetchManifest.json)만 보고 판정.
3. :func:`run_full_flow` — ①·②·③ 수집 + Stage 0 + Stage 1~5 + 저장 일괄 실행.

흐름 (run_full_flow)::

    ① upperLowerPrice   → upperLowerPrice.md
    ② conditionResearch → conditionResearch.md
    ③ organizedCompany  → organizedCompany.md
    Stage 0 prefetch    → 종목별 chart*·investor·finance.md + prefetchManifest.json
    Stage 1~5 filter    → researchedCompany.md + stage*_passed.md

흐름 (수집·필터 분리 워크플로우 — 필터 튜닝용)::

    # 1) 하루 1회: 수집만
    python -m scripts.run_prefetch

    # 2) 필터 룰 수정 후 반복 (API 호출 0회)
    python -m scripts.run_filters

사용 예::

    import asyncio
    from src.kiwoom.researchFlow import (
        filter_today, prefetch_all, run_full_flow,
    )

    # (a) 풀플로우 — 수집 + 필터 한 번에
    summary = asyncio.run(run_full_flow())            # 오늘
    summary = asyncio.run(run_full_flow("20260515"))  # 특정일

    # (b) 분리 워크플로우
    asyncio.run(prefetch_all("20260515"))              # 1회 수집
    results = asyncio.run(filter_today("20260515"))    # 필터 반복
"""

from src.kiwoom.researchFlow.facade import (
    ResearchError,
    filter_today,
    research_today,
    run_full_flow,
)
from src.kiwoom.researchFlow.models import (
    FullFlowSummary,
    PrefetchApiName,
    PrefetchApiStatus,
    PrefetchManifest,
    PrefetchStatus,
    ResearchCandidate,
    ResearchResult,
    StageOutcome,
)
from src.kiwoom.researchFlow.name_resolver import build_name_to_code_map
from src.kiwoom.researchFlow.prefetch import PrefetchError, prefetch_all

__all__ = [
    "FullFlowSummary",
    "PrefetchApiName",
    "PrefetchApiStatus",
    "PrefetchError",
    "PrefetchManifest",
    "PrefetchStatus",
    "ResearchCandidate",
    "ResearchError",
    "ResearchResult",
    "StageOutcome",
    "build_name_to_code_map",
    "filter_today",
    "prefetch_all",
    "research_today",
    "run_full_flow",
]
