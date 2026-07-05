"""Phase B — 임의 상수셋으로 전체 유니버스를 재평가하는 fragility sweep 드라이버.

목적
----
검증완료 ``analyses/phase_b/full_universe_ab.py`` (전체 organizedCompany 순회 ·
as-shipped evaluate_* · ConstantOverride · API 0회 · 골든 reports/ 무접촉)의
평가 머신을 **확장 상수셋**으로 일반화한다. NEW(HEAD f0aafbd) 기저 위에 임의의
overrides dict 를 in-process 로 적용한 뒤, 전 유니버스를 프로덕션 filter_today 와
동일한 6-stage 파이프라인(per-stock 독립 · finance_policy="require")에 통과시켜
funnel 총합(s1,s2,s2_1,s3,s4,s5) + final(s5) + universe_total 을 산출한다.
실행 후 상수는 NEW 로 원복한다.

확장 상수셋 (10 levers — 각 상수는 evaluate_* 호출시점에 모듈전역으로 읽힘,
default-arg/closure 캡처 아님 · 코드확인 완료 → in-process 재대입이 as-shipped 등가)::

  chart240Filter  (stage2)    _MA60_MA306_TOLERANCE            NEW 0.07
  chartDayFilter  (stage3)    _MA60_MA306_LOWER_TOL            NEW 0.15
  chartDayFilter  (stage3)    _MA60_MA306_UPPER_TOL            NEW 0.45
  chartDayFilter  (stage3)    _CLOSE_VS_MA612_LOWER            NEW -0.30
  chartDayFilter  (stage3)    _CLOSE_VS_MA612_UPPER            NEW 1.00
  investorFilter  (stage4)    _THRESHOLD_FOREIGN_CONSEC_SELL   NEW 5
  investorFilter  (stage4)    _THRESHOLD_INST_CONSEC_SELL      NEW 8
  investorFilter  (stage4)    _THRESHOLD_INDI_CONSEC_BUY       NEW 3
  investorFilter  (stage4)    _THRESHOLD_FOREIGN_TOTAL_SELL    NEW 15
  chartDayPreFilter (stage2_1) _DAILY_SURGE_THRESHOLD          NEW 0.15

토글 불가 (구조적 — Verify 에서 bound, override 대상 아님)::
  - finance(stage5): 상수 없음(하드코딩) → override 불가. finance-off 통과수 =
    해당 config 의 s4 카운트로 report(별도 코드토글 불필요 — s4 가 곧 stage5 진입
    후보이고, finance 제거 시 전부 통과).
  - 양봉(stage3 내 구조조건) · stage1(chart60_120 패턴): 상수 아님.

산출: analyses/phase_b/out/fragility/<config>.json (골든 reports/ 무접촉).
메인트리 필터소스 무수정(HEAD f0aafbd 고정, 런타임 오버라이드는 in-process).
API 0회(순수 디스크 재평가).

검증(필수)
----------
overrides={} (baseline) 를 --all 로 실행하면 NEW 기저와 동일하므로
full_universe_ab 앵커와 일치해야 한다::

  universe_total == 29906
  final(=s5)     == 1556
  s4             == 1950
  equivalence_mismatch_count == 0   (baseline 은 4-param mirror 완전 파라미터화)

불일치면 driver 결함.

사용::
  .venv/bin/python -m analyses.phase_b.fragility_sweep --config baseline.json --all
  .venv/bin/python -m analyses.phase_b.fragility_sweep --config cfg.json 20260703
  echo '{}' | .venv/bin/python -m analyses.phase_b.fragility_sweep --config - --all --name baseline
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ENGINE = Path("/Users/tajun/spJavis/auto-korea-stock-javis/engine")
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

# ── 검증완료 full_universe_ab 머신 재사용 (재구현 금지) ──
from analyses.phase_b.full_universe_ab import (
    ORDER, STAGE_KEY, _reached_count, _classify_s5, REPORTS, HEAD,
)
# ── 검증완료 recall_ab driver 재사용 (오라클 evaluate_* + 해석 인프라) ──
from analyses.phase_b.recall_ab import (
    NEW, _p_dict, eval_pick, resolve_pick, _folder_map,
    m_s2, m_s3, m_s4,
)
# ── 확장 상수셋 추가 모듈 (stage2_1) ──
from src.kiwoom.itemFilter import chartDayPreFilter as m_s2_1
from src.kiwoom.researchFlow.facade import _load_stock_names, _ORGANIZED_FILE
from src.kiwoom.researchFlow.name_resolver import build_name_to_code_map
from src.kiwoom.researchFlow.expert_backfill import build_disk_name_to_code_map

OUT = ENGINE / "analyses/phase_b/out/fragility"
FULL_AB_OUT = ENGINE / "analyses/phase_b/out/full_ab"  # 검증완료 앵커 date-set SOT


def _anchor_dates() -> list[str]:
    """--all 전체유니버스 date-set = 검증완료 full_universe_ab 앵커가 평가한 35 거래일.

    reports/ 에는 Phase B 창(20260515~20260703) 밖의 과거 백필 폴더가 섞여 있으므로
    raw glob(96)이 아니라 full_ab 산출물이 실제로 커버한 date-set 을 SOT 로 쓴다.
    이로써 baseline(overrides={}) 이 full_ab 앵커(universe_total=29906·s4=1950·
    final=1556)를 정확히 재현한다. 앵커 산출물 부재 시 raw glob 폴백(정직 경고).
    """
    stems = sorted(p.stem for p in FULL_AB_OUT.glob("*.json")
                   if p.stem.isdigit())
    if stems:
        return stems
    print("[경고] full_ab 앵커 산출물 부재 → reports/ raw glob 폴백(앵커 대조 무의미)",
          file=sys.stderr)
    return sorted(p.parent.name for p in REPORTS.glob("*/organizedCompany.md")
                  if p.parent.name.isdigit())

# ═══════════════════════════════════════════════════════════════════
# Levers — attr → module 바인딩 (call-time module-global reads)
# ═══════════════════════════════════════════════════════════════════
# 각 확장 상수가 살아있는 모듈. bare attr name 은 이 4개 모듈 사이에서 유일하다
# (충돌 없음 · import-time 검증). config overrides 는 bare attr name 을 키로 쓴다.
_LEVER_MODULES = {
    "s2": m_s2,        # chart240Filter
    "s3": m_s3,        # chartDayFilter
    "s4": m_s4,        # investorFilter
    "s2_1": m_s2_1,    # chartDayPreFilter
}
_LEVER_STAGE = {
    "_MA60_MA306_TOLERANCE": "s2",
    "_MA60_MA306_LOWER_TOL": "s3",
    "_MA60_MA306_UPPER_TOL": "s3",
    "_CLOSE_VS_MA612_LOWER": "s3",
    "_CLOSE_VS_MA612_UPPER": "s3",
    "_THRESHOLD_FOREIGN_CONSEC_SELL": "s4",
    "_THRESHOLD_INST_CONSEC_SELL": "s4",
    "_THRESHOLD_INDI_CONSEC_BUY": "s4",
    "_THRESHOLD_FOREIGN_TOTAL_SELL": "s4",
    "_DAILY_SURGE_THRESHOLD": "s2_1",
}


def _build_levers() -> dict:
    """{attr: module} — 각 attr 이 지정 모듈에 실제로 존재함을 import-time 검증."""
    levers = {}
    for attr, stage in _LEVER_STAGE.items():
        mod = _LEVER_MODULES[stage]
        if not hasattr(mod, attr):
            raise RuntimeError(
                f"lever 결함: {mod.__name__} 에 {attr} 없음 (call-time-read 전제 붕괴)")
        levers[attr] = mod
    return levers


LEVERS = _build_levers()

# 4-param mirror(margin_extract) 가 파라미터화하는 상수 ↔ _p_dict 키 매핑.
# 이 4개 override 는 mirror 에 반영되어 등가검증(mism)이 계속 0 을 유지한다.
# 나머지 6개 lever 는 mirror 가 추적하지 않으므로, override 시 real≠mirror 인
# mismatch 가 나타날 수 있다(driver 결함 아님 — mirror 는 4-param 부분 파라미터화).
_MIRROR_KEYS = {
    "_MA60_MA306_TOLERANCE": "s2_MA60_MA306_TOLERANCE",
    "_CLOSE_VS_MA612_LOWER": "s3_CLOSE_VS_MA612_LOWER",
    "_CLOSE_VS_MA612_UPPER": "s3_CLOSE_VS_MA612_UPPER",
    "_THRESHOLD_FOREIGN_CONSEC_SELL": "s4_THRESHOLD_FOREIGN_CONSEC_SELL",
}


class ExtendedConstantOverride:
    """확장 상수셋(≤10 levers)을 in-process 로 오버라이드하고 종료 시 원복(NEW 원상).

    NEW(f0aafbd) 라이브 모듈전역 위에 overrides 를 덮고, __exit__ 에서 저장했던
    이전 값(=NEW)으로 원복한다. recall_ab.ConstantOverride 와 동일 계약이나
    임의 lever 집합을 받는다.
    """

    def __init__(self, overrides: dict):
        self.overrides = overrides
        self._saved: dict = {}

    def __enter__(self):
        for attr, val in self.overrides.items():
            if attr not in LEVERS:
                raise KeyError(f"미지원 lever: {attr} (지원: {sorted(LEVERS)})")
            mod = LEVERS[attr]
            self._saved[(mod, attr)] = getattr(mod, attr)
            setattr(mod, attr, val)
        return self

    def __exit__(self, *exc):
        for (mod, attr), val in self._saved.items():
            setattr(mod, attr, val)
        return False


def _baseline_new() -> dict:
    """현재 라이브 모듈전역(=HEAD f0aafbd NEW 기저) 스냅샷 {attr: value}."""
    return {attr: getattr(mod, attr) for attr, mod in LEVERS.items()}


def _effective_p_dict(overrides: dict) -> dict:
    """NEW 4-mirror-param 위에 overrides 의 mirror 대상 4개를 덮어 _p_dict 생성.

    mirror(margin_extract)가 파라미터화하는 4상수만 P-dict 에 반영한다.
    나머지 6 lever override 는 P-dict 에 없으므로 mirror 등가가 깨질 수 있다(정직).
    """
    eff = dict(NEW)  # NEW = {s2_..., s3_...lo, s3_...up, s4_...} 4키
    for attr, pkey in _MIRROR_KEYS.items():
        if attr in overrides:
            eff[pkey] = overrides[attr]
    return _p_dict(eff)


# ═══════════════════════════════════════════════════════════════════
# 단일 거래일 전체 유니버스 6-stage 평가 (full_universe_ab.evaluate_universe 확장)
# ═══════════════════════════════════════════════════════════════════

def evaluate_universe(date: str, overrides: dict,
                      finance_policy: str = "require") -> dict:
    """단일 상수셋(NEW+overrides)으로 전체 유니버스 6-stage 평가 → 집계.

    ExtendedConstantOverride 하에서 recall_ab.eval_pick 을 전 종목에 적용
    (프로덕션 filter_today 와 동일 per-stock 독립 경로). API 0회.
    """
    ddir = REPORTS / date
    organized = ddir / _ORGANIZED_FILE
    names = _load_stock_names(organized)
    universe_n = len(names)

    folder_map = _folder_map(ddir)
    name_to_code = build_name_to_code_map(ddir)
    if not name_to_code:  # condition/upper.md 부재일 → 폴더에서 복원(facade 폴백)
        name_to_code = {nm: c for nm, (c, _f) in folder_map.items()}
    union_map = build_disk_name_to_code_map([REPORTS, ENGINE / "reports_backfill"])

    P = _effective_p_dict(overrides)
    surv = {s: 0 for s in ORDER}
    final_n = 0
    evaluated_n = 0
    unresolved_n = 0
    finance_present_n = 0
    s5b = {"reached": 0, "pass": 0, "fail_적자": 0, "fail_nodata": 0, "fail_기타": 0}
    total_mismatch = 0

    with ExtendedConstantOverride(overrides):
        # 오버라이드 실측 확인 (as-shipped 재대입 성공 검증)
        applied = {attr: getattr(mod, attr) for attr, mod in LEVERS.items()}
        expect = _baseline_new_under_override(overrides)
        assert applied == expect, f"오버라이드 불일치: {applied} != {expect}"

        for nm in names:
            _nm, cd, folder, method = resolve_pick(
                nm, ddir, folder_map, name_to_code, union_map)
            if folder is None or not folder.exists():
                unresolved_n += 1
                continue
            evaluated_n += 1
            if (folder / "finance.md").exists():
                finance_present_n += 1
            try:
                stages, final_sel, break_at, mism = eval_pick(
                    folder, P, finance_policy)
            except Exception:  # noqa: BLE001
                # 프로덕션 filter_today 는 _run_filter_pipeline 을 try/except 로 감싸
                # 손상 md → stages=[]·final=False 스킵(reached 0). 여기 동일 처리.
                continue
            total_mismatch += mism

            reached = _reached_count(final_sel, break_at)
            for i, s in enumerate(ORDER):
                if i < reached:
                    surv[s] += 1
            if final_sel:
                final_n += 1

            cls = _classify_s5(final_sel, break_at, stages)
            if cls is not None:
                s5b["reached"] += 1
                if cls == "reached_pass":
                    s5b["pass"] += 1
                elif cls == "reached_fail_적자":
                    s5b["fail_적자"] += 1
                elif cls == "reached_fail_nodata":
                    s5b["fail_nodata"] += 1
                else:
                    s5b["fail_기타"] += 1

    agg = {STAGE_KEY[s]: surv[s] for s in ORDER}
    agg["final"] = final_n
    agg["s5_breakdown"] = s5b
    return {
        "date": date,
        "universe_n": universe_n,
        "evaluated_n": evaluated_n,
        "unresolved_n": unresolved_n,
        "finance_present_n": finance_present_n,
        "agg": agg,
        # finance(S5)는 상수無 override 불가 → finance-off 통과수 = s4 카운트
        "s4_finance_off": agg["s4"],
        "equivalence_mismatch_count": total_mismatch,
    }


def _baseline_new_under_override(overrides: dict) -> dict:
    """NEW 라이브 위에 overrides 적용 시 예상되는 {attr: value} (assert 기대값)."""
    exp = _baseline_new()
    exp.update({k: v for k, v in overrides.items() if k in LEVERS})
    return exp


# ═══════════════════════════════════════════════════════════════════
# 스윕: config(overrides) × --all 전 거래일 → funnel 총합
# ═══════════════════════════════════════════════════════════════════

def run_sweep(config_name: str, overrides: dict, dates: list[str],
              finance_policy: str = "require", write: bool = True) -> dict:
    """overrides 를 dates 전체에 적용, per-date + funnel 총합 집계."""
    per_date = []
    tot = {STAGE_KEY[s]: 0 for s in ORDER}
    tot["final"] = 0
    universe_total = 0
    evaluated_total = 0
    unresolved_total = 0
    finance_present_total = 0
    mism_total = 0

    for d in dates:
        ddir = REPORTS / d
        if not (ddir / _ORGANIZED_FILE).exists():
            raise FileNotFoundError(f"organizedCompany.md 없음: {ddir}")
        r = evaluate_universe(d, overrides, finance_policy)
        per_date.append(r)
        a = r["agg"]
        for s in ORDER:
            tot[STAGE_KEY[s]] += a[STAGE_KEY[s]]
        tot["final"] += a["final"]
        universe_total += r["universe_n"]
        evaluated_total += r["evaluated_n"]
        unresolved_total += r["unresolved_n"]
        finance_present_total += r["finance_present_n"]
        mism_total += r["equivalence_mismatch_count"]

    # 실행 후 상수 NEW 원복 검증
    restored = _baseline_new()
    baseline_new = {
        "_MA60_MA306_TOLERANCE": 0.07,
        "_MA60_MA306_LOWER_TOL": 0.15,
        "_MA60_MA306_UPPER_TOL": 0.45,
        "_CLOSE_VS_MA612_LOWER": -0.30,
        "_CLOSE_VS_MA612_UPPER": 1.00,
        "_THRESHOLD_FOREIGN_CONSEC_SELL": 5,
        "_THRESHOLD_INST_CONSEC_SELL": 8,
        "_THRESHOLD_INDI_CONSEC_BUY": 3,
        "_THRESHOLD_FOREIGN_TOTAL_SELL": 15,
        "_DAILY_SURGE_THRESHOLD": 0.15,
    }
    restored_to_new = (restored == baseline_new)

    funnel = {k: tot[k] for k in ("s1", "s2", "s2_1", "s3", "s4", "s5")}
    final = tot["final"]  # == s5

    # baseline 자체검증 (overrides 무관하게 앵커 대조 정보 부착)
    is_baseline = (len(overrides) == 0)
    baseline_check = None
    if is_baseline:
        baseline_check = {
            "universe_total_expected": 29906,
            "final_expected": 1556,
            "s4_expected": 1950,
            "universe_total_ok": universe_total == 29906,
            "final_ok": final == 1556,
            "s4_ok": funnel["s4"] == 1950,
            "mismatch_ok": mism_total == 0,
        }
        baseline_check["all_ok"] = all(
            baseline_check[k] for k in
            ("universe_total_ok", "final_ok", "s4_ok", "mismatch_ok"))

    result = {
        "config_name": config_name,
        "head": HEAD,
        "driver": str(ENGINE / "analyses/phase_b/fragility_sweep.py"),
        "finance_policy": finance_policy,
        "baseline_new": baseline_new,
        "overrides": overrides,
        "applied_over_new": _baseline_new_under_override(overrides),
        "n_dates": len(dates),
        "dates": dates,
        "universe_total": universe_total,
        "evaluated_total": evaluated_total,
        "unresolved_total": unresolved_total,
        "finance_present_total": finance_present_total,
        "funnel": funnel,
        "final": final,
        # finance(S5) 상수無 → override 불가. finance-off 통과수 = s4 총합.
        "s4_finance_off": funnel["s4"],
        "stage_map": {
            "s1": "chart60_120(구조·비토글)", "s2": "chart240(토글: TOLERANCE)",
            "s2_1": "chartDayPre(토글: DAILY_SURGE)", "s3": "chartDay(토글: TOL/밴드)",
            "s4": "investor(토글: 4 threshold)",
            "s5": "finance(상수無·require)=final=s4에서 finance 적용"},
        "equivalence_mismatch_count": mism_total,
        "mirror_note": ("mirror(margin_extract)는 4-param 부분 파라미터화 — "
                        "비-mirror lever override 시 mismatch 가능(정직·driver 결함 아님). "
                        "baseline(overrides={})은 mismatch 0 이어야 함."),
        "restored_after_run": restored,
        "restored_to_new": restored_to_new,
        "baseline_check": baseline_check,
        "per_date": [
            {"date": r["date"], "universe_n": r["universe_n"],
             "evaluated_n": r["evaluated_n"], "unresolved_n": r["unresolved_n"],
             "finance_present_n": r["finance_present_n"], "agg": r["agg"],
             "s4_finance_off": r["s4_finance_off"],
             "equivalence_mismatch_count": r["equivalence_mismatch_count"]}
            for r in per_date
        ],
    }

    if write:
        OUT.mkdir(parents=True, exist_ok=True)
        out_path = OUT / f"{config_name}.json"
        json.dump(result, open(out_path, "w"), ensure_ascii=False, indent=1,
                  default=str)
        result["_out_path"] = str(out_path)

    print(f"=== fragility_sweep [{config_name}] fp={finance_policy} "
          f"dates={len(dates)} ===")
    print(f"  overrides={overrides}")
    print(f"  universe_total={universe_total} evaluated={evaluated_total} "
          f"unresolved={unresolved_total} finance_present={finance_present_total}")
    print(f"  funnel s1={funnel['s1']} s2={funnel['s2']} s2_1={funnel['s2_1']} "
          f"s3={funnel['s3']} s4={funnel['s4']} s5={funnel['s5']} "
          f"FINAL={final} s4_finance_off={funnel['s4']}")
    print(f"  등가 mismatch={mism_total}  원복 NEW 원상={restored_to_new}")
    if baseline_check is not None:
        print(f"  [BASELINE 검증] universe_total={universe_total}"
              f"(exp 29906 {'OK' if baseline_check['universe_total_ok'] else '★FAIL'}) "
              f"final={final}(exp 1556 {'OK' if baseline_check['final_ok'] else '★FAIL'}) "
              f"s4={funnel['s4']}(exp 1950 {'OK' if baseline_check['s4_ok'] else '★FAIL'}) "
              f"→ {'ALL OK' if baseline_check['all_ok'] else '★DRIVER 결함'}")
    if write:
        print(f"  산출: {result['_out_path']}")
    return result


def _load_config(path: str) -> tuple[str, dict]:
    """config JSON 로드 → (name, overrides). '-' 는 stdin.

    허용 형태:
      {"overrides": {...}, "name": "..."}   또는   {...bare overrides...}
    """
    if path == "-":
        raw = sys.stdin.read()
        name_default = "stdin"
    else:
        raw = Path(path).read_text(encoding="utf-8")
        name_default = Path(path).stem
    obj = json.loads(raw) if raw.strip() else {}
    if isinstance(obj, dict) and "overrides" in obj:
        overrides = obj["overrides"] or {}
        name = obj.get("name", name_default)
    else:
        overrides = obj or {}
        name = name_default
    if not isinstance(overrides, dict):
        raise ValueError(f"overrides 는 dict 여야 함: {type(overrides)}")
    # lever 검증
    for k in overrides:
        if k not in LEVERS:
            raise KeyError(f"미지원 lever '{k}' (지원 10개: {sorted(LEVERS)})")
    return name, overrides


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date", nargs="?", default=None, help="YYYYMMDD (단일일)")
    ap.add_argument("--config", required=True,
                    help="config JSON 경로 (overrides dict) 또는 '-'(stdin)")
    ap.add_argument("--all", action="store_true",
                    help="reports/ 하위 organizedCompany.md 보유 전 거래일")
    ap.add_argument("--name", default=None,
                    help="산출 config 이름(미지정 시 config JSON name/파일stem)")
    ap.add_argument("--finance-policy", default="require",
                    choices=["require", "skip_na"])
    args = ap.parse_args()

    name, overrides = _load_config(args.config)
    if args.name:
        name = args.name

    if args.all:
        dates = _anchor_dates()
    elif args.date:
        dates = [args.date]
    else:
        print("[오류] <YYYYMMDD> 또는 --all 필요", file=sys.stderr)
        return 2

    r = run_sweep(name, overrides, dates, args.finance_policy)

    ok = r["restored_to_new"]
    if r["baseline_check"] is not None:
        ok = ok and r["baseline_check"]["all_ok"]
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
