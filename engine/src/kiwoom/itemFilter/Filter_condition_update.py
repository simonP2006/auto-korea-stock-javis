"""masterReference 종목의 Stage 별 탈락 사유 분석·기록.

실행 시점::

    마지막 Stage 까지 끝나고 ``reports/<YYYYMMDD>/researchedCompany.md``
    작성이 완료된 직후 호출한다.

동작::

    1. ``reports/<YYYYMMDD>/masterReference.md`` 에 종목이 한 건도 없으면
       (파일 부재 / 빈 파일 / 공백 only) 아무것도 하지 않고 종료한다.
    2. 종목이 있으면, **종목 단위**로 섹션을 만들고 그 종목이 각 Stage
       통과 결과 파일 6 종
       (``stage1_chart60_120_passed.md`` … ``stage5_finance_passed.md``)
       에 없으면, 해당 Stage 의 필터를 그 종목에 대해 재평가하여 "어떤
       조건에 의해 제외되었는지" 사유를
       ``reports/<YYYYMMDD>/masterReference.log`` 에 기록한다.
    3. 종목 별 섹션의 마지막 라인에 기록 날짜-시간을 함께 남긴다.
    4. researchedCompany.md 가 재실행될 수 있으므로 로그는 덮어쓰지 않고
       **append** 한다 (실행마다 새 블록이 누적된다).

Stage 결과 파일에 종목이 "없다" 는 것은 두 경우를 포함한다:

    (a) 해당 Stage 필터 조건에서 탈락 — 재평가하면 selected=False, 사유 출력.
    (b) 이전 Stage 에서 탈락하여 해당 Stage 에 도달조차 못함 — 단계별
        필터는 독립 평가이므로 재평가 시 selected=True 일 수 있다. 이때는
        "본 단계 자체는 통과(재평가) — 이전 단계 탈락으로 미도달" 로 구분
        기록한다.

실행::

    python -m src.kiwoom.itemFilter.Filter_condition_update            # 오늘
    python -m src.kiwoom.itemFilter.Filter_condition_update 20260516   # 특정일 1건
    python -m src.kiwoom.itemFilter.Filter_condition_update 20260518 20260519 20260520
                                                                       # 여러 날짜 순차 실행

종료 코드 (다중 일자 시 일자별 코드 중 가장 큰 값)::

    0 — 정상 (분석·기록 완료, 또는 종목 0건으로 정상 종료)
    1 — 날짜 폴더 부재 등 진행 불가
    2 — 기타 예외
"""

from __future__ import annotations

import re
import sys
from datetime import datetime
from pathlib import Path
from typing import Callable, Final

from loguru import logger

from src.kiwoom.itemFilter import (
    chart60_120_filter_stock,
    chart240_filter_stock,
    chartday_filter_stock,
    chartday_pre_filter_stock,
    finance_filter_stock,
    investor_filter_stock,
)
from src.kiwoom.researchFlow.name_resolver import build_name_to_code_map

_DEFAULT_REPORTS_ROOT: Final[Path] = Path("reports")
_MASTER_REFERENCE_MD: Final[str] = "masterReference.md"
_MASTER_REFERENCE_LOG: Final[str] = "masterReference.log"
_RESEARCHED_MD: Final[str] = "researchedCompany.md"

# (표시 라벨, Stage 명, 통과 결과 파일명, 단일 종목 필터 콜러블)
# 순서·파일명은 researchFlow.saveReport._STAGE_FILENAMES 와 1:1 일치한다.
_StageFilter = Callable[..., object]
_STAGES: Final[list[tuple[str, str, str, _StageFilter]]] = [
    ("Stage 1", "chart60_120", "stage1_chart60_120_passed.md",
     chart60_120_filter_stock),
    ("Stage 2", "chart240", "stage2_chart240_passed.md",
     chart240_filter_stock),
    ("Stage 2-1", "chartDayPre", "stage2_1_chartDayPre_passed.md",
     chartday_pre_filter_stock),
    ("Stage 3", "chartDay", "stage3_chartDay_passed.md",
     chartday_filter_stock),
    ("Stage 4", "investor", "stage4_investor_passed.md",
     investor_filter_stock),
    ("Stage 5", "finance", "stage5_finance_passed.md",
     finance_filter_stock),
]

