"""Stage 0 — organizedCompany 종목 전체에 대한 일괄 데이터 수집.

본 모듈은 ``organizedCompany.md`` 의 종목을 입력으로 받아 종목별로 6 개
API(chart60·chart120·chart240·chartDay·investor·finance) 를 순차 호출하고
각 응답을 .md 로 저장한다. 한 API 가 빈응답·예외여도 같은 종목의 나머지
API 호출은 계속 수행 (정책 (a) — 데이터 완결성 우선).

저장 산출물::

    reports/<YYYYMMDD>/<stk_nm>(<stk_cd>)/
        ├─ chart60.md
        ├─ chart120.md
        ├─ chart240.md
        ├─ chartDay.md
        ├─ investor.md
        └─ finance.md
    reports/<YYYYMMDD>/prefetchManifest.json   ← 종목별 6콜 상태 인덱스

매니페스트는 후속 Stage 1~5 (``facade.filter_today``) 가 API 재호출 없이
"이 종목의 chart240 은 빈응답" 같은 사실을 즉시 판정하기 위한 용도.

페이싱:
    - 종목 내 API 사이: 0.3 초 sleep
    - 종목 사이: 0.5 초 sleep
    - 병렬화 없음 — rate limit (1700) 충돌을 피하기 위해 순차 진행

캐시 정책:
    (a) 항상 새로 받아 덮어쓴다 — 매 실행 모든 API 호출.
"""

from __future__ import annotations

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import Final

import pandas as pd
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
from src.kiwoom.finance.finance import (
    get_finance_snapshot,
    save_finance_markdown,
)
from src.kiwoom.researchFlow.models import (
    PrefetchManifest,
    PrefetchStatus,
    ResearchCandidate,
)
from src.kiwoom.researchFlow.name_resolver import build_name_to_code_map
from src.kiwoom.researchFlow.saveReport import save_prefetch_manifest

_DEFAULT_REPORTS_ROOT: Final[Path] = Path("reports")
_ORGANIZED_FILE: Final[str] = "organizedCompany.md"

# 분봉 API 빈응답 placeholder 행 감지용 (cntr_tm 14자리 YYYYMMDDHHMMSS).
_VALID_CNTR_TM: Final[re.Pattern[str]] = re.compile(r"\d{14}")

_INTER_API_DELAY: Final[float] = 0.3   # 종목 내 API 사이
_INTER_STOCK_DELAY: Final[float] = 0.5  # 종목 사이


class PrefetchError(RuntimeError):
    """입력 부재 등 Stage 0 진행 불가 오류."""


def _today_yyyymmdd() -> str:
    return datetime.now().strftime("%Y%m%d")


def _load_stock_names(path: Path) -> list[str]:
    """organizedCompany.md 에서 종목명 줄단위 로드 (빈 줄 무시)."""
    text = path.read_text(encoding="utf-8")
    return [line.strip() for line in text.splitlines() if line.strip()]


def _drop_placeholder_minute_rows(df: pd.DataFrame) -> pd.DataFrame:
    """분봉 DataFrame 의 placeholder 행 제거.

    키움 API 가 종목 데이터가 비었을 때 ``cntr_tm=''``, 모든 가격 0 인 1행
    placeholder 를 반환하는 케이스를 ``df.empty`` 가 잡지 못한다 — 이 함수가
    ``cntr_tm`` 가 14자리 숫자가 아닌 행을 제거해 호출자가 ``df.empty`` 만
    으로 빈 응답을 판별할 수 있게 한다.
    """
    if df.empty or "cntr_tm" not in df.columns:
        return df
    mask = df["cntr_tm"].astype(str).str.fullmatch(_VALID_CNTR_TM)
    if mask.all():
        return df
    return df[mask].reset_index(drop=True)


async def _fetch_minute(
    api_name: str,
    fetch_fn,
    save_fn,
    cand: ResearchCandidate,
    *,
    now: datetime,
) -> tuple[str, str]:
    """단일 분봉 API 호출 + 저장.

    Returns:
        (status, error_message). status 는 ``"ok"`` / ``"empty"`` / ``"error"``.
        error_message 는 status == ``"error"`` 인 경우만 사유, 그 외 빈 문자열.
    """
    try:
        df = _drop_placeholder_minute_rows(await fetch_fn(cand.stk_cd))
    except Exception as exc:
        logger.exception(
            "{api} 호출 예외 — {nm}({cd}): {e}",
            api=api_name, nm=cand.stk_nm, cd=cand.stk_cd, e=exc,
        )
        return "error", f"{type(exc).__name__}: {exc}"
    if df.empty:
        return "empty", ""
    try:
        save_fn(df, stk_cd=cand.stk_cd, stk_name=cand.stk_nm, now=now)
    except Exception as exc:
        logger.exception(
            "{api} 저장 예외 — {nm}({cd}): {e}",
            api=api_name, nm=cand.stk_nm, cd=cand.stk_cd, e=exc,
        )
        return "error", f"save: {type(exc).__name__}: {exc}"
    return "ok", ""


