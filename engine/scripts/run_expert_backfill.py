"""전문가 픽 일괄 backfill 드라이버 CLI — 이름해석·라벨기입·대사보고.

주인님이 과거 날짜별로 제공한 전문가 종목 픽(종목명 목록)을 입력받아, 날짜별로
종목명→코드 해석 → 과거일 backfill 수집(조회전용) → finance 제외 필터 → 라벨
기입(masterReference) → 대사 요약 표를 출력한다. 해석 실패 이름은 조용히 버리지
않고 요약의 '미해석명' 열과 ``masterReference.UNRESOLVED.txt`` 로 크게 보고한다.

핵심 로직은 :mod:`src.kiwoom.researchFlow.expert_backfill` 에 있고 본 스크립트는
CLI 래퍼다.

실행::

    python -m scripts.run_expert_backfill picks.txt
    python -m scripts.run_expert_backfill picks.txt --reports-root reports_backfill
    python -m scripts.run_expert_backfill picks.txt --only-date 20260106
    python -m scripts.run_expert_backfill picks.txt --dry-run   # 파싱·해석·보고만

픽 파일 형식::

    # 20260106
    에피소드컴퍼니
    케이엠더블유
    ...(한 줄에 종목명 1개; 섹션은 빈 줄/`---` 구분)

종료 코드:
    0 — 모든 날짜 해석·수집 정상
    1 — 미해석 이름 잔존 또는 수집 실패 날짜 존재 / 파싱·인자 오류
    2 — 기타 예외
"""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path
from typing import Final

from loguru import logger

from src.kiwoom.researchFlow.expert_backfill import (
    ExpertBackfillError,
    batch_exit_code,
    render_summary,
    run_expert_batch,
)

_DEFAULT_BACKFILL_ROOT: Final[Path] = Path("reports_backfill")


def _build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="run_expert_backfill",
        description="전문가 픽 일괄 과거일 backfill (조회전용)",
    )
    parser.add_argument(
        "picks_file",
        type=Path,
        help="전문가 픽 텍스트(# YYYYMMDD 섹션 + 줄당 종목명)",
    )
    parser.add_argument(
        "--reports-root",
        type=Path,
        default=_DEFAULT_BACKFILL_ROOT,
        help="backfill 출력 루트(기본 reports_backfill).",
    )
    parser.add_argument(
        "--only-date",
        default=None,
        help="지정 시 그 날짜(YYYYMMDD) 섹션만 처리.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="파싱·해석·보고만 수행(네트워크·파일쓰기 0).",
    )
    return parser


async def _run(args: argparse.Namespace) -> int:
    try:
        results = await run_expert_batch(
            args.picks_file,
            reports_root=args.reports_root,
            only_date=args.only_date,
            dry_run=args.dry_run,
        )
    except ExpertBackfillError as exc:
        print(f"거부: {exc}")
        return 1

    mode = "DRY-RUN(해석·보고만)" if args.dry_run else "수집·필터"
    print(f"[전문가 픽 backfill] 모드={mode} 출력루트={args.reports_root}")
    print(render_summary(results))

    code = batch_exit_code(results)
    if code != 0:
        print(
            "\n⚠ 미해석 이름 또는 수집 실패가 있습니다 — "
            "위 '미해석명' 열/로그 확인 후 이름 교정 재실행."
        )
    return code


async def main() -> int:
    args = _build_arg_parser().parse_args()
    logger.info(
        "run_expert_backfill 시작 picks={f} dry_run={d}",
        f=args.picks_file, d=args.dry_run,
    )
    try:
        return await _run(args)
    except Exception as exc:  # noqa: BLE001 — 최상위 방어
        logger.exception("예상치 못한 예외: {e}", e=exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
