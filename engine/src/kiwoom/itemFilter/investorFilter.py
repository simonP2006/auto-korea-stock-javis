"""investor.md 기반 종목 필터.

``reports/<YYYYMMDD>/<종목명(종목코드)>/investor.md`` 리포트(:mod:`src.kiwoom.
investor` 모듈이 생성, ka10059)를 입력으로 받아 투자자 수급 조건에 부합하는
종목을 선별한다.

판정 로직 (16봉 = 16거래일 기준)::

    [전제]   봉 수 < 16 → 제외 (데이터 부족)

    [부호 정의]
        매도(-) := value < 0
        매수(+) := value ≥ 0       (0 은 매수로 처리)

    [(2) 외국인 연속 매도]   최근일부터 역순으로 외국인 매도가 ≥ 5회 → 제외
    [(3) 기관계 연속 매도]   최근일부터 역순으로 기관계 매도가 ≥ 8회 → 제외
    [(4) 개인 연속 매수]     최근일부터 역순으로 개인   매수가 ≥ 3회 → 제외
    [(5) 외국인 매도 일수]   16일 중 외국인 매도가 ≥ 15일                → 제외

본 모듈은 키움 API 를 직접 호출하지 않는다. ``investor`` 모듈이 미리 저장한
마크다운 리포트만 읽는다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Callable, Final

import pandas as pd
from loguru import logger

# ─────────────────────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_REPORTS_ROOT: Final[Path] = Path("reports")
_INVESTOR_FILENAME: Final[str] = "investor.md"
_OUTPUT_FILENAME: Final[str] = "investorFilter.md"

_REQUIRED_BARS: Final[int] = 16

# 임계값.
# _THRESHOLD_FOREIGN_CONSEC_SELL 이전: 2 (Phase B 전문가픽 역설계 2026-07-05 —
# 전문가는 단기(≤4일) 외국인 연속매도를 용인. 근거: PHASE_B_PROPOSAL_20260704.md §1-B)
_THRESHOLD_FOREIGN_CONSEC_SELL: Final[int] = 5
_THRESHOLD_INST_CONSEC_SELL: Final[int] = 8
_THRESHOLD_INDI_CONSEC_BUY: Final[int] = 3
_THRESHOLD_FOREIGN_TOTAL_SELL: Final[int] = 15

_STOCK_DIR_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(.+?)\((\d{4,6})\)$")

# investor.md 시계열 표 행 패턴: | 2026-04-15 | -508,327 | +20,238 | +92,896 |
_TABLE_ROW_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\|\s*(\d{4}-\d{2}-\d{2})\s*"
    r"\|\s*([+-]?[\d,]+)\s*"
    r"\|\s*([+-]?[\d,]+)\s*"
    r"\|\s*([+-]?[\d,]+)\s*\|\s*$"
)


# ─────────────────────────────────────────────────────────────────────────────
# 모델
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class InvestorBar:
    """investor.md 시계열 한 행(일별 순매수금액).

    Attributes:
        date: 거래일 ``YYYY-MM-DD``.
        indi: 개인 순매수금액(백만원, 부호 보존).
        foreign: 외국인 순매수금액(백만원, 부호 보존).
        inst: 기관계 순매수금액(백만원, 부호 보존).
    """

    date: str
    indi: int
    foreign: int
    inst: int


@dataclass(slots=True)
class InvestorFilterResult:
    """단일 종목 투자자 필터 판정 결과.

    Attributes:
        stk_cd: 종목코드.
        stk_nm: 종목명.
        report_path: 입력 investor.md 경로.
        bars: 거래일 데이터 (날짜 오름차순).
        selected: 리서치 대상 선정 여부.
        category: ``"선정"`` / ``"제외"``.
        reason: 사람이 읽을 수 있는 판정 사유.
        latest_bar: 최근 거래일 봉 (마지막).
        metrics: 판정 메트릭 dict
            (``foreign_consec_sell``, ``inst_consec_sell``,
            ``indi_consec_buy``, ``foreign_total_sell``).
    """

    stk_cd: str
    stk_nm: str
    report_path: Path
    bars: list[InvestorBar]
    selected: bool
    category: str
    reason: str
    latest_bar: InvestorBar | None = None
    metrics: dict[str, int] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# 파싱
# ─────────────────────────────────────────────────────────────────────────────


def _parse_signed_int(s: str) -> int:
    """``"+20,238"`` / ``"-508,327"`` / ``"123"`` → int (부호 보존)."""
    s = s.strip().replace(",", "")
    if not s:
        return 0
    return int(s)


def parse_investor_md(path: Path) -> tuple[list[InvestorBar], dict[str, str]]:
    """investor.md 를 파싱하여 봉 리스트와 헤더 메타를 반환.

    Args:
        path: ``investor.md`` 경로.

    Returns:
        ``(bars, meta)`` 튜플. ``meta`` 키:
        ``stk_cd``, ``stk_nm``, ``fetched_at``, ``last_bar_date``.

    Raises:
        FileNotFoundError: 파일이 없을 때.
        ValueError: 시계열 표 행이 0개일 때.
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
        elif line.startswith("- **최근 거래일**:"):
            m = re.search(r"\*\*최근 거래일\*\*:\s*(.+)", line)
            if m:
                meta["last_bar_date"] = m.group(1).strip()

    bars: list[InvestorBar] = []
    for line in text.splitlines():
        m = _TABLE_ROW_PATTERN.match(line)
        if not m:
            continue
        bars.append(
            InvestorBar(
                date=m.group(1),
                indi=_parse_signed_int(m.group(2)),
                foreign=_parse_signed_int(m.group(3)),
                inst=_parse_signed_int(m.group(4)),
            )
        )

    if not bars:
        raise ValueError(f"investor.md 시계열 표 파싱 실패 (행 0개): {path}")

    return bars, meta


