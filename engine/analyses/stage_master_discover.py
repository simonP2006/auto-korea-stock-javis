"""stage_master 필터 조건 도출용 분석 스크립트.

목표: positive set(masterReference.md)을 100% 통과시키면서 negative set
(organizedCompany.md - masterReference.md)을 최대한 제외하는 단일 통합
조건을 찾는다.

대상 기간: 20260518~20260522 (positive 36, negative ~5,015).
20260514/15 는 positive 종목의 chartDay/finance 데이터가 0% 커버되어 제외.

실행::

    python -m analyses.stage_master_discover
"""

from __future__ import annotations

import re
import statistics
from pathlib import Path
from typing import Final

REPORTS_ROOT: Final[Path] = Path("reports")
DATES: Final[list[str]] = [
    "20260518", "20260519", "20260520", "20260521", "20260522",
]

_NUM = re.compile(r"-?[\d,]+(?:\.\d+)?")
_DATA_ROW = re.compile(
    r"^\|\s*(\d{4}-\d{2}-\d{2})\s*\|"
    r"\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|\s*([\d,]+)\s*\|"
    r"\s*([\d,]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|"
    r"\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|\s*([\d,.\-—]+)\s*\|"
)


def _to_float(s: str) -> float | None:
    s = s.strip().replace(",", "")
    if s in ("", "—", "-"):
        return None
    try:
        return float(s)
    except ValueError:
        return None


def _to_int(s: str) -> int | None:
    s = s.strip().replace(",", "").replace("+", "")
    if s in ("", "—"):
        return None
    try:
        return int(s)
    except ValueError:
        return None


