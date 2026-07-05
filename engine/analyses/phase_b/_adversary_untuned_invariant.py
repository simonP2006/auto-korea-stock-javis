"""ADVERSARIAL independent verifier — lens='untuned-invariant'.

Recompute, per measurable pick, the INDEPENDENT decision of the three
NON-tuned stages S1(chart60_120) / S2_1(chartDayPre) / S5(finance) under BOTH
the OLD and NEW constant sets, and assert they are identical pick-by-pick.

Independence guarantees this is not circular with the Run's ledger:
  - stages are evaluated in ISOLATION (no pipeline short-circuit);
  - two orthogonal computation paths per stage:
      (a) as-shipped real evaluate_* run UNDER an actual in-process swap of the
          4 tuned module globals (OLD vs NEW) — proves the non-tuned evaluate
          functions do not read any tuned global;
      (b) parameterized mirror_* fed OLD-P vs NEW-P dicts.
  - all 4 recomputations (realOLD, realNEW, mirrorOLD, mirrorNEW) must agree
    for each of S1/S2_1/S5 on every measurable pick.
Any divergence -> FAIL with the offending pick/stage.
"""
from __future__ import annotations
import json, sys
from pathlib import Path

ENGINE = Path("/Users/tajun/spJavis/auto-korea-stock-javis/engine")
sys.path.insert(0, str(ENGINE))

from analyses.phase_b.recall_ab import (
    OLD, NEW, ConstantOverride, _p_dict, _folder_map, _parse_all, resolve_pick,
    m_s2, m_s3, m_s4,
)
from analyses.phase_b.margin_extract import mirror_stage1, mirror_stage21, mirror_stage5
from src.kiwoom.itemFilter.chart60_120Filter import evaluate_chart60_120
from src.kiwoom.itemFilter.chartDayPreFilter import evaluate_chartday_pre
from src.kiwoom.itemFilter.financeFilter import evaluate_finance
from src.kiwoom.researchFlow.name_resolver import build_name_to_code_map
from src.kiwoom.researchFlow.expert_backfill import build_disk_name_to_code_map
from analyses.phase_b.run_ledger import MEASURABLE, DAYS

REPORTS = ENGINE / "reports"

# Independent, hand-inlined copy of the MEASURABLE roster is NOT used; we import
# the Run's roster so we cover EXACTLY the same 61-pick universe it claims.

def real_untuned(folder):
    """Return (s1, s21, s5) via real as-shipped evaluate_* on this folder.
    Assumes the caller has entered the desired ConstantOverride context."""
    b60, b120, b240, bD, inv, cup, fin_invalid, fin_present = _parse_all(folder)
    s1 = evaluate_chart60_120(b60, b120)[0] if (b60 and b120) else None
    s21 = evaluate_chartday_pre(bD)[0] if bD else None
    # finance require-policy: present->evaluate, absent->False (matches driver)
    if fin_present:
        s5 = evaluate_finance(cup, invalid=fin_invalid)[0]
    else:
        s5 = False
    return s1, s21, s5


def mirror_untuned(folder, P):
    b60, b120, b240, bD, inv, cup, fin_invalid, fin_present = _parse_all(folder)
    s1 = mirror_stage1(b60, b120, P)[0] if (b60 and b120) else None
    s21 = mirror_stage21(bD, P) if bD else None
    if fin_present:
        s5 = mirror_stage5(cup)
    else:
        s5 = False
    return s1, s21, s5


def main():
    violations = []
    n_pick_eval = 0
    n_stage_eval = 0
    unresolved = []
    per_pick = []

    for date in DAYS:
        ddir = REPORTS / date
        folder_map = _folder_map(ddir)
        name_to_code = build_name_to_code_map(ddir)
        if not name_to_code:
            name_to_code = {nm: c for nm, (c, _f) in folder_map.items()}
        union_map = build_disk_name_to_code_map([REPORTS, ENGINE / "reports_backfill"])

        for name in MEASURABLE[date]:
            nm, cd, folder, method = resolve_pick(
                name, ddir, folder_map, name_to_code, union_map)
            if folder is None or not folder.exists():
                unresolved.append({"date": date, "pick": name, "method": method})
                continue

            # (a) real as-shipped under actual constant swap
            with ConstantOverride(OLD):
                assert m_s2._MA60_MA306_TOLERANCE == 0.025
                assert m_s3._CLOSE_VS_MA612_LOWER == -0.15
                assert m_s3._CLOSE_VS_MA612_UPPER == 0.50
                assert m_s4._THRESHOLD_FOREIGN_CONSEC_SELL == 2
                r_old = real_untuned(folder)
            with ConstantOverride(NEW):
                assert m_s2._MA60_MA306_TOLERANCE == 0.07
                assert m_s3._CLOSE_VS_MA612_LOWER == -0.30
                assert m_s3._CLOSE_VS_MA612_UPPER == 1.00
                assert m_s4._THRESHOLD_FOREIGN_CONSEC_SELL == 5
                r_new = real_untuned(folder)

            # (b) parameterized mirror under OLD-P / NEW-P
            m_old = mirror_untuned(folder, _p_dict(OLD))
            m_new = mirror_untuned(folder, _p_dict(NEW))

            stages = ["S1", "S2_1", "S5"]
            row = {"date": date, "name": nm, "code": cd, "method": method}
            for i, s in enumerate(stages):
                n_stage_eval += 1
                ro, rn, mo, mn = r_old[i], r_new[i], m_old[i], m_new[i]
                row[s] = {"realOLD": ro, "realNEW": rn, "mirOLD": mo, "mirNEW": mn}
                # invariant: OLD == NEW on the real path
                if ro != rn:
                    violations.append({"date": date, "code": cd, "name": nm,
                                       "stage": s, "kind": "real_OLD!=NEW",
                                       "old": ro, "new": rn})
                # invariant on mirror path
                if mo != mn:
                    violations.append({"date": date, "code": cd, "name": nm,
                                       "stage": s, "kind": "mirror_OLD!=NEW",
                                       "old": mo, "new": mn})
                # cross-path agreement (real vs mirror), OLD side
                if ro != mo:
                    violations.append({"date": date, "code": cd, "name": nm,
                                       "stage": s, "kind": "realOLD!=mirOLD",
                                       "real": ro, "mirror": mo})
                if rn != mn:
                    violations.append({"date": date, "code": cd, "name": nm,
                                       "stage": s, "kind": "realNEW!=mirNEW",
                                       "real": rn, "mirror": mn})
            per_pick.append(row)
            n_pick_eval += 1

    # NEW is the restored/default state; confirm we ended restored to NEW
    restored_new = (m_s2._MA60_MA306_TOLERANCE == 0.07
                    and m_s3._CLOSE_VS_MA612_LOWER == -0.30
                    and m_s3._CLOSE_VS_MA612_UPPER == 1.00
                    and m_s4._THRESHOLD_FOREIGN_CONSEC_SELL == 5)

    out = {
        "n_measurable_declared": sum(len(v) for v in MEASURABLE.values()),
        "n_pick_evaluated": n_pick_eval,
        "n_stage_decisions": n_stage_eval,
        "n_violations": len(violations),
        "violations": violations,
        "unresolved": unresolved,
        "restored_to_new": restored_new,
        "holds": len(violations) == 0,
    }
    print(json.dumps({k: v for k, v in out.items() if k != "per_pick"},
                     ensure_ascii=False, indent=1))
    json.dump({**out, "per_pick": per_pick},
              open(ENGINE / "analyses/phase_b/out/recall_ab/_adversary_untuned.json", "w"),
              ensure_ascii=False, indent=1, default=str)
    return 0 if out["holds"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
