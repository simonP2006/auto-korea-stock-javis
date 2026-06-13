"""organizedCompany 통합 실행 진입점.

실행::

    python -m scripts.run_organize_company             # 오늘
    python -m scripts.run_organize_company 20260510    # 특정일

종료 코드:
    0 — 정상 저장
    1 — 두 입력 파일 모두 부재 (또는 추출 0건)
    2 — 기타 예외
"""

from __future__ import annotations

import sys

from loguru import logger

from src.kiwoom.organizedCompany import OrganizeError, organize_today
from src.kiwoom.organizedCompany.saveReport import save_organized_company


def _format_pct(v: float) -> str:
    return f"{v:+.2f}%"


def main() -> int:
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    logger.info("organizedCompany 통합 시작 date={d}", d=date_arg or "오늘")

    try:
        stocks = organize_today(date_arg)
    except OrganizeError as exc:
        logger.error("진행 불가: {e}", e=exc)
        return 1
    except Exception as exc:
        logger.exception("예상치 못한 예외: {e}", e=exc)
        return 2

    out_path = save_organized_company(stocks, date=date_arg)

    print(f"saved: {out_path}")
    print(f"unique stocks: {len(stocks)}")
    if stocks:
        top = stocks[0]
        bottom = stocks[-1]
        print(f"top: {top.stk_nm} ({_format_pct(top.flu_rt)})")
        print(f"bottom: {bottom.stk_nm} ({_format_pct(bottom.flu_rt)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
