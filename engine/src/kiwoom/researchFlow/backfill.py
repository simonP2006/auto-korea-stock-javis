"""과거일 부분수집 (P1 backfill) — 지정 기준일에 대한 조회전용 데이터 수집.

Stage 0 :mod:`prefetch` 가 "오늘" 유니버스를 실시간 스캔해 6 개 API 를
호출하는 것과 달리, 본 모듈은 **과거 기준일** 에 대해 데이터를 소급 수집한다.
당일 실스캔(상하한가·조건검색)으로만 만들 수 있는 유니버스는 과거로 복원할
수 없으므로, 유니버스는 다음 우선순위로 확보한다:

    1. 호출자가 명시한 종목 목록(``stocks``).
    2. 동결본 재사용 — ``reports/<date>/organizedCompany.md`` (당일 실스캔 결과)
       를 읽기전용으로 재사용.
    3. 둘 다 없으면 :class:`BackfillError`.

prefetch 대비 차이:
    - 5 개 데이터 API(chart60·chart120·chart240·chartDay·investor) 에 모두
      ``base_dt=date`` 를 전달해 과거 시점으로 앵커링한다.
    - finance(ka10001) 는 **호출하지 않는다** — 당일 스냅샷 전용이라 과거
      재무를 복원할 수 없다. 매니페스트 finance 상태는 ``"skipped"``.
    - 산출물은 실스캔 이력(``reports/``)과 분리된 별도 루트
      (기본 ``reports_backfill/``)에 저장한다. 두 루트가 겹치면 즉시 오류.

저장 산출물(prefetch 와 동일 구조, 루트만 분리)::

    reports_backfill/<YYYYMMDD>/<stk_nm>(<stk_cd>)/
        ├─ chart60.md ├─ chart120.md ├─ chart240.md
        ├─ chartDay.md └─ investor.md            (finance.md 없음 — 미수집)
    reports_backfill/<YYYYMMDD>/organizedCompany.md   ← 복원된 유니버스
    reports_backfill/<YYYYMMDD>/prefetchManifest.json ← 종목별 상태 인덱스
    reports_backfill/<YYYYMMDD>/BACKFILL_META.json     ← 정직한 수집시각 메타

메타(``BACKFILL_META.json``) 의 존재 이유:
    savers 는 디렉터리를 ``now`` 의 YYYYMMDD 로 명명하는데, backfill 은 과거
    날짜 폴더에 저장해야 하므로 ``now`` 를 "기준일 + 현재 시각" 으로 만든다
    (prefetch 백필과 동일). 그 결과 .md 내부 "수집시각" 표기는 기준일 기준으로
    렌더링되어 **실제 수집 시각을 오도** 할 수 있다. ``collected_at`` 은 이
    왜곡을 바로잡는 진짜 벽시계 시각이다.

페이싱·캐시 정책은 prefetch 와 동일(종목 내 0.3s / 종목 사이 0.5s, 항상 새로 수집).
"""

from __future__ import annotations

import asyncio
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Final

from loguru import logger

from src.kiwoom.chart60 import get_60min_with_ma
from src.kiwoom.chart60.saveReport import save_chart60_markdown
from src.kiwoom.chart120 import get_120min_with_ma
from src.kiwoom.chart120.saveReport import save_chart120_markdown
from src.kiwoom.chart240 import get_240min_with_ma
from src.kiwoom.chart240.saveReport import save_chart240_markdown
from src.kiwoom.chartDay import get_daily_with_ma
from src.kiwoom.chartDay.saveReport import save_chartday_markdown
from src.kiwoom.investor.investor import (
    get_investor_flow,
    save_investor_markdown,
)
from src.kiwoom.organizedCompany.models import OrganizedStock
from src.kiwoom.organizedCompany.saveReport import save_organized_company
from src.kiwoom.researchFlow.models import (
    PrefetchManifest,
    PrefetchStatus,
    ResearchCandidate,
)
from src.kiwoom.researchFlow.name_resolver import build_name_to_code_map
from src.kiwoom.researchFlow.prefetch import _drop_placeholder_minute_rows
from src.kiwoom.researchFlow.saveReport import (
    load_prefetch_manifest,
    save_prefetch_manifest,
)

