"""debugResearchedCompany — ④ researchedCompany 단계만 단독 실행하는 CLI.

용도:
    이미 같은 날짜의 ``reports/<YYYYMMDD>/organizedCompany.md`` (및 종목코드
    매핑용 ``upperLowerPrice.md`` / ``conditionResearch.md``) 가 존재할 때,
    ①·②·③ 단계를 재실행하지 않고 ④ 단계 (chart60→chartDay→investor 3단
    필터 + researchedCompany.md 저장) 만 다시 돌리기 위한 진입점.

    필터 임계값 튜닝 후 같은 종목 풀에 대한 효과 비교, 부분 재시도, API
    오류 발생 후 ④ 단만 재처리 등에 사용.

전제:
    - ``reports/<YYYYMMDD>/organizedCompany.md`` 가 존재하고 비어있지 않아야 함
    - 종목코드 매핑은 같은 폴더의 ``upperLowerPrice.md`` /
      ``conditionResearch.md`` 에서 자동 로드 (둘 중 하나만 있어도 동작)

실행::

    python -m scripts.debug_researched_company             # 오늘
    python -m scripts.debug_researched_company 20260510    # 특정일

종료 코드:
    0 — 정상 저장
    1 — organizedCompany.md 부재 또는 비어있음
    2 — 기타 예외

주의: 본 스크립트는 ``scripts/run_research_flow.py`` 와 같은 함수를 호출하지만
의도(디버그 / 부분 재실행) 를 명확히 드러내기 위해 별도 진입점으로 분리됨.
실시간 운영 흐름은 ``scripts/run_full_research_flow.py`` 사용 권장.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path

from loguru import logger

from src.kiwoom.researchFlow import ResearchError, research_today
from src.kiwoom.researchFlow.saveReport import save_researched_company

_REPORTS_ROOT = Path("reports")
_ORGANIZED_FILE = "organizedCompany.md"


def _summarize(results: list) -> tuple[int, int, int, int]:
    """``(total, passed, mapping_failed, stage_failed)`` 집계."""
    total = len(results)
    passed = sum(1 for r in results if r.final_selected)
    mapping_failed = sum(1 for r in results if r.skip_reason == "코드 매핑 실패")
    stage_failed = total - passed - mapping_failed
    return total, passed, mapping_failed, stage_failed


def _resolve_date(date_arg: str | None) -> str:
    return date_arg or datetime.now().strftime("%Y%m%d")


def _precheck(yyyymmdd: str) -> tuple[bool, str]:
    """organizedCompany.md 존재/내용 사전 검증."""
    path = _REPORTS_ROOT / yyyymmdd / _ORGANIZED_FILE
    if not path.exists():
        return False, f"organizedCompany.md 없음: {path}"
    if path.stat().st_size == 0:
        return False, f"organizedCompany.md 가 0바이트: {path}"
    return True, ""


async def main() -> int:
    date_arg = sys.argv[1] if len(sys.argv) > 1 else None
    yyyymmdd = _resolve_date(date_arg)

    logger.info("debugResearchedCompany 시작 date={d}", d=yyyymmdd)

    ok, reason = _precheck(yyyymmdd)
    if not ok:
        logger.error("사전 검증 실패: {r}", r=reason)
        print(f"error: {reason}")
        return 1

    try:
        results = await research_today(date_arg)
    except ResearchError as exc:
        logger.error("진행 불가: {e}", e=exc)
        return 1
    except Exception as exc:
        logger.exception("예상치 못한 예외: {e}", e=exc)
        return 2

    out_path = save_researched_company(results, date=date_arg)
    total, passed, mapping_failed, stage_failed = _summarize(results)

    print(f"date: {yyyymmdd}")
    print(f"saved: {out_path}")
    print(f"total: {total}")
    print(f"passed: {passed}")
    print(f"mapping_failed: {mapping_failed}")
    print(f"stage_failed: {stage_failed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
