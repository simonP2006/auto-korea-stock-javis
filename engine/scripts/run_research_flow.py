"""researchFlow 통합 실행 진입점.

``reports/<YYYYMMDD>/organizedCompany.md`` 의 모든 종목을
chart60 → chartDay → investor 3단 필터로 검사하고 통과 종목을
``reports/<YYYYMMDD>/researchedCompany.md`` 에 저장한다.

실행::

    python -m scripts.run_research_flow             # 오늘
    python -m scripts.run_research_flow 20260510    # 특정일

종료 코드:
    0 — 정상 저장
    1 — organizedCompany.md 부재 또는 비어있음
    2 — 기타 예외
"""

from __future__ import annotations

import asyncio
import sys

from loguru import logger

from src.kiwoom.researchFlow import ResearchError, research_today
from src.kiwoom.researchFlow.saveReport import save_researched_company


def _summarize(results: list) -> tuple[int, int, int, int]:
    """``(total, passed, mapping_failed, stage_failed)`` 집계."""
    total = len(results)
    passed = sum(1 for r in results if r.final_selected)
    mapping_failed = sum(1 for r in results if r.skip_reason == "코드 매핑 실패")
    stage_failed = total - passed - mapping_failed
    return total, passed, mapping_failed, stage_failed


async def main() -> int:
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    logger.info("researchFlow 통합 시작 date={d}", d=date_arg or "오늘")

    try:
        results = await research_today(date_arg)
    except ResearchError as exc:
        logger.error("진행 불가: {e}", e=exc)
        return 1
    except Exception as exc:
        logger.exception("예상치 못한 예외: {e}", e=exc)
        return 2

    out_path = save_researched_company(results, date=date_arg)
    total, passed, mapping_failed, stage_failed = _summarize(results)

    print(f"saved: {out_path}")
    print(f"total: {total}")
    print(f"passed: {passed}")
    print(f"mapping_failed: {mapping_failed}")
    print(f"stage_failed: {stage_failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