# finance(ka10001) 는 의도적으로 import 하지 않는다 — backfill 에서 절대
# 호출되지 않음을 코드 레벨에서 보장(당일 스냅샷 전용, 과거 복원 불가).

_DEFAULT_BACKFILL_ROOT: Final[Path] = Path("reports_backfill")
_DEFAULT_UNIVERSE_ROOT: Final[Path] = Path("reports")
_ORGANIZED_FILE: Final[str] = "organizedCompany.md"
_CONDITION_FILE: Final[str] = "conditionResearch.md"
_UPPER_LOWER_FILE: Final[str] = "upperLowerPrice.md"
_MANIFEST_FILE: Final[str] = "prefetchManifest.json"
_META_FILE: Final[str] = "BACKFILL_META.json"

# 분봉 보존범위 밖 여부를 판정할 때 대조군으로 쓰는 우량주(삼성전자).
_CONTROL_STK_CD: Final[str] = "005930"
_PREFLIGHT_BARS: Final[int] = 2

_INTER_API_DELAY: Final[float] = 0.3   # 종목 내 API 사이
_INTER_STOCK_DELAY: Final[float] = 0.5  # 종목 사이

_META_NOTE: Final[str] = (
    "md 파일 내부 수집시각 표기는 기준일 기준으로 렌더링됨(디렉터리 명명 제약) "
    "— 실제 수집 시각은 collected_at"
)


class BackfillError(RuntimeError):
    """유니버스 복원 불가·보존범위 밖·루트 충돌 등 backfill 진행 불가 오류."""


def _load_stock_names(path: Path) -> list[str]:
    """organizedCompany.md 에서 종목명 줄단위 로드 (빈 줄 무시)."""
    text = path.read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def _now_at_current_clock(date: str) -> datetime:
    """``date`` 의 자정에 현재 시각(시/분/초)을 얹은 datetime.

    savers 가 디렉터리를 ``now`` 의 YYYYMMDD 로 명명하므로 과거 날짜 폴더로
    저장하기 위한 값. prefetch_all 의 백필 분기와 동일한 계산.
    """
    current = datetime.now()
    return datetime.strptime(date, "%Y%m%d").replace(
        hour=current.hour,
        minute=current.minute,
        second=current.second,
    )


def _all_data_ok(status: PrefetchStatus) -> bool:
    """5 개 데이터 API 가 모두 ``"ok"`` 인지 (finance 제외 — backfill 미수집)."""
    return (
        status.chart60 == "ok"
        and status.chart120 == "ok"
        and status.chart240 == "ok"
        and status.chartDay == "ok"
        and status.investor == "ok"
    )


# ──────────────────────────────────────────────────────────────────────
# 루트 가드 — 실스캔 이력(reports/) 오염 방지
# ──────────────────────────────────────────────────────────────────────


def _guard_roots(reports_root: Path, universe_reports_root: Path) -> None:
    """backfill 출력 루트가 실스캔 이력을 덮어쓰지 못하도록 강제.

    Raises:
        BackfillError: 출력 루트가 유니버스 루트와 동일하거나, 실제 ``reports``
            디렉터리를 가리킬 때.
    """
    rr = reports_root.resolve()
    ur = universe_reports_root.resolve()
    real_reports = _DEFAULT_UNIVERSE_ROOT.resolve()

    if rr == ur:
        raise BackfillError(
            f"backfill 출력 루트와 유니버스 루트가 동일합니다({rr}) — "
            f"실스캔 이력 오염을 막기 위해 별도 루트를 지정하세요"
        )
    if rr == real_reports:
        raise BackfillError(
            f"backfill 출력 루트가 실제 reports 디렉터리를 가리킵니다({rr}) — "
            f"실스캔 이력 오염 방지"
        )