def bars_to_dataframe(bars: list[InvestorBar]) -> pd.DataFrame:
    """``InvestorBar`` 리스트 → DataFrame (DB화 결과)."""
    return pd.DataFrame(
        [
            {
                "date": b.date,
                "indi": b.indi,
                "foreign": b.foreign,
                "inst": b.inst,
            }
            for b in bars
        ]
    )


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


def find_investor_md(
    stock: str,
    *,
    date_dir: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> Path:
    """종목코드/종목명으로 investor.md 경로를 탐색.

    Args:
        stock: 종목코드(예 ``"005930"``) 또는 종목명(예 ``"삼성전자"``).
        date_dir: ``YYYYMMDD``. ``None`` 이면 가장 최근 날짜 폴더.
        reports_root: 리포트 루트.

    Returns:
        investor.md 의 ``Path``.

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

    investor = matches[0] / _INVESTOR_FILENAME
    if not investor.exists():
        raise FileNotFoundError(f"investor.md 없음: {investor}")
    return investor


# ─────────────────────────────────────────────────────────────────────────────
# 판정 로직
# ─────────────────────────────────────────────────────────────────────────────


def _count_leading(items: list[InvestorBar], pred: Callable[[InvestorBar], bool]) -> int:
    """``items`` 첫 원소부터 ``pred`` 가 True 인 동안의 연속 개수.

    ``items`` 는 호출측에서 최근일이 첫 원소가 되도록 reverse 한 리스트.
    """
    n = 0
    for x in items:
        if pred(x):
            n += 1
        else:
            break
    return n


def evaluate_investor(
    bars: list[InvestorBar],
) -> tuple[bool, str, str, dict[str, int]]:
    """투자자 필터 판정.

    부호 정의: 매도 = ``value < 0``, 매수 = ``value >= 0`` (0 은 매수로 처리).

    Args:
        bars: ``parse_investor_md`` 가 반환한 봉 리스트(날짜 오름차순).

    Returns:
        ``(selected, category, reason, metrics)`` 튜플.
            - ``selected`` (bool): 리서치 대상 여부.
            - ``category`` (str): "선정" / "제외".
            - ``reason`` (str): 판정 사유.
            - ``metrics`` (dict[str, int]):
              ``foreign_consec_sell`` / ``inst_consec_sell`` /
              ``indi_consec_buy`` / ``foreign_total_sell`` /
              ``bar_count``.
    """
    metrics: dict[str, int] = {"bar_count": len(bars)}

    if len(bars) < _REQUIRED_BARS:
        return (
            False,
            "제외",
            f"봉 수 {len(bars)} < {_REQUIRED_BARS} (데이터 부족)",
            metrics,
        )

    rev = list(reversed(bars))  # 최근일이 첫 원소

    foreign_consec_sell = _count_leading(rev, lambda b: b.foreign < 0)
    inst_consec_sell = _count_leading(rev, lambda b: b.inst < 0)
    indi_consec_buy = _count_leading(rev, lambda b: b.indi >= 0)
    foreign_total_sell = sum(1 for b in bars if b.foreign < 0)

    metrics.update(
        {
            "foreign_consec_sell": foreign_consec_sell,
            "inst_consec_sell": inst_consec_sell,
            "indi_consec_buy": indi_consec_buy,
            "foreign_total_sell": foreign_total_sell,
        }
    )

    # (2) 외국인 연속 매도
    if foreign_consec_sell >= _THRESHOLD_FOREIGN_CONSEC_SELL:
        return (
            False,
            "제외",
            f"외국인 {foreign_consec_sell}회 연속 매도 "
            f"(≥ {_THRESHOLD_FOREIGN_CONSEC_SELL})",
            metrics,
        )

    # (3) 기관계 연속 매도
    if inst_consec_sell >= _THRESHOLD_INST_CONSEC_SELL:
        return (
            False,
            "제외",
            f"기관계 {inst_consec_sell}회 연속 매도 "
            f"(≥ {_THRESHOLD_INST_CONSEC_SELL})",
            metrics,
        )

    # (4) 개인 연속 매수
    if indi_consec_buy >= _THRESHOLD_INDI_CONSEC_BUY:
        return (
            False,
            "제외",
            f"개인 {indi_consec_buy}회 연속 매수 "
            f"(≥ {_THRESHOLD_INDI_CONSEC_BUY})",
            metrics,
        )

    # (5) 외국인 16일 중 매도 일수
    if foreign_total_sell >= _THRESHOLD_FOREIGN_TOTAL_SELL:
        return (
            False,
            "제외",
            f"외국인 16일 중 매도일 {foreign_total_sell} "
            f"(≥ {_THRESHOLD_FOREIGN_TOTAL_SELL})",
            metrics,
        )

    return (
        True,
        "선정",
        f"외국인 연속매도 {foreign_consec_sell} / 기관계 연속매도 {inst_consec_sell} "
        f"/ 개인 연속매수 {indi_consec_buy} / 외국인 매도일수 {foreign_total_sell} "
        f"— 모든 조건 통과",
        metrics,
    )


# ─────────────────────────────────────────────────────────────────────────────
# 단일 종목 / 일괄 필터
# ─────────────────────────────────────────────────────────────────────────────


def filter_stock(
    stock: str,
    *,
    date_dir: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> InvestorFilterResult:
    """단일 종목 투자자 필터.

    Args:
        stock: 종목코드 또는 종목명.
        date_dir: ``YYYYMMDD``. ``None`` 이면 최근 날짜.
        reports_root: 리포트 루트.

    Returns:
        :class:`InvestorFilterResult`.
    """
    path = find_investor_md(stock, date_dir=date_dir, reports_root=reports_root)
    bars, meta = parse_investor_md(path)
    selected, category, reason, metrics = evaluate_investor(bars)

    parsed = _split_stock_dirname(path.parent.name)
    stk_nm = meta.get("stk_nm") or (parsed[0] if parsed else "")
    stk_cd = meta.get("stk_cd") or (parsed[1] if parsed else stock)

    return InvestorFilterResult(
        stk_cd=stk_cd,
        stk_nm=stk_nm,
        report_path=path,
        bars=bars,
        selected=selected,
        category=category,
        reason=reason,
        latest_bar=bars[-1] if bars else None,
        metrics=metrics,
    )


def filter_all_stocks(
    *,
    date_dir: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> list[InvestorFilterResult]:
    """지정 날짜 폴더 내 모든 종목 일괄 필터.

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

    results: list[InvestorFilterResult] = []
    for stock_dir in _list_stock_dirs(target):
        investor = stock_dir / _INVESTOR_FILENAME
        if not investor.exists():
            logger.debug("investor.md 없음, 건너뜀: {p}", p=stock_dir.name)
            continue
        parsed = _split_stock_dirname(stock_dir.name)
        if parsed is None:
            continue
        stk_nm, stk_cd = parsed
        try:
            bars, meta = parse_investor_md(investor)
        except (ValueError, FileNotFoundError) as exc:
            logger.warning("파싱 실패 {n}({c}): {e}", n=stk_nm, c=stk_cd, e=exc)
            continue
        selected, category, reason, metrics = evaluate_investor(bars)
        results.append(
            InvestorFilterResult(
                stk_cd=stk_cd,
                stk_nm=stk_nm,
                report_path=investor,
                bars=bars,
                selected=selected,
                category=category,
                reason=reason,
                latest_bar=bars[-1] if bars else None,
                metrics=metrics,
            )
        )
    return results


# ─────────────────────────────────────────────────────────────────────────────
# 마크다운 리포트
# ─────────────────────────────────────────────────────────────────────────────


def _fmt_signed_int(v: object) -> str:
    if v is None:
        return "—"
    n = int(v)
    if n > 0:
        return f"+{n:,}"
    return f"{n:,}"


def render_markdown(
    results: list[InvestorFilterResult],
    *,
    fetched_at: str = "",
    date_dir: str = "",
) -> str:
    """필터 결과를 마크다운 리포트로 렌더링."""
    selected = [r for r in results if r.selected]
    excluded = [r for r in results if not r.selected]

    lines: list[str] = [
        "# 종목 필터 리포트 — investor 투자자 수급",
        "",
        "## 판정 조건",
        f"- **(전제)** 봉 수 < {_REQUIRED_BARS} → 제외 (데이터 부족)",
        "- **(부호)** 매도(-) := 값 < 0 / 매수(+) := 값 ≥ 0 (0 은 매수로 처리)",
        f"- **(2)** 외국인 최근일부터 연속 매도 ≥ **{_THRESHOLD_FOREIGN_CONSEC_SELL}회** → 제외",
        f"- **(3)** 기관계 최근일부터 연속 매도 ≥ **{_THRESHOLD_INST_CONSEC_SELL}회** → 제외",
        f"- **(4)** 개인   최근일부터 연속 매수 ≥ **{_THRESHOLD_INDI_CONSEC_BUY}회** → 제외",
        f"- **(5)** 외국인 16일 중 매도일 ≥ **{_THRESHOLD_FOREIGN_TOTAL_SELL}일** → 제외",
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
        "| # | 종목코드 | 종목명 | 최근일 | 외국인 | 기관계 | 개인 | "
        "외국인 연속매도 | 기관 연속매도 | 개인 연속매수 | 외국인 매도일수 | 사유 |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(selected, start=1):
        b = r.latest_bar
        m = r.metrics
        lines.append(
            "| {n} | {cd} | {nm} | {ts} | {f} | {it} | {id} | {fcs} | {ics} | {ibc} | {fts} | {reason} |".format(
                n=i, cd=r.stk_cd, nm=r.stk_nm,
                ts=b.date if b else "—",
                f=_fmt_signed_int(b.foreign if b else None),
                it=_fmt_signed_int(b.inst if b else None),
                id=_fmt_signed_int(b.indi if b else None),
                fcs=m.get("foreign_consec_sell", "—"),
                ics=m.get("inst_consec_sell", "—"),
                ibc=m.get("indi_consec_buy", "—"),
                fts=m.get("foreign_total_sell", "—"),
                reason=r.reason,
            )
        )
    lines.append("")

    lines += [
        f"## 제외 종목 ({len(excluded)}건)",
        "",
        "| # | 종목코드 | 종목명 | 최근일 | 외국인 | 기관계 | 개인 | "
        "외국인 연속매도 | 기관 연속매도 | 개인 연속매수 | 외국인 매도일수 | 사유 |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(excluded, start=1):
        b = r.latest_bar
        m = r.metrics
        lines.append(
            "| {n} | {cd} | {nm} | {ts} | {f} | {it} | {id} | {fcs} | {ics} | {ibc} | {fts} | {reason} |".format(
                n=i, cd=r.stk_cd, nm=r.stk_nm,
                ts=b.date if b else "—",
                f=_fmt_signed_int(b.foreign if b else None),
                it=_fmt_signed_int(b.inst if b else None),
                id=_fmt_signed_int(b.indi if b else None),
                fcs=m.get("foreign_consec_sell", "—"),
                ics=m.get("inst_consec_sell", "—"),
                ibc=m.get("indi_consec_buy", "—"),
                fts=m.get("foreign_total_sell", "—"),
                reason=r.reason,
            )
        )
    lines += [
        "",
        "## 비고",
        "- 입력 데이터: ``reports/<날짜>/<종목명(종목코드)>/investor.md``",
        "- 단위: 백만원 (부호 보존, + 매수우위 / − 매도우위)",
        "- 본 리포트는 분석 보조 자료이며, 매매 신호로 단정해서는 안 됩니다",
        "",
    ]
    return "\n".join(lines)


def save_investor_filter_markdown(
    results: list[InvestorFilterResult],
    *,
    output_root: Path = _DEFAULT_REPORTS_ROOT,
    date_dir: str | None = None,
    now: datetime | None = None,
) -> Path:
    """필터 결과 리포트를 ``<output_root>/<날짜>/investorFilter.md`` 에 저장."""
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


def _print_single(r: InvestorFilterResult) -> None:
    icon = "✅ 선정" if r.selected else "❌ 제외"
    print(f"{icon} [{r.category}] {r.stk_nm}({r.stk_cd})")
    print(f"  - 리포트: {r.report_path}")
    if r.latest_bar:
        b = r.latest_bar
        print(
            f"  - 최근 {b.date} | 외국인 {b.foreign:+,} | "
            f"기관계 {b.inst:+,} | 개인 {b.indi:+,} (단위: 백만원)"
        )
    m = r.metrics
    print(
        f"  - 메트릭: 외국인 연속매도 {m.get('foreign_consec_sell', '?')} / "
        f"기관 연속매도 {m.get('inst_consec_sell', '?')} / "
        f"개인 연속매수 {m.get('indi_consec_buy', '?')} / "
        f"외국인 매도일수 {m.get('foreign_total_sell', '?')} "
        f"(봉 수 {m.get('bar_count', '?')})"
    )
    print(f"  - 사유: {r.reason}")


def main(argv: list[str] | None = None) -> int:
    """CLI 엔트리포인트.

    사용법::

        python -m src.kiwoom.itemFilter.investorFilter <stock> [<YYYYMMDD>]
        python -m src.kiwoom.itemFilter.investorFilter --all [<YYYYMMDD>]
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
            f"=== 일괄 필터 결과: 분석 {len(results)} / 선정 {sel} / "
            f"제외 {len(results) - sel} ==="
        )
        for r in results:
            _print_single(r)
            print()
        path = save_investor_filter_markdown(results, date_dir=date_dir)
        print(f"\n리포트: {path}")
        return 0

    stock = args[0]
    r = filter_stock(stock, date_dir=date_dir)
    _print_single(r)
    return 0 if r.selected else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "InvestorBar",
    "InvestorFilterResult",
    "bars_to_dataframe",
    "evaluate_investor",
    "filter_all_stocks",
    "filter_stock",
    "find_investor_md",
    "main",
    "parse_investor_md",
    "render_markdown",
    "save_investor_filter_markdown",
]
