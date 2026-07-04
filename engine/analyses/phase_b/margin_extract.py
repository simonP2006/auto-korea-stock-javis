"""Phase B-1 — 마진 추출 하네스 + 베이스라인 (MISSION_PHASE_B_EXEC_20260704 §3 B-1).

설계 (§2 아키텍처):
    - 골든 ``reports/<날짜>/`` 는 **읽기전용**. 산출은 analyses/phase_b/out/ 만.
    - 파싱은 **엔진 파서를 그대로 임포트**(재구현 0) — parse_chart60_md 등.
    - 판정은 엔진 evaluate 를 **오라클**로, 본 하네스의 파라미터화 미러(mirror_*)와
      전 인스턴스 × 전 스테이지 등가성 검증(불일치 = fail-loud).
    - 임의 파라미터 벡터 평가용 프리미티브(원시 봉 배열)를 일자별 .npz 저장.
    - 라벨(masterReference)은 이름-only(조인트일)·이름(코드)(백필일) 양포맷 파싱
      + 2단 해석(당일 폴더 → 디스크 유니언맵). 미해석 UNRESOLVED 정직 집계.

실행::

    .venv/bin/python analyses/phase_b/margin_extract.py --days 20260702,20260703   # 파일럿
    .venv/bin/python analyses/phase_b/margin_extract.py --all                      # 전체
"""
from __future__ import annotations

import argparse
import json
import random
import sys
from collections import Counter
from pathlib import Path

ENGINE = Path("/Users/tajun/spJavis/auto-korea-stock-javis/engine")
sys.path.insert(0, str(ENGINE))

import numpy as np
from loguru import logger

logger.remove()
logger.add(str(ENGINE / "analyses/phase_b/out/extract.log"), level="INFO", enqueue=True)

# ── 엔진 임포트 (파서 + 오라클 evaluate) — 재구현 금지 원칙 ──
from src.kiwoom.itemFilter.chart60Filter import parse_chart60_md, _split_stock_dirname
from src.kiwoom.itemFilter.chart60_120Filter import (
    parse_chart120_md, evaluate_chart60_120,
)
from src.kiwoom.itemFilter.chart240Filter import parse_chart240_md, evaluate_chart240
from src.kiwoom.itemFilter.chartDayFilter import parse_chartday_md, evaluate_chartday
from src.kiwoom.itemFilter.chartDayPreFilter import evaluate_chartday_pre
from src.kiwoom.itemFilter.investorFilter import parse_investor_md, evaluate_investor
from src.kiwoom.itemFilter.financeFilter import (
    parse_finance_md, evaluate_finance, _is_invalid_md,
)
from src.kiwoom.itemFilter.Filter_condition_update import _parse_entry
from src.kiwoom.researchFlow.name_resolver import build_name_to_code_map
from src.kiwoom.researchFlow.expert_backfill import build_disk_name_to_code_map

REPORTS = ENGINE / "reports"
OUT = ENGINE / "analyses/phase_b/out"
PRIMS = OUT / "prims"

# ── 현행 상수 P0 (라이브 grep 대사 완료 — parameter-catalog §SOT 규칙에 따라
#    아래 값은 margin_extract 실행 시 모듈 상수와 assert 대조한다) ──
P0 = dict(
    s1_n=8,            # _REQUIRED_STATIC_BARS
    s1_tL=0.015,       # _ALIGN_TOL_LOOSE
    s1_tA=0.035,       # _TYPE_A_ALIGN_TOL
    s1_rB=0.97,        # _TYPE_B_BELOW_MA60_RATIO
    s1_cC=0.035,       # _TYPE_C_CONVERGE_PCT
    s1_tD=0.020,       # _TYPE_D_ALIGN_TOL_120
    s1_rD=0.50,        # _TYPE_D_CLOSE_OVER_MA60_RATIO
    s1_wD=16,          # _TYPE_D_DYNAMIC_WINDOW
    s1_sE=0.10,        # _TYPE_E_SPREAD_PCT
    s1_wE=8,           # _TYPE_E_DYNAMIC_WINDOW
    s1_rE=0.75,        # _TYPE_E_CLOSE_OVER_MA60_RATIO
    s1_wSA=2,          # _TYPE_E_SHORT_ALIGN_WINDOW
    s1_tSA=0.016,      # _TYPE_E_SHORT_ALIGN_TOL
    s1_tE306=0.035,    # _TYPE_E_MA60_OVER_MA306_TOL
    s2_t=0.025,        # _MA60_MA306_TOLERANCE (240)
    s2_n=3,            # _REQUIRED_CONSECUTIVE_BARS (240)
    s21_surge=0.15,    # _DAILY_SURGE_THRESHOLD
    s3_t=0.05,         # _MA10_MA20_MA60_TOLERANCE
    s3_lo=0.15,        # _MA60_MA306_LOWER_TOL
    s3_up=0.45,        # _MA60_MA306_UPPER_TOL
    s3_c612lo=-0.15,   # _CLOSE_VS_MA612_LOWER
    s3_c612up=0.50,    # _CLOSE_VS_MA612_UPPER
    s3_n=3,            # _REQUIRED_CONSECUTIVE_BARS (day)
    s3_k=2,            # _REQUIRED_ALIGNED_BARS
    s4_n=16,           # _REQUIRED_BARS
    s4_fc=2,           # _THRESHOLD_FOREIGN_CONSEC_SELL
    s4_ic=8,           # _THRESHOLD_INST_CONSEC_SELL
    s4_pc=3,           # _THRESHOLD_INDI_CONSEC_BUY
    s4_ft=15,          # _THRESHOLD_FOREIGN_TOTAL_SELL
)