# ──────────────────────────────────────────────────────────────────────
# 유니버스 복원
# ──────────────────────────────────────────────────────────────────────


def _copy_universe_source_files(src_dir: Path, dst_dir: Path) -> None:
    """동결본 재사용 시 종목명→코드 매핑 원본(condition/upper.md)을 복사.

    ``filter_today`` 가 backfill 루트에서 ``build_name_to_code_map`` 로 종목명을
    코드로 복원할 수 있도록, 유니버스 폴더의 두 매핑 원본을 backfill 폴더로
    읽기전용 복사한다(존재하는 것만). backfill 루트는 이미 가드를 통과했으므로
    쓰기는 안전하다.
    """
    dst_dir.mkdir(parents=True, exist_ok=True)
    for fname in (_CONDITION_FILE, _UPPER_LOWER_FILE):
        src = src_dir / fname
        if src.exists():
            shutil.copyfile(src, dst_dir / fname)
            logger.info("유니버스 매핑 원본 복사: {f}", f=fname)


def _resolve_universe(
    date: str,
    *,
    stocks: list[ResearchCandidate] | None,
    universe_reports_root: Path,
    reports_root: Path,
) -> tuple[list[ResearchCandidate], str]:
    """유니버스를 우선순위대로 확보하고 (후보 리스트, 출처 문자열) 반환.

    1. ``stocks`` 명시 → 그대로 사용, 출처 ``"user-list"``.
    2. ``reports/<date>/organizedCompany.md`` 동결본 재사용 → 종목명 로드 후
       ``build_name_to_code_map`` 로 코드 복원. 매핑 원본을 backfill 루트로 복사.
    3. 둘 다 없으면 :class:`BackfillError`.
    """
    if stocks is not None:
        if not stocks:
            raise BackfillError("제공된 종목 목록이 비어 있습니다")
        return list(stocks), "user-list"

    universe_dir = universe_reports_root / date
    organized_path = universe_dir / _ORGANIZED_FILE
    if not organized_path.exists():
        raise BackfillError(
            "과거 유니버스를 복원할 수 없습니다 — 해당 날짜의 "
            "organizedCompany.md가 없고 종목 목록도 제공되지 않았습니다"
        )

    names = _load_stock_names(organized_path)
    if not names:
        raise BackfillError(
            "과거 유니버스를 복원할 수 없습니다 — 해당 날짜의 "
            "organizedCompany.md가 없고 종목 목록도 제공되지 않았습니다"
        )

    code_map = build_name_to_code_map(universe_dir)
    candidates = [
        ResearchCandidate(stk_nm=nm, stk_cd=code_map.get(nm, "")) for nm in names
    ]

    # filter_today 가 backfill 루트에서 종목명을 코드로 복원할 수 있도록
    # 매핑 원본을 복사(동결본 재사용 경로 전용).
    _copy_universe_source_files(universe_dir, reports_root / date)

    source = f"{universe_reports_root}/{date}/{_ORGANIZED_FILE}"
    return candidates, source


def _write_universe(
    candidates: list[ResearchCandidate],
    *,
    date: str,
    reports_root: Path,
) -> None:
    """복원된 유니버스를 backfill 루트의 organizedCompany.md 로 기록.

    기존 organizedCompany saver 를 재사용한다 — ``render_plain_text`` 가 입력
    순서대로 종목명만 줄단위로 쓰므로 ``_load_stock_names`` 가 그대로 파싱한다.
    """
    stocks = [
        OrganizedStock(stk_nm=c.stk_nm, stk_cd=c.stk_cd, source="conditionRes")
        for c in candidates
    ]
    save_organized_company(stocks, date=date, reports_root=reports_root)


