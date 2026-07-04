"""chart240.md 기반 종목 필터.

``reports/<YYYYMMDD>/<종목명(종목코드)>/chart240.md`` 리포트(:mod:`src.kiwoom.
chart240.saveReport.markdown` 가 생성)를 입력으로 받아 단일 장기추세 조건에
부합하는 종목을 선별한다.

판정 색상-MA 매핑::

    파란색(10일선)  = MA10
    빨간색(20일선)  = MA20
    녹색(60일선)    = MA60
    검은색(306일선) = MA306

봉 1개의 조건 (장기 추세 -7.0% 허용)::

    MA60 ≥ MA306 × 0.93

판정 시점 — 최근 3봉(``bars[-3]``, ``bars[-2]``, ``bars[-1]``) 모두에서 위
조건이 성립하면 선정. 봉 수 < 3, MA 결측, MA306=0, 또는 최근 3봉 중
하나라도 실패 시 제외.

수식::

    선정 = (len(bars) >= 3) and all(
        b.ma60 >= b.ma306 * 0.93
        for b in bars[-3:]
    )

본 모듈은 키움 API 를 직접 호출하지 않는다. ``chart240`` 모듈이 미리 저장한
마크다운 리포트만 읽는다.

사용 예::

    from src.kiwoom.itemFilter.chart240Filter import (
        filter_stock,
        filter_all_stocks,
        save_chart240_filter_markdown,
    )

    # 단일 종목
    r = filter_stock("005930")
    print(r.selected, r.category, r.reason)

    # 일괄 (오늘자 reports/ 전체)
    results = filter_all_stocks()
    save_chart240_filter_markdown(results)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Final

from loguru import logger

from src.kiwoom.itemFilter.chart60Filter import (
    Chart60Bar,
    _STOCK_DIR_PATTERN,
    _TABLE_ROW_PATTERN,
    _parse_int,
    _parse_ma,
    _split_stock_dirname,
)

# ─────────────────────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_REPORTS_ROOT: Final[Path] = Path("reports")
_CHART240_FILENAME: Final[str] = "chart240.md"
_OUTPUT_FILENAME: Final[str] = "chart240Filter.md"

# 장기추세 허용오차 (비대칭, 상단 -7.0% 까지 허용).
# 적용 식: MA60 >= MA306 * (1 - _MA60_MA306_TOLERANCE)
# 이전: 0.025 (Phase B 전문가픽 역설계 2026-07-05 — pre-breakout Stage1→2 전이 회수,
# S2 사망 tol결박 37건 중 27건 회수. 근거: PHASE_B_PROPOSAL_20260704.md §1-B)
_MA60_MA306_TOLERANCE: Final[float] = 0.07

# 조건을 만족해야 하는 최근 봉 개수 (시간 오름차순 마지막 N봉).
_REQUIRED_CONSECUTIVE_BARS: Final[int] = 3


# ─────────────────────────────────────────────────────────────────────────────
# 모델
# ─────────────────────────────────────────────────────────────────────────────


# Chart240Bar 는 Chart60Bar 와 스키마가 동일하므로 alias 로 재사용.
Chart240Bar = Chart60Bar


@dataclass(slots=True)
class Chart240FilterResult:
    """단일 종목 필터 판정 결과.

    Attributes:
        stk_cd: 종목코드.
        stk_nm: 종목명.
        report_path: 입력 chart240.md 경로.
        bars: 16봉 데이터 (시간 오름차순).
        selected: 리서치 대상 선정 여부.
        category: 분류 라벨 — ``"장기추세"`` / ``"제외"``.
        reason: 사람이 읽을 수 있는 판정 사유.
        latest_bar: 가장 최근 봉 (``bars[-1]``).
        ma60_ma306_pct: (MA60 - MA306) / MA306 × 100 (최근 봉 기준, 관찰용).
        extra: 부가 메트릭. 키 예시:
            - ``latest_ts``: 최근 봉 시각.
            - ``gap_60_306_pct``: 최근 봉의 MA60↔MA306 갭 (%).
            - ``passed_recent_3``: 최근 3봉 각각의 조건 통과 여부
              (list[bool], 시간 오름차순 [-3], [-2], [-1]).
    """

    stk_cd: str
    stk_nm: str
    report_path: Path
    bars: list[Chart240Bar]
    selected: bool
    category: str
    reason: str
    latest_bar: Chart240Bar | None = None
    ma60_ma306_pct: float | None = None
    extra: dict[str, object] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# 파싱 (chart60 표 정규식 재사용)
# ─────────────────────────────────────────────────────────────────────────────


def parse_chart240_md(path: Path) -> tuple[list[Chart240Bar], dict[str, str]]:
    """chart240.md 를 파싱하여 봉 리스트와 헤더 메타를 반환.

    Args:
        path: ``chart240.md`` 절대/상대 경로.

    Returns:
        ``(bars, meta)`` 튜플:
            - ``bars``: ``Chart240Bar`` 리스트 (시간 오름차순).
            - ``meta``: 헤더에서 추출한 부가 정보
              (``stk_cd``, ``stk_nm``, ``fetched_at``, ``last_bar_ts``).

    Raises:
        FileNotFoundError: 파일이 없을 때.
        ValueError: 시계열 표 행이 0개일 때 (포맷 오류).
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
        elif line.startswith("- **취득 시각**:"):
            m = re.search(r"\*\*취득 시각\*\*:\s*(.+)", line)
            if m:
                meta["fetched_at"] = m.group(1).strip()
        elif line.startswith("- **최근 봉 시각**:"):
            m = re.search(r"\*\*최근 봉 시각\*\*:\s*(.+)", line)
            if m:
                meta["last_bar_ts"] = m.group(1).strip()

    bars: list[Chart240Bar] = []
    for line in text.splitlines():
        m = _TABLE_ROW_PATTERN.match(line)
        if not m:
            continue
        bars.append(
            Chart240Bar(
                ts=m.group(1),
                open=_parse_int(m.group(2)),
                high=_parse_int(m.group(3)),
                low=_parse_int(m.group(4)),
                close=_parse_int(m.group(5)),
                volume=_parse_int(m.group(6)),
                ma10=_parse_ma(m.group(7)),
                ma20=_parse_ma(m.group(8)),
                ma60=_parse_ma(m.group(9)),
                ma306=_parse_ma(m.group(10)),
            )
        )

    if not bars:
        raise ValueError(f"chart240.md 시계열 표 파싱 실패 (행 0개): {path}")

    return bars, meta


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


