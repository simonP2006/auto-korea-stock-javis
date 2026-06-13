"""두 마크다운(``conditionResearch.md`` / ``upperLowerPrice.md``)을 통합한다.

흐름:
    1. 두 파일을 각각 파싱 (없으면 경고 + 빈 리스트)
    2. 종목명(``stk_nm.strip()``) 기준 1차 dedup
       - 충돌 시 ``upperLower`` 출처 행을 우선 채택(사용자 결정 Q2-b)
    2-1. 정규화 종목코드(``stk_cd.split("_")[0]``) 기준 2차 dedup
       - 동일 종목이 출처별로 다른 종목명(예: conditionRes 10자 절단명 vs
         upperLower 전체명)으로 들어와 1차를 통과한 교차출처 중복을 제거.
         upperLower 출처/더 긴 종목명을 우선 보존.
    3. 등락률 내림차순 정렬 (동률 시 종목명 오름차순)
    4. ``list[OrganizedStock]`` 반환

본 모듈은 부수효과(파일 저장)를 갖지 않는다 — 저장은
``saveReport.save_organized_company`` 의 책임.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Final

from loguru import logger

from src.kiwoom.organizedCompany.models import OrganizedStock
from src.kiwoom.organizedCompany.parsers import (
    parse_condition_research,
    parse_upper_lower_price,
)

_DEFAULT_REPORTS_ROOT: Final[Path] = Path("reports")
_CONDITION_FILE: Final[str] = "conditionResearch.md"
_UPPER_LOWER_FILE: Final[str] = "upperLowerPrice.md"


class OrganizeError(RuntimeError):
    """입력 파일이 모두 부재 등 진행 불가 오류."""


def _today_yyyymmdd() -> str:
    return datetime.now().strftime("%Y%m%d")


def organize_today(
    date: str | None = None,
    *,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> list[OrganizedStock]:
    """주어진 날짜의 두 보고서를 통합한 종목 리스트를 반환한다.

    Args:
        date: ``YYYYMMDD`` 형식. ``None`` 이면 오늘.
        reports_root: 보고서 루트(기본 ``reports/``).

    Returns:
        등락률 내림차순으로 정렬된 ``OrganizedStock`` 리스트.
        두 파일 중 하나라도 있으면 진행. 모두 없으면 :class:`OrganizeError`.
    """
    yyyymmdd = date or _today_yyyymmdd()
    base = reports_root / yyyymmdd

    cond_path = base / _CONDITION_FILE
    upper_path = base / _UPPER_LOWER_FILE

    cond_rows = parse_condition_research(cond_path)
    upper_rows = parse_upper_lower_price(upper_path)

    if not cond_rows and not upper_rows:
        raise OrganizeError(
            f"입력 파일 부재 또는 추출 0건: {cond_path}, {upper_path}"
        )

    # ── dedup: stk_nm 기준, upperLower 우선 ─────────────────────────────
    by_name: dict[str, OrganizedStock] = {}
    duplicates_within_upper = 0
    overrides = 0  # upperLower 가 conditionRes 행을 덮어쓴 횟수

    # 1) upperLower 먼저 채워 우선권 확보
    for s in upper_rows:
        key = s.stk_nm.strip()
        if not key:
            continue
        if key in by_name:
            duplicates_within_upper += 1
            continue
        by_name[key] = s

    # 2) conditionRes 는 빈 자리에만 추가
    for s in cond_rows:
        key = s.stk_nm.strip()
        if not key:
            continue
        if key in by_name:
            existing = by_name[key]
            if existing.source == "upperLower":
                overrides += 1
                if existing.stk_cd and s.stk_cd:
                    # 동명 다코드 케이스 추적용 — DEBUG 로깅만
                    if existing.stk_cd.split("_")[0] != s.stk_cd.split("_")[0]:
                        logger.debug(
                            "동명 다코드 ({n}): upperLower={u} conditionRes={c}",
                            n=key, u=existing.stk_cd, c=s.stk_cd,
                        )
            continue
        by_name[key] = s

    # ── 2차 dedup: 정규화 종목코드(_AL 등 출처별 접미사 제거) 기준 ─────────
    # 동일 종목이 출처별로 다른 종목명으로 들어와 1차 종목명 dedup을 통과한
    # 경우(예: conditionRes "한국타이어앤테크놀로"[10자 절단] vs upperLower
    # "한국타이어앤테크놀로지"[전체], 같은 코드 161390/161390_AL)를 제거한다.
    # 코드가 같으면 동일 종목 — upperLower 출처를 우선 보존하고, 동률이면 더
    # 긴(덜 잘린) 종목명을 채택한다. 코드가 비면 1차(종목명) dedup 결과 유지.
    by_code: dict[str, OrganizedStock] = {}
    no_code: list[OrganizedStock] = []
    cross_source_dups = 0
    for s in by_name.values():
        canon = s.stk_cd.split("_")[0].strip() if s.stk_cd else ""
        if not canon:
            no_code.append(s)
            continue
        existing = by_code.get(canon)
        if existing is None:
            by_code[canon] = s
            continue
        cross_source_dups += 1
        keep = existing
        if existing.source != s.source:
            keep = existing if existing.source == "upperLower" else s
        elif len(s.stk_nm) > len(existing.stk_nm):
            keep = s
        by_code[canon] = keep

    deduped = list(by_code.values()) + no_code

    # ── 정렬: 등락률 desc, 종목명 asc ───────────────────────────────────
    merged = sorted(
        deduped,
        key=lambda x: (-x.flu_rt, x.stk_nm),
    )

    logger.info(
        "통합 완료: upperLower={u} conditionRes={c} → 고유 {n}건 "
        "(upper 내부 중복 {d}, upper가 cond를 덮은 횟수 {o}, "
        "교차출처 동일코드 중복 제거 {x})",
        u=len(upper_rows), c=len(cond_rows), n=len(merged),
        d=duplicates_within_upper, o=overrides, x=cross_source_dups,
    )
    return merged
