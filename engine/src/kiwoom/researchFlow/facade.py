"""researchFlow 오케스트레이터.

본 모듈은 세 진입점을 제공한다:

1. :func:`filter_today` — Stage 0 (prefetch) 결과를 입력으로 6 Stage 필터만
   순수하게 실행한다. API 호출 없음 — 디스크의 .md + PrefetchManifest 만
   사용. 필터 룰을 반복 튜닝하는 워크플로우용.
2. :func:`research_today` — :func:`filter_today` 의 별칭. (구버전 명칭 유지.)
3. :func:`run_full_flow` — ①·② 수집 → ③ 통합 → Stage 0 일괄 수집 →
   Stage 1~5 필터 → 결과 저장 까지 한 번에 실행하는 풀플로우.

──────────────────────────────────────────────────────────────────────
구조 변경 요약 (2026-05 재설계):
    - 기존: 각 Stage 가 API 호출 + 저장 + 필터를 모두 수행.
    - 신규: Stage 0 (``prefetch.prefetch_all``) 가 종목 전체에 대해
      6 개 API 를 미리 호출/저장하고 ``PrefetchManifest`` 를 남긴다.
      Stage 1~5 는 API 호출 없이 .md 와 매니페스트만 보고 판정한다.

filter_today 흐름 (6 Stage 묶음):
    1. ``reports/<YYYYMMDD>/organizedCompany.md`` 존재 확인 후 종목명 로드.
    2. ``conditionResearch.md`` / ``upperLowerPrice.md`` 에서 종목명→종목코드
       매핑 빌드 (``name_resolver``).
    3. ``prefetchManifest.json`` 로드 — 없으면 ``ResearchError``.
    4. 각 종목에 대해 다음 6 Stage 순차 평가:
        Stage 1   chart60_120Filter
        Stage 2   chart240Filter
        Stage 2-1 chartDayPreFilter   (금일 일봉 +10% 이상 사전 차단)
        Stage 3   chartDayFilter
        Stage 4   investorFilter
        Stage 5   financeFilter        (당기순이익 < 0 적자 제외)
       각 Stage 진입 전 매니페스트에서 해당 API 상태가 "ok" 가 아니면
       즉시 실패 처리. 어느 Stage 든 selected=False 면 break.
    5. 모든 Stage 통과 종목만 ``ResearchResult.final_selected=True``.

run_full_flow 흐름 (수집 + 필터 통합):
    ① upperLowerPrice   → reports/<날짜>/upperLowerPrice.md
    ② conditionResearch → reports/<날짜>/conditionResearch.md
    ③ organizedCompany  → reports/<날짜>/organizedCompany.md
    Stage 0 prefetch    → reports/<날짜>/<종목>/chart*·investor·finance.md
                         + prefetchManifest.json
    Stage 1~5 filter    → researchedCompany.md + stage*_passed.md
    C. 탈락사유 분석    → masterReference.md 기반 masterReference.log append

오류 격리:
    - ①·② 단계는 try/except 격리 — 한쪽 실패해도 ③ 진행.
    - ③ 0건 또는 OrganizeError → 이후 단계 스킵, ``skipped_stage`` 기록.
    - Stage 0 ``PrefetchError`` → 필터 단계 스킵.
    - Stage 1~5 종목별 예외는 종목 단위로 격리.

API 호출 페이싱 (Stage 0 내부, ``prefetch`` 모듈 책임):
    - 종목 내 API 사이 0.3 초, 종목 사이 0.5 초.
    - rate limit (1700) / 토큰 만료 (8005) 는 각 클라이언트가 자동 재시도.

필터 단계는 디스크 IO + CPU 만 사용하므로 단계 사이/종목 사이 sleep 없음.
"""

from __future__ import annotations

import asyncio
from datetime import datetime
from pathlib import Path
from typing import Final

from loguru import logger