def assert_p0_matches_live() -> None:
    """P0 가 라이브 모듈 상수와 일치하는지 결정론 대조(드리프트 방지)."""
    from src.kiwoom.itemFilter import chart60_120Filter as m1
    from src.kiwoom.itemFilter import chart240Filter as m2
    from src.kiwoom.itemFilter import chartDayPreFilter as m21
    from src.kiwoom.itemFilter import chartDayFilter as m3
    from src.kiwoom.itemFilter import investorFilter as m4
    pairs = [
        (P0["s1_n"], m1._REQUIRED_STATIC_BARS), (P0["s1_tL"], m1._ALIGN_TOL_LOOSE),
        (P0["s1_tA"], m1._TYPE_A_ALIGN_TOL), (P0["s1_rB"], m1._TYPE_B_BELOW_MA60_RATIO),
        (P0["s1_cC"], m1._TYPE_C_CONVERGE_PCT), (P0["s1_tD"], m1._TYPE_D_ALIGN_TOL_120),
        (P0["s1_rD"], m1._TYPE_D_CLOSE_OVER_MA60_RATIO), (P0["s1_wD"], m1._TYPE_D_DYNAMIC_WINDOW),
        (P0["s1_sE"], m1._TYPE_E_SPREAD_PCT), (P0["s1_wE"], m1._TYPE_E_DYNAMIC_WINDOW),
        (P0["s1_rE"], m1._TYPE_E_CLOSE_OVER_MA60_RATIO), (P0["s1_wSA"], m1._TYPE_E_SHORT_ALIGN_WINDOW),
        (P0["s1_tSA"], m1._TYPE_E_SHORT_ALIGN_TOL), (P0["s1_tE306"], m1._TYPE_E_MA60_OVER_MA306_TOL),
        (P0["s2_t"], m2._MA60_MA306_TOLERANCE), (P0["s2_n"], m2._REQUIRED_CONSECUTIVE_BARS),
        (P0["s21_surge"], m21._DAILY_SURGE_THRESHOLD),
        (P0["s3_t"], m3._MA10_MA20_MA60_TOLERANCE), (P0["s3_lo"], m3._MA60_MA306_LOWER_TOL),
        (P0["s3_up"], m3._MA60_MA306_UPPER_TOL), (P0["s3_c612lo"], m3._CLOSE_VS_MA612_LOWER),
        (P0["s3_c612up"], m3._CLOSE_VS_MA612_UPPER), (P0["s3_n"], m3._REQUIRED_CONSECUTIVE_BARS),
        (P0["s3_k"], m3._REQUIRED_ALIGNED_BARS),
        (P0["s4_n"], m4._REQUIRED_BARS), (P0["s4_fc"], m4._THRESHOLD_FOREIGN_CONSEC_SELL),
        (P0["s4_ic"], m4._THRESHOLD_INST_CONSEC_SELL), (P0["s4_pc"], m4._THRESHOLD_INDI_CONSEC_BUY),
        (P0["s4_ft"], m4._THRESHOLD_FOREIGN_TOTAL_SELL),
    ]
    for i, (mine, live) in enumerate(pairs):
        if mine != live:
            raise AssertionError(f"P0 드리프트 #{i}: harness={mine} live={live}")


# ═══════════════════════════════════════════════════════════════════
# 파라미터화 미러 — 엔진 식을 문자 그대로 복제(표현식 형태 보존: 곱셈 비교)
# ═══════════════════════════════════════════════════════════════════

def _mp(b, *names):  # _ma_present 미러
    for n in names:
        v = getattr(b, n)
        if v is None:
            return False
        if n == "ma306" and v == 0:
            return False
    return True


def _m_4ma(b, tol):  # _is_4ma_aligned 미러
    if not _mp(b, "ma10", "ma20", "ma60", "ma306"):
        return False
    t = 1.0 - tol
    if b.ma10 < b.ma20 * t: return False
    if b.ma20 < b.ma60 * t: return False
    if b.ma60 < b.ma306 * t: return False
    return True


def _m_up3(b, tol):  # _is_upper3_aligned 미러
    if not _mp(b, "ma10", "ma20", "ma60"):
        return False
    t = 1.0 - tol
    if b.ma10 < b.ma20 * t: return False
    if b.ma20 < b.ma60 * t: return False
    return True


def _m_60_306(b, tol):  # _ma60_above_ma306 미러
    if not _mp(b, "ma60", "ma306"):
        return False
    return not (b.ma60 < b.ma306 * (1.0 - tol))


