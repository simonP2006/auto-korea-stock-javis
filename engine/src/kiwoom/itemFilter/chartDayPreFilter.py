"""chartDay.md 기반 사전(stage 2-1) 필터 — 금일 일봉 급상승 종목 제외.

``reports/<YYYYMMDD>/<종목명(종목코드)>/chartDay.md`` (``src.kiwoom.chartDay``
모듈이 생성)를 입력으로 받아, **금일 일봉이 전일 대비 15% 이상 급상승한 종목**
을 제외하기 위한 게이트다.

위치: pipeline 의 stage 2-1 — stage 2(chart240Filter) 와 stage 3(chartDayFilter)
사이에 배치된다. stage 3 의 정배열·MA612 밴드 검사 전에, 과열·고점 추격 위험이
높은 종목을 미리 걸러낸다.

판정식::

    PASS ≡
        len(bars) >= 2
        AND bars[-2].close > 0
        AND (bars[-1].close - bars[-2].close) / bars[-2].close < 0.15

조건 미달(봉 부족 / 전일 종가 0 / 금일 +15% 이상)이면 ``category="제외"`` /
``selected=False``.

본 모듈은 키움 API 를 직접 호출하지 않는다. ``chartDay`` 모듈이 미리 저장한
마크다운 리포트만 읽는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Final

from loguru import logger

from src.kiwoom.itemFilter.chartDayFilter import (
    ChartDayBar,
    _STOCK_DIR_PATTERN,
    _split_stock_dirname,
    parse_chartday_md,
)

# ─────────────────────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_REPORTS_ROOT: Final[Path] = Path("reports")
_CHARTDAY_FILENAME: Final[str] = "chartDay.md"
_OUTPUT_FILENAME: Final[str] = "chartDayPreFilter.md"

# 금일 일봉 변동률 상한. (close - prev_close) / prev_close ≥ 본 값이면 제외.
_DAILY_SURGE_THRESHOLD: Final[float] = 0.15


# ─────────────────────────────────────────────────────────────────────────────
# 모델
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(slots=True)
class ChartDayPreFilterResult:
    """단일 종목 사전 필터 판정 결과.

    Attributes:
        stk_cd: 종목코드.
        stk_nm: 종목명.
        report_path: 입력 chartDay.md 경로.
        bars: 파싱된 봉 데이터 (날짜 오름차순).
        selected: 통과 여부.
        category: ``"정상"`` / ``"제외"``.
        reason: 사람이 읽을 수 있는 판정 사유.
        latest_bar: 가장 최근 봉 (``bars[-1]``).
        daily_change_pct: (today.close - prev.close) / prev.close × 100.
        extra: 부가 메트릭.
    """

    stk_cd: str
    stk_nm: str
    report_path: Path
    bars: list[ChartDayBar]
    selected: bool
    category: str
    reason: str
    latest_bar: ChartDayBar | None = None
    daily_change_pct: float | None = None
    extra: dict[str, object] = field(default_factory=dict)


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


def find_chartday_md(
    stock: str,
    *,
    date_dir: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> Path:
    """종목코드/종목명으로 chartDay.md 경로를 탐색.

    Args:
        stock: 종목코드(예 ``"005930"``) 또는 종목명(예 ``"삼성전자"``).
        date_dir: ``YYYYMMDD``. ``None`` 이면 가장 최근 날짜 폴더.
        reports_root: 리포트 루트.

    Returns:
        chartDay.md 의 ``Path``.

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

    chartday = matches[0] / _CHARTDAY_FILENAME
    if not chartday.exists():
        raise FileNotFoundError(f"chartDay.md 없음: {chartday}")
    return chartday


# ─────────────────────────────────────────────────────────────────────────────
# 판정 로직
# ─────────────────────────────────────────────────────────────────────────────


