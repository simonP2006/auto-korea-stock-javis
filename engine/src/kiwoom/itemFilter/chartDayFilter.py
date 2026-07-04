"""chartDay.md 기반 종목 필터.

``reports/<YYYYMMDD>/<종목명(종목코드)>/chartDay.md`` 리포트(:mod:`src.kiwoom.
chartDay` 모듈이 생성)를 입력으로 받아 일봉 MA 4선 정배열 + MA612 밴드 조건
에 부합하는 종목을 선별한다.

색상-MA 매핑::

    10일선  = MA10
    20일선  = MA20
    60일선  = MA60
    306일선 = MA306
    612일선 = MA612

봉 1개의 정배열 정의 (인접 MA 비대칭/대칭 허용)::

    MA10 ≥ MA20  × 0.95               (-5.0% 비대칭)
    MA20 ≥ MA60  × 0.95               (-5.0% 비대칭)
    MA306 × 0.85 ≤ MA60 ≤ MA306 × 1.45 (-15.0% / +45.0% 비대칭)

판정 시점 — 다음 두 조건을 모두 만족해야 선정::

    (정배열) 최근 3봉 (bars[-3], bars[-2], bars[-1]) 중 **2봉 이상**이 위
             정배열 조건 만족 (단일 봉 노이즈 완충).
    (밴드)   최근 1봉 (bars[-1]) 의:
              - 양봉: bars[-1].close > bars[-2].close (어제 종가보다 오늘
                종가가 높음)
              - 종가 vs MA612: -30% ≤ (close - MA612) / MA612 ≤ +100.0%
                즉 MA612 × 0.70 ≤ close ≤ MA612 × 2.00
              - MA612 결측 시: ``close > MA306`` 면 면제 통과
                (MA306 도 결측이면 불통과)

위 조건 모두 만족 → category="정배열" / selected=True
하나라도 실패 / MA 결측 / 분모 0 / 봉 부족 → category="제외"

본 모듈은 키움 API 를 직접 호출하지 않는다. ``chartDay`` 모듈이 미리 저장한
마크다운 리포트만 읽는다.
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
_CHARTDAY_FILENAME: Final[str] = "chartDay.md"
_OUTPUT_FILENAME: Final[str] = "chartDayFilter.md"

# 정배열 허용오차.
# MA10 ≥ MA20 × 0.95, MA20 ≥ MA60 × 0.95 (-5.0% 비대칭).
_MA10_MA20_MA60_TOLERANCE: Final[float] = 0.05
# MA60-MA306 비대칭 밴드: MA306 × 0.85 ≤ MA60 ≤ MA306 × 1.45.
_MA60_MA306_LOWER_TOL: Final[float] = 0.15   # 하한 = MA306 × (1 − 0.15) = 0.85
_MA60_MA306_UPPER_TOL: Final[float] = 0.45   # 상한 = MA306 × (1 + 0.45) = 1.45

# 최근 1봉의 종가-MA612 밴드. -30% ≤ (close - MA612)/MA612 ≤ +100.0%.
# master 종목은 본질적으로 MA612(장기바닥) 대비 큰 +이격을 가짐.
# 이전: -0.15 / +0.50 (Phase B 전문가픽 역설계 2026-07-05 — 하단 확대='아직 안 오른'
# pre-breakout 픽 회수(밴드하단 사망 41건 p50 -24%), 상단 확대=상단초과 23건 p50 +68%.
# 근거: PHASE_B_PROPOSAL_20260704.md §1-B, PHASE_B_B2PREP §b)
_CLOSE_VS_MA612_LOWER: Final[float] = -0.30
_CLOSE_VS_MA612_UPPER: Final[float] = 1.00

# 정배열을 "최근 3봉 중 N봉 이상" 만족해야 통과 (단일 봉 노이즈 완충).
_REQUIRED_CONSECUTIVE_BARS: Final[int] = 3
_REQUIRED_ALIGNED_BARS: Final[int] = 2

_STOCK_DIR_PATTERN: Final[re.Pattern[str]] = re.compile(r"^(.+?)\((\d{4,6})\)$")

# chartDay.md 시계열 표 행 패턴 (16봉, 11컬럼: 날짜+OHLCV+MA10/20/60/306/612).
_TABLE_ROW_PATTERN: Final[re.Pattern[str]] = re.compile(
    r"^\|\s*(\d{4}-\d{2}-\d{2})\s*"
    r"\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*"
    r"\|\s*([\d,]+)\s*"
    r"\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*"
    r"\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*"
    r"\|\s*([\d,.\-—]+)\s*\|\s*$"
)


# ─────────────────────────────────────────────────────────────────────────────
# 모델
# ─────────────────────────────────────────────────────────────────────────────


@dataclass(frozen=True, slots=True)
class ChartDayBar:
    """chartDay.md 시계열 한 행(일봉).

    Attributes:
        date: 봉 날짜 ``YYYY-MM-DD``.
        open: 시가(원).
        high: 고가(원).
        low: 저가(원).
        close: 종가(원).
        volume: 거래량(주).
        ma10: 10일 SMA (없으면 None).
        ma20: 20일 SMA (없으면 None).
        ma60: 60일 SMA (없으면 None).
        ma306: 306일 SMA (없으면 None).
        ma612: 612일 SMA (없으면 None).
    """

    date: str
    open: int
    high: int
    low: int
    close: int
    volume: int
    ma10: float | None
    ma20: float | None
    ma60: float | None
    ma306: float | None
    ma612: float | None


@dataclass(slots=True)
class ChartDayFilterResult:
    """단일 종목 일봉 필터 판정 결과.

    Attributes:
        stk_cd: 종목코드.
        stk_nm: 종목명.
        report_path: 입력 chartDay.md 경로.
        bars: 16봉 데이터 (날짜 오름차순).
        selected: 리서치 대상 선정 여부.
        category: ``"정배열"`` / ``"제외"``.
        reason: 사람이 읽을 수 있는 판정 사유.
        latest_bar: 가장 최근 봉 (``bars[-1]``).
        ma60_ma306_pct: (MA60 - MA306) / MA306 × 100 (최근 봉 기준, 호환용).
        close_ma612_pct: (close - MA612) / MA612 × 100 (최근 봉 기준).
        extra: 부가 메트릭. 키 예시:
            - ``latest_date``: 최근 봉 날짜.
            - ``gap_10_20_pct`` / ``gap_20_60_pct`` / ``gap_60_306_pct``:
              최근 봉의 인접 MA 갭 (%).
            - ``aligned_recent_3``: 최근 3봉 각각 정배열 통과 여부
              (list[bool], 시간 오름차순).
            - ``ma612_band_ok``: 최근 1봉의 양봉 + MA612 밴드 통과 여부.
            - ``bullish``: 최근 1봉의 양봉 여부 (오늘 종가 > 어제 종가).
    """

    stk_cd: str
    stk_nm: str
    report_path: Path
    bars: list[ChartDayBar]
    selected: bool
    category: str
    reason: str
    latest_bar: ChartDayBar | None = None
    ma60_ma306_pct: float | None = None
    close_ma612_pct: float | None = None
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


def parse_chartday_md(path: Path) -> tuple[list[ChartDayBar], dict[str, str]]:
    """chartDay.md 를 파싱하여 16봉 리스트와 헤더 메타를 반환.

    Args:
        path: ``chartDay.md`` 경로.

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
        elif line.startswith("- **최근 봉 일자**:"):
            m = re.search(r"\*\*최근 봉 일자\*\*:\s*(.+)", line)
            if m:
                meta["last_bar_date"] = m.group(1).strip()

    bars: list[ChartDayBar] = []
    for line in text.splitlines():
        m = _TABLE_ROW_PATTERN.match(line)
        if not m:
            continue
        bars.append(
            ChartDayBar(
                date=m.group(1),
                open=_parse_int(m.group(2)),
                high=_parse_int(m.group(3)),
                low=_parse_int(m.group(4)),
                close=_parse_int(m.group(5)),
                volume=_parse_int(m.group(6)),
                ma10=_parse_ma(m.group(7)),
                ma20=_parse_ma(m.group(8)),
                ma60=_parse_ma(m.group(9)),
                ma306=_parse_ma(m.group(10)),
                ma612=_parse_ma(m.group(11)),
            )
        )

    if not bars:
        raise ValueError(f"chartDay.md 시계열 표 파싱 실패 (행 0개): {path}")

    return bars, meta


