"""조건검색 9개 실행 + reports/YYYYMMDD/conditionResearch.md 저장 진입점.

실행::

    python -m scripts.run_condition_research

전제:
    - ``.env`` 의 ``KIWOOM_APP_KEY`` / ``KIWOOM_SECRET_KEY`` 가 영웅문4에
      9개 식을 등록한 계정과 동일 로그인 ID로 발급됐을 것.
    - ``KIWOOM_MODE`` 는 ``real`` 권장(모의 도메인은 KRX 한정으로 동일하지만
      조건검색 지원범위는 실전 기준).

종료 코드:
    0 — 정상 (저장 성공)
    1 — 조건명 누락 등 사전 검증 실패
    2 — API 오류
"""

from __future__ import annotations

import asyncio
import sys

from loguru import logger

from src.kiwoom.conditionCompany import (
    KiwoomConditionError,
    run_all_conditions,
)
from src.kiwoom.conditionCompany.saveReport import save_condition_research


async def main() -> int:
    logger.info("조건검색 일괄 실행 시작")
    try:
        composite = await run_all_conditions()
    except KiwoomConditionError as exc:
        if exc.code == "MISSING":
            logger.error("사전 검증 실패: {m}", m=exc.msg)
            return 1
        logger.error("API 오류: {e}", e=exc)
        return 2

    out_path = save_condition_research(composite)

    logger.info(
        "완료 — 고유 누적 종목 {u}건, 결과 저장: {p}",
        u=composite.total_unique, p=out_path,
    )
    print(f"saved: {out_path}")
    print(f"unique stocks: {composite.total_unique}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
