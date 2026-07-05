"""Phase B — OLD/NEW filter-only 재평가: measurable 픽 전체 원장 생성.

recall_ab.py 드라이버(as-shipped evaluate_* + name_resolver)를 measurable 픽에 대해
OLD/NEW 각각 CLI 호출 → 산출 JSON을 로드해 aggregate/per_day/per_pick/flips/invariant 산출.

GUARDRAILS: API 0회(순수 디스크 재평가), 골든 reports/ 무접촉, 필터소스 무수정
(recall_ab 의 in-process ConstantOverride, __exit__ NEW 원복), name_resolver 사용.
"""
from __future__ import annotations
import json, subprocess, sys
from pathlib import Path

ENGINE = Path("/Users/tajun/spJavis/auto-korea-stock-javis/engine")
PY = ENGINE / ".venv/bin/python"
DRIVER = ENGINE / "analyses/phase_b/recall_ab.py"
OUT = ENGINE / "analyses/phase_b/out/recall_ab"

# measurable 픽만 (Recon 분류) — code-notation 픽은 '이름(코드)' 그대로 전달
MEASURABLE = {
    "20260515": [],
    "20260518": ["영림원소프트랩","케이아이엔엑스","디지아이","메쎄이상","브이원텍",
                 "제이앤티씨","성우","이연제약","제일파마홀딩스","토박스코리아"],
    "20260519": ["아이스크림미디어","아나패스","다이나믹솔루션","SKAI","코나아이"],
    "20260520": ["그린생명과학","SY동아","인스피언"],
    "20260521": ["아이디피","삼성에스디에스","LX홀딩스","푸른기술","인탑스",
                 "한빛소프트","애드바이오텍","성우","티앤엘"],
    "20260522": ["대원강업","그린생명과학","삼현철강","어보브반도체","HL만도",
                 "제이티","LB세미콘","파인엠텍","셀리드","제이앤티씨"],
    "20260528": ["아이텍","에스엠벡셀","제이앤티씨","아이컴포넌트","DH오토리드",
                 "DYP","조선내화"],
    "20260529": ["한빛소프트","LG디스플레이","케이아이엔엑스","HL만도","유니크","시선AI"],
    "20260601": ["레인보우로보틱스(277810)","한일철강(002220)","아이텍(119830)",
                 "토탈소프트(045340)"],
    "20260604": ["국보디자인","오리온홀딩스"],
    "20260608": ["대원강업(000430)"],
    "20260610": ["한일철강(002220)"],
    "20260611": ["삼현철강(017480)","블루콤(033560)","넥스턴앤롤코리아(089140)"],
}
ORDER = ["stage1","stage2","stage2_1","stage3","stage4","stage5"]
DAYS = [d for d in MEASURABLE if MEASURABLE[d]]

def run(date, consts, picks):
    cmd = [str(PY), str(DRIVER), "--constants", consts, "--date", date,
           "--picks", ",".join(picks), "--finance-policy", "require"]
    r = subprocess.run(cmd, cwd=str(ENGINE), capture_output=True, text=True)
    if r.returncode not in (0,):  # 0=OK 0-mismatch; !=0 => mismatch, report
        print(f"[{date} {consts}] rc={r.returncode}\n{r.stdout}\n{r.stderr}",
              file=sys.stderr)
    data = json.load(open(OUT / f"{date}_{consts}.json"))
    return data

def death_stage(rec):
    if rec.get("final_selected"):
        return "passed"
    b = rec.get("break_at")
    return b if b else "unresolved"

