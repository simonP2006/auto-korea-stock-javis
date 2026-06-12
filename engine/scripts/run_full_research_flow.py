"""researchFlow 통합 풀플로우 실행 진입점 (수집 + 필터 한 번에).

순서::

    ① upperLowerPrice   → reports/<날짜>/upperLowerPrice.md
    ② conditionResearch → reports/<날짜>/conditionResearch.md
    ③ organizedCompany  → reports/<날짜>/organizedCompany.md
    Stage 0 prefetch    → 종목별 chart*·investor·finance.md + prefetchManifest.json
    Stage 1~5 filter    → researchedCompany.md + stage*_passed.md
    C. 탈락사유 분석    → masterReference.md 기반 masterReference.log append

필터 룰만 반복 튜닝하려면 ``scripts/run_prefetch.py`` + ``scripts/run_filters.py``
조합을 사용해 API 호출 없이 필터를 N 회 돌릴 수 있다.

실행::

    python -m scripts.run_full_research_flow             # 오늘
    python -m scripts.run_full_research_flow 20260515    # 특정일

종료 코드:
    0 — 정상 (모든 단계 완료, 또는 ①·② 격리 실패 후 ③·Stage 0·필터 정상)
    1 — ③ organizedCompany 가 0건이거나 진행 불가 → Stage 0/필터 스킵
    2 — 기타 예외
"""

from __future__ import annotations

import asyncio
import sys

from loguru import logger

from src.kiwoom.researchFlow import FullFlowSummary, run_full_flow


def _print_summary(s: FullFlowSummary) -> None:
    print(f"date: {s.date}")
    print(f"① upperLowerPrice   : {s.upper_count} 종목"
          + (f"  (error: {s.upper_error})" if s.upper_error else ""))
    print(f"② conditionResearch : {s.condition_unique_count} 누적고유"
          + (f"  (error: {s.condition_error})" if s.condition_error else ""))
    print(f"③ organizedCompany  : {s.organized_count} 종목"
          + (f"  (error: {s.organize_error})" if s.organize_error else ""))
    if s.skipped_stage:
        print(f"④ researchedCompany : SKIPPED — {s.skip_reason}")
    else:
        total = len(s.research_results)
        passed = s.passed_count
        print(f"④ researchedCompany : 통과 {passed}/{total} 종목")


async def main() -> int:
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    logger.info("run_full_research_flow 시작 date={d}", d=date_arg or "오늘")

    try:
        summary = await run_full_flow(date_arg)
    except Exception as exc:
        logger.exception("예상치 못한 예외: {e}", e=exc)
        return 2

    _print_summary(summary)

    if summary.skipped_stage:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