# ──────────────────────────────────────────────────────────────────────
# 단일 종목 수집 (base_dt 배선, finance 미수집)
# ──────────────────────────────────────────────────────────────────────


async def _fetch_minute_backfill(
    api_name: str,
    fetch_fn,
    save_fn,
    cand: ResearchCandidate,
    *,
    base_dt: str,
    now: datetime,
    reports_root: Path,
) -> tuple[str, str]:
    """단일 분봉 API 호출(base_dt 앵커) + 저장. prefetch._fetch_minute 미러."""
    try:
        df = _drop_placeholder_minute_rows(
            await fetch_fn(cand.stk_cd, base_dt=base_dt)
        )
    except Exception as exc:
        logger.exception(
            "{api} 호출 예외 — {nm}({cd}): {e}",
            api=api_name, nm=cand.stk_nm, cd=cand.stk_cd, e=exc,
        )
        return "error", f"{type(exc).__name__}: {exc}"
    if df.empty:
        return "empty", ""
    try:
        save_fn(
            df,
            stk_cd=cand.stk_cd,
            stk_name=cand.stk_nm,
            output_root=reports_root,
            now=now,
        )
    except Exception as exc:
        logger.exception(
            "{api} 저장 예외 — {nm}({cd}): {e}",
            api=api_name, nm=cand.stk_nm, cd=cand.stk_cd, e=exc,
        )
        return "error", f"save: {type(exc).__name__}: {exc}"
    return "ok", ""


async def _fetch_chartday_backfill(
    cand: ResearchCandidate,
    *,
    base_dt: str,
    now: datetime,
    reports_root: Path,
) -> tuple[str, str, str]:
    """일봉 API 호출(base_dt 앵커) + 저장.

    Returns:
        (status, error_message, last_dt). ``last_dt`` 는 응답 마지막(=최신) 일봉의
        ``dt`` — 거래일 sanity 체크용. 빈응답/예외면 빈 문자열.
    """
    try:
        df = await get_daily_with_ma(cand.stk_cd, base_dt=base_dt)
    except Exception as exc:
        logger.exception(
            "chartDay 호출 예외 — {nm}({cd}): {e}",
            nm=cand.stk_nm, cd=cand.stk_cd, e=exc,
        )
        return "error", f"{type(exc).__name__}: {exc}", ""
    if df.empty:
        return "empty", "", ""
    last_dt = str(df["dt"].iloc[-1]) if "dt" in df.columns else ""
    try:
        save_chartday_markdown(
            df,
            stk_cd=cand.stk_cd,
            stk_name=cand.stk_nm,
            output_root=reports_root,
            now=now,
        )
    except Exception as exc:
        logger.exception(
            "chartDay 저장 예외 — {nm}({cd}): {e}",
            nm=cand.stk_nm, cd=cand.stk_cd, e=exc,
        )
        return "error", f"save: {type(exc).__name__}: {exc}", last_dt
    return "ok", "", last_dt


async def _fetch_investor_backfill(
    cand: ResearchCandidate,
    *,
    base_dt: str,
    now: datetime,
    reports_root: Path,
) -> tuple[str, str]:
    """투자자 동향 API 호출(base_dt 앵커) + 저장."""
    try:
        df = await get_investor_flow(cand.stk_cd, bars=16, base_dt=base_dt)
    except Exception as exc:
        logger.exception(
            "investor 호출 예외 — {nm}({cd}): {e}",
            nm=cand.stk_nm, cd=cand.stk_cd, e=exc,
        )
        return "error", f"{type(exc).__name__}: {exc}"
    if df.empty:
        return "empty", ""
    try:
        save_investor_markdown(
            df,
            stk_cd=cand.stk_cd,
            stk_name=cand.stk_nm,
            output_root=reports_root,
            now=now,
        )
    except Exception as exc:
        logger.exception(
            "investor 저장 예외 — {nm}({cd}): {e}",
            nm=cand.stk_nm, cd=cand.stk_cd, e=exc,
        )
        return "error", f"save: {type(exc).__name__}: {exc}"
    return "ok", ""