def _m_all(bars, chk, n):  # _all_static 미러
    if len(bars) < n:
        return False
    return all(chk(b) for b in bars[-n:])


def mirror_stage1(b60, b120, P):
    """(selected, category) — evaluate_chart60_120 미러. 카테고리=첫 매칭 타입."""
    tA, tL = P["s1_tA"], P["s1_tL"]
    n = P["s1_n"]

    def type_a():
        return _m_all(b120, lambda b: _m_4ma(b, tA), n) and _m_all(b60, lambda b: _m_4ma(b, tA), n)

    def type_b():
        r = P["s1_rB"]; t = 1.0 - tL
        def b120c(b):
            if not _mp(b, "ma10", "ma20", "ma60", "ma306"): return False
            if b.ma10 < b.ma20 * t: return False
            if b.ma10 > b.ma60 * r: return False
            if b.ma20 > b.ma60 * r: return False
            if b.ma60 < b.ma306 * t: return False
            return True
        def b60c(b):
            return _m_up3(b, tL) and _m_60_306(b, tL)
        return _m_all(b120, b120c, n) and _m_all(b60, b60c, n)

    def type_c():
        cC = P["s1_cC"]
        def c120(b):
            if not _mp(b, "ma10", "ma20", "ma60", "ma306"): return False
            ms = [b.ma10, b.ma20, b.ma60]
            m_min, m_max = min(ms), max(ms)
            if m_min <= 0: return False
            if (m_max - m_min) / m_min > cC: return False
            return _m_60_306(b, tL)
        if not _m_all(b120, c120, n): return False
        if len(b60) < 2: return False
        prev, last = b60[-2], b60[-1]
        if prev.ma60 is None or last.ma60 is None: return False
        if not (prev.close <= prev.ma60): return False
        if not (last.close > last.ma60): return False
        return True

    def type_d():
        tD, rD, wD = P["s1_tD"], P["s1_rD"], P["s1_wD"]
        t = 1.0 - tD
        def d120(b):
            if not _mp(b, "ma10", "ma20", "ma60", "ma306"): return False
            if b.ma10 < b.ma60 * t: return False
            if b.ma20 < b.ma60 * t: return False
            return _m_60_306(b, tL)
        if not _m_all(b120, d120, n): return False
        if _m_all(b60, lambda b: _m_4ma(b, tL), n): return True
        window = b60[-wD:] if b60 else []
        if not window: return False
        over = sum(1 for b in window if b.ma60 is not None and b.close > b.ma60)
        return over / len(window) >= rD

    def type_e():
        wE, rE, wSA = P["s1_wE"], P["s1_rE"], P["s1_wSA"]
        if not b120: return False
        if len(b60) < wE: return False
        b = b120[-1]
        if not _mp(b, "ma10", "ma20", "ma60", "ma306"): return False
        if not _m_60_306(b, P["s1_tE306"]): return False
        if not (b.close > b.ma60): return False
        sw = b120[-wSA:]
        at = 1.0 - P["s1_tSA"]
        aligned = sum(1 for x in sw if x.ma10 is not None and x.ma20 is not None and x.ma10 >= x.ma20 * at)
        if aligned == 0: return False
        ms = [b.ma10, b.ma20, b.ma60]
        m_min, m_max = min(ms), max(ms)
        if m_min <= 0: return False
        if (m_max - m_min) / m_min > P["s1_sE"]: return False
        window = b60[-wE:]
        over = sum(1 for x in window if x.ma60 is not None and x.close > x.ma60)
        return over / len(window) >= rE

    for lbl, fn in (("A", type_a), ("B", type_b), ("C", type_c), ("D", type_d), ("E", type_e)):
        if fn():
            return True, lbl
    return False, "제외"


def mirror_stage2(bars, P):
    n, tol = P["s2_n"], P["s2_t"]
    if not bars: return False
    if len(bars) < n: return False
    t = 1.0 - tol
    for b in bars[-n:]:
        if b.ma60 is None or b.ma306 is None or b.ma306 == 0: return False
        if b.ma60 < b.ma306 * t: return False
    return True


def mirror_stage21(bars, P):
    if not bars: return False
    if len(bars) < 2: return False
    last, prev = bars[-1], bars[-2]
    if prev.close <= 0: return False
    return (last.close - prev.close) / prev.close < P["s21_surge"]


def mirror_stage3(bars, P):
    n, k = P["s3_n"], P["s3_k"]
    if not bars: return False
    if len(bars) < n: return False
    t1 = 1.0 - P["s3_t"]
    lo_t, up_t = 1.0 - P["s3_lo"], 1.0 + P["s3_up"]

    def aligned(b):
        if b.ma10 is None or b.ma20 is None or b.ma60 is None or b.ma306 is None: return False
        if b.ma20 == 0 or b.ma60 == 0 or b.ma306 == 0: return False
        if b.ma10 < b.ma20 * t1: return False
        if b.ma20 < b.ma60 * t1: return False
        lo, hi = b.ma306 * lo_t, b.ma306 * up_t
        return lo <= b.ma60 <= hi

    if sum(1 for b in bars[-n:] if aligned(b)) < k: return False
    if len(bars) < 2: return False
    last, prev = bars[-1], bars[-2]
    if not (last.close > prev.close): return False
    if last.ma612 is None or last.ma612 == 0:
        if last.ma306 is None or last.ma306 == 0: return False
        return last.close > last.ma306
    pct = (last.close - last.ma612) / last.ma612
    return not (pct < P["s3_c612lo"] or pct > P["s3_c612up"])


