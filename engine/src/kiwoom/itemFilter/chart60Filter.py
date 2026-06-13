"""chart60.md 기반 종목 필터.

``reports/<YYYYMMDD>/<종목명(종목코드)>/chart60.md`` 리포트(:mod:`src.kiwoom.
chart60.saveReport.markdown` 가 생성)를 입력으로 받아 60분봉 MA 4선 정배열
조건에 부합하는 종목을 선별한다.

판정 색상-MA 매핑::

    파란색(10일선)  = MA10
    빨간색(20일선)  = MA20
    녹색(60일선)    = MA60
    검은색(306일선) = MA306

봉 1개의 정배열 정의 (인접 MA 비대칭 -0.5% 허용)::

    MA10  ≥ MA20  × 0.995
    MA20  ≥ MA60  × 0.995
    MA60  ≥ MA306 × 0.995

판정 시점 — 최근 3봉(``bars[-3]``, ``bars[-2]``, ``bars[-1]``) 모두에서 위
정배열 조건이 성립하면 선정. 봉 수 < 3, MA 결측, MA306=0, 또는 최근 3봉 중
하나라도 정배열 실패 시 제외.

수식::

    선정 = (len(bars) >= 3) and all(
        b.ma10  >= b.ma20  * 0.995 and
        b.ma20  >= b.ma60  * 0.995 and
        b.ma60  >= b.ma306 * 0.995
        for b in bars[-3:]
    )

본 모듈은 키움 API 를 직접 호출하지 않는다. ``chart60`` 모듈이 미리 저장한
마크다운 리포트만 읽는다.

사용 예::

    from src.kiwoom.itemFilter.chart60Filter import (
        filter_stock,
        filter_all_stocks,
        save_chart60_filter_markdown,
    )

    # 단일 종목
    r = filter_stock("005930")
    print(r.selected, r.category, r.reason)

    # 일괄 (오늘자 reports/ 전체)
    results = filter_all_stocks()
    save_chart60_filter_markdown(results)
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Final

import pandas as pd
from loguru import logger

# ─────────────────────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_REPORTS_ROOT: Final[Path] = Path("reports")
_CHART60_FILENAME: Final[str] = "chart60.md"
_OUTPUT_FILENAME: Final[str] = "chart60Filter.md"

# 인접 MA 정배열 허용오차 (비대칭, 상단 -0.5% 까지 허용).
# 상위 MA 가 직하위 MA 의 0.5% 까지는 아래로 빠져도 정배열로 인정.
# 적용 식: upper_MA >= lower_MA * (1 - _MA_ALIGNMENT_TOLERANCE)
_MA_ALIGNMENT_TOLERANCE: Final[float] = 0.005

# 정배열을 만족해야 하는 최근 봉 개수 (시간 오름차순 마지막 N봉).
_REQUIRED_CONSECUTIVE_BARS: Final[int] = 3

# reports leaf 디렉토리명 패턴: "삼성전자(005930)" → ("삼성전자", "005930")
_STOCK_DIR_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(.+?)\((\d{4,6})\)$")

# chart60.md 시계열 표 행 패턴 (16봉).
#  | 2026-05-08 19:00 | 276,500 | 277,000 | 275,500 | 276,500 | 1,777,564 |
#    270,300.00 | 269,700.00 | 251,629.17 | 217,661.44 |
_TABLE_ROW_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\|\s*(\d{4}-\d{2}-\d{2}\s\d{2}:\d{2})\s*"
    r"\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*"
    r"\|\s*([\d,]+)\s*"
    r"\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*"
    r"\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*$"
)


# ─────────────────────────────────────────────────────────────────────────────
# 모델
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class Chart60Bar:
    """chart60.md 시계열 한 행(60분봉).

    Attributes:
        ts: 봉 시각 ``YYYY-MM-DD HH:MM``.
        open: 시가(원).
        high: 고가(원).
        low: 저가(원).
        close: 종가(원).
        volume: 거래량(주).
        ma10: 10기간 SMA (없으면 None).
        ma20: 20기간 SMA (없으면 None).
        ma60: 60기간 SMA (없으면 None).
        ma306: 306기간 SMA (없으면 None).
    """

    ts: str
    open: int
    high: int
    low: int
    close: int
    volume: int
    ma10: float | None
    ma20: float | None
    ma60: float | None
    ma306: float | None


@dataclass(slots=True)
class Chart60FilterResult:
    """단일 종목 필터 판정 결과.

    Attributes:
        stk_cd: 종목코드.
        stk_nm: 종목명.
        report_path: 입력 chart60.md 경로.
        bars: 16봉 데이터 (시간 오름차순).
        selected: 리서치 대상 선정 여부.
        category: 분류 라벨 — ``"정배열"`` / ``"제외"``.
        reason: 사람이 읽을 수 있는 판정 사유.
        latest_bar: 가장 최근 봉 (``bars[-1]``).
        ma60_ma306_pct: (MA60 - MA306) / MA306 × 100 (최근 봉 기준).
            새 판정식에는 직접 쓰이지 않으나 호환·관찰용으로 유지.
        extra: 부가 메트릭. 키 예시:
            - ``latest_ts``: 최근 봉 시각.
            - ``gap_10_20_pct``  / ``gap_20_60_pct`` / ``gap_60_306_pct``:
              최근 봉의 인접 MA 갭 (%) — (상위MA - 하위MA) / 하위MA × 100.
            - ``aligned_recent_3``: 최근 3봉 각각의 정배열 통과 여부
              (list[bool], 시간 오름차순 [-3], [-2], [-1]).
    """

    stk_cd: str
    stk_nm: str
    report_path: Path
    bars: list[Chart60Bar]
    selected: bool
    category: str
    reason: str
    latest_bar: Chart60Bar | None = None
    ma60_ma306_pct: float | None = None
    extra: dict[str, object] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# 파싱
# ─────────────────────────────────────────────────────────────────────────────


def _parse_int(s: str) -> int:
    return int(s.replace(",", ""))


def _parse_ma(s: str) -> float | None:
    s = s.strip()
    if s in ("", "—", "-"):
        return None
    return float(s.replace(",", ""))


def parse_chart60_md(path: Path) -> tuple[list[Chart60Bar], dict[str, str]]:
    """chart60.md 를 파싱하여 16봉 리스트와 헤더 메타를 반환.

    Args:
        path: ``chart60.md`` 절대/상대 경로.

    Returns:
        ``(bars, meta)`` 튜플:
            - ``bars``: ``Chart60Bar`` 리스트 (시간 오름차순).
            - ``meta``: 헤더에서 추출한 부가 정보
              (``stk_cd``, ``stk_nm``, ``fetched_at``, ``last_bar_ts``,
              ``last_close``).

    Raises:
        FileNotFoundError: 파일이 없을 때.
        ValueError: 시계열 표 행이 0개일 때 (포맷 오류).
    """
    text = Path(path).read_text(encoding="utf-8")

    meta: dict[str, str] = {}
    # 헤더 라인 추출 (단순 라벨 매칭).
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

    bars: list[Chart60Bar] = []
    for line in text.splitlines():
        m = _TABLE_ROW_PATTERN.match(line)
        if not m:
            continue
        bars.append(
            Chart60Bar(
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
        raise ValueError(f"chart60.md 시계열 표 파싱 실패 (행 0개): {path}")

    return bars, meta


def bars_to_dataframe(bars: list[Chart60Bar]) -> pd.DataFrame:
    """``Chart60Bar`` 리스트를 DataFrame 으로 변환 (DB화 결과)."""
    return pd.DataFrame(
        [
            {
                "ts": b.ts,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "ma10": b.ma10,
                "ma20": b.ma20,
                "ma60": b.ma60,
                "ma306": b.ma306,
            }
            for b in bars
        ]
    )


# ─────────────────────────────────────────────────────────────────────────────
# 종목 → 리포트 경로 탐색
# ─────────────────────────────────────────────────────────────────────────────


def _list_date_dirs(reports_root: Path) -> list[Path]:
    """``reports/`` 하위 ``YYYYMMDD`` 디렉토리 목록 (이름 내림차순)."""
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
    """날짜 디렉토리 하위 ``종목명(종목코드)`` 폴더 목록."""
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


def find_chart60_md(
    stock: str,
    *,
    date_dir: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> Path:
    """종목코드 또는 종목명으로 chart60.md 경로를 탐색.

    Args:
        stock: 종목코드(예 ``"005930"``) 또는 종목명(예 ``"삼성전자"``).
        date_dir: ``YYYYMMDD`` 폴더명. ``None`` 이면 가장 최근 날짜 폴더.
        reports_root: 리포트 루트(기본 ``reports``).

    Returns:
        chart60.md 의 ``Path``.

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

    chart60 = matches[0] / _CHART60_FILENAME
    if not chart60.exists():
        raise FileNotFoundError(f"chart60.md 없음: {chart60}")
    return chart60