async def _backfill_one_stock(
    cand: ResearchCandidate,
    *,
    base_dt: str,
    now: datetime,
    reports_root: Path,
) -> tuple[PrefetchStatus, str]:
    """단일 종목에 대해 5 개 데이터 API 를 순차 호출 + 저장(finance 미수집).

    prefetch._prefetch_one_stock 의 순서·페이싱·상태처리를 미러하되 base_dt 를
    배선하고 finance 는 호출하지 않는다(상태 ``"skipped"``).

    Returns:
        (status, chartday_last_dt). ``chartday_last_dt`` 는 거래일 sanity 체크용.
    """
    status = PrefetchStatus()

    s, err = await _fetch_minute_backfill(
        "chart60", get_60min_with_ma, save_chart60_markdown, cand,
        base_dt=base_dt, now=now, reports_root=reports_root,
    )
    status.chart60 = s  # type: ignore[assignment]
    if err:
        status.error_messages["chart60"] = err
    await asyncio.sleep(_INTER_API_DELAY)

    s, err = await _fetch_minute_backfill(
        "chart120", get_120min_with_ma, save_chart120_markdown, cand,
        base_dt=base_dt, now=now, reports_root=reports_root,
    )
    status.chart120 = s  # type: ignore[assignment]
    if err:
        status.error_messages["chart120"] = err
    await asyncio.sleep(_INTER_API_DELAY)

    s, err = await _fetch_minute_backfill(
        "chart240", get_240min_with_ma, save_chart240_markdown, cand,
        base_dt=base_dt, now=now, reports_root=reports_root,
    )
    status.chart240 = s  # type: ignore[assignment]
    if err:
        status.error_messages["chart240"] = err
    await asyncio.sleep(_INTER_API_DELAY)

    s, err, last_dt = await _fetch_chartday_backfill(
        cand, base_dt=base_dt, now=now, reports_root=reports_root,
    )
    status.chartDay = s  # type: ignore[assignment]
    if err:
        status.error_messages["chartDay"] = err
    await asyncio.sleep(_INTER_API_DELAY)

    s, err = await _fetch_investor_backfill(
        cand, base_dt=base_dt, now=now, reports_root=reports_root,
    )
    status.investor = s  # type: ignore[assignment]
    if err:
        status.error_messages["investor"] = err

    # finance 는 호출하지 않는다 — ka10001 당일 스냅샷 전용, 과거 복원 불가.
    status.finance = "skipped"  # type: ignore[assignment]

    return status, last_dt


# ──────────────────────────────────────────────────────────────────────
# 사전 게이트 · 메타 · 진입점
# ──────────────────────────────────────────────────────────────────────


async def _preflight_retention_gate(first_stk_cd: str, *, date: str) -> None:
    """루프 전 분봉 보존범위 사전 점검.

    첫 종목의 chart60(bars=2)을 base_dt=date 로 조회해 placeholder 제거 후
    비어 있으면, 대조군(005930)으로 재확인한다. 대조군도 비면 기준일이 분봉
    보존범위 밖으로 판단하고 :class:`BackfillError`. 첫 종목만 빈응답이면 경고만
    남기고 계속(개별 종목 데이터 부재일 수 있음).
    """
    probe = _drop_placeholder_minute_rows(
        await get_60min_with_ma(first_stk_cd, base_dt=date, bars=_PREFLIGHT_BARS)
    )
    if not probe.empty:
        return

    logger.warning(
        "사전점검: 첫 종목({cd}) 분봉 빈응답 — 대조군(005930) 재확인",
        cd=first_stk_cd,
    )
    control = _drop_placeholder_minute_rows(
        await get_60min_with_ma(
            _CONTROL_STK_CD, base_dt=date, bars=_PREFLIGHT_BARS,
        )
    )
    if control.empty:
        raise BackfillError(
            f"기준일 {date}은 분봉 보존범위 밖입니다(실측 보존 ≥1년·<2년)"
        )
    logger.warning(
        "사전점검: 대조군(005930)은 정상 — 첫 종목만 빈응답으로 보고 계속",
    )


