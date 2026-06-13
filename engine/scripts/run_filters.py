"""Stage 1~4 순수 필터 진입점 (API 호출 없음).

본 스크립트는 ``run_prefetch.py`` 가 미리 저장해둔 디스크 산출물만 읽어
필터 5 단계를 평가하고 결과를 저장한다.

전제::

    reports/<날짜>/organizedCompany.md       ← run_prefetch 결과
    reports/<날짜>/prefetchManifest.json     ← run_prefetch 결과
    reports/<날짜>/<종목>/chart60.md … investor.md   ← run_prefetch 결과

저장::

    reports/<날짜>/researchedCompany.md
    reports/<날짜>/stage{1,2,2_1,3,4}_*_passed.md

분리한 의도::

    필터 룰 수정 사이클에서 매번 API 를 다시 부르지 않도록
    "수집 1회 / 필터 N회" 워크플로우를 지원하기 위함.

실행::

    python -m scripts.run_filters             # 오늘
    python -m scripts.run_filters 20260515    # 특정일

종료 코드:
    0 — 정상
    1 — organizedCompany.md 또는 prefetchManifest.json 부재/공백
    2 — 기타 예외
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Final

from loguru import logger

from src.kiwoom.researchFlow import ResearchError, filter_today
from src.kiwoom.researchFlow.saveReport import (
    save_all_stages_passed,
    save_researched_company,
)

_DEFAULT_REPORTS_ROOT: Final[Path] = Path("reports")


async def _run(date_arg: str | None) -> int:
    yyyymmdd = date_arg or datetime.now().strftime("%Y%m%d")
    try:
        results = await filter_today(
            date=date_arg, reports_root=_DEFAULT_REPORTS_ROOT,
        )
    except ResearchError as exc:
        logger.error("run_filters 진행 불가: {e}", e=exc)
        print(f"ResearchError: {exc}")
        return 1

    save_researched_company(
        results, date=yyyymmdd, reports_root=_DEFAULT_REPORTS_ROOT,
    )
    save_all_stages_passed(
        results, date=yyyymmdd, reports_root=_DEFAULT_REPORTS_ROOT,
    )

    total = len(results)
    passed = sum(1 for r in results if r.final_selected)
    print(f"date: {yyyymmdd}")
    print(f"researchedCompany : 통과 {passed}/{total} 종목")
    return 0


async def main() -> int:
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    logger.info("run_filters 시작 date={d}", d=date_arg or "오늘")
    try:
        return await _run(date_arg)
    except Exception as exc:
        logger.exception("예상치 못한 예외: {e}", e=exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