# ─────────────────────────────────────────────────────────────────────────────
# 판정 로직
# ─────────────────────────────────────────────────────────────────────────────


def _is_aligned(bar: Chart60Bar) -> tuple[bool, str | None]:
    """한 봉의 4MA 정배열 여부와 실패 사유.

    정배열 조건 (인접 MA 비대칭 -0.5% 허용)::

        MA10  ≥ MA20  × 0.995
        MA20  ≥ MA60  × 0.995
        MA60  ≥ MA306 × 0.995

    Args:
        bar: 검사 대상 60분봉.

    Returns:
        ``(ok, reason)``. 통과 시 ``(True, None)``. 실패 시 ``(False, 사유)``.
        MA 결측·MA306=0 도 실패로 처리.
    """
    if bar.ma10 is None or bar.ma20 is None or bar.ma60 is None or bar.ma306 is None:
        return False, (
            f"MA 결측 (ma10={bar.ma10} ma20={bar.ma20} "
            f"ma60={bar.ma60} ma306={bar.ma306})"
        )
    if bar.ma306 == 0:
        return False, "MA306=0 (분모 0)"

    t = 1.0 - _MA_ALIGNMENT_TOLERANCE  # = 0.995

    if bar.ma10 < bar.ma20 * t:
        return False, (
            f"MA10({bar.ma10:,.2f}) < MA20×{t:.3f}"
            f"({bar.ma20 * t:,.2f})"
        )
    if bar.ma20 < bar.ma60 * t:
        return False, (
            f"MA20({bar.ma20:,.2f}) < MA60×{t:.3f}"
            f"({bar.ma60 * t:,.2f})"
        )
    if bar.ma60 < bar.ma306 * t:
        return False, (
            f"MA60({bar.ma60:,.2f}) < MA306×{t:.3f}"
            f"({bar.ma306 * t:,.2f})"
        )
    return True, None