def bars_to_dataframe(bars: list[ChartDayBar]) -> pd.DataFrame:
    """``ChartDayBar`` 리스트 → DataFrame (DB화 결과)."""
    return pd.DataFrame(
        [
            {
                "date": b.date,
                "open": b.open,
                "high": b.high,
                "low": b.low,
                "close": b.close,
                "volume": b.volume,
                "ma10": b.ma10,
                "ma20": b.ma20,
                "ma60": b.ma60,
                "ma306": b.ma306,
                "ma612": b.ma612,
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


def _is_aligned(bar: ChartDayBar) -> tuple[bool, str | None]:
    """한 봉의 4MA 정배열 여부와 실패 사유.

    정배열 조건::

        MA10 ≥ MA20  × 0.95                  (-5.0% 비대칭)
        MA20 ≥ MA60  × 0.95                  (-5.0% 비대칭)
        MA306 × 0.85 ≤ MA60 ≤ MA306 × 1.45   (-15.0% / +45.0% 비대칭)

    Args:
        bar: 검사 대상 일봉.

    Returns:
        ``(ok, reason)``. 통과 시 ``(True, None)``. 실패 시 ``(False, 사유)``.
        MA 결측·분모 0 도 실패로 처리. MA612 는 본 함수에서 검사하지 않음.
    """
    if bar.ma10 is None or bar.ma20 is None or bar.ma60 is None or bar.ma306 is None:
        return False, (
            f"MA 결측 (ma10={bar.ma10} ma20={bar.ma20} "
            f"ma60={bar.ma60} ma306={bar.ma306})"
        )
    if bar.ma20 == 0 or bar.ma60 == 0 or bar.ma306 == 0:
        return False, "MA20/60/306 = 0 (분모 0)"

    t1 = 1.0 - _MA10_MA20_MA60_TOLERANCE  # = 0.95

    if bar.ma10 < bar.ma20 * t1:
        return False, (
            f"MA10({bar.ma10:,.2f}) < MA20×{t1:.2f}"
            f"({bar.ma20 * t1:,.2f})"
        )
    if bar.ma20 < bar.ma60 * t1:
        return False, (
            f"MA20({bar.ma20:,.2f}) < MA60×{t1:.2f}"
            f"({bar.ma60 * t1:,.2f})"
        )

    lo = bar.ma306 * (1.0 - _MA60_MA306_LOWER_TOL)
    hi = bar.ma306 * (1.0 + _MA60_MA306_UPPER_TOL)
    if not (lo <= bar.ma60 <= hi):
        return False, (
            f"MA60({bar.ma60:,.2f}) ∉ [MA306×{1.0 - _MA60_MA306_LOWER_TOL:.2f}"
            f"({lo:,.2f}), MA306×{1.0 + _MA60_MA306_UPPER_TOL:.2f}({hi:,.2f})]"
        )
    return True, None


def _is_close_in_ma612_band(
    bars: list[ChartDayBar],
) -> tuple[bool, str | None, dict[str, object]]:
    """최근 1봉의 양봉 + 종가-MA612 밴드 통과 여부.

    조건::

        양봉:    bars[-1].close > bars[-2].close
        밴드:    -30% ≤ (close - MA612) / MA612 ≤ +100.0%

    MA612 가 결측/0 인 경우(신규 상장·짧은 이력) 는 ``close > MA306`` 인
    한 면제 처리한다(MA306 도 결측이면 불통과).

    Args:
        bars: 봉 리스트 (시간 오름차순).

    Returns:
        ``(ok, reason, info)``. ``info`` 에는 ``bullish`` (bool),
        ``close_ma612_pct`` (float | None), ``ma612_skipped`` (bool) 등
        메트릭 포함.
    """
    info: dict[str, object] = {"ma612_skipped": False}
    if len(bars) < 2:
        return False, f"봉 부족 ({len(bars)}봉 < 2봉, 양봉 비교 불가)", info

    last = bars[-1]
    prev = bars[-2]

    bullish = last.close > prev.close
    info["bullish"] = bullish

    if not bullish:
        return False, (
            f"양봉 아님 (오늘 종가 {last.close:,} ≤ 어제 종가 {prev.close:,})"
        ), info

    # MA612 결측·0 — close > MA306 면 면제(MA306 도 결측이면 불통과).
    if last.ma612 is None or last.ma612 == 0:
        info["ma612_skipped"] = True
        if last.ma306 is None or last.ma306 == 0:
            return False, (
                f"MA612 결측 + MA306 결측 (ma612={last.ma612} "
                f"ma306={last.ma306})"
            ), info
        if last.close <= last.ma306:
            return False, (
                f"MA612 결측, fallback 실패 — close({last.close:,}) ≤ "
                f"MA306({last.ma306:,.2f})"
            ), info
        return True, None, info

    pct = (last.close - last.ma612) / last.ma612
    info["close_ma612_pct"] = round(pct * 100.0, 4)

    if pct < _CLOSE_VS_MA612_LOWER or pct > _CLOSE_VS_MA612_UPPER:
        return False, (
            f"종가({last.close:,}) vs MA612({last.ma612:,.2f}) "
            f"{pct * 100:+.2f}% — 밴드 [{_CLOSE_VS_MA612_LOWER * 100:+.1f}%, "
            f"{_CLOSE_VS_MA612_UPPER * 100:+.1f}%] 이탈"
        ), info

    return True, None, info


def evaluate_chartday(
    bars: list[ChartDayBar],
) -> tuple[bool, str, str, dict[str, object]]:
    """일봉 필터 판정 — 최근 3봉 중 2봉 정배열 + 최근 1봉 MA612 밴드 + 양봉.

    판정식::

        (정배열) #{b ∈ bars[-3:] :
                     b.MA10 ≥ b.MA20 × 0.95
                 AND b.MA20 ≥ b.MA60 × 0.95
                 AND b.MA306 × 0.85 ≤ b.MA60 ≤ b.MA306 × 1.45} ≥ 2
        (밴드)   bars[-1].close > bars[-2].close                       (양봉)
                 AND ( -30% ≤ (bars[-1].close - MA612) / MA612 ≤ +100%
                       OR (MA612 결측·0 이면 close > MA306 fallback) )
        선정 = (정배열) AND (밴드)

    Args:
        bars: ``parse_chartday_md`` 가 반환한 봉 리스트 (날짜 오름차순).

    Returns:
        ``(selected, category, reason, extra)`` 튜플.
            - ``selected`` (bool): 리서치 대상 여부.
            - ``category`` (str): ``"정배열"`` / ``"제외"``.
            - ``reason`` (str): 판정 사유.
            - ``extra`` (dict): ``latest_date``, ``gap_10_20_pct``,
              ``gap_20_60_pct``, ``gap_60_306_pct``, ``ma60_ma306_pct``
              (호환), ``close_ma612_pct``, ``bullish``,
              ``aligned_recent_3``, ``aligned_count``,
              ``ma612_band_ok``, ``ma612_skipped``.
    """
    if not bars:
        return False, "제외", "봉 데이터 없음", {}

    last = bars[-1]
    extra: dict[str, object] = {"latest_date": last.date}

    # 최근 봉 메트릭 (가능한 경우).
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
    if last.ma612 not in (None, 0):
        extra["close_ma612_pct"] = round(
            (last.close - last.ma612) / last.ma612 * 100.0, 4
        )

    # 봉 수 검사 — 정배열 3봉 + 전일 종가 비교(양봉) 위해 ≥ 3봉 필요.
    if len(bars) < _REQUIRED_CONSECUTIVE_BARS:
        return (
            False,
            "제외",
            f"봉 부족 ({len(bars)}봉 < {_REQUIRED_CONSECUTIVE_BARS}봉)",
            extra,
        )

    # (1) 정배열 — 최근 3봉 중 ≥ _REQUIRED_ALIGNED_BARS 봉 만족.
    recent = bars[-_REQUIRED_CONSECUTIVE_BARS:]
    flags: list[bool] = []
    fail_msgs: list[str] = []
    for b in recent:
        ok, reason = _is_aligned(b)
        flags.append(ok)
        if not ok:
            fail_msgs.append(f"date={b.date} {reason}")
    extra["aligned_recent_3"] = flags
    extra["aligned_count"] = sum(flags)

    if sum(flags) < _REQUIRED_ALIGNED_BARS:
        joined = " | ".join(fail_msgs) if fail_msgs else "(상세 없음)"
        return (
            False,
            "제외",
            f"최근 {_REQUIRED_CONSECUTIVE_BARS}봉 정배열 {sum(flags)}/{_REQUIRED_CONSECUTIVE_BARS} "
            f"< {_REQUIRED_ALIGNED_BARS} — {joined}",
            extra,
        )

    # (2) MA612 밴드 + 양봉 — 최근 1봉.
    band_ok, band_reason, band_info = _is_close_in_ma612_band(bars)
    extra.update(band_info)
    extra["ma612_band_ok"] = band_ok
    if not band_ok:
        return (
            False,
            "제외",
            f"MA612 밴드/양봉 실패 — {band_reason}",
            extra,
        )

    c_pct = extra.get("close_ma612_pct")
    c_pct_str = f"{c_pct:+.2f}%" if isinstance(c_pct, (int, float)) else "—"
    return (
        True,
        "정배열",
        f"최근 {_REQUIRED_CONSECUTIVE_BARS}봉 정배열 + 양봉 + 종가-MA612 "
        f"{c_pct_str} [{_CLOSE_VS_MA612_LOWER * 100:+.1f}%, "
        f"{_CLOSE_VS_MA612_UPPER * 100:+.1f}%] 통과",
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
) -> ChartDayFilterResult:
    """단일 종목 일봉 필터.

    Args:
        stock: 종목코드 또는 종목명.
        date_dir: ``YYYYMMDD``. ``None`` 이면 최근 날짜.
        reports_root: 리포트 루트.

    Returns:
        :class:`ChartDayFilterResult`.
    """
    path = find_chartday_md(stock, date_dir=date_dir, reports_root=reports_root)
    bars, meta = parse_chartday_md(path)
    selected, category, reason, extra = evaluate_chartday(bars)

    parsed = _split_stock_dirname(path.parent.name)
    stk_nm = meta.get("stk_nm") or (parsed[0] if parsed else "")
    stk_cd = meta.get("stk_cd") or (parsed[1] if parsed else stock)

    return ChartDayFilterResult(
        stk_cd=stk_cd,
        stk_nm=stk_nm,
        report_path=path,
        bars=bars,
        selected=selected,
        category=category,
        reason=reason,
        latest_bar=bars[-1] if bars else None,
        ma60_ma306_pct=extra.get("ma60_ma306_pct"),  # type: ignore[arg-type]
        close_ma612_pct=extra.get("close_ma612_pct"),  # type: ignore[arg-type]
        extra=extra,
    )


def filter_all_stocks(
    *,
    date_dir: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> list[ChartDayFilterResult]:
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

    results: list[ChartDayFilterResult] = []
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
        selected, category, reason, extra = evaluate_chartday(bars)
        results.append(
            ChartDayFilterResult(
                stk_cd=stk_cd,
                stk_nm=stk_nm,
                report_path=chartday,
                bars=bars,
                selected=selected,
                category=category,
                reason=reason,
                latest_bar=bars[-1] if bars else None,
                ma60_ma306_pct=extra.get("ma60_ma306_pct"),  # type: ignore[arg-type]
                close_ma612_pct=extra.get("close_ma612_pct"),  # type: ignore[arg-type]
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
    results: list[ChartDayFilterResult],
    *,
    fetched_at: str = "",
    date_dir: str = "",
) -> str:
    """필터 결과를 마크다운 리포트로 렌더링."""
    selected = [r for r in results if r.selected]
    excluded = [r for r in results if not r.selected]

    by_category: dict[str, int] = {}
    for r in results:
        by_category[r.category] = by_category.get(r.category, 0) + 1

    lines: list[str] = [
        "# 종목 필터 리포트 — chartDay 일봉 MA",
        "",
        "## 판정 조건",
        "- **정배열 정의** (인접 MA 허용오차):",
        "    - MA10 ≥ MA20 × 0.95  (-5.0% 비대칭)",
        "    - MA20 ≥ MA60 × 0.95  (-5.0% 비대칭)",
        "    - MA306 × 0.85 ≤ MA60 ≤ MA306 × 1.45  (-15% / +45% 비대칭)",
        "- **(정배열)** 최근 3봉(``bars[-3]``, ``bars[-2]``, ``bars[-1]``) **중 2봉 이상** 위 조건 만족",
        "- **(밴드)** 최근 1봉(``bars[-1]``):",
        "    - 양봉: 오늘 종가 > 어제 종가",
        "    - 종가 vs MA612: **-30% ≤ (종가 - MA612)/MA612 ≤ +100.0%**",
        "    - MA612 결측 시: ``close > MA306`` 면 면제 통과 (MA306 도 결측이면 불통과)",
        "- **선정** = (정배열) AND (밴드)",
        "- **제외 사유**: 봉 부족 / MA 결측 / 분모 0 / 정배열 2봉 미만 / 양봉 아님 / MA612 밴드 이탈",
        "- **MA 매핑**: 10일선=MA10 / 20일선=MA20 / 60일선=MA60 / 306일선=MA306 / 612일선=MA612",
        "",
        "## 요약",
        f"- **입력 날짜 폴더**: {date_dir or '—'}",
        f"- **취득 시각**: {fetched_at or '—'}",
        f"- **분석 종목 수**: {len(results)}",
        f"- **선정 종목 수**: {len(selected)}",
        f"- **제외 종목 수**: {len(excluded)}",
        f"- **분류 분포**: "
        + (", ".join(f"{k} {v}건" for k, v in sorted(by_category.items())) or "—"),
        "",
    ]

    lines += [
        f"## 선정 종목 ({len(selected)}건)",
        "",
        "| # | 종목코드 | 종목명 | 분류 | 최근 봉 | 종가 | MA10 | MA20 | MA60 | MA306 | MA612 | "
        "Δ10/20 | Δ20/60 | Δ60/306 | (종가-MA612)/MA612 | 사유 |",
        "|---:|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(selected, start=1):
        b = r.latest_bar
        lines.append(
            "| {n} | {cd} | {nm} | {cat} | {ts} | {c} | {m10} | {m20} | {m60} | {m306} | {m612} "
            "| {g1} | {g2} | {g3} | {p612} | {reason} |".format(
                n=i, cd=r.stk_cd, nm=r.stk_nm, cat=r.category,
                ts=b.date if b else "—",
                c=_fmt_int(b.close if b else None),
                m10=_fmt_float(b.ma10 if b else None),
                m20=_fmt_float(b.ma20 if b else None),
                m60=_fmt_float(b.ma60 if b else None),
                m306=_fmt_float(b.ma306 if b else None),
                m612=_fmt_float(b.ma612 if b else None),
                g1=_fmt_pct(r.extra.get("gap_10_20_pct")),
                g2=_fmt_pct(r.extra.get("gap_20_60_pct")),
                g3=_fmt_pct(r.extra.get("gap_60_306_pct")),
                p612=_fmt_pct(r.close_ma612_pct),
                reason=r.reason,
            )
        )
    lines.append("")

    lines += [
        f"## 제외 종목 ({len(excluded)}건)",
        "",
        "| # | 종목코드 | 종목명 | 최근 봉 | 종가 | MA10 | MA20 | MA60 | MA306 | MA612 | 사유 |",
        "|---:|---|---|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(excluded, start=1):
        b = r.latest_bar
        lines.append(
            "| {n} | {cd} | {nm} | {ts} | {c} | {m10} | {m20} | {m60} | {m306} | {m612} | {reason} |".format(
                n=i, cd=r.stk_cd, nm=r.stk_nm,
                ts=b.date if b else "—",
                c=_fmt_int(b.close if b else None),
                m10=_fmt_float(b.ma10 if b else None),
                m20=_fmt_float(b.ma20 if b else None),
                m60=_fmt_float(b.ma60 if b else None),
                m306=_fmt_float(b.ma306 if b else None),
                m612=_fmt_float(b.ma612 if b else None),
                reason=r.reason,
            )
        )
    lines += [
        "",
        "## 비고",
        "- 입력 데이터: ``reports/<날짜>/<종목명(종목코드)>/chartDay.md``",
        "- MA 값은 chartDay 모듈이 산출한 일봉 종가 기준 단순이동평균(SMA)",
        "- 본 리포트는 분석 보조 자료이며, 매매 신호로 단정해서는 안 됩니다",
        "",
    ]
    return "\n".join(lines)


def save_chartday_filter_markdown(
    results: list[ChartDayFilterResult],
    *,
    output_root: Path = _DEFAULT_REPORTS_ROOT,
    date_dir: str | None = None,
    now: datetime | None = None,
) -> Path:
    """필터 결과 리포트를 ``<output_root>/<날짜>/chartDayFilter.md`` 에 저장."""
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


def _print_single(r: ChartDayFilterResult) -> None:
    icon = "✅ 선정" if r.selected else "❌ 제외"
    print(f"{icon} [{r.category}] {r.stk_nm}({r.stk_cd})")
    print(f"  - 리포트: {r.report_path}")
    if r.latest_bar:
        b = r.latest_bar
        print(
            f"  - 최근 봉 {b.date} | 종가 {b.close:,} | "
            f"MA10 {b.ma10} MA20 {b.ma20} MA60 {b.ma60} "
            f"MA306 {b.ma306} MA612 {b.ma612}"
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
    if r.close_ma612_pct is not None:
        print(f"  - (종가-MA612)/MA612 = {r.close_ma612_pct:+.2f}%")
    bullish = r.extra.get("bullish")
    if bullish is not None:
        print(f"  - 양봉(오늘종가>어제종가): {'○' if bullish else '×'}")
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

        python -m src.kiwoom.itemFilter.chartDayFilter <stock> [<YYYYMMDD>]
        python -m src.kiwoom.itemFilter.chartDayFilter --all [<YYYYMMDD>]
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
        path = save_chartday_filter_markdown(results, date_dir=date_dir)
        print(f"\n리포트: {path}")
        return 0

    stock = args[0]
    r = filter_stock(stock, date_dir=date_dir)
    _print_single(r)
    return 0 if r.selected else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "ChartDayBar",
    "ChartDayFilterResult",
    "bars_to_dataframe",
    "evaluate_chartday",
    "filter_all_stocks",
    "filter_stock",
    "find_chartday_md",
    "main",
    "parse_chartday_md",
    "render_markdown",
    "save_chartday_filter_markdown",
]
