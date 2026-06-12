"""chart60 + chart120 결합 종목 필터.

``reports/<YYYYMMDD>/<종목명(종목코드)>/chart60.md`` 와 ``chart120.md`` 두
리포트를 함께 읽어 5가지 패턴(A/B/C/D/E) 중 하나라도 만족하는 종목을 선정한다.

판정 색상-MA 매핑::

    🔵 파란색(10일선)  = MA10
    🔴 빨간색(20일선)  = MA20
    🟢 녹색(60일선)    = MA60
    ⚫ 검은색(306일선) = MA306

판정 윈도우 (노란 블록 = 16봉)::

    정적 구조 조건(정배열·이격·수렴)  → bars[-8:]  (최근 8봉 모두)
    동적 이벤트 조건(돌파·교차)        → bars[-1]   (최근 1봉, 또는 [-2:-1] 비교)
    Type D 보조(close > MA60 비율)     → bars60[-16:] 중 60% 이상
    Type E 60분 지지 비율              → bars60[-8:]  중 75% 이상

판정 우선순위: **A → B → C → D → E** (첫 매칭으로 분류).

5가지 Type 정의 — `docs/charts_rules.jpg` 의 부연설명 반영::

    Type A — 양 시간대 4선 완전 정배열 (-3.5% 허용)
        120분 bars[-8:]: MA10 ≥ MA20×0.965 ≥ MA60×0.965 ≥ MA306×0.965
        60분  bars[-8:]: 동일 4선 정배열

    Type B — 60분 선행 정배열 / 120분 상승 초입
        120분 bars[-8:]:
            MA10 ≥ MA20 × 0.985
            MA10 ≤ MA60 × 0.97   (MA10 이 MA60 대비 3% 이상 아래)
            MA20 ≤ MA60 × 0.97
            MA60 ≥ MA306 × 0.985
        60분  bars[-8:]:
            MA10 ≥ MA20 × 0.985
            MA20 ≥ MA60 × 0.985
            MA60 ≥ MA306 × 0.985

    Type C — 120분 수렴 + 60분 60일선 골든크로스
        120분 bars[-8:]:
            (max(MA10,MA20,MA60) − min(MA10,MA20,MA60)) / min ≤ 0.02
            MA60 ≥ MA306 × 0.985
        60분  교차:
            bars60[-2].close ≤ bars60[-2].ma60
            bars60[-1].close >  bars60[-1].ma60

    Type D — 120분 엉킴 (Type A 미충족) + 60분 정배열/돌파 우세
        Type A 미매칭 (우선순위로 자동 보장)
        120분 bars[-8:]:
            MA10 ≥ MA60 × 0.98   (-2.0% 허용)
            MA20 ≥ MA60 × 0.98   (MA10/MA20 사이 순서 무관 = 엉킴 허용)
            MA60 ≥ MA306 × 0.985
        60분 — 다음 둘 중 하나:
            (a) bars60[-8:] 4선 정배열(-1.5%)
            (b) count(close > ma60 for b in bars60[-16:]) / 16 ≥ 0.60

    Type E — 정배열 직전 + MA60 위 지지 (fresh breakout)
        120분 bars[-1]:
            MA60 ≥ MA306 × 0.985
            close > MA60                       (현재 봉이 60선 위)
            (max(MA10,MA20,MA60) − min) / min ≤ 0.07   (수렴 중)
        120분 bars[-2:] 중 ≥1봉:
            MA10 ≥ MA20 × 0.984                (단기 정렬 직전 — 1.6% tol)
        60분 bars[-8:]:
            count(close > ma60) / 8 ≥ 0.75     (지속적 60선 위 지지)

본 모듈은 키움 API 를 직접 호출하지 않는다. chart60·chart120 모듈이 미리 저장한
마크다운 리포트만 읽는다. ``chart120.md`` 가 없는 종목은 ``카테고리="스킵"``
으로 결과 리스트에 포함된다.

사용 예::

    from src.kiwoom.itemFilter.chart60_120Filter import (
        filter_stock,
        filter_all_stocks,
        save_chart60_120_filter_markdown,
    )

    r = filter_stock("005930")
    print(r.selected, r.category, r.reason)

    results = filter_all_stocks()
    save_chart60_120_filter_markdown(results)
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
    parse_chart60_md,
)

# ─────────────────────────────────────────────────────────────────────────────
# 상수
# ─────────────────────────────────────────────────────────────────────────────

_DEFAULT_REPORTS_ROOT: Final[Path] = Path("reports")
_CHART60_FILENAME: Final[str] = "chart60.md"
_CHART120_FILENAME: Final[str] = "chart120.md"
_OUTPUT_FILENAME: Final[str] = "chart60_120Filter.md"

# 정적 구조 조건의 평가 윈도우: 16봉 중 최근 8봉(bars[-8:]) 모두 만족해야 함.
_REQUIRED_STATIC_BARS: Final[int] = 8

# 정배열 / 장기추세 허용오차(비대칭 -1.5%) — Type B·C·D·E 공통.
# 적용 식: upper >= lower * (1 - _ALIGN_TOL_LOOSE)
_ALIGN_TOL_LOOSE: Final[float] = 0.015  # 0.985

# Type A 전용 4선 정배열 허용오차(-3.5%). _ALIGN_TOL_LOOSE 보다 완화된 값.
# 양 시간대 정배열 종목 중 단기 노이즈로 살짝 어긋난 master 회수가 목적.
# 적용 식: upper >= lower * (1 - _TYPE_A_ALIGN_TOL)
_TYPE_A_ALIGN_TOL: Final[float] = 0.035  # 0.965

# Type B 전용 — 120분에서 MA10/MA20 이 MA60 대비 3% 이상 아래.
_TYPE_B_BELOW_MA60_RATIO: Final[float] = 0.97

# Type C 전용 — 120분 MA10·MA20·MA60 셋의 수렴 폭 (max-min)/min ≤ 3.5%.
_TYPE_C_CONVERGE_PCT: Final[float] = 0.035

# Type D 120분 엉킴 조건 허용오차(2.0%) — MA10/MA20 ≥ MA60×(1-tol).
_TYPE_D_ALIGN_TOL_120: Final[float] = 0.020

# Type D 60분 보조 조건 — bars60[-16:] 중 close > ma60 비율 임계값 (50%).
_TYPE_D_CLOSE_OVER_MA60_RATIO: Final[float] = 0.50
_TYPE_D_DYNAMIC_WINDOW: Final[int] = 16

# Type E 전용 — "정배열 직전 + MA60 위 지지(fresh breakout)" 신규 타입.
# 120분 최근 1봉의 MA10·MA20·MA60 수렴 폭 (max-min)/min ≤ 10%.
# V자 반등 직후 수렴이 아직 좁혀지지 않은 종목까지 회수가 목적 (7% → 10%).
_TYPE_E_SPREAD_PCT: Final[float] = 0.10
# 60분 close > MA60 비율 평가 윈도우(8봉) 및 임계(75%).
_TYPE_E_DYNAMIC_WINDOW: Final[int] = 8
_TYPE_E_CLOSE_OVER_MA60_RATIO: Final[float] = 0.75
# Type E "단기 정렬" 검사 윈도우 — 120분 최근 N봉 중 ≥1봉이 단기 정렬 조건을
# 만족하면 통과. 마지막 봉의 인트라데이 노이즈로 단기 정렬이 살짝 어긋난 경우를 구제.
_TYPE_E_SHORT_ALIGN_WINDOW: Final[int] = 2
# Type E 단기 정렬 허용오차 — MA10 ≥ MA20 × (1 − _TYPE_E_SHORT_ALIGN_TOL).
# V자 반등 직후 "정배열 직전" 종목 회수가 목적 (hard 0% → 1.6% tol).
_TYPE_E_SHORT_ALIGN_TOL: Final[float] = 0.016
# Type E 전용 장기추세 허용오차 — MA60 ≥ MA306 × (1 − _TYPE_E_MA60_OVER_MA306_TOL).
# _ALIGN_TOL_LOOSE(1.5%) 공유 시 Type B/C/D 영향이 커서 Type E 만 별도 임계로 분리.
# V자 반등 직후 MA60 이 아직 MA306 을 살짝 못 넘은 종목(파인엠텍 등) 회수가 목적.
_TYPE_E_MA60_OVER_MA306_TOL: Final[float] = 0.035

# 분류 라벨.
_LABEL_A: Final[str] = "A"
_LABEL_B: Final[str] = "B"
_LABEL_C: Final[str] = "C"
_LABEL_D: Final[str] = "D"
_LABEL_E: Final[str] = "E"
_LABEL_EXCLUDED: Final[str] = "제외"
_LABEL_SKIP: Final[str] = "스킵"


# ─────────────────────────────────────────────────────────────────────────────
# 모델
# ─────────────────────────────────────────────────────────────────────────────


# Chart120Bar 는 Chart60Bar 와 스키마가 동일하므로 alias 로 재사용한다.
Chart120Bar = Chart60Bar


@dataclass(slots=True)
class Chart60_120FilterResult:
    """단일 종목 chart60+chart120 결합 필터 판정 결과.

    Attributes:
        stk_cd: 종목코드.
        stk_nm: 종목명.
        report60_path: chart60.md 경로 (없을 수 있음).
        report120_path: chart120.md 경로 (없을 수 있음).
        bars60: chart60.md 의 16봉 (시간 오름차순). 누락 시 빈 리스트.
        bars120: chart120.md 의 16봉 (시간 오름차순). 누락 시 빈 리스트.
        selected: 리서치 대상 선정 여부.
        category: 분류 라벨 — ``"A"`` / ``"B"`` / ``"C"`` / ``"D"`` / ``"E"`` /
            ``"제외"`` / ``"스킵"``.
        reason: 사람이 읽을 수 있는 판정 사유.
        extra: 부가 메트릭(타입별 체크 통과 여부, 최근 봉 시각 등).
    """

    stk_cd: str
    stk_nm: str
    report60_path: Path | None
    report120_path: Path | None
    bars60: list[Chart60Bar]
    bars120: list[Chart120Bar]
    selected: bool
    category: str
    reason: str
    extra: dict[str, object] = field(default_factory=dict)


# ─────────────────────────────────────────────────────────────────────────────
# chart120.md 파서 (chart60 표 포맷과 동일하므로 동일 정규식 재사용)
# ─────────────────────────────────────────────────────────────────────────────


def parse_chart120_md(path: Path) -> tuple[list[Chart120Bar], dict[str, str]]:
    """chart120.md 를 파싱하여 봉 리스트와 헤더 메타를 반환.

    Args:
        path: ``chart120.md`` 절대/상대 경로.

    Returns:
        ``(bars, meta)`` — ``bars`` 시간 오름차순, ``meta`` 헤더 메타.

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
        elif line.startswith("- **최근 봉 시각**:"):
            m = re.search(r"\*\*최근 봉 시각\*\*:\s*(.+)", line)
            if m:
                meta["last_bar_ts"] = m.group(1).strip()

    bars: list[Chart120Bar] = []
    for line in text.splitlines():
        m = _TABLE_ROW_PATTERN.match(line)
        if not m:
            continue
        bars.append(
            Chart120Bar(
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
        raise ValueError(f"chart120.md 시계열 표 파싱 실패 (행 0개): {path}")

    return bars, meta


# ─────────────────────────────────────────────────────────────────────────────
# 단일 봉 헬퍼
# ─────────────────────────────────────────────────────────────────────────────


def _ma_present(b: Chart60Bar, *names: str) -> tuple[bool, str | None]:
    """주어진 MA 들이 모두 존재하고 MA306>0 인지 검사."""
    for n in names:
        v = getattr(b, n)
        if v is None:
            return False, f"{n} 결측"
        if n == "ma306" and v == 0:
            return False, "MA306=0"
    return True, None


def _is_4ma_aligned(b: Chart60Bar, tol: float) -> tuple[bool, str | None]:
    """4선 정배열: MA10 ≥ MA20·(1−tol) ≥ MA60·(1−tol) ≥ MA306·(1−tol)."""
    ok, reason = _ma_present(b, "ma10", "ma20", "ma60", "ma306")
    if not ok:
        return False, reason
    t = 1.0 - tol
    if b.ma10 < b.ma20 * t:  # type: ignore[operator]
        return False, f"MA10({b.ma10:,.0f}) < MA20×{t:.3f}({b.ma20 * t:,.0f})"  # type: ignore[operator]
    if b.ma20 < b.ma60 * t:  # type: ignore[operator]
        return False, f"MA20({b.ma20:,.0f}) < MA60×{t:.3f}({b.ma60 * t:,.0f})"  # type: ignore[operator]
    if b.ma60 < b.ma306 * t:  # type: ignore[operator]
        return False, f"MA60({b.ma60:,.0f}) < MA306×{t:.3f}({b.ma306 * t:,.0f})"  # type: ignore[operator]
    return True, None


def _is_upper3_aligned(b: Chart60Bar, tol: float) -> tuple[bool, str | None]:
    """상위 3선 정배열: MA10 ≥ MA20·(1−tol) ≥ MA60·(1−tol)."""
    ok, reason = _ma_present(b, "ma10", "ma20", "ma60")
    if not ok:
        return False, reason
    t = 1.0 - tol
    if b.ma10 < b.ma20 * t:  # type: ignore[operator]
        return False, f"MA10({b.ma10:,.0f}) < MA20×{t:.3f}({b.ma20 * t:,.0f})"  # type: ignore[operator]
    if b.ma20 < b.ma60 * t:  # type: ignore[operator]
        return False, f"MA20({b.ma20:,.0f}) < MA60×{t:.3f}({b.ma60 * t:,.0f})"  # type: ignore[operator]
    return True, None


def _ma60_above_ma306(b: Chart60Bar, tol: float) -> tuple[bool, str | None]:
    """장기 추세: MA60 ≥ MA306·(1−tol)."""
    ok, reason = _ma_present(b, "ma60", "ma306")
    if not ok:
        return False, reason
    t = 1.0 - tol
    if b.ma60 < b.ma306 * t:  # type: ignore[operator]
        return False, f"MA60({b.ma60:,.0f}) < MA306×{t:.3f}({b.ma306 * t:,.0f})"  # type: ignore[operator]
    return True, None


def _all_static(
    bars: list[Chart60Bar],
    checker,  # Callable[[Chart60Bar], tuple[bool, str | None]]
    *,
    n: int = _REQUIRED_STATIC_BARS,
) -> tuple[bool, str | None]:
    """``bars`` 의 마지막 ``n`` 봉 모두에서 ``checker`` 가 True 인지.

    실패 시 첫 실패 봉의 사유를 반환한다.
    """
    if len(bars) < n:
        return False, f"봉 부족 ({len(bars)}봉 < {n}봉)"
    window = bars[-n:]
    for b in window:
        ok, reason = checker(b)
        if not ok:
            return False, f"ts={b.ts} {reason}"
    return True, None


# ─────────────────────────────────────────────────────────────────────────────
# Type 체커
# ─────────────────────────────────────────────────────────────────────────────


def _check_type_a(
    bars60: list[Chart60Bar], bars120: list[Chart120Bar]
) -> tuple[bool, str | None]:
    """Type A — 양 시간대 4선 완전 정배열 (-3.5% 허용)."""
    ok120, r120 = _all_static(
        bars120, lambda b: _is_4ma_aligned(b, _TYPE_A_ALIGN_TOL)
    )
    if not ok120:
        return False, f"120분 4선정배열 실패: {r120}"
    ok60, r60 = _all_static(
        bars60, lambda b: _is_4ma_aligned(b, _TYPE_A_ALIGN_TOL)
    )
    if not ok60:
        return False, f"60분 4선정배열 실패: {r60}"
    return True, None


def _check_type_b(
    bars60: list[Chart60Bar], bars120: list[Chart120Bar]
) -> tuple[bool, str | None]:
    """Type B — 60분 선행 정배열 / 120분 상승 초입."""

    def _b120(b: Chart60Bar) -> tuple[bool, str | None]:
        ok, reason = _ma_present(b, "ma10", "ma20", "ma60", "ma306")
        if not ok:
            return False, reason
        t = 1.0 - _ALIGN_TOL_LOOSE
        r = _TYPE_B_BELOW_MA60_RATIO
        if b.ma10 < b.ma20 * t:  # type: ignore[operator]
            return False, f"MA10({b.ma10:,.0f}) < MA20×{t:.3f}"  # type: ignore[operator]
        if b.ma10 > b.ma60 * r:  # type: ignore[operator]
            return False, (
                f"MA10({b.ma10:,.0f}) > MA60×{r:.2f}({b.ma60 * r:,.0f}) "  # type: ignore[operator]
                f"— MA60 대비 {(1 - r) * 100:.0f}% 이상 아래여야 함"
            )
        if b.ma20 > b.ma60 * r:  # type: ignore[operator]
            return False, (
                f"MA20({b.ma20:,.0f}) > MA60×{r:.2f}({b.ma60 * r:,.0f})"  # type: ignore[operator]
            )
        if b.ma60 < b.ma306 * t:  # type: ignore[operator]
            return False, f"MA60({b.ma60:,.0f}) < MA306×{t:.3f}"  # type: ignore[operator]
        return True, None

    ok120, r120 = _all_static(bars120, _b120)
    if not ok120:
        return False, f"120분 Type B 조건 실패: {r120}"

    def _b60(b: Chart60Bar) -> tuple[bool, str | None]:
        ok, reason = _is_upper3_aligned(b, _ALIGN_TOL_LOOSE)
        if not ok:
            return False, reason
        return _ma60_above_ma306(b, _ALIGN_TOL_LOOSE)

    ok60, r60 = _all_static(bars60, _b60)
    if not ok60:
        return False, f"60분 Type B 조건 실패: {r60}"
    return True, None


def _check_type_c(
    bars60: list[Chart60Bar], bars120: list[Chart120Bar]
) -> tuple[bool, str | None]:
    """Type C — 120분 MA10·MA20·MA60 수렴 + 60분 봉 60일선 골든크로스."""

    def _c120(b: Chart60Bar) -> tuple[bool, str | None]:
        ok, reason = _ma_present(b, "ma10", "ma20", "ma60", "ma306")
        if not ok:
            return False, reason
        ms = [b.ma10, b.ma20, b.ma60]
        m_min = min(ms)  # type: ignore[type-var]
        m_max = max(ms)  # type: ignore[type-var]
        if m_min <= 0:
            return False, "MA10/20/60 중 0 이하 존재"
        spread = (m_max - m_min) / m_min  # type: ignore[operator]
        if spread > _TYPE_C_CONVERGE_PCT:
            return False, (
                f"수렴 폭 {spread * 100:.2f}% > {_TYPE_C_CONVERGE_PCT * 100:.1f}% "
                f"(min={m_min:,.0f} max={m_max:,.0f})"
            )
        return _ma60_above_ma306(b, _ALIGN_TOL_LOOSE)

    ok120, r120 = _all_static(bars120, _c120)
    if not ok120:
        return False, f"120분 수렴 실패: {r120}"

    if len(bars60) < 2:
        return False, "60분 봉 부족 (< 2)"
    prev, last = bars60[-2], bars60[-1]
    if prev.ma60 is None or last.ma60 is None:
        return False, "60분 MA60 결측"
    if not (prev.close <= prev.ma60):
        return False, (
            f"60분 이전봉 미돌파 — prev.close({prev.close:,}) > prev.ma60({prev.ma60:,.0f})"
        )
    if not (last.close > last.ma60):
        return False, (
            f"60분 현재봉 미돌파 — last.close({last.close:,}) ≤ last.ma60({last.ma60:,.0f})"
        )
    return True, None


def _check_type_d(
    bars60: list[Chart60Bar], bars120: list[Chart120Bar]
) -> tuple[bool, str | None]:
    """Type D — 120분 엉킴(MA10·MA20 ≥ MA60·(1-tol)) + 60분 정배열 또는 close>MA60 우세.

    (우선순위 체크 — Type A 미충족은 호출자가 보장한다.)
    """

    def _d120(b: Chart60Bar) -> tuple[bool, str | None]:
        ok, reason = _ma_present(b, "ma10", "ma20", "ma60", "ma306")
        if not ok:
            return False, reason
        t = 1.0 - _TYPE_D_ALIGN_TOL_120
        if b.ma10 < b.ma60 * t:  # type: ignore[operator]
            return False, (
                f"MA10({b.ma10:,.0f}) < MA60×{t:.3f}({b.ma60 * t:,.0f})"  # type: ignore[operator]
            )
        if b.ma20 < b.ma60 * t:  # type: ignore[operator]
            return False, (
                f"MA20({b.ma20:,.0f}) < MA60×{t:.3f}({b.ma60 * t:,.0f})"  # type: ignore[operator]
            )
        return _ma60_above_ma306(b, _ALIGN_TOL_LOOSE)

    ok120, r120 = _all_static(bars120, _d120)
    if not ok120:
        return False, f"120분 엉킴 조건 실패: {r120}"

    # 60분 — (a) 4선 정배열 또는 (b) close>MA60 비율 ≥ 75%.
    ok60a, _ = _all_static(
        bars60, lambda b: _is_4ma_aligned(b, _ALIGN_TOL_LOOSE)
    )
    if ok60a:
        return True, None

    window = bars60[-_TYPE_D_DYNAMIC_WINDOW:] if bars60 else []
    if not window:
        return False, "60분 봉 없음"
    over = sum(
        1 for b in window if b.ma60 is not None and b.close > b.ma60
    )
    ratio = over / len(window)
    if ratio >= _TYPE_D_CLOSE_OVER_MA60_RATIO:
        return True, None
    return False, (
        f"60분 보조조건 실패 — 4선정배열 X, close>MA60 비율 "
        f"{ratio * 100:.1f}% < {_TYPE_D_CLOSE_OVER_MA60_RATIO * 100:.0f}%"
    )


def _check_type_e(
    bars60: list[Chart60Bar], bars120: list[Chart120Bar]
) -> tuple[bool, str | None]:
    """Type E — "정배열 직전 + MA60 위 지지(fresh breakout)" 신선 돌파 직후.

    120분 최근 1봉:
        MA60 ≥ MA306 × 0.985 (장기 추세 양호)
        close > MA60 (현재 봉이 60선 위)
        (max(MA10,MA20,MA60) − min)/min ≤ _TYPE_E_SPREAD_PCT (수렴 중)
    120분 최근 _TYPE_E_SHORT_ALIGN_WINDOW 봉:
        ≥1봉이 MA10 ≥ MA20 (단기 정렬 시작 — 마지막 봉 노이즈 구제)
    60분 최근 8봉:
        count(close > MA60) / 8 ≥ _TYPE_E_CLOSE_OVER_MA60_RATIO (60선 위 지지)
    """
    if not bars120:
        return False, "120분 봉 없음"
    if len(bars60) < _TYPE_E_DYNAMIC_WINDOW:
        return False, f"60분 봉 부족 ({len(bars60)} < {_TYPE_E_DYNAMIC_WINDOW})"
    b = bars120[-1]
    ok, reason = _ma_present(b, "ma10", "ma20", "ma60", "ma306")
    if not ok:
        return False, f"120분 최근봉 {reason}"
    ok306, r306 = _ma60_above_ma306(b, _TYPE_E_MA60_OVER_MA306_TOL)
    if not ok306:
        return False, f"120분 장기추세 실패: {r306}"
    if not (b.close > b.ma60):  # type: ignore[operator]
        return False, (
            f"120분 close({b.close:,}) ≤ MA60({b.ma60:,.0f}) — 60선 위 지지 X"  # type: ignore[operator]
        )
    # 단기 정렬(MA10 ≥ MA20 × (1 − tol)) — 최근 N봉 중 ≥1봉이면 통과.
    # (마지막 봉만 검사하면 인트라데이 노이즈로 살짝 어긋난 종목까지 탈락하므로 완화.)
    short_window = bars120[-_TYPE_E_SHORT_ALIGN_WINDOW:]
    align_t = 1.0 - _TYPE_E_SHORT_ALIGN_TOL
    aligned = sum(
        1 for x in short_window
        if x.ma10 is not None and x.ma20 is not None
        and x.ma10 >= x.ma20 * align_t
    )
    if aligned == 0:
        return False, (
            f"120분 MA10 < MA20×{align_t:.3f} (최근 {len(short_window)}봉 모두) "
            f"— 단기 정렬 미시작"
        )
    ms = [b.ma10, b.ma20, b.ma60]
    m_min = min(ms)  # type: ignore[type-var]
    m_max = max(ms)  # type: ignore[type-var]
    if m_min <= 0:
        return False, "120분 MA10/20/60 중 0 이하 존재"
    spread = (m_max - m_min) / m_min  # type: ignore[operator]
    if spread > _TYPE_E_SPREAD_PCT:
        return False, (
            f"120분 수렴 폭 {spread * 100:.2f}% > {_TYPE_E_SPREAD_PCT * 100:.0f}%"
        )
    window = bars60[-_TYPE_E_DYNAMIC_WINDOW:]
    over = sum(1 for x in window if x.ma60 is not None and x.close > x.ma60)
    ratio = over / len(window)
    if ratio < _TYPE_E_CLOSE_OVER_MA60_RATIO:
        return False, (
            f"60분 close>MA60 비율 {ratio * 100:.1f}% < "
            f"{_TYPE_E_CLOSE_OVER_MA60_RATIO * 100:.0f}% "
            f"(최근 {_TYPE_E_DYNAMIC_WINDOW}봉)"
        )
    return True, None


# ─────────────────────────────────────────────────────────────────────────────
# 평가 (우선순위 A → B → C → D → E)
# ─────────────────────────────────────────────────────────────────────────────


_TYPE_CHECKERS: Final[tuple[tuple[str, object], ...]] = (
    (_LABEL_A, _check_type_a),
    (_LABEL_B, _check_type_b),
    (_LABEL_C, _check_type_c),
    (_LABEL_D, _check_type_d),
    (_LABEL_E, _check_type_e),
)


def evaluate_chart60_120(
    bars60: list[Chart60Bar], bars120: list[Chart120Bar]
) -> tuple[bool, str, str, dict[str, object]]:
    """Type A→B→C→D 순으로 검사하여 첫 매칭으로 분류.

    Args:
        bars60: chart60.md 16봉 (시간 오름차순).
        bars120: chart120.md 16봉 (시간 오름차순).

    Returns:
        ``(selected, category, reason, extra)``.
            - ``category``: ``"A"``/``"B"``/``"C"``/``"D"``/``"E"`` 또는 ``"제외"``.
            - ``extra``: ``latest_ts60``, ``latest_ts120``, ``type_results``
              (각 타입별 통과 여부와 실패 사유).
    """
    extra: dict[str, object] = {
        "latest_ts60": bars60[-1].ts if bars60 else None,
        "latest_ts120": bars120[-1].ts if bars120 else None,
    }

    type_results: dict[str, tuple[bool, str | None]] = {}
    for label, checker in _TYPE_CHECKERS:
        ok, reason = checker(bars60, bars120)  # type: ignore[operator]
        type_results[label] = (ok, reason)
        if ok:
            extra["type_results"] = type_results
            return True, label, f"Type {label} 매칭", extra

    extra["type_results"] = type_results
    fail_summary = "; ".join(
        f"{lbl}:{r if r else 'X'}" for lbl, (_o, r) in type_results.items()
    )
    return False, _LABEL_EXCLUDED, f"전 타입 미매칭 — {fail_summary}", extra


# ─────────────────────────────────────────────────────────────────────────────
# 종목 → 리포트 경로 / 단일·일괄 필터
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


def find_stock_dir(
    stock: str,
    *,
    date_dir: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> Path:
    """종목코드 또는 종목명으로 종목 폴더(``종목명(코드)``) 를 탐색.

    Raises:
        FileNotFoundError: 후보 폴더를 찾지 못한 경우.
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
    for sd in _list_stock_dirs(target):
        parsed = _split_stock_dirname(sd.name)
        if parsed is None:
            continue
        nm, cd = parsed
        if is_code and cd == stock:
            matches.append(sd)
        elif not is_code and nm == stock:
            matches.append(sd)

    if not matches:
        raise FileNotFoundError(
            f"종목 폴더 없음: stock={stock!r} date_dir={target.name}"
        )
    if len(matches) > 1:
        logger.warning(
            "종목 폴더 다중 매칭 — 첫 번째 사용: {names}",
            names=[p.name for p in matches],
        )
    return matches[0]


def filter_stock(
    stock: str,
    *,
    date_dir: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> Chart60_120FilterResult:
    """단일 종목 chart60+chart120 결합 필터."""
    stock_dir = find_stock_dir(stock, date_dir=date_dir, reports_root=reports_root)
    p60 = stock_dir / _CHART60_FILENAME
    p120 = stock_dir / _CHART120_FILENAME

    parsed = _split_stock_dirname(stock_dir.name)
    stk_nm = parsed[0] if parsed else ""
    stk_cd = parsed[1] if parsed else stock

    if not p60.exists() or not p120.exists():
        missing = [
            n for n, p in (("chart60.md", p60), ("chart120.md", p120))
            if not p.exists()
        ]
        return Chart60_120FilterResult(
            stk_cd=stk_cd,
            stk_nm=stk_nm,
            report60_path=p60 if p60.exists() else None,
            report120_path=p120 if p120.exists() else None,
            bars60=[],
            bars120=[],
            selected=False,
            category=_LABEL_SKIP,
            reason=f"입력 누락 — {', '.join(missing)}",
        )

    bars60, meta60 = parse_chart60_md(p60)
    bars120, _meta120 = parse_chart120_md(p120)
    selected, category, reason, extra = evaluate_chart60_120(bars60, bars120)

    return Chart60_120FilterResult(
        stk_cd=meta60.get("stk_cd") or stk_cd,
        stk_nm=meta60.get("stk_nm") or stk_nm,
        report60_path=p60,
        report120_path=p120,
        bars60=bars60,
        bars120=bars120,
        selected=selected,
        category=category,
        reason=reason,
        extra=extra,
    )


def filter_all_stocks(
    *,
    date_dir: str | None = None,
    reports_root: Path = _DEFAULT_REPORTS_ROOT,
) -> list[Chart60_120FilterResult]:
    """지정 날짜 폴더 내 모든 종목 일괄 필터.

    chart60.md/chart120.md 둘 중 하나라도 없으면 ``category="스킵"`` 으로
    포함된다 (집계 가시성).
    """
    if date_dir:
        target = reports_root / date_dir
    else:
        target = _latest_date_dir(reports_root)
        if target is None:
            raise FileNotFoundError(f"reports 하위에 날짜 폴더가 없음: {reports_root}")

    results: list[Chart60_120FilterResult] = []
    for stock_dir in _list_stock_dirs(target):
        parsed = _split_stock_dirname(stock_dir.name)
        if parsed is None:
            continue
        stk_nm, stk_cd = parsed
        p60 = stock_dir / _CHART60_FILENAME
        p120 = stock_dir / _CHART120_FILENAME

        if not p60.exists() or not p120.exists():
            missing = [
                n for n, p in (("chart60.md", p60), ("chart120.md", p120))
                if not p.exists()
            ]
            results.append(
                Chart60_120FilterResult(
                    stk_cd=stk_cd,
                    stk_nm=stk_nm,
                    report60_path=p60 if p60.exists() else None,
                    report120_path=p120 if p120.exists() else None,
                    bars60=[],
                    bars120=[],
                    selected=False,
                    category=_LABEL_SKIP,
                    reason=f"입력 누락 — {', '.join(missing)}",
                )
            )
            continue

        try:
            bars60, _ = parse_chart60_md(p60)
            bars120, _ = parse_chart120_md(p120)
        except (ValueError, FileNotFoundError) as exc:
            logger.warning("파싱 실패 {n}({c}): {e}", n=stk_nm, c=stk_cd, e=exc)
            results.append(
                Chart60_120FilterResult(
                    stk_cd=stk_cd,
                    stk_nm=stk_nm,
                    report60_path=p60,
                    report120_path=p120,
                    bars60=[],
                    bars120=[],
                    selected=False,
                    category=_LABEL_SKIP,
                    reason=f"파싱 실패 — {exc}",
                )
            )
            continue

        selected, category, reason, extra = evaluate_chart60_120(bars60, bars120)
        results.append(
            Chart60_120FilterResult(
                stk_cd=stk_cd,
                stk_nm=stk_nm,
                report60_path=p60,
                report120_path=p120,
                bars60=bars60,
                bars120=bars120,
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


def _fmt_int(v: object) -> str:
    if v is None:
        return "—"
    return f"{int(v):,}"


def _fmt_float(v: object) -> str:
    if v is None:
        return "—"
    return f"{float(v):,.2f}"


def render_markdown(
    results: list[Chart60_120FilterResult],
    *,
    fetched_at: str = "",
    date_dir: str = "",
) -> str:
    """필터 결과를 마크다운 리포트로 렌더링."""
    selected = [r for r in results if r.selected]
    excluded = [r for r in results if not r.selected and r.category != _LABEL_SKIP]
    skipped = [r for r in results if r.category == _LABEL_SKIP]

    by_category: dict[str, int] = {}
    for r in results:
        by_category[r.category] = by_category.get(r.category, 0) + 1

    lines: list[str] = [
        "# 종목 필터 리포트 — chart60 + chart120 (4 Type 매칭)",
        "",
        "## 판정 조건",
        "- **Type A** — 양 시간대 4선 완전 정배열 (-3.5% 허용)",
        "    - 120분 & 60분 bars[-8:] 모두: MA10 ≥ MA20·0.965 ≥ MA60·0.965 ≥ MA306·0.965",
        "- **Type B** — 60분 선행 정배열 / 120분 상승 초입",
        "    - 120분 bars[-8:]: MA10 ≥ MA20·0.985, MA10·MA20 ≤ MA60·0.97, MA60 ≥ MA306·0.985",
        "    - 60분  bars[-8:]: MA10 ≥ MA20·0.985 ≥ MA60·0.985, MA60 ≥ MA306·0.985",
        "- **Type C** — 120분 수렴 + 60분 60일선 골든크로스",
        "    - 120분 bars[-8:]: (max−min)/min(MA10,MA20,MA60) ≤ 2.0%, MA60 ≥ MA306·0.985",
        "    - 60분 교차: bars[-2].close ≤ MA60 AND bars[-1].close > MA60",
        "- **Type D** — 120분 엉킴(Type A 미충족) + 60분 정배열 또는 돌파 우세",
        "    - 120분 bars[-8:]: MA10 ≥ MA60·0.98 AND MA20 ≥ MA60·0.98, MA60 ≥ MA306·0.985",
        "    - 60분: bars[-8:] 4선 정배열 또는 bars[-16:] 중 close>MA60 비율 ≥ 60%",
        "- **Type E** — 정배열 직전 + MA60 위 지지 (fresh breakout)",
        "    - 120분 bars[-1]: MA60 ≥ MA306·0.965, close > MA60,"
        " (max−min)/min(MA10,MA20,MA60) ≤ 10%",
        "    - 120분 bars[-2:] 중 ≥1봉: MA10 ≥ MA20·0.984 (단기 정렬 직전, 1.6% tol)",
        "    - 60분 bars[-8:]: close>MA60 비율 ≥ 75%",
        "- **우선순위**: A → B → C → D → E (첫 매칭으로 분류)",
        "- **색상**: 🔵MA10 / 🔴MA20 / 🟢MA60 / ⚫MA306",
        "",
        "## 요약",
        f"- **입력 날짜 폴더**: {date_dir or '—'}",
        f"- **취득 시각**: {fetched_at or '—'}",
        f"- **분석 종목 수**: {len(results)}",
        f"- **선정 종목 수**: {len(selected)}",
        f"- **제외 종목 수**: {len(excluded)}",
        f"- **스킵(입력 누락) 수**: {len(skipped)}",
        "- **분류 분포**: "
        + (
            ", ".join(f"{k} {v}건" for k, v in sorted(by_category.items()))
            or "—"
        ),
        "",
    ]

    lines += [
        f"## 선정 종목 ({len(selected)}건)",
        "",
        "| # | 종목코드 | 종목명 | Type | 60분 최근봉 | 120분 최근봉 | 60분 종가 | 60분 MA10 | 60분 MA20 | 60분 MA60 | 60분 MA306 | 120분 MA10 | 120분 MA20 | 120분 MA60 | 120분 MA306 | 사유 |",
        "|---:|---|---|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for i, r in enumerate(selected, start=1):
        b60 = r.bars60[-1] if r.bars60 else None
        b120 = r.bars120[-1] if r.bars120 else None
        lines.append(
            "| {n} | {cd} | {nm} | {cat} | {ts60} | {ts120} | {c60} | {m10_60} | {m20_60} | {m60_60} | {m306_60} | {m10_120} | {m20_120} | {m60_120} | {m306_120} | {reason} |".format(
                n=i,
                cd=r.stk_cd,
                nm=r.stk_nm,
                cat=r.category,
                ts60=b60.ts if b60 else "—",
                ts120=b120.ts if b120 else "—",
                c60=_fmt_int(b60.close if b60 else None),
                m10_60=_fmt_float(b60.ma10 if b60 else None),
                m20_60=_fmt_float(b60.ma20 if b60 else None),
                m60_60=_fmt_float(b60.ma60 if b60 else None),
                m306_60=_fmt_float(b60.ma306 if b60 else None),
                m10_120=_fmt_float(b120.ma10 if b120 else None),
                m20_120=_fmt_float(b120.ma20 if b120 else None),
                m60_120=_fmt_float(b120.ma60 if b120 else None),
                m306_120=_fmt_float(b120.ma306 if b120 else None),
                reason=r.reason,
            )
        )
    lines.append("")

    lines += [
        f"## 제외 종목 ({len(excluded)}건)",
        "",
        "| # | 종목코드 | 종목명 | 60분 최근봉 | 120분 최근봉 | 사유 |",
        "|---:|---|---|---|---|---|",
    ]
    for i, r in enumerate(excluded, start=1):
        b60 = r.bars60[-1] if r.bars60 else None
        b120 = r.bars120[-1] if r.bars120 else None
        lines.append(
            "| {n} | {cd} | {nm} | {ts60} | {ts120} | {reason} |".format(
                n=i,
                cd=r.stk_cd,
                nm=r.stk_nm,
                ts60=b60.ts if b60 else "—",
                ts120=b120.ts if b120 else "—",
                reason=r.reason,
            )
        )
    lines.append("")

    if skipped:
        lines += [
            f"## 스킵 종목 ({len(skipped)}건)",
            "",
            "| # | 종목코드 | 종목명 | 사유 |",
            "|---:|---|---|---|",
        ]
        for i, r in enumerate(skipped, start=1):
            lines.append(f"| {i} | {r.stk_cd} | {r.stk_nm} | {r.reason} |")
        lines.append("")

    lines += [
        "## 비고",
        "- 입력 데이터: ``reports/<날짜>/<종목명(종목코드)>/chart60.md`` + ``chart120.md``",
        "- MA 값은 각 시간대 종가 기준 단순이동평균(SMA)",
        "- 노란 블록 16봉 = 마크다운 시계열 표 전체. 정적 조건은 최근 8봉, 동적 조건은 최근 1~16봉.",
        "- 본 리포트는 분석 보조 자료이며, 매매 신호로 단정해서는 안 됩니다",
        "",
    ]
    return "\n".join(lines)


def save_chart60_120_filter_markdown(
    results: list[Chart60_120FilterResult],
    *,
    output_root: Path = _DEFAULT_REPORTS_ROOT,
    date_dir: str | None = None,
    now: datetime | None = None,
) -> Path:
    """필터 결과 리포트를 ``<output_root>/<날짜>/chart60_120Filter.md`` 에 저장."""
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


def _print_single(r: Chart60_120FilterResult) -> None:
    if r.category == _LABEL_SKIP:
        icon = "⚪ 스킵"
    elif r.selected:
        icon = "✅ 선정"
    else:
        icon = "❌ 제외"
    print(f"{icon} [{r.category}] {r.stk_nm}({r.stk_cd})")
    print(f"  - chart60 : {r.report60_path}")
    print(f"  - chart120: {r.report120_path}")
    if r.bars60:
        b = r.bars60[-1]
        print(
            f"  - 60분 최근 {b.ts} | 종가 {b.close:,} | "
            f"MA10 {b.ma10} MA20 {b.ma20} MA60 {b.ma60} MA306 {b.ma306}"
        )
    if r.bars120:
        b = r.bars120[-1]
        print(
            f"  - 120분 최근 {b.ts} | 종가 {b.close:,} | "
            f"MA10 {b.ma10} MA20 {b.ma20} MA60 {b.ma60} MA306 {b.ma306}"
        )
    tr = r.extra.get("type_results")
    if isinstance(tr, dict):
        for lbl, (ok, reason) in tr.items():
            mark = "○" if ok else "×"
            print(f"  - Type {lbl}: {mark} {reason or ''}")
    print(f"  - 사유: {r.reason}")


def main(argv: list[str] | None = None) -> int:
    """CLI 엔트리포인트.

    사용법::

        python -m src.kiwoom.itemFilter.chart60_120Filter <stock> [<YYYYMMDD>]
        python -m src.kiwoom.itemFilter.chart60_120Filter --all [<YYYYMMDD>]

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
        skp = sum(1 for r in results if r.category == _LABEL_SKIP)
        print(
            f"=== 일괄 필터 결과: 분석 {len(results)} / 선정 {sel} / "
            f"제외 {len(results) - sel - skp} / 스킵 {skp} ==="
        )
        for r in results:
            _print_single(r)
            print()
        path = save_chart60_120_filter_markdown(results, date_dir=date_dir)
        print(f"\n리포트: {path}")
        return 0

    stock = args[0]
    r = filter_stock(stock, date_dir=date_dir)
    _print_single(r)
    return 0 if r.selected else 1


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = [
    "Chart120Bar",
    "Chart60_120FilterResult",
    "evaluate_chart60_120",
    "filter_all_stocks",
    "filter_stock",
    "find_stock_dir",
    "main",
    "parse_chart120_md",
    "render_markdown",
    "save_chart60_120_filter_markdown",
]