def _load_existing_manifest(
    date: str, *, reports_root: Path
) -> PrefetchManifest | None:
    """resume 용 기존 매니페스트 로드 (없거나 손상되면 ``None``)."""
    path = reports_root / date / _MANIFEST_FILE
    if not path.exists():
        return None
    try:
        return load_prefetch_manifest(date, reports_root=reports_root)
    except Exception as exc:  # noqa: BLE001 — resume 은 best-effort
        logger.warning("기존 매니페스트 로드 실패 — resume 생략: {e}", e=exc)
        return None


def _write_backfill_meta(
    *,
    date: str,
    reports_root: Path,
    collected_at: datetime,
    universe_source: str,
    allow_nonbusiness: bool,
    stocks_total: int,
    nonbusiness_last_dt: str,
) -> Path:
    """정직한 수집시각 메타를 ``BACKFILL_META.json`` 으로 기록."""
    out_dir = reports_root / date
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / _META_FILE

    payload: dict[str, object] = {
        "base_date": date,
        "collected_at": collected_at.isoformat(),
        "universe_source": universe_source,
        "allow_nonbusiness": allow_nonbusiness,
        "stocks_total": stocks_total,
        "note": _META_NOTE,
    }
    # 비거래일을 allow_nonbusiness 로 통과시킨 경우에만 실측 마지막 일봉을 기록.
    if nonbusiness_last_dt:
        payload["nonbusiness_last_daily_dt"] = nonbusiness_last_dt

    out_path.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    logger.info("BACKFILL_META.json 저장: {p}", p=out_path)
    return out_path


