"""researchFlow 결과를 단순 텍스트로 저장한다.

저장 경로 (Stage 4 최종 통과 — 기존):
    ``reports/<YYYYMMDD>/researchedCompany.md``

저장 경로 (Stage 별 통과 — 신규):
    ``reports/<YYYYMMDD>/stage1_chart60_120_passed.md``
    ``reports/<YYYYMMDD>/stage2_chart240_passed.md``
    ``reports/<YYYYMMDD>/stage2_1_chartDayPre_passed.md``
    ``reports/<YYYYMMDD>/stage3_chartDay_passed.md``
    ``reports/<YYYYMMDD>/stage4_investor_passed.md``

포맷 (organizedCompany.md 와 동일, 모든 파일 동일):
    - 줄당 종목명 1개
    - 입력 순서(= organizedCompany.md 의 등락률 내림차순) 보존
    - 헤더/번호/등락률/구분자 모두 미표시
    - UTF-8, LF 줄바꿈, 마지막에 trailing newline 1개
    - 통과 종목 0건이면 빈 파일(0바이트)

확장자는 ``.md`` 지만 본문은 마크다운 표가 아니다 (사용자 결정 — 다음 단계
모듈이 다시 입력으로 사용하기 쉽게).

Stage N 통과 정의::

    len(r.stages) >= N AND r.stages[N-1].selected == True

즉 Stage N 까지 도달해서 그 단계를 통과한 종목 — 이후 단계 결과와는 무관.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Final

from loguru import logger

from src.kiwoom.researchFlow.models import ResearchResult

_DEFAULT_REPORTS_ROOT: Final[Path] = Path("reports")
_FILENAME: Final[str] = "researchedCompany.md"

# 출력 슬롯(1-indexed) → 파일명. ``research_today`` 가 실행하는 6 Stage 순서
# (chart60_120 → chart240 → chartDayPre → chartDay → investor → finance) 와
# 일치해야 한다. 슬롯 번호는 ``ResearchResult.stages`` 의 1-indexed 인덱스 와
# 동일하다.
_STAGE_FILENAMES: Final[dict[int, str]] = {
    1: "stage1_chart60_120_passed.md",
    2: "stage2_chart240_passed.md",
    3: "stage2_1_chartDayPre_passed.md",
    4: "stage3_chartDay_passed.md",
    5: "stage4_investor_passed.md",
    6: "stage5_finance_passed.md",
}


def render_plain_text(results: list[ResearchResult]) -> str:
    """``final_selected=True`` 인 결과만 종목명 줄단위 텍스트로 변환.

    빈 결과면 빈 문자열을 반환한다(파일 0바이트 저장용).
    """
    selected = [r for r in results if r.final_selected]
    if not selected:
        return ""
    return "\n".join(r.candidate.stk_nm for r in selected) + "\n"


def save_researched_company(
    results: list[ResearchResult],
    *,
    date: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> Path:
    """``reports/<YYYYMMDD>/researchedCompany.md`` 로 저장하고 경로 반환.

    Args:
        results: facade.research_today() 의 반환 리스트.
        date: ``YYYYMMDD``. ``None`` 이면 오늘.
        reports_root: 보고서 루트.

    Returns:
        저장된 파일 ``Path``.
    """
    yyyymmdd = date or datetime.now().strftime("%Y%m%d")
    out_dir = reports_root / yyyymmdd
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / _FILENAME

    text = render_plain_text(results)
    out_path.write_text(text, encoding="utf-8")

    selected = sum(1 for r in results if r.final_selected)
    logger.info(
        "researchedCompany.md 저장: {p} (통과 {s}/{n}건, {b} bytes)",
        p=out_path, s=selected, n=len(results), b=len(text.encode("utf-8")),
    )
    return out_path


def render_stage_passed(
    results: list[ResearchResult],
    stage_idx: int,
) -> str:
    """Stage ``stage_idx`` 까지 도달해서 그 단계를 통과한 종목명 리스트.

    Args:
        results: facade.research_today() 의 반환 리스트.
        stage_idx: 1-indexed 출력 슬롯 번호 (1·2·3·4·5·6).
            stages 인덱스(``r.stages[idx-1]``)와 1:1 대응한다.

    Returns:
        통과 종목명을 줄단위로 연결한 문자열 (없으면 빈 문자열).
    """
    passed = [
        r for r in results
        if len(r.stages) >= stage_idx and r.stages[stage_idx - 1].selected
    ]
    if not passed:
        return ""
    return "\n".join(r.candidate.stk_nm for r in passed) + "\n"


def save_stage_passed(
    results: list[ResearchResult],
    *,
    stage_idx: int,
    date: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> Path:
    """Stage ``stage_idx`` 통과 종목을 단순 텍스트로 저장하고 경로 반환.

    Args:
        results: facade.research_today() 반환 리스트.
        stage_idx: 1·2·3·4·5·6 중 하나.
        date: ``YYYYMMDD``. ``None`` 이면 오늘.
        reports_root: 보고서 루트.

    Returns:
        저장된 파일 ``Path``.

    Raises:
        ValueError: ``stage_idx`` 가 1·2·3·4·5·6 범위 밖일 때.
    """
    if stage_idx not in _STAGE_FILENAMES:
        raise ValueError(f"stage_idx must be 1·2·3·4·5·6, got {stage_idx}")

    yyyymmdd = date or datetime.now().strftime("%Y%m%d")
    out_dir = reports_root / yyyymmdd
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / _STAGE_FILENAMES[stage_idx]

    text = render_stage_passed(results, stage_idx)
    out_path.write_text(text, encoding="utf-8")

    passed = sum(
        1 for r in results
        if len(r.stages) >= stage_idx and r.stages[stage_idx - 1].selected
    )
    logger.info(
        "{f} 저장: {p} (통과 {s}/{n}건, {b} bytes)",
        f=_STAGE_FILENAMES[stage_idx], p=out_path,
        s=passed, n=len(results), b=len(text.encode("utf-8")),
    )
    return out_path


def save_all_stages_passed(
    results: list[ResearchResult],
    *,
    date: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> list[Path]:
    """Stage 1·2·2-1·3·4·5 통과 종목 리스트를 각각 별도 파일로 저장.

    Args:
        results: facade.research_today() 반환 리스트.
        date: ``YYYYMMDD``. ``None`` 이면 오늘.
        reports_root: 보고서 루트.

    Returns:
        저장된 파일 경로 6개 (stage 순서).
    """
    return [
        save_stage_passed(
            results, stage_idx=idx, date=date, reports_root=reports_root,
        )
        for idx in (1, 2, 3, 4, 5, 6)
    ]


__all__ = [
    "render_plain_text",
    "render_stage_passed",
    "save_all_stages_passed",
    "save_researched_company",
    "save_stage_passed",
]