def mirror_stage4(bars, P):
    if len(bars) < P["s4_n"]: return False
    rev = list(reversed(bars))

    def lead(pred):
        c = 0
        for b in rev:
            if pred(b): c += 1
            else: break
        return c

    fc = lead(lambda b: b.foreign < 0)
    ic = lead(lambda b: b.inst < 0)
    pc = lead(lambda b: b.indi >= 0)
    ft = sum(1 for b in bars if b.foreign < 0)
    if fc >= P["s4_fc"]: return False
    if ic >= P["s4_ic"]: return False
    if pc >= P["s4_pc"]: return False
    if ft >= P["s4_ft"]: return False
    return True


def mirror_stage5(cup_nga):
    return not (cup_nga is not None and cup_nga < 0)


# ═══════════════════════════════════════════════════════════════════
# 리포팅용 임계값(마진) — 라벨 인스턴스 전용 (판정에는 미사용·보고 전용)
# ═══════════════════════════════════════════════════════════════════

def _crit_ratio(upper, lower):
    """upper ≥ lower×(1−t) 의 임계 t* = 1 − upper/lower (lower>0 가정)."""
    if upper is None or lower is None or lower <= 0:
        return None  # 구조적 불가(결측)
    return 1.0 - upper / lower


def label_margins(b60, b120, b240, bD, inv, cup, P):
    """라벨 인스턴스의 스테이지·조건별 임계값(현행 윈도우 기준·보고용)."""
    n = P["s1_n"]
    out = {}

    def win_max(bars, f):
        if len(bars) < n: return None
        vals = [f(b) for b in bars[-n:]]
        if any(v is None for v in vals): return None
        return max(vals)

    # Type A: t* = max over both windows of 3쌍 임계
    def a_bar(b):
        cs = [_crit_ratio(b.ma10, b.ma20), _crit_ratio(b.ma20, b.ma60), _crit_ratio(b.ma60, b.ma306)]
        return None if any(c is None for c in cs) else max(cs)
    a120, a60 = win_max(b120, a_bar), win_max(b60, a_bar)
    out["A_tol_star"] = None if (a120 is None or a60 is None) else max(a120, a60)

    # Type C: 수렴폭 임계 + 골든크로스 구조 플래그
    def spread(b):
        if not _mp(b, "ma10", "ma20", "ma60", "ma306"): return None
        ms = [b.ma10, b.ma20, b.ma60]
        if min(ms) <= 0: return None
        return (max(ms) - min(ms)) / min(ms)
    out["C_spread_star"] = win_max(b120, spread)
    cross = (len(b60) >= 2 and b60[-2].ma60 is not None and b60[-1].ma60 is not None
             and b60[-2].close <= b60[-2].ma60 and b60[-1].close > b60[-1].ma60)
    out["C_cross_ok"] = bool(cross)

    # Type D: 엉킴 임계 + 60분 보조비율
    def d_bar(b):
        cs = [_crit_ratio(b.ma10, b.ma60), _crit_ratio(b.ma20, b.ma60)]
        return None if any(c is None for c in cs) else max(cs)
    out["D_tol_star"] = win_max(b120, d_bar)
    wD = P["s1_wD"]
    w = b60[-wD:] if b60 else []
    out["D_ratio"] = (sum(1 for b in w if b.ma60 is not None and b.close > b.ma60) / len(w)) if w else None

    # Type E (최근봉)
    if b120:
        b = b120[-1]
        out["E_t306_star"] = _crit_ratio(b.ma60, b.ma306)
        out["E_spread_star"] = spread(b)
        out["E_close_gt_ma60"] = bool(b.ma60 is not None and b.close > b.ma60)
        sw = b120[-P["s1_wSA"]:]
        cs = [_crit_ratio(x.ma10, x.ma20) for x in sw]
        cs = [c for c in cs if c is not None]
        out["E_tSA_star"] = min(cs) if cs else None
        wE = P["s1_wE"]
        if len(b60) >= wE:
            we = b60[-wE:]
            out["E_ratio60"] = sum(1 for x in we if x.ma60 is not None and x.close > x.ma60) / len(we)
        else:
            out["E_ratio60"] = None

    # Stage 2
    if len(b240) >= P["s2_n"]:
        cs = [_crit_ratio(b.ma60, b.ma306) for b in b240[-P["s2_n"]:]]
        out["S2_t_star"] = None if any(c is None for c in cs) else max(cs)
    else:
        out["S2_t_star"] = None

    # Stage 2-1 / 3 / 4
    if len(bD) >= 2 and bD[-2].close > 0:
        out["S21_surge"] = (bD[-1].close - bD[-2].close) / bD[-2].close
    if len(bD) >= P["s3_n"]:
        trip = []
        for b in bD[-P["s3_n"]:]:
            trip.append({
                "t3_star": None if (_crit_ratio(b.ma10, b.ma20) is None or _crit_ratio(b.ma20, b.ma60) is None)
                           else max(_crit_ratio(b.ma10, b.ma20), _crit_ratio(b.ma20, b.ma60)),
                "lo_star": _crit_ratio(b.ma60, b.ma306),
                "up_star": (b.ma60 / b.ma306 - 1.0) if (b.ma60 and b.ma306) else None,
            })
        out["S3_bars"] = trip
        last, prev = bD[-1], bD[-2]
        out["S3_bullish"] = bool(last.close > prev.close)
        if last.ma612 not in (None, 0):
            out["S3_c612_pct"] = (last.close - last.ma612) / last.ma612
        else:
            out["S3_ma612_missing_fb_ok"] = bool(last.ma306 not in (None, 0) and last.close > last.ma306)
    if inv:
        rev = list(reversed(inv))
        def lead(pred):
            c = 0
            for b in rev:
                if pred(b): c += 1
                else: break
            return c
        out["S4"] = {
            "bar_count": len(inv),
            "foreign_consec_sell": lead(lambda b: b.foreign < 0),
            "inst_consec_sell": lead(lambda b: b.inst < 0),
            "indi_consec_buy": lead(lambda b: b.indi >= 0),
            "foreign_total_sell": sum(1 for b in inv if b.foreign < 0),
        }
    out["S5_cup_nga"] = cup
    return out


