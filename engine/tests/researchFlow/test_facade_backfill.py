"""filter_today 의 backfill 부가 파라미터 검증 — finance_policy · code_map.

item filter 6종을 facade 네임스페이스에서 monkeypatch 로 '통과' 가짜로 대체해,
디스크 차트 픽스처 없이 Stage 5 재무 정책과 종목명→코드 매핑 주입만 검증한다.
기본 정책("require")은 현행 동작(재무 결측 → 탈락)을 그대로 유지해야 하므로
회귀 핀으로 함께 고정한다.
"""

from __future__ import annotations

from types import SimpleNamespace

import pytest

import src.kiwoom.researchFlow.facade as facade
from src.kiwoom.researchFlow.facade import filter_today
from src.kiwoom.researchFlow.models import PrefetchManifest, PrefetchStatus
from src.kiwoom.researchFlow.saveReport import save_prefetch_manifest

DATE = "20260618"
NAME = "삼성전자"
CODE = "005930"


def _pass_result(report_attr: str) -> SimpleNamespace:
    ns = SimpleNamespace(selected=True, category="통과", reason="통과(가짜)")
    setattr(ns, report_attr, None)
    return ns


def _patch_filters_pass(monkeypatch) -> None:
    """Stage 1~4(+2-1) item filter 를 전부 통과 가짜로 대체."""
    monkeypatch.setattr(
        facade, "chart60_120_filter_stock",
        lambda stock, *, date_dir=None, reports_root=None: _pass_result("report60_path"),
    )
    for attr in (
        "chart240_filter_stock",
        "chartday_pre_filter_stock",
        "chartday_filter_stock",
        "investor_filter_stock",
    ):
        monkeypatch.setattr(
            facade, attr,
            lambda stock, *, date_dir=None, reports_root=None: _pass_result("report_path"),
        )


def _seed(reports_root, *, finance: str) -> None:
    """organizedCompany.md + prefetchManifest.json 를 심는다(데이터 전부 ok)."""
    d = reports_root / DATE
    d.mkdir(parents=True, exist_ok=True)
    (d / "organizedCompany.md").write_text(f"{NAME}\n", encoding="utf-8")
    manifest = PrefetchManifest(date=DATE)
    manifest.by_stock[CODE] = PrefetchStatus(
        chart60="ok", chart120="ok", chart240="ok",
        chartDay="ok", investor="ok", finance=finance,  # type: ignore[arg-type]
    )
    save_prefetch_manifest(manifest, reports_root=reports_root)


@pytest.mark.asyncio
async def test_skip_na_lets_finance_skipped_stock_pass(monkeypatch, tmp_path) -> None:
    _patch_filters_pass(monkeypatch)
    _seed(tmp_path, finance="skipped")

    results = await filter_today(
        DATE, reports_root=tmp_path,
        finance_policy="skip_na", code_map={NAME: CODE},
    )

    assert len(results) == 1
    r = results[0]
    assert r.final_selected is True
    assert r.stages[-1].name == "finance"
    assert r.stages[-1].selected is True
    assert r.stages[-1].category == "N/A"


@pytest.mark.asyncio
async def test_require_policy_still_fails_finance_skipped(monkeypatch, tmp_path) -> None:
    # 회귀 핀: 기본 정책은 재무 결측 종목을 그대로 탈락시킨다.
    _patch_filters_pass(monkeypatch)
    _seed(tmp_path, finance="skipped")

    results = await filter_today(
        DATE, reports_root=tmp_path, code_map={NAME: CODE},
    )  # finance_policy 기본 = "require"

    r = results[0]
    assert r.final_selected is False
    assert r.stages[-1].name == "finance"
    assert r.stages[-1].selected is False
    assert r.stages[-1].category == "제외"


@pytest.mark.asyncio
async def test_require_policy_unchanged_for_finance_ok(monkeypatch, tmp_path) -> None:
    # finance="ok" 면 skip_na 든 require 든 실제 finance_filter_stock 을 탄다 —
    # 정책 분기가 정상 데이터 경로를 건드리지 않음을 고정.
    _patch_filters_pass(monkeypatch)
    monkeypatch.setattr(
        facade, "finance_filter_stock",
        lambda stock, *, date_dir=None, reports_root=None: _pass_result("report_path"),
    )
    _seed(tmp_path, finance="ok")

    results = await filter_today(
        DATE, reports_root=tmp_path, code_map={NAME: CODE},
    )
    r = results[0]
    assert r.final_selected is True
    assert r.stages[-1].category == "통과"  # 가짜 finance_filter_stock 결과


@pytest.mark.asyncio
async def test_code_map_overrides_name_resolution(monkeypatch, tmp_path) -> None:
    # condition/upper.md 가 없어 build_name_to_code_map 은 빈 매핑을 낸다.
    # code_map 을 주입하면 종목명이 코드로 해소되어 파이프라인에 진입한다.
    _patch_filters_pass(monkeypatch)
    _seed(tmp_path, finance="skipped")

    results = await filter_today(
        DATE, reports_root=tmp_path,
        finance_policy="skip_na", code_map={NAME: CODE},
    )
    r = results[0]
    assert r.candidate.stk_cd == CODE
    assert r.skip_reason == ""
    assert r.final_selected is True


@pytest.mark.asyncio
async def test_without_code_map_and_no_source_skips(monkeypatch, tmp_path) -> None:
    # 대조군: code_map 미주입 + condition/upper.md 부재 → 코드 매핑 실패.
    _patch_filters_pass(monkeypatch)
    _seed(tmp_path, finance="skipped")

    results = await filter_today(DATE, reports_root=tmp_path)  # code_map=None
    r = results[0]
    assert r.candidate.stk_cd == ""
    assert "코드 매핑 실패" in r.skip_reason
