"""Phase B-2 옵티마이저 — 브리프 v1.1 §4.5 (A)(B)(C)(D')(E)(G)(H) 준수.

- 평가기: prims npz → per-instance 임계 프리컴퓨트(윈도우 후보별) → 임의 파라미터
  벡터 O(1) 평가. S3 등 다중상수 per-bar conjunction 은 **per-bar joint**(v1.1-B).
- 검증: P0 에서 instances.json 퍼널 pass 와 전 인스턴스 정확 일치(등가검증).
- 분할(v1.1-A): S1 라벨일 앞70/뒤30 · S2(0514·0515 제외) 앞8/뒤5일 · S3 앞14/뒤7일.
- 목적: maximize TRAIN(S1+S2) recall s.t. TRAIN-guard 중앙값 ≤ 캡{30,45,60,90}
  · range-map 물리범위+danger zone 하드 · 변경수 최소(lexicographic)→최소이탈.
- (G) pick-precision 미사용. (E) Type B 상수 동결. (H) 윈도우 하한 1 하드 + s5 가드.
- HOLDOUT 은 캡별 확정 후보에 1회만 평가(재선택 금지) · 갭 보고.
"""
from __future__ import annotations

import itertools
import json
import statistics
import sys
from pathlib import Path

import numpy as np

ENGINE = Path("/Users/tajun/spJavis/auto-korea-stock-javis/engine")
sys.path.insert(0, str(ENGINE))
OUT = ENGINE / "analyses/phase_b/out"
PRIMS = OUT / "prims"

EXCLUDE_DAYS = {"20260514", "20260515"}  # v1.1 (C)(D')

P0 = dict(s1_n=8, s1_tL=0.015, s1_tA=0.035, s1_cC=0.035, s1_tD=0.020, s1_rD=0.50,
          s1_wD=16, s1_sE=0.10, s1_wE=8, s1_rE=0.75, s1_wSA=2, s1_tSA=0.016,
          s1_tE306=0.035, s2_t=0.025, s2_n=3, s21_surge=0.15, s3_t=0.05, s3_lo=0.15,
          s3_up=0.45, s3_c612lo=-0.15, s3_c612up=0.50, s3_n=3, s3_k=2,
          s4_n=16, s4_fc=2, s4_ic=8, s4_pc=3, s4_ft=15)

# range-map 준수 그리드(현행값 포함·danger zone 배제·완화 방향 위주). (E) rB 동결.
GRID = {
    "s1_tA":  [0.035, 0.045, 0.055, 0.065, 0.075, 0.09, 0.11, 0.14, 0.20, 0.29],
    "s1_tL":  [0.015, 0.02, 0.025, 0.03, 0.04, 0.05, 0.07, 0.10, 0.14],
    "s1_cC":  [0.035, 0.05, 0.06, 0.08, 0.099],
    "s1_tD":  [0.02, 0.03, 0.04, 0.06, 0.08, 0.10, 0.14],
    "s1_rD":  [0.50, 0.45, 0.40, 0.35, 0.30, 0.25],
    "s1_wD":  [16, 12, 8, 6, 4],
    "s1_sE":  [0.10, 0.12, 0.15, 0.19],
    "s1_wE":  [8, 6, 4],
    "s1_rE":  [0.75, 0.65, 0.55, 0.45, 0.35],
    "s1_wSA": [2, 3, 4],
    "s1_tSA": [0.016, 0.03, 0.05, 0.08],
    "s1_tE306": [0.035, 0.05, 0.07, 0.10, 0.14],
    "s1_n":   [8, 7, 6, 5, 4, 3],
    "s2_t":   [0.025, 0.035, 0.05, 0.06, 0.07, 0.079],
    "s2_n":   [3, 2],
    "s21_surge": [0.15, 0.20, 0.25, 0.29],
    "s3_t":   [0.05, 0.07, 0.09, 0.12, 0.14],
    "s3_lo":  [0.15, 0.20, 0.25, 0.30, 0.39],
    "s3_up":  [0.45, 0.60, 0.80, 1.0, 1.2, 1.49],
    "s3_c612lo": [-0.15, -0.20, -0.25, -0.30, -0.39],
    "s3_c612up": [0.50, 0.65, 0.80, 1.0, 1.2, 1.49],
    "s3_n":   [3, 4, 2],
    "s3_k":   [2, 1],
    "s4_n":   [16, 12, 8],
    "s4_fc":  [2, 3, 4, 5],
    "s4_ic":  [8, 10, 12, 13],
    "s4_pc":  [3, 4, 5, 6],
    # s4_ft: danger ≥16 → 완화방향 없음 = 동결
}
N_RANGE = list(range(3, 14))          # s1_n 물리 3~13 (danger ≥14)
W_RANGE = list(range(4, 17))          # wD/wE 4~16
WSA_RANGE = list(range(1, 8))         # 1~7
S2N_RANGE = [2, 3, 4, 5]
S3N_MAX = 7