# ═══════════════════════════════════════════════════════════════════
# 스트라텀 / 라벨 로딩
# ═══════════════════════════════════════════════════════════════════

def scan_strata():
    days = {}
    for d in sorted(REPORTS.iterdir()):
        if not (d.is_dir() and len(d.name) == 8 and d.name.isdigit()):
            continue
        mr = d / "masterReference.md"
        labels = [l for l in mr.read_text(encoding="utf-8").splitlines() if l.strip()] if mr.exists() else []
        org = d / "organizedCompany.md"
        orgn = len([l for l in org.read_text(encoding="utf-8").splitlines() if l.strip()]) if org.exists() else 0
        ndirs = len([x for x in d.iterdir() if x.is_dir()])
        if labels and orgn >= 90 and ndirs >= 90:
            s = "S2"       # 조인트(0608 유니버스91 포함 — master 목록에 +1 플래그)
        elif labels and ndirs == 0:
            s = "ORPHAN"   # 20260112 — 데이터 0 측정불가
        elif labels:
            s = "S1"       # 픽-only 백필일
        elif orgn > 100:
            s = "S3"
        else:
            s = "SKIP"
        days[d.name] = {"stratum": s, "n_labels": len(labels), "orgn": orgn, "ndirs": ndirs}
    return days


def load_labels(day: str, folder_map: dict, union_map: dict):
    """(resolved [(name, code, folder|None)], unresolved [raw]) — 양포맷+2단 해석."""
    mr = REPORTS / day / "masterReference.md"
    resolved, unresolved = [], []
    code_to_folder = {c: f for (nm, (c, f)) in folder_map.items()}
    for raw in mr.read_text(encoding="utf-8").splitlines():
        raw = raw.strip()
        if not raw:
            continue
        nm, cd = _parse_entry(raw)
        if cd:  # 이름(코드) 포맷
            f = code_to_folder.get(cd)
            resolved.append((nm, cd, f))
            continue
        if nm in folder_map:  # 당일 폴더 정확 매치
            c, f = folder_map[nm]
            resolved.append((nm, c, f))
            continue
        if nm in union_map:  # 디스크 유니언맵 (코드 확보·당일 폴더 재탐색)
            c = union_map[nm]
            resolved.append((nm, c, code_to_folder.get(c)))
            continue
        unresolved.append(raw)
    return resolved, unresolved


# ═══════════════════════════════════════════════════════════════════
# 일자 처리: 파싱 → npz + 오라클 등가검증 + P0 퍼널
# ═══════════════════════════════════════════════════════════════════

STATUS_CODE = {"ok": 0, "empty": 1, "error": 2, "skipped": 3}


def bars_to_arrays(bars, fields, nmax=16):
    """봉 리스트 → (nmax, len(fields)) float64, 우측정렬, 결측 NaN."""
    a = np.full((nmax, len(fields)), np.nan)
    for i, b in enumerate(bars[-nmax:]):
        for j, f in enumerate(fields):
            v = getattr(b, f)
            a[i + (nmax - min(len(bars), nmax)), j] = np.nan if v is None else float(v)
    return a


