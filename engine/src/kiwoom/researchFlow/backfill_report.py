"""backfill 계열 CLI 공용 — 필터 산출물 저장 + stage 퍼널 집계.

``run_backfill``(단일 과거일)과 ``run_expert_backfill``(전문가 픽 일괄)이 공유
하는 필터-후 저장 시퀀스와 stage 퍼널 집계를 한 곳에 둔다. ``run_filters.py``
의 저장 시퀀스(researchedCompany + 전 stage passed)를 backfill 루트에 대해
동일 적용하며, 퍼널 카운트는 ``render_stage_passed`` 와 동일 술어로 세어
디스크의 ``stage{N}_passed.md`` 파일 내용과 정확히 일치한다.
"""

from __future__ import annotations

from pathlib import Path
from typing import Final

from src.kiwoom.researchFlow.models import PrefetchStatus, ResearchResult
from src.kiwoom.researchFlow.saveReport import (
    save_all_stages_passed,
    save_researched_company,
)

# 필터 퍼널 라벨 — save_all_stages_passed 의 slot 1~5(데이터 5단계)과 1:1.
# slot 6(finance/Stage5)은 backfill 에서 N/A 판정제외이므로 퍼널에 넣지 않고
# 호출측이 별도 요약 줄로 안내한다.
STAGE_FUNNEL_LABELS: Final[dict[int, str]] = {
    1: "Stage1 chart60_120",
    2: "Stage2 chart240",
    3: "Stage2-1 chartDayPre",
    4: "Stage3 chartDay",
    5: "Stage4 investor",
}


def count_all_data_ok(by_stock: dict[str, PrefetchStatus]) -> int:
    """5 개 데이터 API 전부 ``"ok"`` 인 종목 수(finance 제외)."""
    return sum(
        1 for s in by_stock.values()
        if s.chart60 == "ok" and s.chart120 == "ok" and s.chart240 == "ok"
        and s.chartDay == "ok" and s.investor == "ok"
    )


def stage_funnel(results: list[ResearchResult]) -> list[tuple[str, int]]:
    """데이터 5단계(slot 1~5) 통과 종목 수를 stage 순서대로 반환.

    ``render_stage_passed`` 와 동일 술어(``len(stages) >= slot`` 그리고
    ``stages[slot-1].selected``)로 세므로, 각 카운트는 디스크의
    ``stage{N}_passed.md`` 파일 내용과 정확히 일치한다. 파이프라인이 첫 탈락에서
    끊기므로 카운트는 단조 비증가(진짜 퍼널)이다.
    """
    out: list[tuple[str, int]] = []
    for slot, label in STAGE_FUNNEL_LABELS.items():
        cnt = sum(
            1 for r in results
            if len(r.stages) >= slot and r.stages[slot - 1].selected
        )
        out.append((label, cnt))
    return out


def save_backfill_results(
    results: list[ResearchResult],
    *,
    date: str,
    reports_root: Path,
) -> None:
    """run_filters.py 와 동일한 저장 시퀀스 — researchedCompany + 전 stage passed.

    Args:
        results: ``filter_today`` 반환 리스트.
        date: ``YYYYMMDD``.
        reports_root: backfill 출력 루트.
    """
    save_researched_company(results, date=date, reports_root=reports_root)
    save_all_stages_passed(results, date=date, reports_root=reports_root)


__all__ = [
    "STAGE_FUNNEL_LABELS",
    "count_all_data_ok",
    "save_backfill_results",
    "stage_funnel",
]
