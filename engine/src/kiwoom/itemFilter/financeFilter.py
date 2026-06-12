"""finance.md 기반 종목 필터 — 당기순이익 적자 종목 제외.

``reports/<YYYYMMDD>/<종목명(종목코드)>/finance.md`` (ka10001,
:mod:`src.kiwoom.finance.finance` 모듈이 생성)를 입력으로 받아, **당기순이익
(억원)이 0보다 작은 종목을 대상에서 제외** 한다.

판정식::

    PASS(선정)    ≡  cup_nga is None  OR  cup_nga >= 0
    EXCLUDE(제외) ≡  cup_nga is not None  AND  cup_nga < 0

결측(``—``) / finance.md 무효("응답 데이터 없음") 는 음수임이 확인되지 않았
으므로 **선정(관대)** 처리하되, 사유 문구로 적자 통과와 구분한다.

본 모듈은 키움 API 를 직접 호출하지 않는다. ``finance`` 모듈이 미리 저장한
마크다운 리포트만 읽으며, finance 도메인 모듈에 의존하지 않는다(공용 인프라
및 itemFilter 패키지 내부 패턴만 재사용).
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Final

from loguru import logger

# ─────────────────────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_REPORTS_ROOT: Final[Path] = Path("reports")
_FINANCE_FILENAME: Final[str] = "finance.md"
_OUTPUT_FILENAME: Final[str] = "financeFilter.md"

_STOCK_DIR_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(.+?)\((\d{4,6})\)$")

# finance.md 당기순이익 행: | 당기순이익 (억원) | 452,068 |
_CUP_NGA_ROW_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\|\s*당기순이익 \(억원\)\s*\|\s*(.+?)\s*\|\s*$"
)

# finance.md 무효 본문 마커 (finance.render_markdown 의 is_empty 분기).
_INVALID_MARKER: Final[str] = "응답 데이터 없음"


# ─────────────────────────────────────────────────────────────────────────────
# 모델
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class FinanceFilterResult:
    """단일 종목 재무 필터 판정 결과.

    Attributes:
        stk_cd: 종목코드.
        stk_nm: 종목명.
        report_path: 입력 finance.md 경로.
        cup_nga: 당기순이익(억원, 부호 보존). 결측/무효 시 ``None``.
        selected: 리서치 대상 선정 여부.
        category: ``"선정"`` / ``"제외"``.
        reason: 사람이 읽을 수 있는 판정 사유.
        extra: 부가 메트릭 (``cup_nga_raw`` 등).
    """

    stk_cd: str
    stk_nm: str
    report_path: Path
    cup_nga: float | None
    selected: bool
    category: str
    reason: str
    extra: dict[str, object] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# 파싱
# ─────────────────────────────────────────────────────────────────────────────


def _to_float(value: str) -> float | None:
    """``"452,068"`` / ``"-1,234"`` / ``"1,234.56"`` → float (부호 보존).

    ``"—"`` / 빈값 / 부호만 / 변환불가 → ``None``.
    """
    s = value.strip().replace(",", "")
    if not s or s in {"+", "-", "—"}:
        return None
    try:
        return float(s)
    except ValueError:
        return None


def parse_finance_md(path: Path) -> tuple[float | None, dict[str, str]]:
    """finance.md 를 파싱하여 ``(cup_nga, meta)`` 를 반환.

    Args:
        path: ``finance.md`` 경로.

    Returns:
        ``(cup_nga, meta)`` 튜플.
            - ``cup_nga`` (float | None): 당기순이익(억원). 결측/무효 시 ``None``.
            - ``meta`` (dict): ``stk_cd``, ``stk_nm`` (있을 때).

    Raises:
        FileNotFoundError: 파일이 없을 때.
        ValueError: 무효 마커도 없고 당기순이익 행도 찾지 못했을 때
            (예상치 못한 포맷 — 일괄 처리 시 skip 대상).
    """
    text = Path(path).read_text(encoding="utf-8")

    meta: dict[str, str] = {}
    for line in text.splitlines():
        if line.startswith("- **종목코드**:"):
            m = re.search(r"\*\*종목코드\*\*:\s*(\d{4,6})", line)
            if m:
                meta["stk_cd"] = m.group(1)
        elif line.startswith("- **종목명**:"):
            m = re.search(r"\*\*종목명\*\*:\s*(.+)", line)
            if m:
                meta["stk_nm"] = m.group(1).strip()

    for line in text.splitlines():
        m = _CUP_NGA_ROW_PATTERN.match(line)
        if m:
            return _to_float(m.group(1)), meta

    # 당기순이익 행 없음 — 무효 문서면 결측(None)으로 정상 처리.
    if _INVALID_MARKER in text:
        return None, meta

    raise ValueError(f"finance.md 당기순이익 행 파싱 실패: {path}")


# ─────────────────────────────────────────────────────────────────────────────
# 종목 → 리포트 경로 탐색
# ─────────────────────────────────────────────────────────────────────────────


def _list_date_dirs(reports_root: Path) -> list[Path]:
    if not reports_root.exists():
        return []
    out = [
        p for p in reports_root.iterdir()
        if p.is_dir() and re.fullmatch(r"\d{8}", p.name)
    ]
    out.sort(key=lambda p: p.name, reverse=True)
    return out


def _latest_date_dir(reports_root: Path) -> Path | None:
    dirs = _list_date_dirs(reports_root)
    return dirs[0] if dirs else None


def _list_stock_dirs(date_dir: Path) -> list[Path]:
    if not date_dir.exists():
        return []
    return [
        p for p in date_dir.iterdir()
        if p.is_dir() and _STOCK_DIR_PATTERN.match(p.name)
    ]


def _split_stock_dirname(dirname: str) -> tuple[str, str] | None:
    m = _STOCK_DIR_PATTERN.match(dirname)
    if not m:
        return None
    return m.group(1), m.group(2)


def find_finance_md(
    stock: str,
    *,
    date_dir: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> Path:
    """종목코드/종목명으로 finance.md 경로를 탐색.

    Args:
        stock: 종목코드(예 ``"005930"``) 또는 종목명(예 ``"삼성전자"``).
        date_dir: ``YYYYMMDD``. ``None`` 이면 가장 최근 날짜 폴더.
        reports_root: 리포트 루트.

    Returns:
        finance.md 의 ``Path``.

    Raises:
        FileNotFoundError: 후보 폴더 또는 파일이 없을 때.
    """
    if date_dir:
        target = reports_root / date_dir
        if not target.exists():
            raise FileNotFoundError(f"날짜 폴더 없음: {target}")
    else:
        target = _latest_date_dir(reports_root)
        if target is None:
            raise FileNotFoundError(f"reports 하위에 날짜 폴더가 없음: {reports_root}")

    is_code = bool(re.fullmatch(r"\d{4,6}", stock))
    matches: list[Path] = []
    for stock_dir in _list_stock_dirs(target):
        parsed = _split_stock_dirname(stock_dir.name)
        if parsed is None:
            continue
        nm, cd = parsed
        if is_code and cd == stock:
            matches.append(stock_dir)
        elif not is_code and nm == stock:
            matches.append(stock_dir)

    if not matches:
        raise FileNotFoundError(
            f"종목 폴더 없음: stock={stock!r} date_dir={target.name}"
        )
    if len(matches) > 1:
        logger.warning(
            "종목 폴더 다중 매칭 — 첫 번째 사용: {names}",
            names=[p.name for p in matches],
        )

    finance = matches[0] / _FINANCE_FILENAME
    if not finance.exists():
        raise FileNotFoundError(f"finance.md 없음: {finance}")
    return finance


# ─────────────────────────────────────────────────────────────────────────────
# 판정 로직
# ─────────────────────────────────────────────────────────────────────────────


def evaluate_finance(
    cup_nga: float | None,
    *,
    invalid: bool = False,
) -> tuple[bool, str, str, dict[str, object]]:
    """재무 필터 판정 — 당기순이익 < 0 이면 제외.

    판정식::

        PASS(선정)    ≡  cup_nga is None  OR  cup_nga >= 0
        EXCLUDE(제외) ≡  cup_nga is not None  AND  cup_nga < 0

    Args:
        cup_nga: 당기순이익(억원). 결측 시 ``None``.
        invalid: finance.md 가 무효 문서였는지 여부(사유 문구 구분용).

    Returns:
        ``(selected, category, reason, extra)``.
            - ``selected`` (bool): 리서치 대상 여부.
            - ``category`` (str): ``"선정"`` / ``"제외"``.
            - ``reason`` (str): 판정 사유.
            - ``extra`` (dict): ``cup_nga``.
    """
    extra: dict[str, object] = {"cup_nga": cup_nga}

    if cup_nga is None:
        if invalid:
            return True, "선정", "재무 데이터 무효 — 음수 미확인, 통과", extra
        return True, "선정", "당기순이익 결측 — 음수 미확인, 통과", extra

    if cup_nga < 0:
        return (
            False,
            "제외",
            f"당기순이익 {cup_nga:,.0f}억원 < 0 (적자)",
            extra,
        )

    return (
        True,
        "선정",
        f"당기순이익 {cup_nga:,.0f}억원 ≥ 0",
        extra,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 단일 종목 / 일괄 필터
# ─────────────────────────────────────────────────────────────────────────────


def _is_invalid_md(path: Path) -> bool:
    try:
        return _INVALID_MARKER in Path(path).read_text(encoding="utf-8")
    except OSError:
        return False


def filter_stock(
    stock: str,
    *,
    date_dir: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> FinanceFilterResult:
    """단일 종목 재무 필터.

    Args:
        stock: 종목코드 또는 종목명.
        date_dir: ``YYYYMMDD``. ``None`` 이면 최근 날짜.
        reports_root: 리포트 루트.

    Returns:
        :class:`FinanceFilterResult`.
    """
    path = find_finance_md(stock, date_dir=date_dir, reports_root=reports_root)
    cup_nga, meta = parse_finance_md(path)
    invalid = cup_nga is None and _is_invalid_md(path)
    selected, category, reason, extra = evaluate_finance(cup_nga, invalid=invalid)

    parsed = _split_stock_dirname(path.parent.name)
    stk_nm = meta.get("stk_nm") or (parsed[0] if parsed else "")
    stk_cd = meta.get("stk_cd") or (parsed[1] if parsed else stock)

    return FinanceFilterResult(
        stk_cd=stk_cd,
        stk_nm=stk_nm,
        report_path=path,
        cup_nga=cup_nga,
        selected=selected,
        category=category,
        reason=reason,
        extra=extra,
    )


def filter_all_stocks(
    *,
    date_dir: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> list[FinanceFilterResult]:
    """지정 날짜 폴더 내 모든 종목 일괄 재무 필터.

    Args:
        date_dir: ``YYYYMMDD``. ``None`` 이면 최근 날짜.
        reports_root: 리포트 루트.

    Returns:
        모든 종목의 결과 리스트 (선정/제외 모두 포함).
    """
    if date_dir:
        target = reports_root / date_dir
    else:
        target = _latest_date_dir(reports_root)
        if target is None:
            raise FileNotFoundError(f"reports 하위에 날짜 폴더가 없음: {reports_root}")

    results: list[FinanceFilterResult] = []
    for stock_dir in _list_stock_dirs(target):
        finance = stock_dir / _FINANCE_FILENAME
        if not finance.exists():
            logger.debug("finance.md 없음, 건너뜀: {p}", p=stock_dir.name)
            continue
        parsed = _split_stock_dirname(stock_dir.name)
        if parsed is None:
            continue
        stk_nm, stk_cd = parsed
        try:
            cup_nga, meta = parse_finance_md(finance)
        except (ValueError, FileNotFoundError) as exc:
            logger.warning("파싱 실패 {n}({c}): {e}", n=stk_nm, c=stk_cd, e=exc)
            continue
        invalid = cup_nga is None and _is_invalid_md(finance)
        selected, category, reason, extra = evaluate_finance(
            cup_nga, invalid=invalid
        )
        results.append(
            FinanceFilterResult(
                stk_cd=meta.get("stk_cd") or stk_cd,
                stk_nm=meta.get("stk_nm") or stk_nm,
                report_path=finance,
                cup_nga=cup_nga,
                selected=selected,
                category=category,
                reason=reason,
                extra=extra,
            )
        )
    return results


# ─────────────────────────────────────────────────────────────────────────────
# 마크다운 리포트
# ─────────────────────────────────────────────────────────────────────────────


def _fmt_cup_nga(v: float | None) -> str:
    if v is None:
        return "—"
    return f"{v:,.0f}"


def render_markdown(
    results: list[FinanceFilterResult],
    *,
    fetched_at: str = "",
    date_dir: str = "",
) -> str:
    """필터 결과를 마크다운 리포트로 렌더링."""
    selected = [r for r in results if r.selected]
    excluded = [r for r in results if not r.selected]

    lines: list[str] = [
        "# 종목 필터 리포트 — finance 당기순이익",
        "",
        "## 판정 조건",
        "- **제외**: 당기순이익(억원) < 0 (적자)",
        "- **선정**: 당기순이익 ≥ 0",
        "- **결측/무효**: 음수 미확인 → 선정(관대) 처리, 사유로 구분",
        "",
        "## 요약",
        f"- **입력 날짜 폴더**: {date_dir or '—'}",
        f"- **취득 시각**: {fetched_at or '—'}",
        f"- **분석 종목 수**: {len(results)}",
        f"- **선정 종목 수**: {len(selected)}",
        f"- **제외 종목 수**: {len(excluded)}",
        "",
    ]

    lines += [
        f"## 선정 종목 ({len(selected)}건)",
        "",
        "| # | 종목코드 | 종목명 | 당기순이익(억원) | 사유 |",
        "|---:|---|---|---:|---|",
    ]
    for i, r in enumerate(selected, start=1):
        lines.append(
            "| {n} | {cd} | {nm} | {v} | {reason} |".format(
                n=i, cd=r.stk_cd, nm=r.stk_nm,
                v=_fmt_cup_nga(r.cup_nga), reason=r.reason,
            )
        )
    lines.append("")

    lines += [
        f"## 제외 종목 ({len(excluded)}건)",
        "",
        "| # | 종목코드 | 종목명 | 당기순이익(억원) | 사유 |",
        "|---:|---|---|---:|---|",
    ]
    for i, r in enumerate(excluded, start=1):
        lines.append(
            "| {n} | {cd} | {nm} | {v} | {reason} |".format(
                n=i, cd=r.stk_cd, nm=r.stk_nm,
                v=_fmt_cup_nga(r.cup_nga), reason=r.reason,
            )
        )
    lines += [
        "",
        "## 비고",
        "- 입력 데이터: ``reports/<날짜>/<종목명(종목코드)>/finance.md`` (ka10001)",
        "- 단위: 억원 (부호 보존, 음수 = 적자)",
        "- 결측(`—`)·무효 응답은 음수 미확인이므로 제외하지 않음",
        "- 본 리포트는 분석 보조 자료이며, 매매 신호로 단정해서는 안 됩니다",
        "",
    ]
    return "\n".join(lines)


def save_finance_filter_markdown(
    results: list[FinanceFilterResult],
    *,
    output_root: Path = _DEFAULT_REPORTS_ROOT,
    date_dir: str | None = None,
    now: datetime | None = None,
) -> Path:
    """필터 결과 리포트를 ``<output_root>/<날짜>/financeFilter.md`` 에 저장."""
    current = now or datetime.now()
    if date_dir is None:
        date_dir = current.strftime("%Y%m%d")
    fetched_at = current.strftime("%Y-%m-%d %H:%M:%S")

    md = render_markdown(results, fetched_at=fetched_at, date_dir=date_dir)

    out_dir = output_root / date_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / _OUTPUT_FILENAME
    out_path.write_text(md, encoding="utf-8")
    logger.info("필터 리포트 저장: {p}", p=out_path)
    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def _print_single(r: FinanceFilterResult) -> None:
    icon = "✅ 선정" if r.selected else "❌ 제외"
    print(f"{icon} [{r.category}] {r.stk_nm}({r.stk_cd})")
    print(f"  - 리포트: {r.report_path}")
    print(f"  - 당기순이익(억원): {_fmt_cup_nga(r.cup_nga)}")
    print(f"  - 사유: {r.reason}")


def main(argv: list[str] | None = None) -> int:
    """CLI 엔트리포인트.

    사용법::

        python -m src.kiwoom.itemFilter.financeFilter <stock> [<YYYYMMDD>]
        python -m src.kiwoom.itemFilter.financeFilter --all [<YYYYMMDD>]
    """
    import sys

    args = list(argv if argv is not None else sys.argv[1:])
    bulk = False
    if not args or args[0] == "--all":
        bulk = True
        if args and args[0] == "--all":
            args = args[1:]

    date_dir = (
        args[1] if (not bulk and len(args) >= 2)
        else (args[0] if (bulk and args) else None)
    )

    if bulk:
        results = filter_all_stocks(date_dir=date_dir)
        sel = sum(1 for r in results if r.selected)
        print(
            f"=== 재무 필터 일괄 결과: 분석 {len(results)} / 선정 {sel} / "
            f"제외 {len(results) - sel} ==="
        )
        for r in results:
            _print_single(r)
            print()
        path = save_finance_filter_markdown(results, date_dir=date_dir)
        print(f"\n리포트: {path}")
        return 0

    stock = args[0]
    r = filter_stock(stock, date_dir=date_dir)
    _print_single(r)
    return 0 if r.selected else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "FinanceFilterResult",
    "evaluate_finance",
    "filter_all_stocks",
    "filter_stock",
    "find_finance_md",
    "main",
    "parse_finance_md",
    "render_markdown",
    "save_finance_filter_markdown",
]