async def backfill_prefetch_all(
    date: str,
    *,
    stocks: list[ResearchCandidate] | None = None,
    reports_root: Path = _DEFAULT_BACKFILL_ROOT,
    universe_reports_root: Path = _DEFAULT_UNIVERSE_ROOT,
    allow_nonbusiness: bool = False,
) -> PrefetchManifest:
    """과거 기준일 ``date`` 에 대해 5 개 데이터 API 를 부분수집(조회전용).

    Args:
        date: ``YYYYMMDD`` 기준일.
        stocks: 명시 유니버스. ``None`` 이면 동결본(organizedCompany.md) 재사용.
        reports_root: backfill 출력 루트(기본 ``reports_backfill/``). 실스캔
            이력(``reports/``)과 반드시 분리되어야 한다.
        universe_reports_root: 동결본 유니버스를 읽어올 루트(기본 ``reports/``).
        allow_nonbusiness: 비거래일 기준일도 진행할지. 기본 False 면 첫 일봉의
            마지막 dt 가 기준일과 다를 때 :class:`BackfillError`.

    Returns:
        :class:`PrefetchManifest` — finance 는 모두 ``"skipped"``. 디스크에도
        ``prefetchManifest.json`` + ``BACKFILL_META.json`` 저장.

    Raises:
        BackfillError: 루트 충돌·유니버스 복원 불가·보존범위 밖·비거래일 등.
    """
    _guard_roots(reports_root, universe_reports_root)

    candidates, universe_source = _resolve_universe(
        date,
        stocks=stocks,
        universe_reports_root=universe_reports_root,
        reports_root=reports_root,
    )
    _write_universe(candidates, date=date, reports_root=reports_root)

    fetchable = [c for c in candidates if c.stk_cd]
    if not fetchable:
        raise BackfillError(
            "유니버스 종목의 코드를 하나도 확인할 수 없습니다 — "
            "종목 목록 또는 organizedCompany 매핑을 확인하세요"
        )

    now = _now_at_current_clock(date)
    collected_at = datetime.now()

    logger.info(
        "backfill 시작 date={d} 종목 수={n} (코드확인 {f}) 출처={s}",
        d=date, n=len(candidates), f=len(fetchable), s=universe_source,
    )

    await _preflight_retention_gate(fetchable[0].stk_cd, date=date)

    existing = _load_existing_manifest(date, reports_root=reports_root)

    manifest = PrefetchManifest(date=date, started_at=collected_at)
    business_checked = False
    nonbusiness_last_dt = ""
    resume_skipped = 0

    for idx, cand in enumerate(candidates, start=1):
        if not cand.stk_cd:
            logger.warning(
                "[{i}/{n}] 코드 매핑 실패 — 스킵: {nm}",
                i=idx, n=len(candidates), nm=cand.stk_nm,
            )
            continue

        prev = existing.by_stock.get(cand.stk_cd) if existing else None
        if prev is not None and _all_data_ok(prev):
            manifest.by_stock[cand.stk_cd] = prev
            resume_skipped += 1
            logger.info(
                "[{i}/{n}] resume 스킵(데이터 전부 ok): {nm}({cd})",
                i=idx, n=len(candidates), nm=cand.stk_nm, cd=cand.stk_cd,
            )
            continue

        logger.info(
            "[{i}/{n}] backfill 시작: {nm}({cd})",
            i=idx, n=len(candidates), nm=cand.stk_nm, cd=cand.stk_cd,
        )
        status, last_dt = await _backfill_one_stock(
            cand, base_dt=date, now=now, reports_root=reports_root,
        )
        manifest.by_stock[cand.stk_cd] = status

        logger.info(
            "[{i}/{n}] backfill 완료: {nm}({cd}) "
            "c60={c60} c120={c120} c240={c240} cD={cD} inv={inv} fin=skipped",
            i=idx, n=len(candidates), nm=cand.stk_nm, cd=cand.stk_cd,
            c60=status.chart60, c120=status.chart120, c240=status.chart240,
            cD=status.chartDay, inv=status.investor,
        )

        # 거래일 sanity — 첫 번째 성공한 일봉의 마지막 dt 가 기준일과 다르면
        # 비거래일로 판단.
        if not business_checked and status.chartDay == "ok":
            business_checked = True
            if last_dt and last_dt != date:
                if not allow_nonbusiness:
                    raise BackfillError(
                        f"{date}는 거래일이 아닌 것으로 보입니다"
                        f"(마지막 일봉 {last_dt}). 거래일을 지정하세요."
                    )
                nonbusiness_last_dt = last_dt
                logger.warning(
                    "{d}는 거래일이 아닐 수 있으나 allow_nonbusiness=True 로 "
                    "계속(마지막 일봉 {last})",
                    d=date, last=last_dt,
                )

        if idx < len(candidates):
            await asyncio.sleep(_INTER_STOCK_DELAY)

    manifest.finished_at = datetime.now()
    save_prefetch_manifest(manifest, reports_root=reports_root)
    _write_backfill_meta(
        date=date,
        reports_root=reports_root,
        collected_at=collected_at,
        universe_source=universe_source,
        allow_nonbusiness=allow_nonbusiness,
        stocks_total=len(candidates),
        nonbusiness_last_dt=nonbusiness_last_dt,
    )

    ok_total = sum(1 for s in manifest.by_stock.values() if _all_data_ok(s))
    logger.info(
        "backfill 종료 — date={d} 종목 {n} / 데이터 전부 ok {ok} / "
        "resume 스킵 {r} / finance=skipped(전종목)",
        d=date, n=len(manifest.by_stock), ok=ok_total, r=resume_skipped,
    )
    return manifest


__all__ = ["BackfillError", "backfill_prefetch_all"]