def process_day(day: str, meta: dict, union_map: dict, audit_pool: list):
    ddir = REPORTS / day

    folder_map = {}
    for x in ddir.iterdir():
        if x.is_dir():
            p = _split_stock_dirname(x.name)
            if p:
                folder_map[p[0]] = (p[1], x.name)

    # facade 미러: organizedCompany 순회 + name→code + manifest 게이팅
    org_names = [l.strip() for l in (ddir / "organizedCompany.md").read_text(encoding="utf-8").splitlines() if l.strip()]
    name_to_code = build_name_to_code_map(ddir)
    if not name_to_code:
        # 백필일: condition/upper.md 부재 — 프로덕션은 filter_today(code_map=명시주입)
        # 이었으므로 폴더맵으로 동등 복원(공식명==폴더명, expert flow 라벨기입 규약).
        name_to_code = {nm: c for nm, (c, _f) in folder_map.items()}

    manifest_synthetic = False
    mpath = ddir / "prefetchManifest.json"
    if mpath.exists():
        by_stock = json.load(open(mpath))["by_stock"]
    else:
        # 구파이프라인 일자(예 20260514): manifest 부재 → 파일존재 기반 합성 게이팅.
        manifest_synthetic = True
        by_stock = {}
        for nm, (c, fdir) in folder_map.items():
            fp = ddir / fdir
            by_stock[c] = {
                "chart60": "ok" if (fp / "chart60.md").exists() else "missing",
                "chart120": "ok" if (fp / "chart120.md").exists() else "missing",
                "chart240": "ok" if (fp / "chart240.md").exists() else "missing",
                "chartDay": "ok" if (fp / "chartDay.md").exists() else "missing",
                "investor": "ok" if (fp / "investor.md").exists() else "missing",
                "finance": "ok" if (fp / "finance.md").exists() else "missing",
            }

    labels_resolved, labels_unresolved = ([], [])
    if meta["n_labels"]:
        labels_resolved, labels_unresolved = load_labels(day, folder_map, union_map)
    label_codes = {c for (_n, c, _f) in labels_resolved}

    rows = []            # per-instance record
    mismatches = []
    finance_policy = "skip_na" if meta["stratum"] in ("S1",) else "require"

    for nm in org_names:
        cd = name_to_code.get(nm, "")
        rec = {"day": day, "name": nm, "code": cd, "label": cd in label_codes,
               "skip": None, "funnel": None, "s1_type": None}
        if not cd:
            rec["skip"] = "code-map"
            rows.append(rec); continue
        st = by_stock.get(cd)
        if st is None:
            rec["skip"] = "manifest"
            rows.append(rec); continue
        folder = None
        for fnm, (fcd, fdir) in folder_map.items():
            if fcd == cd:
                folder = ddir / fdir; break
        if folder is None:
            rec["skip"] = "no-folder"
            rows.append(rec); continue

        # 파싱 (엔진 파서) — 실패는 facade 예외-스킵 미러
        try:
            b60, _ = parse_chart60_md(folder / "chart60.md") if (folder / "chart60.md").exists() else ([], {})
            b120, _ = parse_chart120_md(folder / "chart120.md") if (folder / "chart120.md").exists() else ([], {})
            b240, _ = parse_chart240_md(folder / "chart240.md") if (folder / "chart240.md").exists() else ([], {})
            bD, _ = parse_chartday_md(folder / "chartDay.md") if (folder / "chartDay.md").exists() else ([], {})
            inv, _ = parse_investor_md(folder / "investor.md") if (folder / "investor.md").exists() else ([], {})
        except (ValueError, FileNotFoundError) as e:
            rec["skip"] = f"parse:{type(e).__name__}"
            rows.append(rec); continue
        cup = None; fin_invalid = False
        if st.get("finance") == "ok" and (folder / "finance.md").exists():
            try:
                fin_invalid = _is_invalid_md(folder / "finance.md")
                cup, _ = parse_finance_md(folder / "finance.md")
            except (ValueError, FileNotFoundError):
                cup = None

        # ── 오라클 등가검증 (전 스테이지·퍼널 무관) ──
        stage_mirror = {}
        if b60 and b120:
            o_sel, o_cat, _r, _x = evaluate_chart60_120(b60, b120)
            m_sel, m_cat = mirror_stage1(b60, b120, P0)
            stage_mirror["s1"] = m_sel
            rec["s1_type"] = m_cat if m_sel else None
            if (o_sel, o_cat if o_sel else None) != (m_sel, m_cat if m_sel else None):
                mismatches.append((day, cd, "s1", o_sel, o_cat, m_sel, m_cat))
        if b240:
            o = evaluate_chart240(b240)[0]; m = mirror_stage2(b240, P0)
            stage_mirror["s2"] = m
            if o != m: mismatches.append((day, cd, "s2", o, m))
        if bD:
            o = evaluate_chartday_pre(bD)[0]; m = mirror_stage21(bD, P0)
            stage_mirror["s21"] = m
            if o != m: mismatches.append((day, cd, "s21", o, m))
            o = evaluate_chartday(bD)[0]; m = mirror_stage3(bD, P0)
            stage_mirror["s3"] = m
            if o != m: mismatches.append((day, cd, "s3", o, m))
        if inv:
            o = evaluate_investor(inv)[0]; m = mirror_stage4(inv, P0)
            stage_mirror["s4"] = m
            if o != m: mismatches.append((day, cd, "s4", o, m))
        o = evaluate_finance(cup, invalid=fin_invalid)[0]; m = mirror_stage5(cup)
        if o != m: mismatches.append((day, cd, "s5", o, m))

        # ── P0 퍼널 (facade 게이팅 미러: manifest status + 순차 break) ──
        funnel = []
        def gate(api):
            return st.get(api) == "ok"
        alive = True
        # S1
        if not (gate("chart60") and gate("chart120")):
            funnel.append(("s1", False, "datagap")); alive = False
        elif not (b60 and b120):
            funnel.append(("s1", False, "parse")); alive = False
        else:
            ok = stage_mirror.get("s1", False)
            funnel.append(("s1", ok, rec["s1_type"] or "")); alive = ok
        if alive:
            if not gate("chart240"): funnel.append(("s2", False, "datagap")); alive = False
            elif not b240: funnel.append(("s2", False, "parse")); alive = False
            else:
                ok = stage_mirror.get("s2", False); funnel.append(("s2", ok, "")); alive = ok
        if alive:
            if not gate("chartDay"): funnel.append(("s21", False, "datagap")); alive = False
            elif not bD: funnel.append(("s21", False, "parse")); alive = False
            else:
                ok = stage_mirror.get("s21", False); funnel.append(("s21", ok, "")); alive = ok
        if alive:
            ok = stage_mirror.get("s3", False); funnel.append(("s3", ok, "")); alive = ok
        if alive:
            if not gate("investor"): funnel.append(("s4", False, "datagap")); alive = False
            elif not inv: funnel.append(("s4", False, "parse")); alive = False
            else:
                ok = stage_mirror.get("s4", False); funnel.append(("s4", ok, "")); alive = ok
        if alive:
            if st.get("finance") != "ok":
                if finance_policy == "skip_na":
                    funnel.append(("s5", True, "N/A"))
                else:
                    funnel.append(("s5", False, "datagap")); alive = False
            else:
                ok = mirror_stage5(cup); funnel.append(("s5", ok, "")); alive = ok
        rec["funnel"] = funnel
        rec["passed"] = alive

        # 라벨 인스턴스: 마진 + npz 소스 + 감사풀
        if rec["label"]:
            rec["margins"] = label_margins(b60, b120, b240, bD, inv, cup, P0)
            audit_pool.append({
                "day": day, "code": cd, "name": nm,
                "folder": str(folder),
                "funnel": funnel, "s1_type": rec["s1_type"],
                "margins": rec["margins"],
            })
        rec["_arrays"] = {
            "c60": bars_to_arrays(b60, ["close", "ma10", "ma20", "ma60", "ma306"]),
            "c120": bars_to_arrays(b120, ["close", "ma10", "ma20", "ma60", "ma306"]),
            "c240": bars_to_arrays(b240, ["ma60", "ma306"]),
            "cD": bars_to_arrays(bD, ["close", "ma10", "ma20", "ma60", "ma306", "ma612"]),
            "inv": bars_to_arrays(inv, ["indi", "foreign", "inst"]) if inv else np.full((16, 3), np.nan),
            "nb": np.array([len(b60), len(b120), len(b240), len(bD), len(inv) if inv else 0]),
            "fin": np.array([np.nan if cup is None else float(cup)]),
            "gap": np.array([STATUS_CODE.get(st.get(k), 4) for k in
                             ("chart60", "chart120", "chart240", "chartDay", "investor", "finance")]),
        }
        rows.append(rec)

    # 유니버스 밖 라벨 — 정직 집계(라벨부재≠거부·측정불가 명시)
    seen_codes = {r["code"] for r in rows if r["code"]}
    for (lnm, lcd, _lf) in labels_resolved:
        if lcd and lcd not in seen_codes:
            rows.append({"day": day, "name": lnm, "code": lcd, "label": True,
                         "skip": "label-not-in-universe", "funnel": None,
                         "s1_type": None, "passed": False})

    # npz 저장
    keep = [r for r in rows if "_arrays" in r]
    if keep:
        PRIMS.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            PRIMS / f"{day}.npz",
            codes=np.array([r["code"] for r in keep]),
            names=np.array([r["name"] for r in keep]),
            label=np.array([r["label"] for r in keep]),
            **{f"{k}_{i}": r["_arrays"][k] for i, r in enumerate(keep) for k in r["_arrays"]},
        )
    for r in rows:
        r.pop("_arrays", None)
    return rows, mismatches, labels_unresolved, len(labels_resolved)


