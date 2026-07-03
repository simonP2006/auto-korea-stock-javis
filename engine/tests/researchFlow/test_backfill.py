"""backfill(과거일 부분수집) 단위 검증.

네트워크 없이 5 개 fetcher / 5 개 saver 를 모듈 네임스페이스에서 monkeypatch 로
가짜 주입해 backfill 로직만 검증한다:

    - base_dt 가 5 개 데이터 fetcher 전부에 전달되는가.
    - finance 는 호출되지 않고 매니페스트 상태가 "skipped" 인가.
    - 루트 가드가 실스캔 이력을 보호하는가.
    - 유니버스 복원 우선순위(명시 목록 / 동결본 / 부재 오류).
    - resume 가 전 데이터 ok 종목을 재수집하지 않는가.
    - BACKFILL_META.json 이 정직한 collected_at + 올바른 universe_source 로 기록되는가.
    - 분봉 보존범위 사전게이트 / 비거래일 sanity.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pandas as pd
import pytest

import src.kiwoom.researchFlow.backfill as bf
from src.kiwoom.researchFlow.backfill import BackfillError, backfill_prefetch_all
from src.kiwoom.researchFlow.models import (
    PrefetchManifest,
    PrefetchStatus,
    ResearchCandidate,
)
from src.kiwoom.researchFlow.saveReport import save_prefetch_manifest

DATE = "20260618"  # 목요일(거래일)


# ──────────────────────────────────────────────────────────────────────
# 가짜 응답 · monkeypatch 헬퍼
# ──────────────────────────────────────────────────────────────────────


def _minute_df() -> pd.DataFrame:
    """유효 cntr_tm(14자리) 을 가진 비어있지 않은 분봉 DataFrame."""
    return pd.DataFrame(
        {"cntr_tm": [f"{DATE}150000", f"{DATE}143000"], "close": [100, 101]}
    )


def _placeholder_minute_df() -> pd.DataFrame:
    """placeholder(빈응답) — cntr_tm 이 14자리가 아니라 drop 후 empty."""
    return pd.DataFrame({"cntr_tm": [""], "close": [0]})


def _chartday_df(last_dt: str = DATE) -> pd.DataFrame:
    """마지막(최신) 행 dt 가 ``last_dt`` 인 일봉 DataFrame."""
    return pd.DataFrame({"dt": ["20260617", last_dt], "cur_prc": [100, 101]})


def _investor_df() -> pd.DataFrame:
    return pd.DataFrame({"dt": [DATE], "ind_invsr": [1]})


class _Recorder:
    def __init__(self) -> None:
        self.fetch_calls: list[tuple[str, str, str | None, int | None]] = []
        self.save_calls: list[tuple[str, str, object]] = []


def _patch(
    monkeypatch,
    rec: _Recorder,
    *,
    minute_fn=None,
    chartday_df_fn=None,
    investor_fn=None,
) -> None:
    """5 fetcher + 5 saver 를 backfill 네임스페이스에서 가짜로 대체하고 delay 0."""
    minute_fn = minute_fn or (lambda stk_cd: _minute_df())
    chartday_df_fn = chartday_df_fn or (lambda stk_cd: _chartday_df())
    investor_fn = investor_fn or (lambda stk_cd: _investor_df())

    monkeypatch.setattr(bf, "_INTER_API_DELAY", 0.0)
    monkeypatch.setattr(bf, "_INTER_STOCK_DELAY", 0.0)

    def _make_minute(api: str):
        async def _fake(stk_cd, base_dt=None, *, bars=None, days=None, **kw):
            rec.fetch_calls.append((api, stk_cd, base_dt, bars))
            return minute_fn(stk_cd)
        return _fake

    monkeypatch.setattr(bf, "get_60min_with_ma", _make_minute("chart60"))
    monkeypatch.setattr(bf, "get_120min_with_ma", _make_minute("chart120"))
    monkeypatch.setattr(bf, "get_240min_with_ma", _make_minute("chart240"))

    async def _fake_day(stk_cd, base_dt=None, *, bars=None, **kw):
        rec.fetch_calls.append(("chartDay", stk_cd, base_dt, bars))
        return chartday_df_fn(stk_cd)

    monkeypatch.setattr(bf, "get_daily_with_ma", _fake_day)

    async def _fake_inv(stk_cd, *, bars=None, base_dt=None, **kw):
        rec.fetch_calls.append(("investor", stk_cd, base_dt, bars))
        return investor_fn(stk_cd)

    monkeypatch.setattr(bf, "get_investor_flow", _fake_inv)

    def _make_save(api: str):
        def _fake(df, *, stk_cd, stk_name="", output_root=None, now=None):
            rec.save_calls.append((api, stk_cd, output_root))
            return Path(str(output_root))
        return _fake

    for attr, api in (
        ("save_chart60_markdown", "chart60"),
        ("save_chart120_markdown", "chart120"),
        ("save_chart240_markdown", "chart240"),
        ("save_chartday_markdown", "chartDay"),
        ("save_investor_markdown", "investor"),
    ):
        monkeypatch.setattr(bf, attr, _make_save(api))


def _seed_frozen_universe(universe_root: Path, *, date: str = DATE) -> None:
    """동결본 유니버스(organizedCompany.md + conditionResearch.md) 생성."""
    d = universe_root / date
    d.mkdir(parents=True, exist_ok=True)
    (d / "organizedCompany.md").write_text("삼성전자\n", encoding="utf-8")
    (d / "conditionResearch.md").write_text(
        "| # | 종목코드 | 종목명 | 등락률 |\n"
        "|---|---|---|---|\n"
        "| 1 | 005930 | 삼성전자 | +1.5 |\n",
        encoding="utf-8",
    )


# ──────────────────────────────────────────────────────────────────────
# base_dt 배선 · finance skipped
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_backfill_threads_base_dt_into_all_five_fetchers(
    monkeypatch, tmp_path
) -> None:
    rec = _Recorder()
    _patch(monkeypatch, rec)
    stocks = [ResearchCandidate(stk_nm="삼성전자", stk_cd="005930")]

    manifest = await backfill_prefetch_all(
        DATE,
        stocks=stocks,
        reports_root=tmp_path / "bf",
        universe_reports_root=tmp_path / "uni",
    )

    apis_called = {c[0] for c in rec.fetch_calls}
    assert {"chart60", "chart120", "chart240", "chartDay", "investor"} <= apis_called
    # 모든 데이터 fetch 가 base_dt=DATE 로 앵커링.
    assert rec.fetch_calls, "fetcher 가 한 번도 호출되지 않음"
    for api, stk_cd, base_dt, _bars in rec.fetch_calls:
        assert base_dt == DATE, f"{api} base_dt={base_dt} (기대 {DATE})"

    assert manifest.by_stock["005930"].finance == "skipped"


@pytest.mark.asyncio
async def test_finance_never_called_and_status_skipped(monkeypatch, tmp_path) -> None:
    # 구조적 보장: backfill 모듈은 finance API 를 import 조차 하지 않는다.
    assert not hasattr(bf, "get_finance_snapshot")
    assert not hasattr(bf, "save_finance_markdown")

    rec = _Recorder()
    _patch(monkeypatch, rec)
    stocks = [ResearchCandidate(stk_nm="삼성전자", stk_cd="005930")]
    bf_root = tmp_path / "bf"

    manifest = await backfill_prefetch_all(
        DATE, stocks=stocks, reports_root=bf_root,
        universe_reports_root=tmp_path / "uni",
    )

    assert all(s.finance == "skipped" for s in manifest.by_stock.values())
    # finance saver 는 호출되지 않았으므로 어떤 finance.md 도 없어야 한다.
    assert not any(c[0] == "finance" for c in rec.save_calls)


# ──────────────────────────────────────────────────────────────────────
# 루트 가드
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_root_guard_rejects_real_reports_dir() -> None:
    with pytest.raises(BackfillError, match="reports"):
        await backfill_prefetch_all(
            DATE,
            stocks=[ResearchCandidate(stk_nm="삼성전자", stk_cd="005930")],
            reports_root=Path("reports"),
        )


@pytest.mark.asyncio
async def test_root_guard_rejects_same_root(tmp_path) -> None:
    same = tmp_path / "same"
    with pytest.raises(BackfillError, match="동일"):
        await backfill_prefetch_all(
            DATE,
            stocks=[ResearchCandidate(stk_nm="삼성전자", stk_cd="005930")],
            reports_root=same,
            universe_reports_root=same,
        )


# ──────────────────────────────────────────────────────────────────────
# 유니버스 복원 우선순위
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_universe_explicit_stocks_wins(monkeypatch, tmp_path) -> None:
    rec = _Recorder()
    _patch(monkeypatch, rec)
    # 동결본이 존재해도 명시 목록이 우선.
    _seed_frozen_universe(tmp_path / "uni")
    stocks = [ResearchCandidate(stk_nm="사용자종목", stk_cd="000660")]

    await backfill_prefetch_all(
        DATE, stocks=stocks, reports_root=tmp_path / "bf",
        universe_reports_root=tmp_path / "uni",
    )

    meta = json.loads((tmp_path / "bf" / DATE / "BACKFILL_META.json").read_text())
    assert meta["universe_source"] == "user-list"
    # 명시 종목 코드로 수집.
    assert any(c[1] == "000660" for c in rec.fetch_calls)


@pytest.mark.asyncio
async def test_universe_frozen_reuse(monkeypatch, tmp_path) -> None:
    rec = _Recorder()
    _patch(monkeypatch, rec)
    _seed_frozen_universe(tmp_path / "uni")
    bf_root = tmp_path / "bf"

    await backfill_prefetch_all(
        DATE, stocks=None, reports_root=bf_root,
        universe_reports_root=tmp_path / "uni",
    )

    meta = json.loads((bf_root / DATE / "BACKFILL_META.json").read_text())
    assert meta["universe_source"].endswith("organizedCompany.md")
    assert DATE in meta["universe_source"]
    # 동결본에서 코드(005930) 복원 후 수집.
    assert any(c[1] == "005930" for c in rec.fetch_calls)
    # filter 가 backfill 루트에서 이름을 코드로 복원할 수 있도록 매핑 원본 복사됨.
    assert (bf_root / DATE / "conditionResearch.md").exists()
    # 유니버스 목록이 backfill 루트에 기록됨.
    assert (bf_root / DATE / "organizedCompany.md").exists()


@pytest.mark.asyncio
async def test_universe_error_when_neither_source(tmp_path) -> None:
    with pytest.raises(BackfillError, match="과거 유니버스를 복원할 수 없습니다"):
        await backfill_prefetch_all(
            DATE, stocks=None, reports_root=tmp_path / "bf",
            universe_reports_root=tmp_path / "empty_uni",
        )


# ──────────────────────────────────────────────────────────────────────
# resume
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_resume_skips_all_ok_stocks(monkeypatch, tmp_path) -> None:
    rec = _Recorder()
    _patch(monkeypatch, rec)
    bf_root = tmp_path / "bf"

    # 기존 매니페스트: 전 데이터 ok.
    (bf_root / DATE).mkdir(parents=True)
    seed = PrefetchManifest(date=DATE)
    seed.by_stock["005930"] = PrefetchStatus(
        chart60="ok", chart120="ok", chart240="ok",
        chartDay="ok", investor="ok", finance="skipped",
    )
    save_prefetch_manifest(seed, reports_root=bf_root)

    stocks = [ResearchCandidate(stk_nm="삼성전자", stk_cd="005930")]
    manifest = await backfill_prefetch_all(
        DATE, stocks=stocks, reports_root=bf_root,
        universe_reports_root=tmp_path / "uni",
    )

    # chartDay 는 per-stock 루프에서만 호출된다 — resume 스킵이면 0회.
    # (chart60 은 사전 보존게이트 probe 로 1회 호출될 수 있으므로 chartDay 로 판별.)
    chartday_calls = [c for c in rec.fetch_calls if c[0] == "chartDay"]
    assert chartday_calls == []
    # 기존 상태가 매니페스트에 보존.
    assert manifest.by_stock["005930"].chart60 == "ok"


# ──────────────────────────────────────────────────────────────────────
# BACKFILL_META 정직성
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_backfill_meta_has_real_collected_at(monkeypatch, tmp_path) -> None:
    rec = _Recorder()
    _patch(monkeypatch, rec)
    bf_root = tmp_path / "bf"
    stocks = [ResearchCandidate(stk_nm="삼성전자", stk_cd="005930")]

    await backfill_prefetch_all(
        DATE, stocks=stocks, reports_root=bf_root,
        universe_reports_root=tmp_path / "uni",
    )

    meta = json.loads((bf_root / DATE / "BACKFILL_META.json").read_text())
    assert meta["base_date"] == DATE
    assert meta["stocks_total"] == 1
    assert meta["allow_nonbusiness"] is False
    assert meta["note"]
    # collected_at 은 실제 벽시계(=오늘) — 기준일(과거)이 아니다.
    collected = datetime.fromisoformat(meta["collected_at"])
    assert collected.strftime("%Y%m%d") != DATE
    assert collected.strftime("%Y%m%d") == datetime.now().strftime("%Y%m%d")


# ──────────────────────────────────────────────────────────────────────
# 분봉 보존게이트 · 비거래일 sanity
# ──────────────────────────────────────────────────────────────────────


@pytest.mark.asyncio
async def test_retention_gate_raises_when_control_also_empty(
    monkeypatch, tmp_path
) -> None:
    rec = _Recorder()
    # 모든 분봉이 placeholder → drop 후 empty(첫 종목 + 대조군 005930 둘 다).
    _patch(monkeypatch, rec, minute_fn=lambda stk_cd: _placeholder_minute_df())
    stocks = [ResearchCandidate(stk_nm="삼성전자", stk_cd="005930")]

    with pytest.raises(BackfillError, match="보존범위"):
        await backfill_prefetch_all(
            DATE, stocks=stocks, reports_root=tmp_path / "bf",
            universe_reports_root=tmp_path / "uni",
        )


@pytest.mark.asyncio
async def test_nonbusiness_day_raises_without_flag(monkeypatch, tmp_path) -> None:
    rec = _Recorder()
    _patch(monkeypatch, rec, chartday_df_fn=lambda stk_cd: _chartday_df("20260617"))
    stocks = [ResearchCandidate(stk_nm="삼성전자", stk_cd="005930")]

    with pytest.raises(BackfillError, match="거래일"):
        await backfill_prefetch_all(
            DATE, stocks=stocks, reports_root=tmp_path / "bf",
            universe_reports_root=tmp_path / "uni",
        )


@pytest.mark.asyncio
async def test_nonbusiness_day_allowed_records_meta(monkeypatch, tmp_path) -> None:
    rec = _Recorder()
    _patch(monkeypatch, rec, chartday_df_fn=lambda stk_cd: _chartday_df("20260617"))
    bf_root = tmp_path / "bf"
    stocks = [ResearchCandidate(stk_nm="삼성전자", stk_cd="005930")]

    await backfill_prefetch_all(
        DATE, stocks=stocks, reports_root=bf_root,
        universe_reports_root=tmp_path / "uni",
        allow_nonbusiness=True,
    )

    meta = json.loads((bf_root / DATE / "BACKFILL_META.json").read_text())
    assert meta["allow_nonbusiness"] is True
    assert meta["nonbusiness_last_daily_dt"] == "20260617"
