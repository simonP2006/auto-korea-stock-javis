"""6개 종목 일봉 데이터를 키움 API로 받아 chartDay.md를 생성한다.

stage 2(chart240Filter strict)에서 탈락한 6개 종목은 chartDay.md가 없어
chartDay 임계값 산출이 불가능했다. 일회용 fetch 스크립트로 일봉 데이터를
가져와 reports/<YYYYMMDD>/<종목명(종목코드)>/chartDay.md를 생성한다.

실행::

    python -m scripts.fetch_chartday_8stocks
"""

from __future__ import annotations

import asyncio

from loguru import logger

from src.kiwoom.chartDay import get_daily_with_ma
from src.kiwoom.chartDay.saveReport import save_chartday_markdown

_TARGETS: list[tuple[str, str]] = [
    ("093320", "케이아이엔엑스"),
    ("469750", "아이비젼웍스"),
    ("060310", "3S"),
    ("053060", "세동"),
    ("212710", "아이에스티이"),
    ("254120", "자비스"),
]

_BARS = 16
_INTER_DELAY = 0.5


async def main() -> int:
    fails: list[str] = []
    for stk_cd, stk_nm in _TARGETS:
        logger.info("fetch 시작 {n}({c})", n=stk_nm, c=stk_cd)
        try:
            df = await get_daily_with_ma(stk_cd, bars=_BARS)
        except Exception as exc:
            logger.exception("예외 {n}({c}): {e}", n=stk_nm, c=stk_cd, e=exc)
            fails.append(f"{stk_nm}({stk_cd}): {exc}")
            await asyncio.sleep(_INTER_DELAY)
            continue
        if df.empty:
            logger.warning("빈 응답 {n}({c})", n=stk_nm, c=stk_cd)
            fails.append(f"{stk_nm}({stk_cd}): empty")
            await asyncio.sleep(_INTER_DELAY)
            continue
        out = save_chartday_markdown(df, stk_cd=stk_cd, stk_name=stk_nm)
        logger.info("저장 완료: {p}", p=out)
        await asyncio.sleep(_INTER_DELAY)

    if fails:
        logger.error("실패: {f}", f=fails)
        return 1
    logger.info("전 종목 fetch 완료 — {n}건", n=len(_TARGETS))
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
