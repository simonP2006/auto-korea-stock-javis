"""Stage 0 일괄 데이터 수집 진입점.

순서::

    ① upperLowerPrice   → reports/<날짜>/upperLowerPrice.md
    ② conditionResearch → reports/<날짜>/conditionResearch.md
    ③ organizedCompany  → reports/<날짜>/organizedCompany.md
    Stage 0 prefetch    → 종목별 chart60·chart120·chart240·chartDay·investor.md
                         + reports/<날짜>/prefetchManifest.json

본 스크립트는 데이터 수집만 수행한다 — Stage 1~4 필터링은 별도
``run_filters.py`` 가 수행한다. 분리한 의도:

    필터 룰 수정 사이클에서 매번 API 를 다시 부르지 않도록
    "수집 1회 / 필터 N회" 워크플로우를 지원하기 위함.

실행::

    python -m scripts.run_prefetch             # 오늘
    python -m scripts.run_prefetch 20260515    # 특정일

종료 코드:
    0 — 정상 (또는 ①·② 격리 실패 후 ③·Stage 0 정상)
    1 — ③ organizedCompany 0건/실패 → Stage 0 스킵
    2 — 기타 예외
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Final

from loguru import logger

from src.kiwoom.conditionCompany import (
    KiwoomConditionError,
    run_all_conditions,
)
from src.kiwoom.conditionCompany.saveReport import save_condition_research
from src.kiwoom.organizedCompany import OrganizeError, organize_today
from src.kiwoom.organizedCompany.saveReport import save_organized_company
from src.kiwoom.researchFlow import PrefetchError, prefetch_all
from src.kiwoom.upperLowerPrice.upperLowerPrice import (
    get_upper_lower_price,
    save_upper_lower_price_markdown,
)

_DEFAULT_REPORTS_ROOT: Final[Path] = Path("reports")
_INTER_STAGE_DELAY: Final[float] = 0.3


def _today_yyyymmdd() -> str:
    return datetime.now().strftime("%Y%m%d")


async def _run(date_arg: str | None) -> int:
    yyyymmdd = date_arg or _today_yyyymmdd()
    if date_arg is None:
        now = datetime.now()
    else:
        current = datetime.now()
        now = datetime.strptime(date_arg, "%Y%m%d").replace(
            hour=current.hour,
            minute=current.minute,
            second=current.second,
        )

    reports_root = _DEFAULT_REPORTS_ROOT
    logger.info("run_prefetch 시작 date={d}", d=yyyymmdd)

    upper_count = 0
    upper_error = ""
    condition_count = 0
    condition_error = ""

    # ① upperLowerPrice
    try:
        df = await get_upper_lower_price()
        save_upper_lower_price_markdown(df, output_root=reports_root, now=now)
        upper_count = len(df)
        logger.info(
            "[run_prefetch ①] upperLowerPrice 저장 — 종목수={n}", n=upper_count,
        )
    except Exception as exc:
        upper_error = f"{type(exc).__name__}: {exc}"
        logger.exception("[run_prefetch ①] upperLowerPrice 실패: {e}", e=exc)

    await asyncio.sleep(_INTER_STAGE_DELAY)

    # ② conditionResearch
    try:
        composite = await run_all_conditions()
        if composite.fetched_at.strftime("%Y%m%d") != yyyymmdd:
            composite.fetched_at = now
        save_condition_research(composite, output_root=reports_root)
        condition_count = composite.total_unique
        logger.info(
            "[run_prefetch ②] conditionResearch 저장 — 누적고유={n}",
            n=condition_count,
        )
    except KiwoomConditionError as exc:
        condition_error = f"KiwoomConditionError: {exc}"
        logger.error("[run_prefetch ②] conditionResearch 실패: {e}", e=exc)
    except Exception as exc:
        condition_error = f"{type(exc).__name__}: {exc}"
        logger.exception("[run_prefetch ②] conditionResearch 예외: {e}", e=exc)

    await asyncio.sleep(_INTER_STAGE_DELAY)

    # ③ organizedCompany
    try:
        stocks = organize_today(date=date_arg, reports_root=reports_root)
    except OrganizeError as exc:
        organized_count = 0
        organize_err = str(exc)
        logger.warning("[run_prefetch ③] organizedCompany 진행 불가: {e}", e=exc)
        print(f"date: {yyyymmdd}")
        print(f"① upperLowerPrice   : {upper_count} 종목"
              + (f"  (error: {upper_error})" if upper_error else ""))
        print(f"② conditionResearch : {condition_count} 누적고유"
              + (f"  (error: {condition_error})" if condition_error else ""))
        print(f"③ organizedCompany  : 0 종목  (error: {organize_err})")
        print("Stage 0 prefetch    : SKIPPED — ③ 실패")
        return 1

    save_organized_company(stocks, date=yyyymmdd, reports_root=reports_root)
    organized_count = len(stocks)
    logger.info(
        "[run_prefetch ③] organizedCompany 저장 — 종목수={n}", n=organized_count,
    )

    if organized_count == 0:
        print(f"date: {yyyymmdd}")
        print(f"① upperLowerPrice   : {upper_count} 종목"
              + (f"  (error: {upper_error})" if upper_error else ""))
        print(f"② conditionResearch : {condition_count} 누적고유"
              + (f"  (error: {condition_error})" if condition_error else ""))
        print(f"③ organizedCompany  : 0 종목")
        print("Stage 0 prefetch    : SKIPPED — ③ 결과 0건")
        return 1

    await asyncio.sleep(_INTER_STAGE_DELAY)

    # Stage 0 prefetch
    try:
        manifest = await prefetch_all(date=date_arg, reports_root=reports_root)
    except PrefetchError as exc:
        logger.error("[run_prefetch Stage 0] 진행 불가: {e}", e=exc)
        print(f"date: {yyyymmdd}")
        print(f"① upperLowerPrice   : {upper_count} 종목")
        print(f"② conditionResearch : {condition_count} 누적고유")
        print(f"③ organizedCompany  : {organized_count} 종목")
        print(f"Stage 0 prefetch    : SKIPPED — {exc}")
        return 1

    all_ok = sum(
        1 for s in manifest.by_stock.values()
        if s.chart60 == "ok" and s.chart120 == "ok"
        and s.chart240 == "ok" and s.chartDay == "ok"
        and s.investor == "ok"
    )

    print(f"date: {yyyymmdd}")
    print(f"① upperLowerPrice   : {upper_count} 종목"
          + (f"  (error: {upper_error})" if upper_error else ""))
    print(f"② conditionResearch : {condition_count} 누적고유"
          + (f"  (error: {condition_error})" if condition_error else ""))
    print(f"③ organizedCompany  : {organized_count} 종목")
    print(f"Stage 0 prefetch    : 전API ok {all_ok}/{len(manifest.by_stock)} 종목")
    return 0


async def main() -> int:
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        return await _run(date_arg)
    except Exception as exc:
        logger.exception("예상치 못한 예외: {e}", e=exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