from src.kiwoom.conditionCompany import (
    KiwoomConditionError,
    run_all_conditions,
)
from src.kiwoom.conditionCompany.saveReport import save_condition_research
from src.kiwoom.itemFilter import (
    chart60_120_filter_stock,
    chart240_filter_stock,
    chartday_filter_stock,
    chartday_pre_filter_stock,
    finance_filter_stock,
    investor_filter_stock,
)
from src.kiwoom.organizedCompany import OrganizeError, organize_today
from src.kiwoom.organizedCompany.saveReport import save_organized_company
from src.kiwoom.researchFlow.models import (
    FullFlowSummary,
    PrefetchManifest,
    PrefetchStatus,
    ResearchCandidate,
    ResearchResult,
    StageOutcome,
)
from src.kiwoom.researchFlow.name_resolver import build_name_to_code_map
from src.kiwoom.researchFlow.prefetch import PrefetchError, prefetch_all
from src.kiwoom.researchFlow.saveReport import (
    load_prefetch_manifest,
    save_all_stages_passed,
    save_researched_company,
)
from src.kiwoom.upperLowerPrice.upperLowerPrice import (
    get_upper_lower_price,
    save_upper_lower_price_markdown,
)

_DEFAULT_REPORTS_ROOT: Final[Path] = Path("reports")
_ORGANIZED_FILE: Final[str] = "organizedCompany.md"

_INTER_STAGE_DELAY: Final[float] = 0.3  # 수집 단계 ①·②·③ 사이만 사용


class ResearchError(RuntimeError):
    """입력 부재 등 진행 불가 오류."""


def _today_yyyymmdd() -> str:
    return datetime.now().strftime("%Y%m%d")


def _load_stock_names(path: Path) -> list[str]:
    """organizedCompany.md 에서 종목명 줄단위 로드 (빈 줄 무시)."""
    text = path.read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


# ──────────────────────────────────────────────────────────────────────
# Stage 1~5 — 순수 필터 (API 호출 없음, manifest + 디스크 .md 만 사용)
# ──────────────────────────────────────────────────────────────────────


def _missing_data_outcome(
    stage_name: str,
    api_status: str,
) -> StageOutcome:
    """매니페스트 상태가 ``"ok"`` 가 아닐 때 즉시 실패 outcome 생성."""
    reason_map = {
        "empty": "API 응답 없음 (Stage 0 빈응답)",
        "error": "API 호출 실패 (Stage 0 예외)",
    }
    return StageOutcome(
        name=stage_name,  # type: ignore[arg-type]
        selected=False,
        category="제외",
        reason=reason_map.get(api_status, f"Stage 0 상태={api_status}"),
    )


def _filter_stage_chart60_120(
    cand: ResearchCandidate,
    *,
    date_dir: str,
    status: PrefetchStatus,
) -> StageOutcome:
    """Stage 1 — chart60·chart120 .md 만 보고 chart60_120Filter 평가."""
    if status.chart60 != "ok":
        return _missing_data_outcome("chart60_120", status.chart60)
    if status.chart120 != "ok":
        return _missing_data_outcome("chart60_120", status.chart120)
    r = chart60_120_filter_stock(cand.stk_cd, date_dir=date_dir)
    return StageOutcome(
        name="chart60_120",
        selected=r.selected,
        category=r.category,
        reason=r.reason,
        report_path=r.report60_path,
    )


def _filter_stage_chart240(
    cand: ResearchCandidate,
    *,
    date_dir: str,
    status: PrefetchStatus,
) -> StageOutcome:
    """Stage 2 — chart240.md 만 보고 chart240Filter 평가."""
    if status.chart240 != "ok":
        return _missing_data_outcome("chart240", status.chart240)
    r = chart240_filter_stock(cand.stk_cd, date_dir=date_dir)
    return StageOutcome(
        name="chart240",
        selected=r.selected,
        category=r.category,
        reason=r.reason,
        report_path=r.report_path,
    )


def _filter_stage_chartday_pre(
    cand: ResearchCandidate,
    *,
    date_dir: str,
    status: PrefetchStatus,
) -> StageOutcome:
    """Stage 2-1 — chartDay.md 만 보고 chartDayPreFilter 평가."""
    if status.chartDay != "ok":
        return _missing_data_outcome("chartDayPre", status.chartDay)
    r = chartday_pre_filter_stock(cand.stk_cd, date_dir=date_dir)
    return StageOutcome(
        name="chartDayPre",
        selected=r.selected,
        category=r.category,
        reason=r.reason,
        report_path=r.report_path,
    )