def evaluate_chart60(bars: list[Chart60Bar]) -> tuple[bool, str, str, dict[str, object]]:
    """**최근 3봉** 기준으로 4MA 정배열 필터 판정.

    판정식::

        선정 = (len(bars) >= 3) AND ∀ b ∈ bars[-3:]:
                   b.MA10  ≥ b.MA20  × 0.995
               AND b.MA20  ≥ b.MA60  × 0.995
               AND b.MA60  ≥ b.MA306 × 0.995

    Args:
        bars: ``parse_chart60_md`` 가 반환한 봉 리스트 (시간 오름차순).

    Returns:
        ``(selected, category, reason, extra)`` 튜플.
            - ``selected`` (bool): 리서치 대상 여부.
            - ``category`` (str): ``"정배열"`` / ``"제외"``.
            - ``reason`` (str): 판정 사유 (사람이 읽을 수 있는 한 줄).
            - ``extra`` (dict): 부가 메트릭 — ``latest_ts``, 인접 MA 갭(%)
              3종 (``gap_10_20_pct``, ``gap_20_60_pct``, ``gap_60_306_pct``),
              ``aligned_recent_3`` (list[bool] 시간 오름차순),
              ``ma60_ma306_pct`` (호환용).
    """
    if not bars:
        return False, "제외", "봉 데이터 없음", {}

    last = bars[-1]
    extra: dict[str, object] = {"latest_ts": last.ts}

    # 최근 봉의 인접 MA 갭(%) 기록 — 결측이면 건너뜀.
    if last.ma10 is not None and last.ma20 not in (None, 0):
        extra["gap_10_20_pct"] = round(
            (last.ma10 - last.ma20) / last.ma20 * 100.0, 4
        )
    if last.ma20 is not None and last.ma60 not in (None, 0):
        extra["gap_20_60_pct"] = round(
            (last.ma20 - last.ma60) / last.ma60 * 100.0, 4
        )
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
        ok, reason = _is_aligned(b)
        flags.append(ok)
        if not ok and fail_msg is None:
            fail_msg = f"ts={b.ts} {reason}"
    extra["aligned_recent_3"] = flags

    if all(flags):
        return (
            True,
            "정배열",
            f"최근 {_REQUIRED_CONSECUTIVE_BARS}봉 모두 정배열 "
            f"(MA10≥MA20×{1.0 - _MA_ALIGNMENT_TOLERANCE:.3f}≥..≥MA306×{1.0 - _MA_ALIGNMENT_TOLERANCE:.3f})",
            extra,
        )

    return (
        False,
        "제외",
        f"최근 {_REQUIRED_CONSECUTIVE_BARS}봉 정배열 실패 — {fail_msg}",
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
) -> Chart60FilterResult:
    """단일 종목 필터.

    Args:
        stock: 종목코드 또는 종목명.
        date_dir: ``YYYYMMDD``. ``None`` 이면 최근 날짜 자동 선택.
        reports_root: 리포트 루트.

    Returns:
        :class:`Chart60FilterResult`.
    """
    path = find_chart60_md(stock, date_dir=date_dir, reports_root=reports_root)
    bars, meta = parse_chart60_md(path)
    selected, category, reason, extra = evaluate_chart60(bars)

    parsed = _split_stock_dirname(path.parent.name)
    stk_nm = meta.get("stk_nm") or (parsed[0] if parsed else "")
    stk_cd = meta.get("stk_cd") or (parsed[1] if parsed else stock)

    return Chart60FilterResult(
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
) -> list[Chart60FilterResult]:
    """지정 날짜 폴더 내 모든 종목 일괄 필터.

    Args:
        date_dir: ``YYYYMMDD``. ``None`` 이면 최근 날짜 폴더.
        reports_root: 리포트 루트.

    Returns:
        모든 종목의 :class:`Chart60FilterResult` 리스트
        (선정/제외 모두 포함, 입력 폴더 정렬 순).
    """
    if date_dir:
        target = reports_root / date_dir
    else:
        target = _latest_date_dir(reports_root)
        if target is None:
            raise FileNotFoundError(f"reports 하위에 날짜 폴더가 없음: {reports_root}")

    results: list[Chart60FilterResult] = []
    for stock_dir in _list_stock_dirs(target):
        chart60 = stock_dir / _CHART60_FILENAME
        if not chart60.exists():
            logger.debug("chart60.md 없음, 건너뜀: {p}", p=stock_dir.name)
            continue
        parsed = _split_stock_dirname(stock_dir.name)
        if parsed is None:
            continue
        stk_nm, stk_cd = parsed
        try:
            bars, meta = parse_chart60_md(chart60)
        except (ValueError, FileNotFoundError) as exc:
            logger.warning("파싱 실패 {n}({c}): {e}", n=stk_nm, c=stk_cd, e=exc)
            continue
        selected, category, reason, extra = evaluate_chart60(bars)
        results.append(
            Chart60FilterResult(
                stk_cd=stk_cd,
                stk_nm=stk_nm,
                report_path=chart60,
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
    results: list[Chart60FilterResult],
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
        "# 종목 필터 리포트 — chart60 60분봉 MA",
        "",
        "## 판정 조건",
        "- **정배열 정의** (인접 MA 비대칭 -0.5% 허용):",
        "    - MA10  ≥ MA20  × 0.995",
        "    - MA20  ≥ MA60  × 0.995",
        "    - MA60  ≥ MA306 × 0.995",
        "- **필요조건**: 최근 3봉(``bars[-3]``, ``bars[-2]``, ``bars[-1]``) "
        "모두 위 정배열 조건 만족",
        "- **제외 사유**: 봉 수 < 3 / MA 결측 / MA306=0 / "
        "최근 3봉 중 하나라도 정배열 실패",
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
        "| # | 종목코드 | 종목명 | 분류 | 최근 봉 | 종가 | MA10 | MA20 | MA60 | MA306 | Δ10/20 | Δ20/60 | Δ60/306 | 사유 |",
        "|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(selected, start=1):
        b = r.latest_bar
        lines.append(
            "| {n} | {cd} | {nm} | {cat} | {ts} | {c} | {m10} | {m20} | {m60} | {m306} | {g1} | {g2} | {g3} | {reason} |".format(
                n=i, cd=r.stk_cd, nm=r.stk_nm, cat=r.category,
                ts=b.ts if b else "—",
                c=_fmt_int(b.close if b else None),
                m10=_fmt_float(b.ma10 if b else None),
                m20=_fmt_float(b.ma20 if b else None),
                m60=_fmt_float(b.ma60 if b else None),
                m306=_fmt_float(b.ma306 if b else None),
                g1=_fmt_pct(r.extra.get("gap_10_20_pct")),
                g2=_fmt_pct(r.extra.get("gap_20_60_pct")),
                g3=_fmt_pct(r.extra.get("gap_60_306_pct")),
                reason=r.reason,
            )
        )
    lines.append("")

    lines += [
        f"## 제외 종목 ({len(excluded)}건)",
        "",
        "| # | 종목코드 | 종목명 | 최근 봉 | MA10 | MA20 | MA60 | MA306 | 사유 |",
        "|---:|---|---|---|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(excluded, start=1):
        b = r.latest_bar
        lines.append(
            "| {n} | {cd} | {nm} | {ts} | {m10} | {m20} | {m60} | {m306} | {reason} |".format(
                n=i, cd=r.stk_cd, nm=r.stk_nm,
                ts=b.ts if b else "—",
                m10=_fmt_float(b.ma10 if b else None),
                m20=_fmt_float(b.ma20 if b else None),
                m60=_fmt_float(b.ma60 if b else None),
                m306=_fmt_float(b.ma306 if b else None),
                reason=r.reason,
            )
        )
    lines += [
        "",
        "## 비고",
        "- 입력 데이터: ``reports/<날짜>/<종목명(종목코드)>/chart60.md``",
        "- MA 값은 chart60 모듈이 산출한 60분봉 종가 기준 단순이동평균(SMA)",
        "- 본 리포트는 분석 보조 자료이며, 매매 신호로 단정해서는 안 됩니다",
        "",
    ]
    return "\n".join(lines)


def save_chart60_filter_markdown(
    results: list[Chart60FilterResult],
    *,
    output_root: Path = _DEFAULT_REPORTS_ROOT,
    date_dir: str | None = None,
    now: datetime | None = None,
) -> Path:
    """필터 결과 리포트를 ``<output_root>/<날짜>/chart60Filter.md`` 에 저장.

    Args:
        results: 필터 결과 리스트.
        output_root: 저장 루트 (기본 ``reports``).
        date_dir: 저장 폴더명 ``YYYYMMDD``. ``None`` 이면 ``now`` 기준 오늘.
        now: 실행 시각. ``None`` 이면 ``datetime.now()``.

    Returns:
        저장된 파일 경로.
    """
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


def _print_single(r: Chart60FilterResult) -> None:
    icon = "✅ 선정" if r.selected else "❌ 제외"
    print(f"{icon} [{r.category}] {r.stk_nm}({r.stk_cd})")
    print(f"  - 리포트: {r.report_path}")
    if r.latest_bar:
        b = r.latest_bar
        print(
            f"  - 최근 봉 {b.ts} | 종가 {b.close:,} | "
            f"MA10 {b.ma10} MA20 {b.ma20} MA60 {b.ma60} MA306 {b.ma306}"
        )
    g1 = r.extra.get("gap_10_20_pct")
    g2 = r.extra.get("gap_20_60_pct")
    g3 = r.extra.get("gap_60_306_pct")
    if g1 is not None or g2 is not None or g3 is not None:
        def _fmt(v: object) -> str:
            return f"{float(v):+.2f}%" if v is not None else "—"  # type: ignore[arg-type]
        print(
            f"  - 인접 MA 갭: Δ10/20={_fmt(g1)} Δ20/60={_fmt(g2)} Δ60/306={_fmt(g3)}"
        )
    flags = r.extra.get("aligned_recent_3")
    if isinstance(flags, list) and flags:
        print(
            f"  - 최근 {len(flags)}봉 정배열: "
            + " ".join("○" if x else "×" for x in flags)
        )
    print(f"  - 사유: {r.reason}")


def main(argv: list[str] | None = None) -> int:
    """CLI 엔트리포인트.

    사용법::

        python -m src.kiwoom.itemFilter.chart60Filter <stock> [<YYYYMMDD>]
        python -m src.kiwoom.itemFilter.chart60Filter --all [<YYYYMMDD>]

    인자가 없으면 ``--all`` 과 동일하게 동작.
    """
    import sys

    args = list(argv if argv is not None else sys.argv[1:])
    bulk = False
    if not args or args[0] == "--all":
        bulk = True
        if args and args[0] == "--all":
            args = args[1:]

    date_dir = args[1] if (not bulk and len(args) >= 2) else (args[0] if (bulk and args) else None)

    if bulk:
        results = filter_all_stocks(date_dir=date_dir)
        sel = sum(1 for r in results if r.selected)
        print(f"=== 일괄 필터 결과: 분석 {len(results)} / 선정 {sel} / 제외 {len(results) - sel} ===")
        for r in results:
            _print_single(r)
            print()
        path = save_chart60_filter_markdown(results, date_dir=date_dir)
        print(f"\n리포트: {path}")
        return 0

    stock = args[0]
    r = filter_stock(stock, date_dir=date_dir)
    _print_single(r)
    return 0 if r.selected else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "Chart60Bar",
    "Chart60FilterResult",
    "bars_to_dataframe",
    "evaluate_chart60",
    "filter_all_stocks",
    "filter_stock",
    "find_chart60_md",
    "main",
    "parse_chart60_md",
    "render_markdown",
    "save_chart60_filter_markdown",
]
