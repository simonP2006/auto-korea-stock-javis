"""run_backfill CLI 헬퍼 단위 검증 — 주말 거부 · 종목 목록 파싱.

CLI 프로세스가 아니라 순수 헬퍼(``_is_weekend`` / ``_parse_stocks_file``)를
직접 검증한다(네트워크·프로세스 없음).
"""

from __future__ import annotations

import argparse
import asyncio

import pytest

import scripts.run_backfill as rb
from scripts.run_backfill import _is_weekend, _parse_stocks_file
from src.kiwoom.researchFlow.backfill import BackfillError
from src.kiwoom.researchFlow.models import (
    PrefetchManifest,
    PrefetchStatus,
    ResearchCandidate,
    ResearchResult,
    StageOutcome,
)

# save_all_stages_passed 가 쓰는 6 개 slot 파일(= run_filters 패리티 대상).
_STAGE_FILES = [
    "stage1_chart60_120_passed.md",
    "stage2_chart240_passed.md",
    "stage2_1_chartDayPre_passed.md",
    "stage3_chartDay_passed.md",
    "stage4_investor_passed.md",
    "stage5_finance_passed.md",
]


def test_is_weekend_saturday_sunday_true() -> None:
    assert _is_weekend("20260620") is True   # 토
    assert _is_weekend("20260621") is True   # 일


def test_is_weekend_weekday_false() -> None:
    assert _is_weekend("20260618") is False  # 목
    assert _is_weekend("20260619") is False  # 금


def test_parse_stocks_file_code_and_name(tmp_path) -> None:
    p = tmp_path / "stocks.txt"
    p.write_text(
        "# 주석 줄\n"
        "005930,삼성전자\n"
        "\n"
        "000660\n",  # NAME 생략 → CODE 를 종목명으로
        encoding="utf-8",
    )
    candidates, code_map = _parse_stocks_file(p)

    assert [(c.stk_cd, c.stk_nm) for c in candidates] == [
        ("005930", "삼성전자"),
        ("000660", "000660"),
    ]
    assert code_map == {"삼성전자": "005930", "000660": "000660"}


def test_parse_stocks_file_missing_raises(tmp_path) -> None:
    with pytest.raises(BackfillError, match="없음"):
        _parse_stocks_file(tmp_path / "nope.txt")


def test_parse_stocks_file_empty_raises(tmp_path) -> None:
    p = tmp_path / "empty.txt"
    p.write_text("# 주석만\n\n", encoding="utf-8")
    with pytest.raises(BackfillError, match="유효한 종목이 없습니다"):
        _parse_stocks_file(p)


# ──────────────────────────────────────────────────────────────────────
# run_filters 패리티 — stage*_passed.md 저장 · 퍼널 카운트
# ──────────────────────────────────────────────────────────────────────


def _stage(name: str, selected: bool) -> StageOutcome:
    return StageOutcome(name=name, selected=selected, category="x", reason="x")  # type: ignore[arg-type]


def _res(name: str, code: str, stages: list[StageOutcome]) -> ResearchResult:
    return ResearchResult(
        candidate=ResearchCandidate(stk_nm=name, stk_cd=code),
        stages=stages,
        final_selected=len(stages) == 6 and all(s.selected for s in stages),
    )


def test_run_backfill_writes_all_stage_files_zero_pass(monkeypatch, tmp_path) -> None:
    # 0-pass 여도 stage{1..5}_passed.md 6 개 파일이 0-byte 로 EXIST 해야 한다
    # (run_filters 패리티 핀 — WHY_REJECTED/탈락분석 흐름이 이 파일에 의존).
    date = "20260618"
    bf = tmp_path / "bf"

    async def _fake_backfill(d, *, stocks=None, reports_root=None, allow_nonbusiness=False):
        m = PrefetchManifest(date=d)
        m.by_stock["005930"] = PrefetchStatus(
            chart60="ok", chart120="ok", chart240="ok",
            chartDay="ok", investor="ok", finance="skipped",
        )
        return m

    async def _fake_filter(d, *, reports_root=None, finance_policy="require", code_map=None):
        # stage1 에서 전량 탈락 → 어떤 stage 도 통과 0.
        return [_res("삼성전자", "005930", [_stage("chart60_120", False)])]

    monkeypatch.setattr(rb, "backfill_prefetch_all", _fake_backfill)
    monkeypatch.setattr(rb, "filter_today", _fake_filter)

    ns = argparse.Namespace(
        date=date, stocks_file=None, reports_root=bf,
        no_filters=False, allow_nonbusiness=False,
    )
    rc = asyncio.run(rb._run(ns))
    assert rc == 0

    for fn in _STAGE_FILES:
        p = bf / date / fn
        assert p.exists(), f"{fn} 미생성 — run_filters 패리티 위반"
        assert p.read_text(encoding="utf-8") == "", f"{fn} 는 0-pass 이므로 0-byte 여야"
    assert (bf / date / "researchedCompany.md").exists()


def test_run_backfill_no_filters_skips_stage_files(monkeypatch, tmp_path) -> None:
    # --no-filters 면 stage 파일도 저장하지 않는다(수집만).
    date = "20260618"
    bf = tmp_path / "bf"

    async def _fake_backfill(d, *, stocks=None, reports_root=None, allow_nonbusiness=False):
        m = PrefetchManifest(date=d)
        m.by_stock["005930"] = PrefetchStatus(finance="skipped")
        return m

    monkeypatch.setattr(rb, "backfill_prefetch_all", _fake_backfill)

    ns = argparse.Namespace(
        date=date, stocks_file=None, reports_root=bf,
        no_filters=True, allow_nonbusiness=False,
    )
    rc = asyncio.run(rb._run(ns))
    assert rc == 0
    assert not (bf / date / "stage1_chart60_120_passed.md").exists()
    assert not (bf / date / "researchedCompany.md").exists()


def test_stage_funnel_counts_on_mixed_results() -> None:
    # A: 데이터 5단계 전부 통과(+finance N/A) → 최종 통과.
    a = _res("A", "1", [
        _stage("chart60_120", True), _stage("chart240", True),
        _stage("chartDayPre", True), _stage("chartDay", True),
        _stage("investor", True), _stage("finance", True),
    ])
    # B: Stage1·2 통과, Stage2-1(chartDayPre) 탈락.
    b = _res("B", "2", [
        _stage("chart60_120", True), _stage("chart240", True),
        _stage("chartDayPre", False),
    ])
    # C: Stage1 즉시 탈락.
    c = _res("C", "3", [_stage("chart60_120", False)])

    funnel = rb._stage_funnel([a, b, c])
    counts = [cnt for _label, cnt in funnel]
    labels = [label for label, _cnt in funnel]

    assert counts == [2, 2, 1, 1, 1]
    # 단조 비증가(진짜 퍼널).
    assert all(counts[i] >= counts[i + 1] for i in range(len(counts) - 1))
    # 라벨 순서/개수(데이터 5단계).
    assert len(funnel) == 5
    assert labels[0].startswith("Stage1")
    assert labels[2].startswith("Stage2-1")
    assert labels[-1].startswith("Stage4")