async def _fetch_chartday(
    cand: ResearchCandidate,
    *,
    now: datetime,
) -> tuple[str, str]:
    """일봉 API 호출 + 저장. 분봉과 달리 placeholder 가드 불필요."""
    try:
        df = await get_daily_with_ma(cand.stk_cd)
    except Exception as exc:
        logger.exception(
            "chartDay 호출 예외 — {nm}({cd}): {e}",
            nm=cand.stk_nm, cd=cand.stk_cd, e=exc,
        )
        return "error", f"{type(exc).__name__}: {exc}"
    if df.empty:
        return "empty", ""
    try:
        save_chartday_markdown(
            df, stk_cd=cand.stk_cd, stk_name=cand.stk_nm, now=now,
        )
    except Exception as exc:
        logger.exception(
            "chartDay 저장 예외 — {nm}({cd}): {e}",
            nm=cand.stk_nm, cd=cand.stk_cd, e=exc,
        )
        return "error", f"save: {type(exc).__name__}: {exc}"
    return "ok", ""


async def _fetch_investor(
    cand: ResearchCandidate,
    *,
    now: datetime,
) -> tuple[str, str]:
    """투자자 동향 API 호출 + 저장."""
    try:
        df = await get_investor_flow(cand.stk_cd, bars=16)
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
            df, stk_cd=cand.stk_cd, stk_name=cand.stk_nm, now=now,
        )
    except Exception as exc:
        logger.exception(
            "investor 저장 예외 — {nm}({cd}): {e}",
            nm=cand.stk_nm, cd=cand.stk_cd, e=exc,
        )
        return "error", f"save: {type(exc).__name__}: {exc}"
    return "ok", ""


async def _fetch_finance(
    cand: ResearchCandidate,
    *,
    now: datetime,
) -> tuple[str, str]:
    """재무 기본정보(ka10001) 호출 + 저장.

    ka10001 은 단발 스냅샷이라 ``empty`` 는 응답 자체가 무효
    (종목명 없음 + 5지표 전부 결측)인 경우만이다. PER/EPS/ROE/PBR 이
    벤더 미갱신으로 비어 있어도 호출은 성공이므로 ``ok`` 로 본다.
    """
    try:
        snap = await get_finance_snapshot(cand.stk_cd)
    except Exception as exc:
        logger.exception(
            "finance 호출 예외 — {nm}({cd}): {e}",
            nm=cand.stk_nm, cd=cand.stk_cd, e=exc,
        )
        return "error", f"{type(exc).__name__}: {exc}"
    if snap.is_empty:
        return "empty", ""
    try:
        save_finance_markdown(
            snap, stk_cd=cand.stk_cd, stk_name=cand.stk_nm, now=now,
        )
    except Exception as exc:
        logger.exception(
            "finance 저장 예외 — {nm}({cd}): {e}",
            nm=cand.stk_nm, cd=cand.stk_cd, e=exc,
        )
        return "error", f"save: {type(exc).__name__}: {exc}"
    return "ok", ""


async def _prefetch_one_stock(
    cand: ResearchCandidate,
    *,
    now: datetime,
) -> PrefetchStatus:
    """단일 종목에 대해 6 개 API 를 순차 호출 + 저장.

    한 API 가 empty/error 여도 나머지 API 호출은 계속한다 (정책 (a)).
    """
    status = PrefetchStatus()

    s, err = await _fetch_minute(
        "chart60", get_60min_with_ma, save_chart60_markdown, cand, now=now,
    )
    status.chart60 = s  # type: ignore[assignment]
    if err:
        status.error_messages["chart60"] = err
    await asyncio.sleep(_INTER_API_DELAY)

    s, err = await _fetch_minute(
        "chart120", get_120min_with_ma, save_chart120_markdown, cand, now=now,
    )
    status.chart120 = s  # type: ignore[assignment]
    if err:
        status.error_messages["chart120"] = err
    await asyncio.sleep(_INTER_API_DELAY)

    s, err = await _fetch_minute(
        "chart240", get_240min_with_ma, save_chart240_markdown, cand, now=now,
    )
    status.chart240 = s  # type: ignore[assignment]
    if err:
        status.error_messages["chart240"] = err
    await asyncio.sleep(_INTER_API_DELAY)

    s, err = await _fetch_chartday(cand, now=now)
    status.chartDay = s  # type: ignore[assignment]
    if err:
        status.error_messages["chartDay"] = err
    await asyncio.sleep(_INTER_API_DELAY)

    s, err = await _fetch_investor(cand, now=now)
    status.investor = s  # type: ignore[assignment]
    if err:
        status.error_messages["investor"] = err
    await asyncio.sleep(_INTER_API_DELAY)

    s, err = await _fetch_finance(cand, now=now)
    status.finance = s  # type: ignore[assignment]
    if err:
        status.error_messages["finance"] = err

    return status