def evaluate_chartday_pre(
    bars: list[ChartDayBar],
) -> tuple[bool, str, str, dict[str, object]]:
    """사전 필터 판정 — 금일 일봉 변동률 ≥ 15% 면 제외.

    판정식::

        PASS ≡
            len(bars) >= 2
            AND bars[-2].close > 0
            AND (bars[-1].close - bars[-2].close) / bars[-2].close < 0.15

    Args:
        bars: ``parse_chartday_md`` 가 반환한 봉 리스트 (날짜 오름차순).

    Returns:
        ``(selected, category, reason, extra)``.
            - ``selected`` (bool): 통과 여부.
            - ``category`` (str): ``"정상"`` / ``"제외"``.
            - ``reason`` (str): 사유.
            - ``extra`` (dict): ``latest_date``, ``daily_change_pct``.
    """
    if not bars:
        return False, "제외", "봉 데이터 없음", {}

    extra: dict[str, object] = {"latest_date": bars[-1].date}

    if len(bars) < 2:
        return False, "제외", f"봉 부족 ({len(bars)}봉 < 2봉)", extra

    last = bars[-1]
    prev = bars[-2]

    if prev.close <= 0:
        return False, "제외", f"전일 종가 ≤ 0 (prev.close={prev.close})", extra

    pct = (last.close - prev.close) / prev.close
    extra["daily_change_pct"] = round(pct * 100.0, 4)

    if pct >= _DAILY_SURGE_THRESHOLD:
        return (
            False,
            "제외",
            (
                f"금일 일봉 {pct * 100:+.2f}% — "
                f"{_DAILY_SURGE_THRESHOLD * 100:.0f}% 이상 급상승"
            ),
            extra,
        )

    return (
        True,
        "정상",
        (
            f"금일 일봉 {pct * 100:+.2f}% — "
            f"{_DAILY_SURGE_THRESHOLD * 100:.0f}% 미만"
        ),
        extra,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 단일 종목 / 일괄 필터
# ─────────────────────────────────────────────────────────────────────────────


def filter_stock(
    stock: str,
    *,
    date_dir: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> ChartDayPreFilterResult:
    """단일 종목 사전 필터.

    Args:
        stock: 종목코드 또는 종목명.
        date_dir: ``YYYYMMDD``. ``None`` 이면 최근 날짜.
        reports_root: 리포트 루트.

    Returns:
        :class:`ChartDayPreFilterResult`.
    """
    path = find_chartday_md(stock, date_dir=date_dir, reports_root=reports_root)
    bars, meta = parse_chartday_md(path)
    selected, category, reason, extra = evaluate_chartday_pre(bars)

    parsed = _split_stock_dirname(path.parent.name)
    stk_nm = meta.get("stk_nm") or (parsed[0] if parsed else "")
    stk_cd = meta.get("stk_cd") or (parsed[1] if parsed else stock)

    return ChartDayPreFilterResult(
        stk_cd=stk_cd,
        stk_nm=stk_nm,
        report_path=path,
        bars=bars,
        selected=selected,
        category=category,
        reason=reason,
        latest_bar=bars[-1] if bars else None,
        daily_change_pct=extra.get("daily_change_pct"),  # type: ignore[arg-type]
        extra=extra,
    )


def filter_all_stocks(
    *,
    date_dir: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> list[ChartDayPreFilterResult]:
    """지정 날짜 폴더 내 모든 종목 일괄 사전 필터.

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

    results: list[ChartDayPreFilterResult] = []
    for stock_dir in _list_stock_dirs(target):
        chartday = stock_dir / _CHARTDAY_FILENAME
        if not chartday.exists():
            logger.debug("chartDay.md 없음, 건너뜀: {p}", p=stock_dir.name)
            continue
        parsed = _split_stock_dirname(stock_dir.name)
        if parsed is None:
            continue
        stk_nm, stk_cd = parsed
        try:
            bars, meta = parse_chartday_md(chartday)
        except (ValueError, FileNotFoundError) as exc:
            logger.warning("파싱 실패 {n}({c}): {e}", n=stk_nm, c=stk_cd, e=exc)
            continue
        selected, category, reason, extra = evaluate_chartday_pre(bars)
        results.append(
            ChartDayPreFilterResult(
                stk_cd=stk_cd,
                stk_nm=stk_nm,
                report_path=chartday,
                bars=bars,
                selected=selected,
                category=category,
                reason=reason,
                latest_bar=bars[-1] if bars else None,
                daily_change_pct=extra.get("daily_change_pct"),  # type: ignore[arg-type]
                extra=extra,
            )
        )
    return results


# ─────────────────────────────────────────────────────────────────────────────
# 마크다운 리포트
# ─────────────────────────────────────────────────────────────────────────────


def _fmt_int(v: object) -> str:
    if v is None:
        return "—"
    return f"{int(v):,}"


def _fmt_pct(v: object) -> str:
    if v is None:
        return "—"
    return f"{float(v):+.2f}%"


def render_markdown(
    results: list[ChartDayPreFilterResult],
    *,
    fetched_at: str = "",
    date_dir: str = "",
) -> str:
    """사전 필터 결과를 마크다운 리포트로 렌더링."""
    selected = [r for r in results if r.selected]
    excluded = [r for r in results if not r.selected]

    lines: list[str] = [
        "# 종목 사전 필터 리포트 — chartDay 일봉 급상승 제외 (stage 2-1)",
        "",
        "## 판정 조건",
        f"- **금일 변동률**: (오늘 종가 - 어제 종가) / 어제 종가 < "
        f"+{_DAILY_SURGE_THRESHOLD * 100:.1f}%",
        "- **제외 사유**: 봉 부족 / 전일 종가 ≤ 0 / "
        f"금일 +{_DAILY_SURGE_THRESHOLD * 100:.0f}% 이상 급상승",
        "- **목적**: 고점 추격·과열 회피용 게이트. stage 3(chartDay 정배열 필터) 진입 전 적용.",
        "",
        "## 요약",
        f"- **입력 날짜 폴더**: {date_dir or '—'}",
        f"- **취득 시각**: {fetched_at or '—'}",
        f"- **분석 종목 수**: {len(results)}",
        f"- **통과 종목 수**: {len(selected)}",
        f"- **제외 종목 수**: {len(excluded)}",
        "",
    ]

    lines += [
        f"## 통과 종목 ({len(selected)}건)",
        "",
        "| # | 종목코드 | 종목명 | 최근 봉 | 전일 종가 | 금일 종가 | 금일 변동률 | 사유 |",
        "|---:|---|---|---|---:|---:|---:|---|",
    ]
    for i, r in enumerate(selected, start=1):
        b = r.latest_bar
        prev_close = r.bars[-2].close if len(r.bars) >= 2 else None
        lines.append(
            "| {n} | {cd} | {nm} | {ts} | {p} | {c} | {pct} | {reason} |".format(
                n=i, cd=r.stk_cd, nm=r.stk_nm,
                ts=b.date if b else "—",
                p=_fmt_int(prev_close),
                c=_fmt_int(b.close if b else None),
                pct=_fmt_pct(r.daily_change_pct),
                reason=r.reason,
            )
        )
    lines.append("")

    lines += [
        f"## 제외 종목 ({len(excluded)}건)",
        "",
        "| # | 종목코드 | 종목명 | 최근 봉 | 전일 종가 | 금일 종가 | 금일 변동률 | 사유 |",
        "|---:|---|---|---|---:|---:|---:|---|",
    ]
    for i, r in enumerate(excluded, start=1):
        b = r.latest_bar
        prev_close = r.bars[-2].close if len(r.bars) >= 2 else None
        lines.append(
            "| {n} | {cd} | {nm} | {ts} | {p} | {c} | {pct} | {reason} |".format(
                n=i, cd=r.stk_cd, nm=r.stk_nm,
                ts=b.date if b else "—",
                p=_fmt_int(prev_close),
                c=_fmt_int(b.close if b else None),
                pct=_fmt_pct(r.daily_change_pct),
                reason=r.reason,
            )
        )
    lines += [
        "",
        "## 비고",
        "- 입력 데이터: ``reports/<날짜>/<종목명(종목코드)>/chartDay.md``",
        "- 본 리포트는 분석 보조 자료이며, 매매 신호로 단정해서는 안 됩니다",
        "",
    ]
    return "\n".join(lines)


def save_chartday_pre_filter_markdown(
    results: list[ChartDayPreFilterResult],
    *,
    output_root: Path = _DEFAULT_REPORTS_ROOT,
    date_dir: str | None = None,
    now: datetime | None = None,
) -> Path:
    """필터 결과 리포트를 ``<output_root>/<날짜>/chartDayPreFilter.md`` 에 저장."""
    current = now or datetime.now()
    if date_dir is None:
        date_dir = current.strftime("%Y%m%d")
    fetched_at = current.strftime("%Y-%m-%d %H:%M:%S")

    md = render_markdown(results, fetched_at=fetched_at, date_dir=date_dir)

    out_dir = output_root / date_dir
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / _OUTPUT_FILENAME
    out_path.write_text(md, encoding="utf-8")
    logger.info("사전 필터 리포트 저장: {p}", p=out_path)
    return out_path


# ─────────────────────────────────────────────────────────────────────────────
# CLI
# ─────────────────────────────────────────────────────────────────────────────


def _print_single(r: ChartDayPreFilterResult) -> None:
    icon = "✅ 통과" if r.selected else "❌ 제외"
    print(f"{icon} [{r.category}] {r.stk_nm}({r.stk_cd})")
    print(f"  - 리포트: {r.report_path}")
    if r.latest_bar:
        b = r.latest_bar
        prev = r.bars[-2] if len(r.bars) >= 2 else None
        if prev is not None:
            print(
                f"  - 최근 봉 {b.date} | 전일 종가 {prev.close:,} → "
                f"금일 종가 {b.close:,}"
            )
        else:
            print(f"  - 최근 봉 {b.date} | 금일 종가 {b.close:,}")
    if r.daily_change_pct is not None:
        print(f"  - 금일 변동률 = {r.daily_change_pct:+.2f}%")
    print(f"  - 사유: {r.reason}")


def main(argv: list[str] | None = None) -> int:
    """CLI 엔트리포인트.

    사용법::

        python -m src.kiwoom.itemFilter.chartDayPreFilter <stock> [<YYYYMMDD>]
        python -m src.kiwoom.itemFilter.chartDayPreFilter --all [<YYYYMMDD>]
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
            f"=== 사전 필터 일괄 결과: 분석 {len(results)} / 통과 {sel} / "
            f"제외 {len(results) - sel} ==="
        )
        for r in results:
            _print_single(r)
            print()
        path = save_chartday_pre_filter_markdown(results, date_dir=date_dir)
        print(f"\n리포트: {path}")
        return 0

    stock = args[0]
    r = filter_stock(stock, date_dir=date_dir)
    _print_single(r)
    return 0 if r.selected else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ChartDayPreFilterResult",
    "evaluate_chartday_pre",
    "filter_all_stocks",
    "filter_stock",
    "find_chartday_md",
    "main",
    "render_markdown",
    "save_chartday_pre_filter_markdown",
]