def parse_chartday(path: Path) -> dict | None:
    """chartDay.md → 마지막 봉 + 직전 봉 + ma 값 dict."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    bars = []
    for line in text.splitlines():
        m = _DATA_ROW.match(line)
        if not m:
            continue
        bars.append({
            "date": m.group(1),
            "open": _to_int(m.group(2)),
            "high": _to_int(m.group(3)),
            "low": _to_int(m.group(4)),
            "close": _to_int(m.group(5)),
            "volume": _to_int(m.group(6)),
            "ma10": _to_float(m.group(7)),
            "ma20": _to_float(m.group(8)),
            "ma60": _to_float(m.group(9)),
            "ma306": _to_float(m.group(10)),
            "ma612": _to_float(m.group(11)),
        })
    if len(bars) < 2:
        return None
    last = bars[-1]
    prev = bars[-2]
    return {"bars": bars, "last": last, "prev": prev}


def parse_finance(path: Path) -> dict | None:
    """finance.md → per/eps/roe/pbr/순이익 dict."""
    try:
        text = path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return None
    out: dict = {}
    for line in text.splitlines():
        # |지표 | 값|
        m = re.match(r"\|\s*([^|]+?)\s*\|\s*([^|]+?)\s*\|\s*$", line)
        if not m:
            continue
        k = m.group(1).strip()
        v = _to_float(m.group(2))
        if v is None:
            continue
        if k == "PER":
            out["per"] = v
        elif k == "EPS":
            out["eps"] = v
        elif k == "ROE":
            out["roe"] = v
        elif k == "PBR":
            out["pbr"] = v
        elif "당기순이익" in k:
            out["net_income"] = v  # 억원
    return out or None


def _stock_dir(date_dir: Path, name: str) -> Path | None:
    for p in date_dir.iterdir():
        if not p.is_dir():
            continue
        if p.name.startswith(name + "(") and p.name.endswith(")"):
            return p
    return None


def features(date: str, name: str) -> dict | None:
    """한 종목·한 날짜의 피처 벡터."""
    date_dir = REPORTS_ROOT / date
    sd = _stock_dir(date_dir, name)
    if sd is None:
        return None
    cd = parse_chartday(sd / "chartDay.md")
    fn = parse_finance(sd / "finance.md")
    if cd is None:
        return None
    last = cd["last"]
    prev = cd["prev"]
    if not all([last["close"], prev["close"], last["ma60"],
                last["ma10"], last["ma20"]]):
        return None
    # MA306/612 는 결측 가능 (신규 상장 종목) — 결측이면 파생 피처도 None.
    f = {
        "date": date,
        "name": name,
        "close": last["close"],
        "volume": last["volume"],
        "open": last["open"],
        "high": last["high"],
        "low": last["low"],
        "ma10": last["ma10"],
        "ma20": last["ma20"],
        "ma60": last["ma60"],
        "ma306": last["ma306"],
        "ma612": last["ma612"],
        "pct_today": (last["close"] - prev["close"]) / prev["close"] * 100,
        "bullish_today": last["close"] > last["open"],
        "close_over_ma60": (last["close"] / last["ma60"] - 1) * 100,
        "close_over_ma20": (last["close"] / last["ma20"] - 1) * 100,
        "close_over_ma10": (last["close"] / last["ma10"] - 1) * 100,
        "ma10_over_ma20": (last["ma10"] / last["ma20"] - 1) * 100,
        "ma20_over_ma60": (last["ma20"] / last["ma60"] - 1) * 100,
    }
    if last["ma306"]:
        f["close_over_ma306"] = (last["close"] / last["ma306"] - 1) * 100
        f["ma60_over_ma306"] = (last["ma60"] / last["ma306"] - 1) * 100
    if last["ma612"]:
        f["close_over_ma612"] = (last["close"] / last["ma612"] - 1) * 100
        f["ma60_over_ma612"] = (last["ma60"] / last["ma612"] - 1) * 100
    # 5일 등락률
    if len(cd["bars"]) >= 6:
        bar5 = cd["bars"][-6]
        if bar5["close"]:
            f["pct_5day"] = (last["close"] - bar5["close"]) / bar5["close"] * 100
    # 평균 거래량 (직전 5일)
    if len(cd["bars"]) >= 6 and last["volume"]:
        recent_vols = [b["volume"] for b in cd["bars"][-6:-1] if b["volume"]]
        if recent_vols:
            avg5 = sum(recent_vols) / len(recent_vols)
            if avg5 > 0:
                f["vol_ratio_5d"] = last["volume"] / avg5
    if fn:
        f.update(fn)
    return f


def read_lines(p: Path) -> list[str]:
    if not p.exists():
        return []
    return [ln.strip() for ln in p.read_text(encoding="utf-8").splitlines()
            if ln.strip()]


def collect_samples() -> tuple[list[dict], list[dict]]:
    """5일치 positive/negative 피처 벡터 수집."""
    pos_set: set[tuple[str, str]] = set()
    pos_list: list[dict] = []
    neg_list: list[dict] = []
    for d in DATES:
        master_names = read_lines(REPORTS_ROOT / d / "masterReference.md")
        org_names = read_lines(REPORTS_ROOT / d / "organizedCompany.md")
        for n in master_names:
            pos_set.add((d, n))
            f = features(d, n)
            if f:
                f["is_positive"] = True
                pos_list.append(f)
        for n in org_names:
            if (d, n) in pos_set:
                continue
            f = features(d, n)
            if f:
                f["is_positive"] = False
                neg_list.append(f)
    return pos_list, neg_list


def stat_summary(vals: list[float]) -> dict:
    vals = [v for v in vals if v is not None]
    if not vals:
        return {}
    vals_sorted = sorted(vals)
    n = len(vals_sorted)
    def pct(p):
        i = int(p * (n - 1))
        return vals_sorted[i]
    return {
        "n": n,
        "min": vals_sorted[0],
        "p10": pct(0.10),
        "p25": pct(0.25),
        "p50": pct(0.50),
        "p75": pct(0.75),
        "p90": pct(0.90),
        "max": vals_sorted[-1],
        "mean": statistics.mean(vals),
    }


def print_table(features_keys: list[str], pos: list[dict], neg: list[dict]) -> None:
    print(f"{'feature':28s} {'pos_n':>5} {'pos_min':>10} {'pos_max':>10} "
          f"{'neg_n':>6} {'neg_p25':>10} {'neg_p75':>10} "
          f"{'pos_in_neg_range?':>20}")
    print("-" * 110)
    for k in features_keys:
        ps = [r[k] for r in pos if k in r and r[k] is not None]
        ns = [r[k] for r in neg if k in r and r[k] is not None]
        pst = stat_summary(ps)
        nst = stat_summary(ns)
        if not pst or not nst:
            print(f"{k:28s} (n/a)")
            continue
        # 만약 positive의 [min,max] 가 negative 의 [p25,p75] 안에 들어있다면 변별력 낮음
        narrow = (
            nst['p25'] <= pst['min'] and pst['max'] <= nst['p75']
        )
        flag = "(narrow)" if narrow else ""
        print(f"{k:28s} {pst['n']:>5} {pst['min']:>10.2f} {pst['max']:>10.2f} "
              f"{nst['n']:>6} {nst['p25']:>10.2f} {nst['p75']:>10.2f}  {flag}")


def evaluate_threshold(
    pos: list[dict], neg: list[dict], key: str,
    *, op: str, threshold: float,
) -> tuple[int, int]:
    """단일 임계값 조건의 (positive 통과수, negative 통과수)."""
    def check(v):
        if v is None:
            return False
        if op == ">=":
            return v >= threshold
        if op == "<=":
            return v <= threshold
        if op == ">":
            return v > threshold
        if op == "<":
            return v < threshold
        return False
    pp = sum(1 for r in pos if check(r.get(key)))
    nn = sum(1 for r in neg if check(r.get(key)))
    return pp, nn


def _band(records: list[dict], key: str, lo: float, hi: float) -> list[dict]:
    out = []
    for r in records:
        v = r.get(key)
        if v is None:
            continue
        if lo <= v <= hi:
            out.append(r)
    return out


def find_best_range(
    pos: list[dict], neg: list[dict], key: str,
) -> tuple[float, float, int, int] | None:
    """positive [min, max] band 적용 시 (lo, hi, pos_pass, neg_pass).

    positive 결측은 허용하지 않음 (전 종목 통과 보장). 단 negative 결측은
    조건 미충족(탈락) 처리 — 결측을 무조건 통과로 두면 selectivity 가 떨어진다.
    """
    ps = [r[key] for r in pos if key in r and r[key] is not None]
    if not ps or len(ps) < len(pos):
        # positive 결측이 하나라도 있으면 이 feature 는 강제 조건으로 못 씀
        return None
    lo, hi = min(ps), max(ps)
    ns = [r[key] for r in neg if key in r and r[key] is not None]
    neg_pass = sum(1 for v in ns if lo <= v <= hi)
    return (lo, hi, len(ps), neg_pass)


def evaluate_combo(
    pos: list[dict], neg: list[dict],
    conds: list[tuple[str, float, float]],
) -> tuple[int, int]:
    def check(r):
        for k, lo, hi in conds:
            v = r.get(k)
            if v is None:
                return False
            if not (lo <= v <= hi):
                return False
        return True
    return sum(1 for r in pos if check(r)), sum(1 for r in neg if check(r))


def main() -> int:
    pos, neg = collect_samples()
    print(f"positive samples: {len(pos)} / negative samples: {len(neg)}")
    print()
    keys = [
        "close", "pct_today", "pct_5day", "vol_ratio_5d",
        "close_over_ma612", "close_over_ma306", "close_over_ma60",
        "close_over_ma20", "close_over_ma10",
        "ma60_over_ma306", "ma60_over_ma612", "ma10_over_ma20", "ma20_over_ma60",
        "eps", "roe", "pbr", "net_income",
    ]

    print("=== 단일 [min, max] band 조건 통과율 ===")
    print(f"{'feature':24s}  {'lo':>10}  {'hi':>10}  {'pos':>5}  "
          f"{'neg_pass':>9}  {'neg_rate':>8}")
    print("-" * 80)
    single = []
    for k in keys:
        r = find_best_range(pos, neg, k)
        if r is None:
            continue
        lo, hi, pp, nn = r
        rate = nn / len(neg) * 100
        single.append((k, lo, hi, pp, nn, rate))
    single.sort(key=lambda x: x[4])  # neg_pass 오름차순
    for k, lo, hi, pp, nn, rate in single:
        print(f"{k:24s}  {lo:>10.2f}  {hi:>10.2f}  {pp:>5}  {nn:>9}  {rate:>7.1f}%")

    print()
    print("=== top-3 features AND 조합 ===")
    top = single[:7]
    # 모든 (2개, 3개) 조합
    from itertools import combinations
    for size in (2, 3, 4, 5):
        results = []
        for combo in combinations(top, size):
            conds = [(c[0], c[1], c[2]) for c in combo]
            pp, nn = evaluate_combo(pos, neg, conds)
            if pp != len(pos):
                continue  # positive 손실 안 됨 보장
            results.append((conds, pp, nn))
        results.sort(key=lambda x: x[2])
        print(f"\n  {size}개 조합 top3 (positive 100% 유지):")
        for conds, pp, nn in results[:3]:
            rate = nn / len(neg) * 100
            cond_str = " AND ".join(
                f"{lo:.2f}≤{k}≤{hi:.2f}" for k, lo, hi in conds
            )
            print(f"    pos {pp}/{len(pos)}  neg {nn}/{len(neg)} ({rate:.1f}%)  "
                  f"| {cond_str}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
