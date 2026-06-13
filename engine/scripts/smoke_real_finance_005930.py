"""실전 서버 스모크 — 삼성전자(005930) 재무 기본정보 (ka10001).

PER·EPS·ROE·PBR·당기순이익을 단발 조회해 finance.md 로 저장한다.
당기순이익 단위(PDF 미명시)를 HTS 종목정보 화면과 대조 검증하는 용도.

실행::

    python -m scripts.smoke_real_finance_005930

결과는 ``reports/<오늘 YYYYMMDD>/삼성전자(005930)/finance.md`` 로 저장된다.
"""

from __future__ import annotations

import asyncio

from loguru import logger

from src.kiwoom.finance.finance import (
    get_finance_snapshot,
    save_finance_markdown,
)

_STK_CD = "005930"
_STK_NAME = "삼성전자"


async def main() -> int:
    logger.info("실전 호출 시작 stk_cd={s}", s=_STK_CD)

    snap = await get_finance_snapshot(_STK_CD)

    if snap.is_empty:
        logger.warning("빈/무효 결과")
        return 1

    out_path = save_finance_markdown(
        snap, stk_cd=_STK_CD, stk_name=_STK_NAME,
    )
    logger.info("저장 완료: {p}", p=out_path)

    print(
        f"PER={snap.per} EPS={snap.eps} ROE={snap.roe} "
        f"PBR={snap.pbr} 당기순이익={snap.cup_nga}"
    )
    print(f"raw={snap.raw}")
    return 0


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