def main():
    ledger = {}          # date -> {code -> {name, old:{stages,final,death}, new:{...}}}
    total_mismatch = 0
    restored_ok_all = True
    for date in DAYS:
        picks = MEASURABLE[date]
        old = run(date, "old", picks)
        new = run(date, "new", picks)
        total_mismatch += old["equivalence_mismatch_count"] + new["equivalence_mismatch_count"]
        restored_ok_all &= bool(new.get("restored_to_new")) and bool(old.get("restored_to_new"))
        by = {}
        for tag, dd in (("old", old), ("new", new)):
            for rec in dd["picks"]:
                code = rec.get("code") or f"UNRESOLVED::{rec['pick']}"
                e = by.setdefault(code, {"name": rec["name"], "pick": rec["pick"],
                                         "resolve_method": rec.get("resolve_method")})
                stages = rec.get("stages") or {}
                e[tag] = {
                    "stage_selected": {s: (stages.get(s, {}) or {}).get("selected")
                                       for s in ORDER},
                    "final": rec.get("final_selected"),
                    "death": death_stage(rec),
                    "break_at": rec.get("break_at"),
                    "error": rec.get("error"),
                }
        ledger[date] = by

    # ── cumulative funnel (파이프라인: 앞 stage 탈락 시 이후 전부 탈락) ──
    def funnel(tag):
        surv = {s: 0 for s in ORDER}
        for date in DAYS:
            for code, e in ledger[date].items():
                d = e[tag]["death"]
                # death=='passed' → 모든 stage survive; death=='stageX' → X 이전까지 survive
                if d == "passed":
                    reached = len(ORDER)
                else:
                    base = d.split(":")[0]
                    reached = ORDER.index(base) if base in ORDER else 0
                # stage N 까지 살아남음 = index < reached (탈락 stage 자신은 미생존)
                for i, s in enumerate(ORDER):
                    if i < reached:
                        surv[s] += 1
        return surv

    n_meas = sum(len(v) for v in MEASURABLE.values())
    old_f = funnel("old"); new_f = funnel("new")
    old_final = sum(1 for date in DAYS for e in ledger[date].values() if e["old"]["final"])
    new_final = sum(1 for date in DAYS for e in ledger[date].values() if e["new"]["final"])

    # funnel s5 == 최종통과. 확인용.
    def agg(tag, fn, final_n):
        return {"s1": fn["stage1"], "s2": fn["stage2"], "s2_1": fn["stage2_1"],
                "s3": fn["stage3"], "s4": fn["stage4"], "s5": fn["stage5"],
                "final_selected": final_n,
                "final_recall_pct": round(100.0*final_n/n_meas, 2) if n_meas else 0.0}

    aggregate = {"measurable": n_meas,
                 "old": agg("old", old_f, old_final),
                 "new": agg("new", new_f, new_final)}

    # ── per_day ──
    per_day = []
    for date in DAYS:
        picks = ledger[date]
        of = {s: 0 for s in ORDER}; nf = {s: 0 for s in ORDER}
        o_final = n_final = 0
        for e in picks.values():
            for tag, acc in (("old", of), ("new", nf)):
                d = e[tag]["death"]
                reached = len(ORDER) if d == "passed" else (
                    ORDER.index(d.split(":")[0]) if d.split(":")[0] in ORDER else 0)
                for i, s in enumerate(ORDER):
                    if i < reached:
                        acc[s] += 1
            o_final += 1 if e["old"]["final"] else 0
            n_final += 1 if e["new"]["final"] else 0
        m = len(picks)
        per_day.append({
            "date": date, "measurable": m,
            "old": {"s1": of["stage1"], "s2": of["stage2"], "s2_1": of["stage2_1"],
                    "s3": of["stage3"], "s4": of["stage4"], "s5": of["stage5"],
                    "final": o_final,
                    "recall_pct": round(100.0*o_final/m, 2) if m else 0.0},
            "new": {"s1": nf["stage1"], "s2": nf["stage2"], "s2_1": nf["stage2_1"],
                    "s3": nf["stage3"], "s4": nf["stage4"], "s5": nf["stage5"],
                    "final": n_final,
                    "recall_pct": round(100.0*n_final/m, 2) if m else 0.0},
        })

    # ── per_pick + flips + invariant ──
    TUNED = {"stage2": "s2_MA60_MA306_TOLERANCE(0.025→0.07)",
             "stage3": "s3_CLOSE_VS_MA612_LO/UP(-0.15/0.5→-0.30/1.0)",
             "stage4": "s4_FOREIGN_CONSEC_SELL(2→5)"}
    NONTUNED = ["stage1", "stage2_1", "stage5"]
    per_pick = []; flips = []
    inv_break = []
    for date in DAYS:
        for code, e in ledger[date].items():
            o, n = e["old"], e["new"]
            old_death, new_death = o["death"], n["death"]
            old_final, new_final_ = bool(o["final"]), bool(n["final"])
            changed = (old_death != new_death) or (old_final != new_final_)
            # cause_stage: 파이프라인 death 가 바뀐 지점 or 튜닝 stage 중 stage-selected 가 바뀐 것
            cause = ""
            if changed:
                # 어느 stage 의 독립 판정이 OLD→NEW 로 바뀌었나 (튜닝 stage 위주)
                diffs = [s for s in ORDER
                         if o["stage_selected"].get(s) != n["stage_selected"].get(s)]
                cause = ",".join(f"{s}:{TUNED.get(s,'(비튜닝?!)')}" for s in diffs) or \
                        f"death:{old_death}->{new_death}"
            note = ""
            if old_final != new_final_ and new_final_ and not old_final:
                flips.append({"date": date, "name": e["name"], "code": code,
                              "old_death_stage": old_death, "cause_stage": cause,
                              "note": "OLD 탈락 → NEW 선정 (recall 회복)"})
                note = "FLIP: OLD 탈락→NEW 선정"
            elif old_final and not new_final_:
                note = "역FLIP: OLD 선정→NEW 탈락"
            # 불변식: 비튜닝 stage 독립판정 OLD==NEW (도달=데이터존재해 not None)
            for s in NONTUNED:
                ov, nv = o["stage_selected"].get(s), n["stage_selected"].get(s)
                if ov is not None and nv is not None and ov != nv:
                    inv_break.append({"date": date, "code": code, "name": e["name"],
                                      "stage": s, "old": ov, "new": nv})
            per_pick.append({
                "date": date, "name": e["name"], "code": code,
                "resolve_method": e.get("resolve_method"),
                "old_death_stage": old_death, "new_death_stage": new_death,
                "old_final": old_final, "new_final": new_final_,
                "changed": changed, "cause_stage": cause,
                "old_stage_selected": o["stage_selected"],
                "new_stage_selected": n["stage_selected"],
                "note": note,
            })

    invariant = {
        "holds": len(inv_break) == 0,
        "detail": (f"비튜닝 stage(S1/S2_1/S5) 독립판정 OLD==NEW 전 픽 성립 "
                   f"(위반 0건). 등가검증 mismatch 총 {total_mismatch}건, "
                   f"NEW 원복 전건 확인={restored_ok_all}."
                   if not inv_break else
                   f"★불변식 위반 {len(inv_break)}건: {inv_break}"),
        "violations": inv_break,
        "equivalence_mismatch_total": total_mismatch,
        "restored_to_new_all": restored_ok_all,
    }

    result = {
        "constants_used": {
            "OLD": {"_MA60_MA306_TOLERANCE":0.025,"_CLOSE_VS_MA612_LOWER":-0.15,
                    "_CLOSE_VS_MA612_UPPER":0.5,"_THRESHOLD_FOREIGN_CONSEC_SELL":2},
            "NEW": {"_MA60_MA306_TOLERANCE":0.07,"_CLOSE_VS_MA612_LOWER":-0.30,
                    "_CLOSE_VS_MA612_UPPER":1.0,"_THRESHOLD_FOREIGN_CONSEC_SELL":5},
            "finance_policy": "require (production filter_today default)",
            "head": "f0aafbd", "driver": str(DRIVER),
            "stage_map": {"s1":"chart60_120(비튜닝)","s2":"chart240(튜닝 tol)",
                          "s2_1":"chartDayPre(비튜닝)","s3":"chartDay(튜닝 c612 lo/up)",
                          "s4":"investor(튜닝 consec)","s5":"finance(하드코딩·비튜닝)"},
        },
        "aggregate": aggregate,
        "per_day": per_day,
        "per_pick": per_pick,
        "flips": flips,
        "invariant_untuned_identical": invariant,
        "ledger": ledger,
    }
    OUT.mkdir(parents=True, exist_ok=True)
    json.dump(result, open(OUT / "ledger.json", "w"), ensure_ascii=False,
              indent=1, default=str)
    print(json.dumps({"aggregate": aggregate,
                      "flips": flips,
                      "invariant": {"holds": invariant["holds"],
                                    "mismatch": total_mismatch,
                                    "restored": restored_ok_all},
                      "n_per_pick": len(per_pick)},
                     ensure_ascii=False, indent=1))
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