# ═══════════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", default=None, help="쉼표구분 파일럿 일자")
    ap.add_argument("--all", action="store_true")
    args = ap.parse_args()

    OUT.mkdir(parents=True, exist_ok=True)
    assert_p0_matches_live()
    print("P0 라이브 대조 OK (29 상수 일치)")

    strata = scan_strata()
    if args.days:
        targets = args.days.split(",")
    elif args.all:
        targets = [d for d, m in strata.items() if m["stratum"] in ("S1", "S2", "S3")]
    else:
        print("사용법: --days 20260702,20260703 또는 --all"); return 1

    union_map = build_disk_name_to_code_map([REPORTS, ENGINE / "reports_backfill"])

    all_rows, all_mismatch, unresolved_report = [], [], {}
    audit_pool = []
    for i, day in enumerate(sorted(targets), 1):
        meta = strata[day]
        rows, mm, unres, nres = process_day(day, meta, union_map, audit_pool)
        all_rows.extend(rows)
        all_mismatch.extend(mm)
        if unres:
            unresolved_report[day] = unres
        npass = sum(1 for r in rows if r.get("passed"))
        print(f"[{i}/{len(targets)}] {day} {meta['stratum']} inst={len(rows)} pass@P0={npass} "
              f"label={meta['n_labels']}(res={nres} unres={len(unres)}) mm={len(mm)}")

    # ── 산출 저장 ──
    json.dump(all_rows, open(OUT / "instances.json", "w"), ensure_ascii=False, default=str)
    json.dump(strata, open(OUT / "strata.json", "w"), ensure_ascii=False, indent=1)
    json.dump(unresolved_report, open(OUT / "labels_unresolved.json", "w"), ensure_ascii=False, indent=1)
    json.dump(audit_pool, open(OUT / "labels_audit_pool.json", "w"), ensure_ascii=False, default=str)

    # ── 오라클 판정 ──
    if all_mismatch:
        json.dump(all_mismatch, open(OUT / "ORACLE_MISMATCH.json", "w"), ensure_ascii=False, default=str)
        print(f"★★ 오라클 불일치 {len(all_mismatch)}건 — fail-loud (ORACLE_MISMATCH.json)")
        return 2
    print("오라클 등가검증: 전 인스턴스 × 전 스테이지 불일치 0 ✔")

    # ── 베이스라인 통계 ──
    stats = {"per_day": {}, "recall": {}, "death": {}}
    for day in sorted(set(r["day"] for r in all_rows)):
        drs = [r for r in all_rows if r["day"] == day]
        st = strata[day]["stratum"]
        f_counts = Counter()
        for r in drs:
            if r.get("funnel"):
                for sname, ok, _ in r["funnel"]:
                    if ok:
                        f_counts[sname] += 1
        stats["per_day"][day] = {
            "stratum": st, "n": len(drs),
            "pass": sum(1 for r in drs if r.get("passed")),
            "funnel": dict(f_counts),
            "skips": Counter(r["skip"] for r in drs if r["skip"]).most_common(),
        }
    for st_name in ("S1", "S2"):
        lab = [r for r in all_rows if r["label"] and strata[r["day"]]["stratum"] == st_name]
        death = Counter()
        n_pass_full = n_meas_full = 0
        n_s123_meas = n_s123_pass = 0
        n_oou = 0
        for r in lab:
            if r.get("skip") == "label-not-in-universe":
                n_oou += 1
                death["skip:label-not-in-universe"] += 1
                continue
            if r.get("skip"):
                death[f"skip:{r['skip']}"] += 1
                continue
            fun = r.get("funnel") or []
            fmap = {s: (ok, why) for s, ok, why in fun}
            # 차트게이트(S1·S2·S2-1·S3) 측정가능성: 그 구간 datagap/parse 없음
            chart_gap = any(
                (s in ("s1", "s2", "s21", "s3")) and (not ok) and why in ("datagap", "parse")
                for s, ok, why in fun
            )
            if not chart_gap:
                n_s123_meas += 1
                s3ok = fmap.get("s3", (False, ""))[0]
                if s3ok:
                    n_s123_pass += 1
            # 풀퍼널 측정가능성: 퍼널 어디에도 datagap/parse 없음
            full_gap = any((not ok) and why in ("datagap", "parse") for s, ok, why in fun)
            if not full_gap:
                n_meas_full += 1
                if r.get("passed"):
                    n_pass_full += 1
            if not r.get("passed"):
                last = fun[-1] if fun else ("?", False, "")
                death[f"{last[0]}{':' + last[2] if last[2] and not last[1] else ''}"] += 1
        stats["recall"][st_name] = {
            "n_label_rows": len(lab),
            "out_of_universe": n_oou,
            "full_funnel_measurable": n_meas_full, "full_funnel_pass": n_pass_full,
            "recall_full": (n_pass_full / n_meas_full) if n_meas_full else None,
            "chartgate_s1_s3_measurable": n_s123_meas, "chartgate_s1_s3_pass": n_s123_pass,
            "recall_chartgate": (n_s123_pass / n_s123_meas) if n_s123_meas else None,
        }
        stats["death"][st_name] = death.most_common()
    json.dump(stats, open(OUT / "baseline_stats.json", "w"), ensure_ascii=False, indent=1, default=str)

    # 무작위 5 인스턴스 상세 (master 독립 재검증용·결정론 시드)
    rng = random.Random(20260704)
    sample = rng.sample(audit_pool, min(5, len(audit_pool)))
    json.dump(sample, open(OUT / "audit_5_instances.json", "w"), ensure_ascii=False, indent=1, default=str)

    print("베이스라인 통계 저장 완료 → baseline_stats.json / audit_5_instances.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
