"""과거일 부분수집 (P1 backfill) 진입점 — 조회전용.

지정한 과거 기준일에 대해 5 개 데이터 API(chart60·chart120·chart240·chartDay·
investor)를 ``base_dt`` 앵커로 소급 수집하고(finance 는 미수집), 이어서 Stage
1~5 필터를 재무 제외 정책으로 실행한다. 산출물은 실스캔 이력(``reports/``)과
분리된 별도 루트(기본 ``reports_backfill/``)에 저장된다.

유니버스:
    - ``--stocks-file`` 제공 → 사용자 목록 사용.
    - 미제공 → ``reports/<date>/organizedCompany.md`` 동결본 재사용
      (당일 실스캔 결과). 없으면 오류.

실행::

    python -m scripts.run_backfill 20260618
    python -m scripts.run_backfill 20260618 --stocks-file mylist.txt
    python -m scripts.run_backfill 20260618 --no-filters
    python -m scripts.run_backfill 20260620 --allow-nonbusiness   # 주말/휴일

``--stocks-file`` 형식: 한 줄에 ``CODE`` 또는 ``CODE,NAME`` (NAME 생략 시 CODE).
``#`` 로 시작하는 줄과 빈 줄은 무시.

종료 코드:
    0 — 정상
    1 — 도메인 오류(주말 거부·유니버스 복원 불가·보존범위 밖·비거래일·루트 충돌)
    2 — 기타 예외
"""

from __future__ import annotations

import argparse
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Final

from loguru import logger

from src.kiwoom.researchFlow.backfill import BackfillError, backfill_prefetch_all
from src.kiwoom.researchFlow.facade import filter_today
from src.kiwoom.researchFlow.models import (
    PrefetchStatus,
    ResearchCandidate,
    ResearchResult,
)
from src.kiwoom.researchFlow.saveReport import (
    save_all_stages_passed,
    save_researched_company,
)

_DEFAULT_BACKFILL_ROOT: Final[Path] = Path("reports_backfill")

# 필터 퍼널 라벨 — save_all_stages_passed 의 slot 1~5(데이터 5단계)과 1:1.
# slot 6(finance/Stage5)은 backfill 에서 N/A 판정제외이므로 퍼널에 넣지 않고
# 별도 요약 줄로 안내한다. render_stage_passed 와 동일 술어로 세므로 출력 카운트가
# 디스크의 stage{N}_passed.md 파일과 정확히 일치한다.
_STAGE_FUNNEL_LABELS: Final[dict[int, str]] = {
    1: "Stage1 chart60_120",
    2: "Stage2 chart240",
    3: "Stage2-1 chartDayPre",
    4: "Stage3 chartDay",
    5: "Stage4 investor",
}


def _is_weekend(date: str) -> bool:
    """``YYYYMMDD`` 가 토(5)/일(6)요일이면 True."""
    return datetime.strptime(date, "%Y%m%d").weekday() >= 5


def _parse_stocks_file(
    path: Path,
) -> tuple[list[ResearchCandidate], dict[str, str]]:
    """종목 목록 파일을 ``ResearchCandidate`` 리스트 + 종목명→코드 매핑으로 파싱.

    각 줄은 ``CODE`` 또는 ``CODE,NAME`` (NAME 생략 시 CODE 를 종목명으로).
    ``#`` 주석 줄과 빈 줄은 무시한다.

    Raises:
        BackfillError: 파일이 없거나 유효 종목이 한 건도 없을 때.
    """
    if not path.exists():
        raise BackfillError(f"종목 목록 파일 없음: {path}")

    candidates: list[ResearchCandidate] = []
    code_map: dict[str, str] = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = [p.strip() for p in line.split(",", 1)]
        code = parts[0]
        if not code:
            continue
        name = parts[1] if len(parts) > 1 and parts[1] else code
        candidates.append(ResearchCandidate(stk_nm=name, stk_cd=code))
        code_map[name] = code

    if not candidates:
        raise BackfillError(f"종목 목록 파일에 유효한 종목이 없습니다: {path}")
    return candidates, code_map


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_backfill",
        description="과거일 부분수집(P1 backfill) — 조회전용",
    )
    parser.add_argument("date", help="기준일 YYYYMMDD")
    parser.add_argument(
        "--stocks-file",
        type=Path,
        default=None,
        help="종목 목록 파일(CODE[,NAME] 줄단위). 미지정 시 동결본 재사용.",
    )
    parser.add_argument(
        "--reports-root",
        type=Path,
        default=_DEFAULT_BACKFILL_ROOT,
        help="backfill 출력 루트(기본 reports_backfill).",
    )
    parser.add_argument(
        "--no-filters",
        action="store_true",
        help="수집만 하고 Stage 1~5 필터를 실행하지 않는다.",
    )
    parser.add_argument(
        "--allow-nonbusiness",
        action="store_true",
        help="주말/비거래일 기준일도 진행한다.",
    )
    return parser