# "종목명(123456)" 형태에서 이름/코드 분리.
_NAME_CODE_RE: Final[re.Pattern[str]] = re.compile(r"^(?P<nm>.*?)\((?P<cd>\d{4,6})\)\s*$")


def _today_yyyymmdd() -> str:
    return datetime.now().strftime("%Y%m%d")


def _parse_entry(line: str) -> tuple[str, str]:
    """한 줄을 ``(종목명, 종목코드)`` 로 파싱. 코드 없으면 빈 문자열."""
    s = line.strip()
    m = _NAME_CODE_RE.match(s)
    if m:
        return m.group("nm").strip(), m.group("cd")
    return s, ""


def _read_names(path: Path) -> list[tuple[str, str]]:
    """줄단위 ``(종목명, 종목코드)`` 리스트. 파일 부재/빈 줄은 무시."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    out: list[tuple[str, str]] = []
    for raw in text.splitlines():
        if raw.strip():
            out.append(_parse_entry(raw))
    return out


def _read_passed_names(path: Path) -> set[str]:
    """Stage 통과 결과 .md 의 종목명 집합 (코드 접미사 있으면 제거)."""
    return {nm for nm, _cd in _read_names(path)}


def _resolve_ident(
    name: str,
    code: str,
    code_map: dict[str, str],
) -> str:
    """필터 콜러블에 넘길 식별자 — 코드 우선, 없으면 종목명."""
    if code:
        return code
    mapped = code_map.get(name, "")
    return mapped or name


def _analyze_stock(
    filter_fn: _StageFilter,
    ident: str,
    *,
    date_dir: str,
    reports_root: Path,
) -> str:
    """단일 종목·단일 Stage 재평가 → 사람이 읽을 로그 한 줄(사유부)."""
    try:
        r = filter_fn(ident, date_dir=date_dir, reports_root=reports_root)
    except FileNotFoundError as exc:
        return f"필터 평가 불가 — 입력 데이터 없음: {exc}"
    except Exception as exc:  # noqa: BLE001 — 종목 단위 격리
        return f"필터 평가 불가 — {type(exc).__name__}: {exc}"

    selected = bool(getattr(r, "selected", False))
    category = str(getattr(r, "category", ""))
    reason = str(getattr(r, "reason", ""))

    if selected:
        return (
            f"[{category}] 본 단계 자체는 통과(재평가) — "
            f"이전 단계 탈락으로 미도달 / 사유: {reason}"
        )
    return f"[{category}] {reason}"


def run_filter_condition_update(
    date: str | None = None,
    *,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> int:
    """masterReference 종목의 Stage 별 탈락 사유를 분석·append 기록.

    Args:
        date: ``YYYYMMDD``. ``None`` 이면 오늘.
        reports_root: 보고서 루트(기본 ``reports/``).

    Returns:
        종료 코드 (0 정상 / 1 진행 불가).
    """
    yyyymmdd = date or _today_yyyymmdd()
    date_dir = reports_root / yyyymmdd

    if not date_dir.exists():
        logger.error("날짜 폴더 없음: {p}", p=date_dir)
        print(f"진행 불가 — 날짜 폴더 없음: {date_dir}")
        return 1

    researched = date_dir / _RESEARCHED_MD
    if not researched.exists():
        # 사양상 researchedCompany.md 완료 후 실행 전제 — 경고만 하고 진행.
        logger.warning(
            "{f} 부재 — 사양상 마지막 Stage 완료 후 실행 전제이나 계속 진행",
            f=_RESEARCHED_MD,
        )

    master_md = date_dir / _MASTER_REFERENCE_MD
    targets = _read_names(master_md)
    if not targets:
        logger.info(
            "masterReference 종목 0건 — 아무것도 하지 않고 종료 (path={p})",
            p=master_md,
        )
        print(f"masterReference 종목 0건 — 종료 (path={master_md})")
        return 0

    code_map = build_name_to_code_map(date_dir)
    now = datetime.now()
    stamp = now.strftime("%Y-%m-%d %H:%M:%S")

    lines: list[str] = []
    sep = "=" * 78
    lines.append(sep)
    lines.append(
        f"[{stamp}] masterReference 분석 (date={yyyymmdd}, "
        f"대상 {len(targets)}종목)"
    )
    lines.append(sep)

    # Stage 별 통과 종목 집합·파일 부재 여부를 1회만 계산해 둔다.
    stage_ctx: list[tuple[str, str, str, _StageFilter, set[str], str]] = []
    for label, stage_name, passed_file, filter_fn in _STAGES:
        passed_path = date_dir / passed_file
        passed = _read_passed_names(passed_path)
        file_note = "" if passed_path.exists() else "  (※ 결과 파일 부재)"
        stage_ctx.append(
            (label, stage_name, passed_file, filter_fn, passed, file_note)
        )

    # 종목 단위로 각 Stage 의 원인 조건을 기술한다.
    for nm, cd in targets:
        ident = _resolve_ident(nm, cd, code_map)
        disp = f"{nm}({cd})" if cd else nm

        lines.append("")
        lines.append(f"### {disp}")

        recorded = False
        for label, stage_name, passed_file, filter_fn, passed, file_note in (
            stage_ctx
        ):
            if nm in passed:
                continue  # 해당 Stage 통과 — 기록 대상 아님
            detail = _analyze_stock(
                filter_fn, ident,
                date_dir=yyyymmdd, reports_root=reports_root,
            )
            lines.append(
                f"- {label} — {stage_name} ({passed_file})"
                f"{file_note}: {detail}"
            )
            recorded = True

        if not recorded:
            lines.append("- (전 Stage 통과 — 기록 대상 없음)")

        lines.append(f"(기록 {stamp})")

    lines.append("")

    log_path = date_dir / _MASTER_REFERENCE_LOG
    with log_path.open("a", encoding="utf-8") as fp:
        fp.write("\n".join(lines) + "\n")

    logger.info(
        "masterReference.log append 완료: {p} (대상 {n}종목, {b} bytes 추가)",
        p=log_path, n=len(targets),
        b=len("\n".join(lines).encode("utf-8")) + 1,
    )
    print(
        f"date: {yyyymmdd}\n"
        f"masterReference 대상 : {len(targets)} 종목\n"
        f"masterReference.log  : append 완료 ({log_path})"
    )
    return 0


def main() -> int:
    """CLI — 인자 없으면 오늘 1건, 1개 이상이면 각 일자에 대해 순차 실행.

    종료 코드는 일자별 코드 중 가장 큰 값 (모두 성공이면 0).
    """
    dates: list[str | None] = (
        list(sys.argv[1:]) if len(sys.argv) > 1 else [None]
    )
    logger.info(
        "Filter_condition_update 시작 dates={d}",
        d=[d or "오늘" for d in dates],
    )

    worst = 0
    for idx, d in enumerate(dates, start=1):
        if len(dates) > 1:
            header = f"--- [{idx}/{len(dates)}] date={d or '오늘'} ---"
            print(header)
        try:
            code = run_filter_condition_update(d)
        except Exception as exc:  # noqa: BLE001
            logger.exception("예상치 못한 예외 (date={d}): {e}", d=d, e=exc)
            code = 2
        if code > worst:
            worst = code
    return worst


if __name__ == "__main__":
    raise SystemExit(main())