def _filter_stage_chartday(
    cand: ResearchCandidate,
    *,
    date_dir: str,
    status: PrefetchStatus,
) -> StageOutcome:
    """Stage 3 — chartDay.md 만 보고 chartDayFilter 평가."""
    if status.chartDay != "ok":
        return _missing_data_outcome("chartDay", status.chartDay)
    r = chartday_filter_stock(cand.stk_cd, date_dir=date_dir)
    return StageOutcome(
        name="chartDay",
        selected=r.selected,
        category=r.category,
        reason=r.reason,
        report_path=r.report_path,
    )


def _filter_stage_investor(
    cand: ResearchCandidate,
    *,
    date_dir: str,
    status: PrefetchStatus,
) -> StageOutcome:
    """Stage 4 — investor.md 만 보고 investorFilter 평가."""
    if status.investor != "ok":
        return _missing_data_outcome("investor", status.investor)
    r = investor_filter_stock(cand.stk_cd, date_dir=date_dir)
    return StageOutcome(
        name="investor",
        selected=r.selected,
        category=r.category,
        reason=r.reason,
        report_path=r.report_path,
    )


def _filter_stage_finance(
    cand: ResearchCandidate,
    *,
    date_dir: str,
    status: PrefetchStatus,
) -> StageOutcome:
    """Stage 5 — finance.md 만 보고 financeFilter 평가."""
    if status.finance != "ok":
        return _missing_data_outcome("finance", status.finance)
    r = finance_filter_stock(cand.stk_cd, date_dir=date_dir)
    return StageOutcome(
        name="finance",
        selected=r.selected,
        category=r.category,
        reason=r.reason,
        report_path=r.report_path,
    )


def _run_filter_pipeline(
    cand: ResearchCandidate,
    *,
    date_dir: str,
    status: PrefetchStatus,
) -> ResearchResult:
    """단일 종목에 대해 6 Stage 필터 순차 평가. 어느 단계든 False 면 break."""
    result = ResearchResult(candidate=cand)

    stage1 = _filter_stage_chart60_120(cand, date_dir=date_dir, status=status)
    result.stages.append(stage1)
    if not stage1.selected:
        return result

    stage2 = _filter_stage_chart240(cand, date_dir=date_dir, status=status)
    result.stages.append(stage2)
    if not stage2.selected:
        return result

    stage2_1 = _filter_stage_chartday_pre(cand, date_dir=date_dir, status=status)
    result.stages.append(stage2_1)
    if not stage2_1.selected:
        return result

    stage3 = _filter_stage_chartday(cand, date_dir=date_dir, status=status)
    result.stages.append(stage3)
    if not stage3.selected:
        return result

    stage4 = _filter_stage_investor(cand, date_dir=date_dir, status=status)
    result.stages.append(stage4)
    if not stage4.selected:
        return result

    stage5 = _filter_stage_finance(cand, date_dir=date_dir, status=status)
    result.stages.append(stage5)
    if not stage5.selected:
        return result

    result.final_selected = True
    return result


