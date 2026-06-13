"""organizedCompany 도메인 모델.

마크다운 입력 두 종(``conditionResearch.md`` / ``upperLowerPrice.md``)에서
추출한 종목 한 건을 표현한다.

- ``stk_nm`` (종목명) 이 1차 dedup 키.
- ``stk_cd`` 는 2차 dedup 키(정규화 코드 ``split("_")[0]``)로 사용된다 — 동일 종목이
  출처별로 다른 종목명(절단명 vs 전체명)으로 들어온 교차출처 중복을 제거한다. 진단 로깅에도 사용.
- ``flu_rt`` 는 정렬 키. 출력에는 표시되지 않는다.
- ``source`` 는 충돌 시 우선권 결정에 사용된다(``upperLower`` 우선).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict


SourceLabel = Literal["upperLower", "conditionRes"]


class OrganizedStock(BaseModel):
    """정리 대상 종목 한 건.

    Attributes:
        stk_cd: 종목코드(원본 그대로, 진단용). 비어 있을 수 있음.
        stk_nm: 종목명. **공백 제거 후** dedup 및 정렬에 사용.
        flu_rt: 등락률(%, 부호 보존). 정렬 키.
        source: 어느 입력 파일에서 왔는지.
    """

    model_config = ConfigDict(extra="ignore")

    stk_cd: str = ""
    stk_nm: str
    flu_rt: float = 0.0
    source: SourceLabel
