"""종목명 → 종목코드 매핑 빌더.

``reports/<YYYYMMDD>/organizedCompany.md`` 는 종목명만 줄 단위로 보관하므로,
키움 API 호출에 필요한 종목코드를 같은 폴더의 두 입력 파일에서 복원한다:

    - ``conditionResearch.md``
    - ``upperLowerPrice.md``

두 파일 모두 ``종목코드 / 종목명`` 컬럼을 가진 표를 포함하며, organizedCompany
모듈이 이미 ``parse_condition_research`` / ``parse_upper_lower_price`` 로
파싱 로직을 구현해두었다 — 본 모듈은 그 파서를 재사용한다.

종목코드 정규화:
    - upperLowerPrice.md 의 코드는 ``"044820_AL"`` 처럼 거래소 접미사가 붙어 있다.
    - chart60/chartDay/investor 모듈의 saveReport 는 종목코드를 그대로
      디렉토리명(``종목명(종목코드)``)에 사용하지만, itemFilter 모듈의 폴더 매칭
      정규식은 ``\\d{4,6}`` 만 허용한다 — 따라서 본 모듈은 접미사를 잘라낸
      평문 6자리만 반환한다.

충돌 정책 (organizedCompany.facade 와 동일):
    - 종목명이 두 파일 모두에 등장하면 ``upperLower`` 출처 코드를 우선 채택.
    - 동일 출처 내 중복은 첫 번째를 유지.
    - ``stk_cd`` 가 빈 행은 매핑에 추가하지 않는다.

본 모듈은 부수효과(파일 저장)를 갖지 않는다.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Final

from loguru import logger

from src.kiwoom.organizedCompany.parsers import (
    parse_condition_research,
    parse_upper_lower_price,
)

_CONDITION_FILE: Final[str] = "conditionResearch.md"
_UPPER_LOWER_FILE: Final[str] = "upperLowerPrice.md"

# 거래소 접미사(``_AL``/``_NX`` 등) 제거용. 평문 4~6자리 숫자만 추출.
_CODE_DIGITS_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(\d{4,6})")


def _strip_exchange_suffix(stk_cd: str) -> str:
    """``"044820_AL"`` / ``"005930"`` → ``"044820"`` / ``"005930"``.

    선두 4~6자리 숫자만 추출. 매칭 실패 시 빈 문자열.
    """
    m = _CODE_DIGITS_PATTERN.match(stk_cd.strip())
    return m.group(1) if m else ""


def build_name_to_code_map(date_dir: Path) -> dict[str, str]:
    """주어진 날짜 폴더에서 ``{종목명: 종목코드}`` 매핑을 빌드.

    Args:
        date_dir: ``reports/<YYYYMMDD>`` 절대/상대 경로.

    Returns:
        종목명을 키, 6자리 종목코드(접미사 없음)를 값으로 갖는 dict.
        두 입력 파일 모두 부재이면 빈 dict 반환 (caller 가 결정).
    """
    cond_path = date_dir / _CONDITION_FILE
    upper_path = date_dir / _UPPER_LOWER_FILE

    upper_rows = parse_upper_lower_price(upper_path)
    cond_rows = parse_condition_research(cond_path)

    out: dict[str, str] = {}
    upper_filled = 0
    cond_filled = 0
    overrides_skipped = 0

    for s in upper_rows:
        key = s.stk_nm.strip()
        cd = _strip_exchange_suffix(s.stk_cd)
        if not key or not cd:
            continue
        if key in out:
            continue
        out[key] = cd
        upper_filled += 1

    for s in cond_rows:
        key = s.stk_nm.strip()
        cd = _strip_exchange_suffix(s.stk_cd)
        if not key or not cd:
            continue
        if key in out:
            overrides_skipped += 1
            continue
        out[key] = cd
        cond_filled += 1

    logger.info(
        "name→code 매핑 완료: total={t} (upper={u}, cond={c}, "
        "upper 우선유지={o})",
        t=len(out), u=upper_filled, c=cond_filled, o=overrides_skipped,
    )
    return out


__all__ = ["build_name_to_code_map"]