async def filter_today(
    date: str | None = None,
    *,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> list[ResearchResult]:
    """Stage 0 가 끝난 날짜에 대해 Stage 1~5 필터를 순수 평가.

    API 호출 0회. organizedCompany.md / prefetchManifest.json / 각 종목의
    chart*·investor·finance.md 만 디스크에서 읽는다.

    Args:
        date: ``YYYYMMDD``. ``None`` 이면 오늘.
        reports_root: 보고서 루트(기본 ``reports/``).

    Returns:
        종목별 :class:`ResearchResult` 리스트 (입력 순서 보존).
        ``final_selected=True`` 인 항목만 ``researchedCompany.md`` 에 기록.

    Raises:
        ResearchError: organizedCompany.md 또는 prefetchManifest.json 부재/공백.
    """
    yyyymmdd = date or _today_yyyymmdd()
    date_dir_path = reports_root / yyyymmdd
    organized_path = date_dir_path / _ORGANIZED_FILE

    if not organized_path.exists():
        raise ResearchError(f"organizedCompany.md 없음: {organized_path}")

    names = _load_stock_names(organized_path)
    if not names:
        raise ResearchError(f"organizedCompany.md 가 비어있음: {organized_path}")

    try:
        manifest = load_prefetch_manifest(yyyymmdd, reports_root=reports_root)
    except FileNotFoundError as exc:
        raise ResearchError(
            f"prefetchManifest.json 없음 — 먼저 Stage 0 prefetch 를 실행하세요: "
            f"{exc}"
        ) from exc

    code_map = build_name_to_code_map(date_dir_path)

    logger.info(
        "filter_today 시작 date={d} 종목={n} 매핑코드={m} manifest종목={k}",
        d=yyyymmdd, n=len(names), m=len(code_map), k=len(manifest.by_stock),
    )

    results: list[ResearchResult] = []
    for idx, stk_nm in enumerate(names, start=1):
        stk_cd = code_map.get(stk_nm, "")
        cand = ResearchCandidate(stk_nm=stk_nm, stk_cd=stk_cd)

        if not stk_cd:
            logger.warning(
                "[{i}/{n}] 코드 매핑 실패 — 스킵: {nm}",
                i=idx, n=len(names), nm=stk_nm,
            )
            results.append(
                ResearchResult(
                    candidate=cand,
                    stages=[],
                    final_selected=False,
                    skip_reason="코드 매핑 실패",
                )
            )
            continue

        status = manifest.by_stock.get(stk_cd)
        if status is None:
            logger.warning(
                "[{i}/{n}] manifest 미등재 — 스킵: {nm}({cd})",
                i=idx, n=len(names), nm=stk_nm, cd=stk_cd,
            )
            results.append(
                ResearchResult(
                    candidate=cand,
                    stages=[],
                    final_selected=False,
                    skip_reason="manifest 미등재 (Stage 0 미실행)",
                )
            )
            continue

        try:
            r = _run_filter_pipeline(cand, date_dir=yyyymmdd, status=status)
        except Exception as exc:
            logger.exception(
                "[{i}/{n}] 필터 예외 — 스킵: {nm}({cd})",
                i=idx, n=len(names), nm=stk_nm, cd=stk_cd,
            )
            r = ResearchResult(
                candidate=cand,
                stages=[],
                final_selected=False,
                skip_reason=f"예외: {exc}",
            )
        results.append(r)

        if r.final_selected:
            logger.info(
                "[{i}/{n}] ✅ 통과: {nm}({cd})",
                i=idx, n=len(names), nm=stk_nm, cd=stk_cd,
            )

    passed = sum(1 for r in results if r.final_selected)
    logger.info(
        "filter_today 종료 — 입력 {n} / 통과 {p} / 탈락 {f}",
        n=len(results), p=passed, f=len(results) - passed,
    )
    return results


# ``research_today`` 라는 이름이 기존 외부 코드에서 사용 중이라 별칭 유지.
research_today = filter_today


# ──────────────────────────────────────────────────────────────────────
# ①·②·③ 수집 단계 (변경 없음)
# ──────────────────────────────────────────────────────────────────────


async def _stage_upper_lower_price(
    *,
    yyyymmdd: str,
    now: datetime,
    reports_root: Path,
) -> tuple[int, str]:
    """① upperLowerPrice 단계 — 응답 종목수와 (있으면) 에러 메시지 반환."""
    df = await get_upper_lower_price()
    save_upper_lower_price_markdown(
        df,
        output_root=reports_root,
        now=now,
    )
    logger.info(
        "[full_flow ①] upperLowerPrice 저장 완료 — date={d} 종목수={n}",
        d=yyyymmdd, n=len(df),
    )
    return len(df), ""


async def _stage_condition_research(
    *,
    yyyymmdd: str,
    now: datetime,
    reports_root: Path,
) -> tuple[int, str]:
    """② conditionResearch 단계 — 누적 고유 종목수와 (있으면) 에러 메시지 반환.

    ``save_condition_research`` 는 ``CompositeResult.fetched_at`` 의 YYYYMMDD 를
    디렉터리명으로 쓰므로, ``date`` 인자로 과거 날짜를 지정한 백필 호출 시
    저장 경로 일치를 위해 fetched_at 을 ``now`` 로 덮어쓴다.
    """
    composite = await run_all_conditions()
    if composite.fetched_at.strftime("%Y%m%d") != yyyymmdd:
        composite.fetched_at = now
    save_condition_research(composite, output_root=reports_root)
    logger.info(
        "[full_flow ②] conditionResearch 저장 완료 — date={d} 누적고유={n}",
        d=yyyymmdd, n=composite.total_unique,
    )
    return composite.total_unique, ""


def _stage_organized_company(
    *,
    date: str | None,
    yyyymmdd: str,
    reports_root: Path,
) -> tuple[int, str]:
    """③ organizedCompany 단계 — 통합 종목수와 (있으면) 에러 메시지 반환.

    ``OrganizeError`` (입력 0건) 는 잡아서 (0, 메시지) 로 반환 — caller 가
    이후 단계 스킵 결정.
    """
    try:
        stocks = organize_today(date=date, reports_root=reports_root)
    except OrganizeError as exc:
        logger.warning("[full_flow ③] organizedCompany 진행 불가: {e}", e=exc)
        return 0, str(exc)
    save_organized_company(stocks, date=yyyymmdd, reports_root=reports_root)
    logger.info(
        "[full_flow ③] organizedCompany 저장 완료 — date={d} 종목수={n}",
        d=yyyymmdd, n=len(stocks),
    )
    return len(stocks), ""


# ──────────────────────────────────────────────────────────────────────
# run_full_flow — ①·②·③ + Stage 0 prefetch + Stage 1~5 filter + save
# ──────────────────────────────────────────────────────────────────────


async def run_full_flow(
    date: str | None = None,
    *,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> FullFlowSummary:
    """수집·필터 통합 풀플로우 실행.

    순서::

        ① upperLowerPrice   → reports/<날짜>/upperLowerPrice.md
        ② conditionResearch → reports/<날짜>/conditionResearch.md
        ③ organizedCompany  → reports/<날짜>/organizedCompany.md
        Stage 0 prefetch    → 종목별 chart*·investor·finance.md + prefetchManifest.json
        Stage 1~5 filter    → researchedCompany.md + stage*_passed.md
    C. 탈락사유 분석    → masterReference.md 기반 masterReference.log append

    오류 격리:
        - ①·② 단계 중 한쪽 실패는 ``upper_error`` / ``condition_error`` 에
          기록만 하고 계속 진행. ③ 단계는 다른 한쪽 입력만으로도 동작 가능.
        - ③ 단계가 0건이면 Stage 0/필터 단계 스킵하고 ``skipped_stage``.
        - Stage 0 ``PrefetchError`` → 필터 단계 스킵.

    Args:
        date: ``YYYYMMDD``. ``None`` 이면 오늘. 백필 시 ①·② 는 현재 시점 데이터를
            지정 날짜 폴더에 저장한다(스크리너 API 는 실시간성이라 의미 한정).
        reports_root: 보고서 루트(기본 ``reports/``).

    Returns:
        :class:`FullFlowSummary` — 단계별 카운트와 필터 단계 상세결과.
    """
    yyyymmdd = date or _today_yyyymmdd()
    if date is None:
        now = datetime.now()
    else:
        current = datetime.now()
        now = datetime.strptime(date, "%Y%m%d").replace(
            hour=current.hour,
            minute=current.minute,
            second=current.second,
        )

    summary = FullFlowSummary(date=yyyymmdd)
    logger.info("run_full_flow 시작 date={d}", d=yyyymmdd)

    # ── ① upperLowerPrice ──────────────────────────────────────────
    try:
        summary.upper_count, _ = await _stage_upper_lower_price(
            yyyymmdd=yyyymmdd, now=now, reports_root=reports_root,
        )
    except Exception as exc:
        logger.exception("[full_flow ①] upperLowerPrice 실패: {e}", e=exc)
        summary.upper_error = f"{type(exc).__name__}: {exc}"

    await asyncio.sleep(_INTER_STAGE_DELAY)

    # ── ② conditionResearch ────────────────────────────────────────
    try:
        summary.condition_unique_count, _ = await _stage_condition_research(
            yyyymmdd=yyyymmdd, now=now, reports_root=reports_root,
        )
    except KiwoomConditionError as exc:
        logger.error("[full_flow ②] conditionResearch 실패: {e}", e=exc)
        summary.condition_error = f"KiwoomConditionError: {exc}"
    except Exception as exc:
        logger.exception("[full_flow ②] conditionResearch 예외: {e}", e=exc)
        summary.condition_error = f"{type(exc).__name__}: {exc}"

    await asyncio.sleep(_INTER_STAGE_DELAY)

    # ── ③ organizedCompany ─────────────────────────────────────────
    summary.organized_count, organize_err = _stage_organized_company(
        date=date, yyyymmdd=yyyymmdd, reports_root=reports_root,
    )
    if organize_err:
        summary.organize_error = organize_err
        summary.skipped_stage = "researchedCompany"
        summary.skip_reason = (
            f"organizedCompany 단계 실패로 이후 단계 스킵: {organize_err}"
        )
        logger.warning(
            "run_full_flow 종료 — ③ 실패로 Stage 0/필터 스킵: {r}",
            r=summary.skip_reason,
        )
        return summary

    if summary.organized_count == 0:
        summary.skipped_stage = "researchedCompany"
        summary.skip_reason = "organizedCompany 결과 0건 — 이후 단계 스킵"
        logger.warning("run_full_flow 종료 — {r}", r=summary.skip_reason)
        return summary

    await asyncio.sleep(_INTER_STAGE_DELAY)

    # ── Stage 0 prefetch (일괄 수집) ────────────────────────────────
    try:
        await prefetch_all(date=date, reports_root=reports_root)
    except PrefetchError as exc:
        logger.error("[full_flow Stage 0] prefetch 진행 불가: {e}", e=exc)
        summary.skipped_stage = "researchedCompany"
        summary.skip_reason = f"PrefetchError: {exc}"
        return summary

    # ── Stage 1~5 filter (순수 필터) ───────────────────────────────
    try:
        results = await filter_today(date=date, reports_root=reports_root)
    except ResearchError as exc:
        logger.error("[full_flow Stage 1~5] 필터 진행 불가: {e}", e=exc)
        summary.skipped_stage = "researchedCompany"
        summary.skip_reason = f"ResearchError: {exc}"
        return summary

    summary.research_results = results
    save_researched_company(results, date=yyyymmdd, reports_root=reports_root)
    save_all_stages_passed(results, date=yyyymmdd, reports_root=reports_root)

    # ── C. masterReference 탈락사유 분석 ───────────────────────────
    # researchedCompany.md 작성 완료 직후 실행. masterReference.md 가
    # 비어있으면 내부에서 즉시 no-op 종료한다. 분석 실패가 풀플로우
    # 전체를 멈추지 않도록 격리한다.
    try:
        from src.kiwoom.itemFilter.Filter_condition_update import (
            run_filter_condition_update,
        )

        rc = run_filter_condition_update(yyyymmdd, reports_root=reports_root)
        logger.info(
            "[full_flow C] Filter_condition_update 완료 — rc={rc}", rc=rc,
        )
    except Exception as exc:  # noqa: BLE001 — 분석 단계 격리
        logger.exception(
            "[full_flow C] Filter_condition_update 예외(격리): {e}", e=exc,
        )

    logger.info(
        "run_full_flow 종료 — date={d} ①={u} ②={c} ③={o} ④통과={p}/{t}",
        d=yyyymmdd,
        u=summary.upper_count,
        c=summary.condition_unique_count,
        o=summary.organized_count,
        p=summary.passed_count,
        t=len(results),
    )
    return summary


__all__ = [
    "ResearchError",
    "filter_today",
    "research_today",
    "run_full_flow",
]