async def prefetch_all(
    date: str | None = None,
    *,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> PrefetchManifest:
    """organizedCompany.md 의 모든 종목에 대해 6 개 API 일괄 호출 + 저장.

    Args:
        date: ``YYYYMMDD``. ``None`` 이면 오늘.
        reports_root: 보고서 루트(기본 ``reports/``).

    Returns:
        :class:`PrefetchManifest` — 종목코드 → :class:`PrefetchStatus` 매핑.
        디스크에도 ``prefetchManifest.json`` 으로 동시 저장된다.

    Raises:
        PrefetchError: ``organizedCompany.md`` 가 없거나 비어있을 때.
    """
    yyyymmdd = date or _today_yyyymmdd()
    date_dir = reports_root / yyyymmdd
    organized_path = date_dir / _ORGANIZED_FILE

    if not organized_path.exists():
        raise PrefetchError(f"organizedCompany.md 없음: {organized_path}")

    names = _load_stock_names(organized_path)
    if not names:
        raise PrefetchError(f"organizedCompany.md 가 비어있음: {organized_path}")

    code_map = build_name_to_code_map(date_dir)

    if date is None:
        now = datetime.now()
    else:
        current = datetime.now()
        now = datetime.strptime(date, "%Y%m%d").replace(
            hour=current.hour,
            minute=current.minute,
            second=current.second,
        )

    started_at = datetime.now()
    logger.info(
        "Stage 0 prefetch 시작 date={d} 종목 수={n} 매핑된 코드 수={m}",
        d=yyyymmdd, n=len(names), m=len(code_map),
    )

    manifest = PrefetchManifest(date=yyyymmdd, started_at=started_at)

    for idx, stk_nm in enumerate(names, start=1):
        stk_cd = code_map.get(stk_nm, "")
        cand = ResearchCandidate(stk_nm=stk_nm, stk_cd=stk_cd)

        if not stk_cd:
            logger.warning(
                "[{i}/{n}] 코드 매핑 실패 — Stage 0 스킵: {nm}",
                i=idx, n=len(names), nm=stk_nm,
            )
            continue

        logger.info(
            "[{i}/{n}] Stage 0 시작: {nm}({cd})",
            i=idx, n=len(names), nm=stk_nm, cd=stk_cd,
        )
        status = await _prefetch_one_stock(cand, now=now)
        manifest.by_stock[stk_cd] = status

        logger.info(
            "[{i}/{n}] Stage 0 완료: {nm}({cd}) "
            "c60={c60} c120={c120} c240={c240} cD={cD} inv={inv} fin={fin}",
            i=idx, n=len(names), nm=stk_nm, cd=stk_cd,
            c60=status.chart60, c120=status.chart120,
            c240=status.chart240, cD=status.chartDay, inv=status.investor,
            fin=status.finance,
        )

        if idx < len(names):
            await asyncio.sleep(_INTER_STOCK_DELAY)

    manifest.finished_at = datetime.now()
    save_prefetch_manifest(manifest, reports_root=reports_root)

    ok_total = sum(
        1 for s in manifest.by_stock.values()
        if s.chart60 == "ok" and s.chart120 == "ok"
        and s.chart240 == "ok" and s.chartDay == "ok"
        and s.investor == "ok"
    )
    fin_ok = sum(
        1 for s in manifest.by_stock.values() if s.finance == "ok"
    )
    logger.info(
        "Stage 0 prefetch 종료 — date={d} 종목 {n} / "
        "차트+투자자 ok {ok} / finance ok {fin}",
        d=yyyymmdd, n=len(manifest.by_stock), ok=ok_total, fin=fin_ok,
    )
    return manifest


__all__ = ["PrefetchError", "prefetch_all"]