def _crit(u, l):
    """upper ≥ lower×(1−t) 임계 t*: NaN 전파. l<=0 → +inf(불가)."""
    with np.errstate(invalid="ignore", divide="ignore"):
        out = 1.0 - u / l
    out = np.where(np.isnan(u) | np.isnan(l) | (l <= 0), np.inf, out)
    return out


class Day:
    """일자별 프리컴퓨트 임계 테이블."""

    def __init__(self, day: str, stratum: str):
        self.day, self.stratum = day, stratum
        z = np.load(PRIMS / f"{day}.npz", allow_pickle=True)
        codes = list(z["codes"])
        n = len(codes)
        self.codes = codes
        self.label = np.array(z["label"], dtype=bool)
        # stack instance arrays
        g = lambda k, i: z[f"{k}_{i}"]
        c60 = np.stack([g("c60", i) for i in range(n)])    # (n,16,5) close,ma10,20,60,306
        c120 = np.stack([g("c120", i) for i in range(n)])
        c240 = np.stack([g("c240", i) for i in range(n)])  # (n,16,2) ma60,ma306
        cD = np.stack([g("cD", i) for i in range(n)])      # (n,16,6) close,ma10,20,60,306,612
        inv = np.stack([g("inv", i) for i in range(n)])    # (n,16,3) indi,foreign,inst
        self.nb = np.stack([g("nb", i) for i in range(n)]).astype(int)   # n60,n120,n240,nD,ninv
        self.fin = np.stack([g("fin", i) for i in range(n)])[:, 0]
        self.gap = np.stack([g("gap", i) for i in range(n)]).astype(int)  # 6 API status codes

        def mp4(c):  # _ma_present(4) 미러: ma10/20/60/306 존재 & ma306≠0
            m = c[:, :, 1:5]
            return (~np.isnan(m).any(axis=2)) & (c[:, :, 4] != 0)

        def wmax(per_bar, avail, rng):
            """per_bar (n,16) → {w: 윈도우 max over last w} · avail<w → inf."""
            out = {}
            for w in rng:
                v = per_bar[:, 16 - w:].max(axis=1)
                out[w] = np.where(avail >= w, v, np.inf)
            return out

        # ── S1 임계 (per n) ──
        n60, n120 = self.nb[:, 0], self.nb[:, 1]
        avail = np.minimum(n60, n120)
        for c, tag in ((c60, "60"), (c120, "120")):
            ok4 = mp4(c)
            a = np.maximum.reduce([_crit(c[:, :, 1], c[:, :, 2]),
                                   _crit(c[:, :, 2], c[:, :, 3]),
                                   _crit(c[:, :, 3], c[:, :, 4])])
            setattr(self, f"a4_{tag}", np.where(ok4, a, np.inf))          # 4MA 정렬 임계
            setattr(self, f"t306_{tag}", np.where(ok4, _crit(c[:, :, 3], c[:, :, 4]), np.inf))
        # Type A: max(both charts) per n — 양 차트 각자 avail 게이트
        self.A = {}
        a60w = wmax(self.a4_60, n60, N_RANGE); a120w = wmax(self.a4_120, n120, N_RANGE)
        for nn in N_RANGE:
            self.A[nn] = np.maximum(a60w[nn], a120w[nn])
        # Type B (rB=0.97 동결): 120 구조(≤조건)+tL임계 / 60 up3+306
        okB = mp4(c120) & (c120[:, :, 1] <= c120[:, :, 3] * 0.97) & (c120[:, :, 2] <= c120[:, :, 3] * 0.97)
        b120_t = np.where(okB, np.maximum(_crit(c120[:, :, 1], c120[:, :, 2]),
                                          _crit(c120[:, :, 3], c120[:, :, 4])), np.inf)
        ok3_60 = ~np.isnan(c60[:, :, 1:4]).any(axis=2)
        b60_t = np.where(ok3_60 & mp4(c60),
                         np.maximum.reduce([_crit(c60[:, :, 1], c60[:, :, 2]),
                                            _crit(c60[:, :, 2], c60[:, :, 3]),
                                            _crit(c60[:, :, 3], c60[:, :, 4])]), np.inf)
        bw120 = wmax(b120_t, n120, N_RANGE); bw60 = wmax(b60_t, n60, N_RANGE)
        self.B = {nn: np.maximum(bw120[nn], bw60[nn]) for nn in N_RANGE}
        # Type C: spread 임계(120)+t306(120), cross 구조(60 last2)
        ms = c120[:, :, 1:4]
        mmin, mmax = np.nanmin(ms, axis=2), np.nanmax(ms, axis=2)
        with np.errstate(invalid="ignore", divide="ignore"):
            spread = (mmax - mmin) / mmin
        sp = np.where(mp4(c120) & (mmin > 0), spread, np.inf)
        spw = wmax(sp, n120, N_RANGE); t306w = wmax(self.t306_120, n120, N_RANGE)
        self.C_sp, self.C_t306 = spw, t306w
        pc, lc = c60[:, -2, :], c60[:, -1, :]
        self.C_cross = ((n60 >= 2) & ~np.isnan(pc[:, 3]) & ~np.isnan(lc[:, 3])
                        & (pc[:, 0] <= pc[:, 3]) & (lc[:, 0] > lc[:, 3]))
        # Type D: tD임계(120)+t306(120) / (a)60 4MA tL임계 (b)ratio(wD)
        okD = mp4(c120)
        d_t = np.where(okD, np.maximum(_crit(c120[:, :, 1], c120[:, :, 3]),
                                       _crit(c120[:, :, 2], c120[:, :, 3])), np.inf)
        self.D_t = wmax(d_t, n120, N_RANGE)
        self.D_t306 = t306w
        self.Da_tL = {nn: wmax(self.a4_60, n60, N_RANGE)[nn] for nn in N_RANGE}
        cgt60 = (~np.isnan(c60[:, :, 3])) & (c60[:, :, 0] > c60[:, :, 3])
        self.Db_ratio = {}
        for w in W_RANGE:
            win = cgt60[:, 16 - w:]
            cnt = np.where(np.arange(16)[16 - w:] >= (16 - n60[:, None]), win, False).sum(axis=1)
            eff = np.minimum(n60, w)
            with np.errstate(invalid="ignore", divide="ignore"):
                r = cnt / eff
            self.Db_ratio[w] = np.where(eff > 0, r, -np.inf)   # 빈 윈도우=실패
        # Type E
        lb = c120[:, -1, :]
        okE = (n120 >= 1) & ~np.isnan(lb[:, 1:5]).any(axis=1) & (lb[:, 4] != 0)
        self.E_t306 = np.where(okE, _crit(lb[:, 3:4], lb[:, 4:5])[:, 0], np.inf)
        with np.errstate(invalid="ignore", divide="ignore"):
            e_mmin = np.nanmin(lb[:, 1:4], axis=1); e_mmax = np.nanmax(lb[:, 1:4], axis=1)
            e_sp = (e_mmax - e_mmin) / e_mmin
        self.E_sp = np.where(okE & (e_mmin > 0), e_sp, np.inf)
        self.E_cgt = okE & (lb[:, 0] > lb[:, 3])
        tSA_bar = _crit(c120[:, :, 1], c120[:, :, 2])   # NaN→inf by _crit? ma20<=0→inf; NaN→inf
        tSA_bar = np.where(np.isnan(c120[:, :, 1]) | np.isnan(c120[:, :, 2]), np.inf, tSA_bar)
        self.E_tSA = {}
        for w in WSA_RANGE:
            v = tSA_bar[:, 16 - w:].min(axis=1)
            self.E_tSA[w] = np.where(n120 >= 1, v, np.inf)  # 엔진: 슬라이스는 avail로 자동 축소
        self.E_r60 = {}
        for w in W_RANGE:
            self.E_r60[w] = np.where(n60 >= w, self.Db_ratio[w], -np.inf)  # len<wE → fail
        self.n60, self.n120 = n60, n120
        # ── S2 ──
        m60, m306 = c240[:, :, 0], c240[:, :, 1]
        s2c = np.where(np.isnan(m60) | np.isnan(m306) | (m306 == 0), np.inf, _crit(m60, m306))
        self.S2 = {}
        for nn in S2N_RANGE:
            v = s2c[:, 16 - nn:].max(axis=1)
            self.S2[nn] = np.where(self.nb[:, 2] >= nn, v, np.inf)
        # ── S2-1 ──
        cl = cD[:, :, 0]
        prev, last = cl[:, -2], cl[:, -1]
        with np.errstate(invalid="ignore", divide="ignore"):
            surge = (last - prev) / prev
        self.S21 = np.where((self.nb[:, 3] >= 2) & (prev > 0), surge, np.inf)  # inf=구조탈락
        # ── S3 per-bar joint (마지막 7봉) ──
        okA = ~np.isnan(cD[:, :, 1:5]).any(axis=2) & (cD[:, :, 2] != 0) & (cD[:, :, 3] != 0) & (cD[:, :, 4] != 0)
        t3b = np.where(okA, np.maximum(_crit(cD[:, :, 1], cD[:, :, 2]),
                                       _crit(cD[:, :, 2], cD[:, :, 3])), np.inf)
        with np.errstate(invalid="ignore", divide="ignore"):
            lo_b = 1.0 - cD[:, :, 3] / cD[:, :, 4]
            up_b = cD[:, :, 3] / cD[:, :, 4] - 1.0
        lo_b = np.where(okA, lo_b, np.inf); up_b = np.where(okA, up_b, np.inf)
        self.S3_t, self.S3_lo, self.S3_up = t3b[:, -S3N_MAX:], lo_b[:, -S3N_MAX:], up_b[:, -S3N_MAX:]
        self.S3_bull = (self.nb[:, 3] >= 2) & (last > prev)
        m612, m306d = cD[:, -1, 5], cD[:, -1, 4]
        has612 = ~np.isnan(m612) & (m612 != 0)
        with np.errstate(invalid="ignore", divide="ignore"):
            pct = (last - m612) / m612
        self.S3_has612, self.S3_pct = has612, pct
        self.S3_fb = (~has612) & ~np.isnan(m306d) & (m306d != 0) & (last > m306d)
        self.S3_nD = self.nb[:, 3]
        # ── S4 ──
        ninv = self.nb[:, 4]
        idx16 = np.arange(16)
        valid = idx16[None, :] >= (16 - ninv[:, None])
        f_neg = np.where(valid, inv[:, :, 1] < 0, False)
        i_neg = np.where(valid, inv[:, :, 2] < 0, False)
        p_pos = np.where(valid, inv[:, :, 0] >= 0, False)
        def lead(m):
            # 최근(오른쪽)부터 연속 True — reversed cumprod
            rev = m[:, ::-1]
            return np.cumprod(rev, axis=1).sum(axis=1)
        # 주의: valid 밖(False)이 run 을 끊음 — 엔진은 avail 봉만 보므로 등가
        self.S4_fc, self.S4_ic, self.S4_pc = lead(f_neg), lead(i_neg), lead(p_pos)
        self.S4_ft = f_neg.sum(axis=1)
        self.S4_nb = ninv
        # ── S5/게이팅 ──
        self.fin_ok = self.gap[:, 5] == 0
        self.skip_na = stratum == "S1"
        self.g60 = (self.gap[:, 0] == 0) & (self.gap[:, 1] == 0) & (n60 > 0) & (n120 > 0)
        self.g240 = (self.gap[:, 2] == 0) & (self.nb[:, 2] > 0)
        self.gD = (self.gap[:, 3] == 0) & (self.nb[:, 3] > 0)
        self.gInv = (self.gap[:, 4] == 0) & (ninv > 0)

    def eval(self, P):
        """파라미터 벡터 → (pass bool 배열)."""
        nn = P["s1_n"]
        s1 = self.A[nn] <= P["s1_tA"]
        s1 |= self.B[nn] <= P["s1_tL"]
        s1 |= self.C_cross & (self.C_sp[nn] <= P["s1_cC"]) & (self.C_t306[nn] <= P["s1_tL"])
        d60 = (self.Da_tL[nn] <= P["s1_tL"]) | (self.Db_ratio[P["s1_wD"]] >= P["s1_rD"])
        s1 |= (self.D_t[nn] <= P["s1_tD"]) & (self.D_t306[nn] <= P["s1_tL"]) & d60
        e = (self.E_t306 <= P["s1_tE306"]) & self.E_cgt & (self.E_sp <= P["s1_sE"])
        e &= self.E_tSA[P["s1_wSA"]] <= P["s1_tSA"]
        e &= self.E_r60[P["s1_wE"]] >= P["s1_rE"]
        s1 |= e
        s1 &= self.g60
        s2 = self.g240 & (self.S2[P["s2_n"]] <= P["s2_t"])
        s21 = self.gD & (self.S21 < P["s21_surge"])
        k, n3 = P["s3_k"], P["s3_n"]
        bars = slice(S3N_MAX - n3, S3N_MAX)
        okbar = ((self.S3_t[:, bars] <= P["s3_t"])
                 & (self.S3_lo[:, bars] <= P["s3_lo"])
                 & (self.S3_up[:, bars] <= P["s3_up"]))
        band = np.where(self.S3_has612,
                        (self.S3_pct >= P["s3_c612lo"]) & (self.S3_pct <= P["s3_c612up"]),
                        self.S3_fb)
        s3 = self.gD & (self.S3_nD >= n3) & (okbar.sum(axis=1) >= k) & self.S3_bull & band
        s4 = (self.gInv & (self.S4_nb >= P["s4_n"])
              & (self.S4_fc < P["s4_fc"]) & (self.S4_ic < P["s4_ic"])
              & (self.S4_pc < P["s4_pc"]) & (self.S4_ft < P["s4_ft"]))
        s5 = np.where(self.fin_ok, ~(np.nan_to_num(self.fin, nan=0.0) < 0) | np.isnan(self.fin),
                      self.skip_na)
        # s5 정밀: fin_ok & fin<0 → False; fin_ok & (결측·≥0) → True
        s5 = np.where(self.fin_ok, ~((~np.isnan(self.fin)) & (self.fin < 0)), self.skip_na)
        return s1 & s2 & s21 & s3 & s4 & s5