def _count_all_data_ok(by_stock: dict[str, PrefetchStatus]) -> int:
    """5 개 데이터 API 전부 ``"ok"`` 인 종목 수(finance 제외)."""
    return sum(
        1 for s in by_stock.values()
        if s.chart60 == "ok" and s.chart120 == "ok" and s.chart240 == "ok"
        and s.chartDay == "ok" and s.investor == "ok"
    )


def _stage_funnel(results: list[ResearchResult]) -> list[tuple[str, int]]:
    """데이터 5단계(slot 1~5) 통과 종목 수를 stage 순서대로 반환.

    ``render_stage_passed`` 와 동일 술어(``len(stages) >= slot`` 그리고
    ``stages[slot-1].selected``)로 세므로, 각 카운트는 디스크의
    ``stage{N}_passed.md`` 파일 내용과 정확히 일치한다. 파이프라인이 첫 탈락에서
    끊기므로 카운트는 단조 비증가(진짜 퍼널)이다.
    """
    out: list[tuple[str, int]] = []
    for slot, label in _STAGE_FUNNEL_LABELS.items():
        cnt = sum(
            1 for r in results
            if len(r.stages) >= slot and r.stages[slot - 1].selected
        )
        out.append((label, cnt))
    return out


async def _run(args: argparse.Namespace) -> int:
    date: str = args.date
    backfill_root: Path = args.reports_root

    # 주말 fast-fail — 어떤 API 호출도 하기 전에 거부.
    if _is_weekend(date) and not args.allow_nonbusiness:
        print(f"date: {date}")
        print("거부: 주말(토/일)은 거래일이 아닙니다. "
              "거래일을 지정하거나 --allow-nonbusiness 를 사용하세요.")
        return 1

    stocks: list[ResearchCandidate] | None = None
    code_map: dict[str, str] | None = None
    if args.stocks_file is not None:
        try:
            stocks, code_map = _parse_stocks_file(args.stocks_file)
        except BackfillError as exc:
            print(f"date: {date}")
            print(f"거부: {exc}")
            return 1
        universe_label = "사용자 제공 목록"
    else:
        universe_label = "동결본 재사용(당일 실스캔)"

    logger.info("run_backfill 시작 date={d} 유니버스={u}", d=date, u=universe_label)

    # 수집 (조회전용).
    try:
        manifest = await backfill_prefetch_all(
            date,
            stocks=stocks,
            reports_root=backfill_root,
            allow_nonbusiness=args.allow_nonbusiness,
        )
    except BackfillError as exc:
        logger.error("[run_backfill] 수집 진행 불가: {e}", e=exc)
        print(f"date: {date}")
        print(f"backfill    : SKIPPED — {exc}")
        return 1

    collected = len(manifest.by_stock)
    all_ok = _count_all_data_ok(manifest.by_stock)

    passed = -1
    funnel: list[tuple[str, int]] = []
    if not args.no_filters:
        results = await filter_today(
            date,
            reports_root=backfill_root,
            finance_policy="skip_na",
            code_map=code_map,
        )
        # run_filters.py 와 동일한 저장 시퀀스: researchedCompany + 전 stage passed.
        save_researched_company(results, date=date, reports_root=backfill_root)
        save_all_stages_passed(results, date=date, reports_root=backfill_root)
        passed = sum(1 for r in results if r.final_selected)
        funnel = _stage_funnel(results)

    print(f"date: {date}")
    print(f"유니버스           : {universe_label}")
    print(f"수집 종목 수        : {collected} 종목")
    print(f"전API ok           : {all_ok}/{collected} 종목 (finance 제외)")
    if args.no_filters:
        print("필터               : SKIPPED (--no-filters)")
    else:
        print("필터 퍼널(데이터 5단계):")
        for label, cnt in funnel:
            print(f"  {label:<22}: {cnt}/{collected} 통과")
        print(f"필터 통과(최종)     : {passed}/{collected} 종목")
    print("재무 Stage5        : 판정 제외(과거 미지원)")
    return 0


async def main() -> int:
    args = _build_arg_parser().parse_args()
    try:
        return await _run(args)
    except Exception as exc:  # noqa: BLE001 — 최상위 방어
        logger.exception("예상치 못한 예외: {e}", e=exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