def find_chart240_md(
    stock: str,
    *,
    date_dir: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> Path:
    """종목코드 또는 종목명으로 chart240.md 경로를 탐색.

    Raises:
        FileNotFoundError: 후보 폴더 또는 파일을 찾지 못한 경우.
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

    chart240 = matches[0] / _CHART240_FILENAME
    if not chart240.exists():
        raise FileNotFoundError(f"chart240.md 없음: {chart240}")
    return chart240


# ─────────────────────────────────────────────────────────────────────────────
# 판정 로직 (단일 조건: MA60 ≥ MA306 × (1 − tol); 현행 tol=0.07 → × 0.93)
# ─────────────────────────────────────────────────────────────────────────────


def _check_bar(bar: Chart240Bar) -> tuple[bool, str | None]:
    """한 봉의 MA60↔MA306 조건 검사.

    조건: ``MA60 ≥ MA306 × (1 − _MA60_MA306_TOLERANCE)``.

    Args:
        bar: 검사 대상 240분봉.

    Returns:
        ``(ok, reason)``. 통과 시 ``(True, None)``. 실패 시 ``(False, 사유)``.
        MA60/MA306 결측·MA306=0 도 실패로 처리.
    """
    if bar.ma60 is None or bar.ma306 is None:
        return False, f"MA 결측 (ma60={bar.ma60} ma306={bar.ma306})"
    if bar.ma306 == 0:
        return False, "MA306=0 (분모 0)"

    t = 1.0 - _MA60_MA306_TOLERANCE  # = 0.93 (tol=0.07)

    if bar.ma60 < bar.ma306 * t:
        return False, (
            f"MA60({bar.ma60:,.2f}) < MA306×{t:.3f}"
            f"({bar.ma306 * t:,.2f})"
        )
    return True, None


def evaluate_chart240(
    bars: list[Chart240Bar],
) -> tuple[bool, str, str, dict[str, object]]:
    """**최근 3봉** 기준으로 MA60↔MA306 조건 판정.

    판정식::

        선정 = (len(bars) >= 3) AND ∀ b ∈ bars[-3:]:
                   b.MA60 ≥ b.MA306 × 0.93

    Args:
        bars: ``parse_chart240_md`` 가 반환한 봉 리스트 (시간 오름차순).

    Returns:
        ``(selected, category, reason, extra)`` 튜플.
            - ``selected`` (bool): 리서치 대상 여부.
            - ``category`` (str): ``"장기추세"`` / ``"제외"``.
            - ``reason`` (str): 판정 사유 (사람이 읽을 수 있는 한 줄).
            - ``extra`` (dict): 부가 메트릭 — ``latest_ts``,
              ``gap_60_306_pct``, ``ma60_ma306_pct`` (호환),
              ``passed_recent_3`` (list[bool] 시간 오름차순).
    """
    if not bars:
        return False, "제외", "봉 데이터 없음", {}

    last = bars[-1]
    extra: dict[str, object] = {"latest_ts": last.ts}

    # 최근 봉의 MA60↔MA306 갭(%) 기록 — 결측이면 건너뜀.
    if last.ma60 is not None and last.ma306 not in (None, 0):
        gap = (last.ma60 - last.ma306) / last.ma306 * 100.0
        extra["gap_60_306_pct"] = round(gap, 4)
        extra["ma60_ma306_pct"] = round(gap, 4)  # 호환

    if len(bars) < _REQUIRED_CONSECUTIVE_BARS:
        return (
            False,
            "제외",
            f"봉 부족 ({len(bars)}봉 < {_REQUIRED_CONSECUTIVE_BARS}봉)",
            extra,
        )

    recent = bars[-_REQUIRED_CONSECUTIVE_BARS:]
    flags: list[bool] = []
    fail_msg: str | None = None
    for b in recent:
        ok, reason = _check_bar(b)
        flags.append(ok)
        if not ok and fail_msg is None:
            fail_msg = f"ts={b.ts} {reason}"
    extra["passed_recent_3"] = flags

    if all(flags):
        return (
            True,
            "장기추세",
            f"최근 {_REQUIRED_CONSECUTIVE_BARS}봉 모두 "
            f"MA60 ≥ MA306×{1.0 - _MA60_MA306_TOLERANCE:.3f}",
            extra,
        )

    return (
        False,
        "제외",
        f"최근 {_REQUIRED_CONSECUTIVE_BARS}봉 MA60↔MA306 실패 — {fail_msg}",
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
) -> Chart240FilterResult:
    """단일 종목 필터.

    Args:
        stock: 종목코드 또는 종목명.
        date_dir: ``YYYYMMDD``. ``None`` 이면 최근 날짜 자동 선택.
        reports_root: 리포트 루트.

    Returns:
        :class:`Chart240FilterResult`.
    """
    path = find_chart240_md(stock, date_dir=date_dir, reports_root=reports_root)
    bars, meta = parse_chart240_md(path)
    selected, category, reason, extra = evaluate_chart240(bars)

    parsed = _split_stock_dirname(path.parent.name)
    stk_nm = meta.get("stk_nm") or (parsed[0] if parsed else "")
    stk_cd = meta.get("stk_cd") or (parsed[1] if parsed else stock)

    return Chart240FilterResult(
        stk_cd=stk_cd,
        stk_nm=stk_nm,
        report_path=path,
        bars=bars,
        selected=selected,
        category=category,
        reason=reason,
        latest_bar=bars[-1] if bars else None,
        ma60_ma306_pct=extra.get("ma60_ma306_pct"),  # type: ignore[arg-type]
        extra=extra,
    )


def filter_all_stocks(
    *,
    date_dir: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> list[Chart240FilterResult]:
    """지정 날짜 폴더 내 모든 종목 일괄 필터.

    Args:
        date_dir: ``YYYYMMDD``. ``None`` 이면 최근 날짜 폴더.
        reports_root: 리포트 루트.

    Returns:
        모든 종목의 :class:`Chart240FilterResult` 리스트
        (선정/제외 모두 포함, 입력 폴더 정렬 순).
    """
    if date_dir:
        target = reports_root / date_dir
    else:
        target = _latest_date_dir(reports_root)
        if target is None:
            raise FileNotFoundError(f"reports 하위에 날짜 폴더가 없음: {reports_root}")

    results: list[Chart240FilterResult] = []
    for stock_dir in _list_stock_dirs(target):
        chart240 = stock_dir / _CHART240_FILENAME
        if not chart240.exists():
            logger.debug("chart240.md 없음, 건너뜀: {p}", p=stock_dir.name)
            continue
        parsed = _split_stock_dirname(stock_dir.name)
        if parsed is None:
            continue
        stk_nm, stk_cd = parsed
        try:
            bars, meta = parse_chart240_md(chart240)
        except (ValueError, FileNotFoundError) as exc:
            logger.warning("파싱 실패 {n}({c}): {e}", n=stk_nm, c=stk_cd, e=exc)
            continue
        selected, category, reason, extra = evaluate_chart240(bars)
        results.append(
            Chart240FilterResult(
                stk_cd=stk_cd,
                stk_nm=stk_nm,
                report_path=chart240,
                bars=bars,
                selected=selected,
                category=category,
                reason=reason,
                latest_bar=bars[-1] if bars else None,
                ma60_ma306_pct=extra.get("ma60_ma306_pct"),  # type: ignore[arg-type]
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


def _fmt_float(v: object) -> str:
    if v is None:
        return "—"
    return f"{float(v):,.2f}"


def _fmt_pct(v: object) -> str:
    if v is None:
        return "—"
    return f"{float(v):+.2f}%"


def render_markdown(
    results: list[Chart240FilterResult],
    *,
    fetched_at: str = "",
    date_dir: str = "",
) -> str:
    """필터 결과를 마크다운 리포트로 렌더링.

    Args:
        results: ``filter_all_stocks`` 또는 ``[filter_stock(...)]`` 결과.
        fetched_at: 표시용 시각.
        date_dir: 입력 날짜 폴더명(헤더 표기용).

    Returns:
        마크다운 본문 문자열.
    """
    selected = [r for r in results if r.selected]
    excluded = [r for r in results if not r.selected]

    by_category: dict[str, int] = {}
    for r in results:
        by_category[r.category] = by_category.get(r.category, 0) + 1

    lines: list[str] = [
        "# 종목 필터 리포트 — chart240 240분봉 장기추세",
        "",
        "## 판정 조건",
        "- **장기추세 정의** (장기 추세 -7.0% 허용):",
        "    - MA60 ≥ MA306 × 0.93",
        "- **필요조건**: 최근 3봉(``bars[-3]``, ``bars[-2]``, ``bars[-1]``) "
        "모두 위 조건 만족",
        "- **제외 사유**: 봉 수 < 3 / MA60 또는 MA306 결측 / MA306=0 / "
        "최근 3봉 중 하나라도 조건 실패",
        "- **색상 매핑**: 🔵파랑=MA10 / 🔴빨강=MA20 / 🟢초록=MA60 / ⚫검정=MA306",
        "",
        "## 요약",
        f"- **입력 날짜 폴더**: {date_dir or '—'}",
        f"- **취득 시각**: {fetched_at or '—'}",
        f"- **분석 종목 수**: {len(results)}",
        f"- **선정 종목 수**: {len(selected)}",
        f"- **제외 종목 수**: {len(excluded)}",
        f"- **분류 분포**: "
        + (
            ", ".join(f"{k} {v}건" for k, v in sorted(by_category.items()))
            or "—"
        ),
        "",
    ]

    lines += [
        f"## 선정 종목 ({len(selected)}건)",
        "",
        "| # | 종목코드 | 종목명 | 분류 | 최근 봉 | 종가 | MA60 | MA306 | Δ60/306 | 사유 |",
        "|---:|---|---|---|---|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(selected, start=1):
        b = r.latest_bar
        lines.append(
            "| {n} | {cd} | {nm} | {cat} | {ts} | {c} | {m60} | {m306} | {g} | {reason} |".format(
                n=i, cd=r.stk_cd, nm=r.stk_nm, cat=r.category,
                ts=b.ts if b else "—",
                c=_fmt_int(b.close if b else None),
                m60=_fmt_float(b.ma60 if b else None),
                m306=_fmt_float(b.ma306 if b else None),
                g=_fmt_pct(r.extra.get("gap_60_306_pct")),
                reason=r.reason,
            )
        )
    lines.append("")

    lines += [
        f"## 제외 종목 ({len(excluded)}건)",
        "",
        "| # | 종목코드 | 종목명 | 최근 봉 | MA60 | MA306 | 사유 |",
        "|---:|---|---|---|---:|---:|---|",
    ]
    for i, r in enumerate(excluded, start=1):
        b = r.latest_bar
        lines.append(
            "| {n} | {cd} | {nm} | {ts} | {m60} | {m306} | {reason} |".format(
                n=i, cd=r.stk_cd, nm=r.stk_nm,
                ts=b.ts if b else "—",
                m60=_fmt_float(b.ma60 if b else None),
                m306=_fmt_float(b.ma306 if b else None),
                reason=r.reason,
            )
        )
    lines += [
        "",
        "## 비고",
        "- 입력 데이터: ``reports/<날짜>/<종목명(종목코드)>/chart240.md``",
        "- MA 값은 chart240 모듈이 산출한 240분봉 종가 기준 단순이동평균(SMA)",
        "- 본 리포트는 분석 보조 자료이며, 매매 신호로 단정해서는 안 됩니다",
        "",
    ]
    return "\n".join(lines)


def save_chart240_filter_markdown(
    results: list[Chart240FilterResult],
    *,
    output_root: Path = _DEFAULT_REPORTS_ROOT,
    date_dir: str | None = None,
    now: datetime | None = None,
) -> Path:
    """필터 결과 리포트를 ``<output_root>/<날짜>/chart240Filter.md`` 에 저장."""
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


def _print_single(r: Chart240FilterResult) -> None:
    icon = "✅ 선정" if r.selected else "❌ 제외"
    print(f"{icon} [{r.category}] {r.stk_nm}({r.stk_cd})")
    print(f"  - 리포트: {r.report_path}")
    if r.latest_bar:
        b = r.latest_bar
        print(
            f"  - 최근 봉 {b.ts} | 종가 {b.close:,} | "
            f"MA60 {b.ma60} MA306 {b.ma306}"
        )
    g = r.extra.get("gap_60_306_pct")
    if g is not None:
        print(f"  - MA60↔MA306 갭: {float(g):+.2f}%")  # type: ignore[arg-type]
    flags = r.extra.get("passed_recent_3")
    if isinstance(flags, list) and flags:
        print(
            f"  - 최근 {len(flags)}봉 조건: "
            + " ".join("○" if x else "×" for x in flags)
        )
    print(f"  - 사유: {r.reason}")


def main(argv: list[str] | None = None) -> int:
    """CLI 엔트리포인트.

    사용법::

        python -m src.kiwoom.itemFilter.chart240Filter <stock> [<YYYYMMDD>]
        python -m src.kiwoom.itemFilter.chart240Filter --all [<YYYYMMDD>]

    인자가 없으면 ``--all`` 과 동일하게 동작.
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
            f"=== 일괄 필터 결과: 분석 {len(results)} / "
            f"선정 {sel} / 제외 {len(results) - sel} ==="
        )
        for r in results:
            _print_single(r)
            print()
        path = save_chart240_filter_markdown(results, date_dir=date_dir)
        print(f"\n리포트: {path}")
        return 0

    stock = args[0]
    r = filter_stock(stock, date_dir=date_dir)
    _print_single(r)
    return 0 if r.selected else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "Chart240Bar",
    "Chart240FilterResult",
    "evaluate_chart240",
    "filter_all_stocks",
    "filter_stock",
    "find_chart240_md",
    "main",
    "parse_chart240_md",
    "render_markdown",
    "save_chart240_filter_markdown",
]