def load_all():
    strata = json.load(open(OUT / "strata.json"))
    days = {}
    for d, m in sorted(strata.items()):
        if m["stratum"] in ("S1", "S2", "S3") and (PRIMS / f"{d}.npz").exists():
            days[d] = Day(d, m["stratum"])
    return days, strata


def main():
    days, strata = load_all()
    # ── (K) 분할 동결 전: 인접거래일 라벨 Jaccard ≥0.8 중복이벤트 검사 (76 라벨일 전체) ──
    lab_days = sorted(d for d, m in strata.items() if m["n_labels"] > 0)
    from src.kiwoom.itemFilter.Filter_condition_update import _parse_entry
    def lset(d):
        f = ENGINE / "reports" / d / "masterReference.md"
        if not f.exists():
            return set()
        return {_parse_entry(x.strip())[0] for x in f.read_text(encoding="utf-8").splitlines() if x.strip()}
    jac_flags = []
    for a, b in zip(lab_days, lab_days[1:]):
        sa, sb = lset(a), lset(b)
        if sa and sb:
            j = len(sa & sb) / len(sa | sb)
            if j >= 0.8:
                jac_flags.append((a, b, round(j, 3)))
    print(f"(K) 라벨일 {len(lab_days)}개 · 인접 Jaccard≥0.8 플래그: {jac_flags if jac_flags else '없음(0514/0515 기제외 외)'}")

    # ── 분할(v1.1-A + v1.2-I: 0703 제약셋 제외) ──
    s1_days = sorted(d for d, m in strata.items() if m["stratum"] == "S1" and d in days)
    s2_days = sorted(d for d, m in strata.items() if m["stratum"] == "S2" and d in days and d not in EXCLUDE_DAYS)
    s3_days = sorted(d for d, m in strata.items() if m["stratum"] == "S3" and d in days and d != "20260703")
    s1_cut = len(s1_days) * 7 // 10
    s3_cut = len(s3_days) * 2 // 3
    s1_tr, s1_ho = s1_days[:s1_cut], s1_days[s1_cut:]
    s2_tr, s2_ho = s2_days[:8], s2_days[8:]
    s3_tr, s3_ho = s3_days[:s3_cut], s3_days[s3_cut:]
    print(f"분할: S1 {len(s1_tr)}/{len(s1_ho)} · S2 {len(s2_tr)}/{len(s2_ho)} · S3guard {len(s3_tr)}/{len(s3_ho)} (0703 제외 v1.2-I)")
    print(f"  S2 train={s2_tr} holdout={s2_ho}")

    # ── (L) S2/S3 일별 5-파일 커버리지 표 + manifest 유무 ──
    coverage = {}
    for d in s2_days + s3_days + ["20260703"]:
        if d not in days:
            continue
        dy = days[d]
        n = len(dy.codes)
        coverage[d] = {
            "stratum": dy.stratum, "n": n,
            "manifest": (ENGINE / "reports" / d / "prefetchManifest.json").exists(),
            "ok_c60": int(dy.g60.sum()), "ok_c240": int(dy.g240.sum()),
            "ok_cD": int(dy.gD.sum()), "ok_inv": int(dy.gInv.sum()),
            "ok_fin": int(dy.fin_ok.sum()),
        }

    june_tr = [d for d in s3_tr if d[:6] != "202605"]

    def metrics(P, day_list, labels_only):
        vals = []
        for d in day_list:
            dy = days[d]
            p = dy.eval(P)
            if labels_only:
                vals.append(p[dy.label])
            else:
                vals.append(p.sum())
        return vals

    def train_recall(P):
        v = np.concatenate(metrics(P, s1_tr + s2_tr, True))
        return v.mean(), int(v.sum()), len(v)

    def guard(P, day_list):
        return [int(x) for x in metrics(P, day_list, False)]

    # ── P0 등가검증: instances.json 퍼널과 전 인스턴스 대조 ──
    rows = json.load(open(OUT / "instances.json"))
    want = {}
    for r in rows:
        if r.get("skip") or r["day"] not in days:
            continue
        want[(r["day"], r["code"])] = bool(r.get("passed"))
    mism = 0
    for d, dy in days.items():
        p = dy.eval(P0)
        for i, c in enumerate(dy.codes):
            w = want.get((d, c))
            if w is not None and w != bool(p[i]):
                mism += 1
                if mism <= 5:
                    print(f"  MISMATCH {d} {c}: instances={w} eval={bool(p[i])}")
    print(f"P0 등가검증: 대조 {len(want)} 불일치 {mism}")
    if mism:
        return 2

    r0, h0, n0 = train_recall(P0)
    g0 = guard(P0, s3_tr)
    print(f"P0: TRAIN recall {h0}/{n0}={r0:.3f} · guard중앙값(전체 {len(g0)}일)={statistics.median(g0)} · 6~7월만={statistics.median([g for d,g in zip(s3_tr,g0) if d[:6]!='202605'])}")

    # ── 탐색: lexicographic 변경수 k=1→4 빔 ──
    CAPS = [30, 45, 60, 90]

    def feasible(P, cap):
        g = guard(P, s3_tr)
        med_all = statistics.median(g)
        med_jj = statistics.median([x for d, x in zip(s3_tr, g) if d[:6] != "202605"])
        return (med_all <= cap and med_jj <= cap), med_all, med_jj

    def deviation(P):
        dv = 0.0
        for k, v in P.items():
            lo, hi = min(GRID.get(k, [P0[k]])), max(GRID.get(k, [P0[k]]))
            if hi > lo:
                dv += abs(v - P0[k]) / (hi - lo)
        return dv

    # k=1 스윕
    singles = []
    for prm, vals in GRID.items():
        for v in vals:
            if v == P0[prm]:
                continue
            P = dict(P0); P[prm] = v
            r, h, n = train_recall(P)
            singles.append((r, h, prm, v, P))
    singles.sort(key=lambda x: -x[0])
    top_params = []
    for r, h, prm, v, P in singles:
        if prm not in top_params:
            top_params.append(prm)
        if len(top_params) >= 10:
            break
    print("k=1 top10 파라미터:", top_params)

    results = {}
    all_cands = {}   # k → list[(recall, hits, P)]
    all_cands[1] = [(r, h, P) for r, h, _p, _v, P in singles]

    # k=2: top 파라미터 쌍 전수(값 그리드 전조합)
    cands2 = []
    for a, b in itertools.combinations(top_params, 2):
        for va in GRID[a]:
            for vb in GRID[b]:
                if va == P0[a] and vb == P0[b]:
                    continue
                P = dict(P0); P[a] = va; P[b] = vb
                r, h, n = train_recall(P)
                cands2.append((r, h, P))
    cands2.sort(key=lambda x: -x[0])
    all_cands[2] = cands2
    print(f"k=2 평가 {len(cands2)}개 최고 recall {cands2[0][0]:.3f}")

    # k=3/k=4: 빔 확장(상위 20 조합 × top 파라미터 × 그리드)
    beam = [c for c in cands2[:20]]
    for kk in (3, 4):
        nxt = []
        seen = set()
        for r, h, P in beam:
            changed = {k for k in GRID if P[k] != P0[k]}
            for prm in top_params:
                if prm in changed:
                    continue
                for v in GRID[prm]:
                    if v == P0[prm]:
                        continue
                    P2 = dict(P); P2[prm] = v
                    key = tuple(sorted((k, P2[k]) for k in GRID if P2[k] != P0[k]))
                    if key in seen:
                        continue
                    seen.add(key)
                    r2, h2, _ = train_recall(P2)
                    nxt.append((r2, h2, P2))
        nxt.sort(key=lambda x: -x[0])
        all_cands[kk] = nxt
        beam = nxt[:20]
        print(f"k={kk} 평가 {len(nxt)}개 최고 recall {nxt[0][0]:.3f}")

    # 캡별 최종후보: 전 k 풀에서 feasible 중 recall 최대 → 동률 시 변경수 최소 → 최소이탈
    final = {}
    pool = [(r, h, P) for kk in all_cands for (r, h, P) in all_cands[kk][:400]]
    pool.append((r0, h0, dict(P0)))
    for cap in CAPS:
        best = None
        for r, h, P in pool:
            ok, ma, mj = feasible(P, cap)
            if not ok:
                continue
            nch = sum(1 for k in GRID if P[k] != P0[k])
            key = (-r, nch, deviation(P))
            if best is None or key < best[0]:
                best = (key, r, h, P, ma, mj, nch)
        _k, r, h, P, ma, mj, nch = best
        chg = {k: (P0[k], P[k]) for k in GRID if P[k] != P0[k]}
        final[cap] = {"recall_train": r, "hits": h, "changed": chg, "n_changed": nch,
                      "guard_med_all": ma, "guard_med_junejul": mj, "P": P}
        print(f"[cap {cap}] TRAIN recall {r:.3f} ({h}) · 변경 {nch} {list(chg)} · guard {ma}/{mj}")

    # HOLDOUT 1회 평가(확정 후보만·재선택 금지) — v1.2-J 스트라텀별 분리 보고
    def ho_eval(P):
        v1 = np.concatenate(metrics(P, s1_ho, True))
        v2 = np.concatenate(metrics(P, s2_ho, True))
        v = np.concatenate([v1, v2])
        return {"recall_holdout": float(v.mean()), "holdout_hits": int(v.sum()), "holdout_n": len(v),
                "ho_S1": {"recall": float(v1.mean()), "hits": int(v1.sum()), "n": len(v1)},
                "ho_S2": {"recall": float(v2.mean()), "hits": int(v2.sum()), "n": len(v2)}}
    for cap, f in final.items():
        P = f["P"]
        f.update(ho_eval(P))
        gh = guard(P, s3_ho)
        f["guard_holdout"] = gh; f["guard_holdout_med"] = statistics.median(gh)
        f["gap"] = f["recall_train"] - f["recall_holdout"]
    base = ho_eval(P0)
    base_ho = base["recall_holdout"]
    gb = guard(P0, s3_ho)
    print(f"P0 HOLDOUT recall={base_ho:.3f} (S1 {base['ho_S1']['recall']:.3f} · S2 {base['ho_S2']['recall']:.3f}) guard_med={statistics.median(gb)}")

    # (L) pick-hit-rate 참고지표(부트스트랩 CI·서술 전용·최적화 미사용) — 캡45 후보·S2 train+holdout
    rng = np.random.default_rng(20260704)
    P45 = final[45]["P"]
    hits_list = []
    for d in s2_days:
        dy = days[d]
        p = dy.eval(P45)
        hits_list.extend([int(x) for x in p[dy.label]])
    arr = np.array(hits_list)
    boot = [rng.choice(arr, len(arr), replace=True).mean() for _ in range(2000)]
    phr = {"mean": float(arr.mean()), "n": len(arr),
           "ci95": [float(np.percentile(boot, 2.5)), float(np.percentile(boot, 97.5))]}

    # 민감도(캡45 헤드라인 후보): 변경 파라미터별 ±1 그리드 스텝
    sens = {}
    Ph = final[45]["P"]
    for prm in final[45]["changed"]:
        g = GRID[prm]; i = g.index(Ph[prm])
        for lbl, j in (("-1", i - 1), ("+1", i + 1)):
            if 0 <= j < len(g):
                P2 = dict(Ph); P2[prm] = g[j]
                r2, h2, _ = train_recall(P2)
                ok2, ma2, mj2 = feasible(P2, 45)
                sens[f"{prm}{lbl}({g[j]})"] = {"recall": r2, "guard_ok": ok2, "med": ma2}
    out = {"split": {"s1_tr": len(s1_tr), "s1_ho": len(s1_ho), "s2_tr": s2_tr, "s2_ho": s2_ho,
                     "s3_tr": s3_tr, "s3_ho": s3_ho, "jaccard_flags": jac_flags,
                     "label_days_total": len(lab_days)},
           "coverage": coverage,
           "P0": {"recall_train": r0, "recall_holdout": base_ho, "ho_strata": base,
                  "guard_train": g0, "guard_holdout": gb},
           "final": final, "sensitivity_cap45": sens, "pick_hit_rate_cap45_ref": phr,
           "k1_top": [(r, prm, v) for r, h, prm, v, P in singles[:25]]}
    json.dump(out, open(OUT / "b2_results.json", "w"), ensure_ascii=False, indent=1, default=str)
    print("WROTE b2_results.json")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
