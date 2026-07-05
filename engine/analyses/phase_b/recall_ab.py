"""Phase B — OLD/NEW 상수 A/B 재평가 드라이버 (as-shipped 충실).

목적
----
Phase B 튜닝 4상수의 OLD↔NEW 전환을 **실제 엔진 evaluate_* 로직**으로 재평가한다.
4상수는 모두 evaluate_* **호출시점에 모듈전역**으로 읽히므로(default-arg/closure 캡처
아님 — 코드 확인 완료), 런타임 오버라이드(모듈속성 재대입)가 as-shipped 와 동일하다.
따라서 격리 worktree 물리스왑은 불필요하다.

  chart240Filter._MA60_MA306_TOLERANCE      OLD 0.025 ↔ NEW 0.07
  chartDayFilter._CLOSE_VS_MA612_LOWER      OLD -0.15 ↔ NEW -0.30
  chartDayFilter._CLOSE_VS_MA612_UPPER      OLD 0.50  ↔ NEW 1.00
  investorFilter._THRESHOLD_FOREIGN_CONSEC_SELL  OLD 2 ↔ NEW 5

Stage 모듈 매핑 (facade._run_filter_pipeline 와 동일 순서)::

    stage1   chart60_120Filter.evaluate_chart60_120  (chart60.md + chart120.md)
    stage2   chart240Filter.evaluate_chart240        (chart240.md)   ← 튜닝(s2_t)
    stage2_1 chartDayPreFilter.evaluate_chartday_pre (chartDay.md)
    stage3   chartDayFilter.evaluate_chartday        (chartDay.md)   ← 튜닝(c612 lo/up)
    stage4   investorFilter.evaluate_investor        (investor.md)   ← 튜닝(foreign consec)
    stage5   financeFilter.evaluate_finance          (finance.md, 하드코딩·비튜닝)

산출: analyses/phase_b/out/recall_ab/<date>_<constants>.json (골든 reports/ 무접촉).
메인트리 필터소스는 편집하지 않는다(런타임 오버라이드는 in-process, 파일 불변).

등가검증: margin_extract 의 파라미터화 mirror(P-dict)를 독립 2차 계산으로 사용,
각 stage 에서 real evaluate_*(오버라이드) 와 mirror(P_mode) 결과 일치 여부 카운트.

사용::

    .venv/bin/python analyses/phase_b/recall_ab.py \
        --constants new --date 20260528 --picks-from-master
    .venv/bin/python analyses/phase_b/recall_ab.py \
        --constants old --date 20260528 --picks "아이텍,DYP,조선내화"
"""
from __future__ import annotations

import argparse
import copy
import json
import sys
from pathlib import Path

ENGINE = Path("/Users/tajun/spJavis/auto-korea-stock-javis/engine")
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

# ── 엔진 상수 모듈 (런타임 오버라이드 타깃) ──
from src.kiwoom.itemFilter import chart240Filter as m_s2
from src.kiwoom.itemFilter import chartDayFilter as m_s3
from src.kiwoom.itemFilter import investorFilter as m_s4

# ── 엔진 파서 + 오라클 evaluate_* (재구현 금지 — 실제 로직) ──
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

# ── 등가검증용 mirror(파라미터화) + P0(=OLD 라이브 스냅샷) ──
from analyses.phase_b.margin_extract import (
    P0, mirror_stage1, mirror_stage2, mirror_stage21,
    mirror_stage3, mirror_stage4, mirror_stage5,
)

REPORTS = ENGINE / "reports"
OUT = ENGINE / "analyses/phase_b/out/recall_ab"

# ── A/B 상수 정의 (SOT) ──
OLD = {
    "s2_MA60_MA306_TOLERANCE": 0.025,
    "s3_CLOSE_VS_MA612_LOWER": -0.15,
    "s3_CLOSE_VS_MA612_UPPER": 0.50,
    "s4_THRESHOLD_FOREIGN_CONSEC_SELL": 2,
}
NEW = {
    "s2_MA60_MA306_TOLERANCE": 0.07,
    "s3_CLOSE_VS_MA612_LOWER": -0.30,
    "s3_CLOSE_VS_MA612_UPPER": 1.00,
    "s4_THRESHOLD_FOREIGN_CONSEC_SELL": 5,
}


def _p_dict(consts: dict) -> dict:
    """P0(OLD 스냅샷) 위에 A/B 4상수를 덮어 mirror 용 P-dict 생성."""
    P = copy.deepcopy(P0)
    P["s2_t"] = consts["s2_MA60_MA306_TOLERANCE"]
    P["s3_c612lo"] = consts["s3_CLOSE_VS_MA612_LOWER"]
    P["s3_c612up"] = consts["s3_CLOSE_VS_MA612_UPPER"]
    P["s4_fc"] = consts["s4_THRESHOLD_FOREIGN_CONSEC_SELL"]
    return P


class ConstantOverride:
    """4상수를 in-process 로 오버라이드하고, 종료 시 원복(NEW 원상)."""

    def __init__(self, consts: dict):
        self.consts = consts
        self._saved: dict = {}

    def __enter__(self):
        self._saved = {
            (m_s2, "_MA60_MA306_TOLERANCE"): m_s2._MA60_MA306_TOLERANCE,
            (m_s3, "_CLOSE_VS_MA612_LOWER"): m_s3._CLOSE_VS_MA612_LOWER,
            (m_s3, "_CLOSE_VS_MA612_UPPER"): m_s3._CLOSE_VS_MA612_UPPER,
            (m_s4, "_THRESHOLD_FOREIGN_CONSEC_SELL"): m_s4._THRESHOLD_FOREIGN_CONSEC_SELL,
        }
        m_s2._MA60_MA306_TOLERANCE = self.consts["s2_MA60_MA306_TOLERANCE"]
        m_s3._CLOSE_VS_MA612_LOWER = self.consts["s3_CLOSE_VS_MA612_LOWER"]
        m_s3._CLOSE_VS_MA612_UPPER = self.consts["s3_CLOSE_VS_MA612_UPPER"]
        m_s4._THRESHOLD_FOREIGN_CONSEC_SELL = self.consts["s4_THRESHOLD_FOREIGN_CONSEC_SELL"]
        return self

    def __exit__(self, *exc):
        for (mod, attr), val in self._saved.items():
            setattr(mod, attr, val)
        return False


# ═══════════════════════════════════════════════════════════════════
# 픽 → 코드 → 폴더 해석 (엔진 name_resolver, naive substring 금지)
# ═══════════════════════════════════════════════════════════════════

def _folder_map(ddir: Path) -> dict[str, tuple[str, str]]:
    """{종목명: (코드, 폴더명)} — 당일 폴더 스캔."""
    out: dict[str, tuple[str, str]] = {}
    for x in ddir.iterdir():
        if x.is_dir():
            p = _split_stock_dirname(x.name)
            if p:
                out[p[0]] = (p[1], x.name)
    return out


def resolve_pick(name: str, ddir: Path, folder_map: dict, name_to_code: dict,
                 union_map: dict) -> tuple[str, str, Path | None, str]:
    """픽 이름 → (name, code, folder_path|None, method). 엔진 규칙만 사용.

    우선순위: (1) 이름(코드) 포맷 → 괄호 코드, (2) name_resolver(condition/upper),
    (3) 당일 폴더 정확 매치, (4) 디스크 유니언맵. naive substring 미사용.
    """
    nm, cd = _parse_entry(name)
    code_to_folder = {c: f for (n, (c, f)) in folder_map.items()}
    if cd:
        f = code_to_folder.get(cd)
        return nm, cd, (ddir / f) if f else None, "explicit-code"
    if nm in name_to_code:
        c = name_to_code[nm]
        f = code_to_folder.get(c)
        return nm, c, (ddir / f) if f else None, "name_resolver"
    if nm in folder_map:
        c, f = folder_map[nm]
        return nm, c, ddir / f, "folder-exact"
    if nm in union_map:
        c = union_map[nm]
        f = code_to_folder.get(c)
        return nm, c, (ddir / f) if f else None, "disk-union"
    return nm, "", None, "UNRESOLVED"


# ═══════════════════════════════════════════════════════════════════
# 단일 픽 6-stage 평가 (real evaluate_* + mirror 등가검증)
# ═══════════════════════════════════════════════════════════════════

def _parse_all(folder: Path):
    def g(fn, fname):
        p = folder / fname
        return fn(p) if p.exists() else ([], {})
    b60, _ = g(parse_chart60_md, "chart60.md")
    b120, _ = g(parse_chart120_md, "chart120.md")
    b240, _ = g(parse_chart240_md, "chart240.md")
    bD, _ = g(parse_chartday_md, "chartDay.md")
    inv, _ = g(parse_investor_md, "investor.md")
    cup, fin_invalid, fin_present = None, False, False
    fp = folder / "finance.md"
    if fp.exists():
        fin_present = True
        try:
            fin_invalid = _is_invalid_md(fp)
            cup, _ = parse_finance_md(fp)
        except (ValueError, FileNotFoundError):
            cup = None
    return b60, b120, b240, bD, inv, cup, fin_invalid, fin_present


def eval_pick(folder: Path, P: dict, finance_policy: str):
    """6-stage per-stage (selected, reason) via real evaluate_*  +  mirror 등가.

    real evaluate_* 는 오버라이드된 모듈전역을 호출시점에 읽는다(as-shipped).
    mirror_* 는 P-dict 를 읽는다(독립 2차 계산). 두 결과 stage별 비교 → mismatch.
    """
    b60, b120, b240, bD, inv, cup, fin_invalid, fin_present = _parse_all(folder)
    stages: dict[str, dict] = {}
    mism = 0

    # stage1 (비튜닝) — b60 & b120 필요
    if b60 and b120:
        r_sel, r_cat, r_rsn, _ = evaluate_chart60_120(b60, b120)
        m_sel, m_cat = mirror_stage1(b60, b120, P)
        eq = (r_sel, r_cat if r_sel else None) == (m_sel, m_cat if m_sel else None)
        mism += 0 if eq else 1
        stages["stage1"] = {"selected": r_sel, "category": r_cat, "reason": r_rsn,
                            "mirror_selected": m_sel, "match": eq}
    else:
        stages["stage1"] = {"selected": None, "reason": "chart60/120 데이터 부재",
                            "mirror_selected": None, "match": None}

    # stage2 (튜닝 s2_t)
    if b240:
        r_sel, r_cat, r_rsn, _ = evaluate_chart240(b240)
        m_sel = mirror_stage2(b240, P)
        eq = r_sel == m_sel
        mism += 0 if eq else 1
        stages["stage2"] = {"selected": r_sel, "category": r_cat, "reason": r_rsn,
                            "mirror_selected": m_sel, "match": eq}
    else:
        stages["stage2"] = {"selected": None, "reason": "chart240 데이터 부재",
                            "mirror_selected": None, "match": None}

    # stage2_1 (비튜닝)
    if bD:
        r_sel, r_cat, r_rsn, _ = evaluate_chartday_pre(bD)
        m_sel = mirror_stage21(bD, P)
        eq = r_sel == m_sel
        mism += 0 if eq else 1
        stages["stage2_1"] = {"selected": r_sel, "category": r_cat, "reason": r_rsn,
                              "mirror_selected": m_sel, "match": eq}
    else:
        stages["stage2_1"] = {"selected": None, "reason": "chartDay 데이터 부재",
                              "mirror_selected": None, "match": None}

    # stage3 (튜닝 c612 lo/up)
    if bD:
        r_sel, r_cat, r_rsn, _ = evaluate_chartday(bD)
        m_sel = mirror_stage3(bD, P)
        eq = r_sel == m_sel
        mism += 0 if eq else 1
        stages["stage3"] = {"selected": r_sel, "category": r_cat, "reason": r_rsn,
                            "mirror_selected": m_sel, "match": eq}
    else:
        stages["stage3"] = {"selected": None, "reason": "chartDay 데이터 부재",
                            "mirror_selected": None, "match": None}

    # stage4 (튜닝 foreign consec)
    if inv:
        r_sel, r_cat, r_rsn, _ = evaluate_investor(inv)
        m_sel = mirror_stage4(inv, P)
        eq = r_sel == m_sel
        mism += 0 if eq else 1
        stages["stage4"] = {"selected": r_sel, "category": r_cat, "reason": r_rsn,
                            "mirror_selected": m_sel, "match": eq}
    else:
        stages["stage4"] = {"selected": None, "reason": "investor 데이터 부재",
                            "mirror_selected": None, "match": None}

    # stage5 (하드코딩·비튜닝) — finance_policy 반영
    if fin_present:
        r_sel, r_cat, r_rsn, _ = evaluate_finance(cup, invalid=fin_invalid)
        m_sel = mirror_stage5(cup)
        eq = r_sel == m_sel
        mism += 0 if eq else 1
        stages["stage5"] = {"selected": r_sel, "category": r_cat, "reason": r_rsn,
                            "mirror_selected": m_sel, "match": eq}
    else:
        if finance_policy == "skip_na":
            stages["stage5"] = {"selected": True, "category": "선정",
                                "reason": "finance N/A — skip_na 통과",
                                "mirror_selected": True, "match": True}
        else:
            stages["stage5"] = {"selected": False, "category": "제외",
                                "reason": "finance 데이터 부재 — require 탈락",
                                "mirror_selected": False, "match": True}

    # facade 순차 최종판정 (첫 False 에서 break)
    order = ["stage1", "stage2", "stage2_1", "stage3", "stage4", "stage5"]
    final_selected = True
    break_at = None
    for s in order:
        sel = stages[s]["selected"]
        if sel is None:
            final_selected = False
            break_at = s + ":데이터부재"
            break
        if not sel:
            final_selected = False
            break_at = s
            break
    return stages, final_selected, break_at, mism


# ═══════════════════════════════════════════════════════════════════
# 메인
# ═══════════════════════════════════════════════════════════════════

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--constants", choices=["old", "new"], required=True)
    ap.add_argument("--date", required=True, help="YYYYMMDD (reports/ 하위)")
    ap.add_argument("--picks", default=None, help="쉼표구분 종목명(또는 이름(코드))")
    ap.add_argument("--picks-from-master", action="store_true",
                    help="reports/<date>/masterReference.md 픽 사용")
    ap.add_argument("--finance-policy", default="require",
                    choices=["require", "skip_na"],
                    help="Stage5 재무정책 (프로덕션 filter_today 기본=require; "
                         "backfill=skip_na)")
    args = ap.parse_args()

    consts = OLD if args.constants == "old" else NEW
    P = _p_dict(consts)
    ddir = REPORTS / args.date
    if not ddir.exists():
        print(f"[오류] 날짜 폴더 없음: {ddir}")
        return 2

    # 픽 목록
    if args.picks_from_master:
        mr = ddir / "masterReference.md"
        picks = [l.strip() for l in mr.read_text(encoding="utf-8").splitlines()
                 if l.strip()] if mr.exists() else []
    elif args.picks:
        picks = [p.strip() for p in args.picks.split(",") if p.strip()]
    else:
        print("[오류] --picks 또는 --picks-from-master 필요")
        return 2

    # 해석 인프라 (엔진)
    folder_map = _folder_map(ddir)
    name_to_code = build_name_to_code_map(ddir)
    if not name_to_code:
        name_to_code = {nm: c for nm, (c, _f) in folder_map.items()}
    union_map = build_disk_name_to_code_map([REPORTS, ENGINE / "reports_backfill"])

    out_picks = []
    total_mismatch = 0
    with ConstantOverride(consts):
        # 오버라이드 실측 확인
        applied = {
            "s2_MA60_MA306_TOLERANCE": m_s2._MA60_MA306_TOLERANCE,
            "s3_CLOSE_VS_MA612_LOWER": m_s3._CLOSE_VS_MA612_LOWER,
            "s3_CLOSE_VS_MA612_UPPER": m_s3._CLOSE_VS_MA612_UPPER,
            "s4_THRESHOLD_FOREIGN_CONSEC_SELL": m_s4._THRESHOLD_FOREIGN_CONSEC_SELL,
        }
        assert applied == consts, f"오버라이드 불일치: {applied} != {consts}"

        for name in picks:
            nm, cd, folder, method = resolve_pick(
                name, ddir, folder_map, name_to_code, union_map)
            rec = {"pick": name, "name": nm, "code": cd,
                   "resolve_method": method,
                   "folder": folder.name if folder else None}
            if folder is None or not folder.exists():
                rec["error"] = "폴더 미해석/부재"
                rec["final_selected"] = None
                out_picks.append(rec)
                continue
            stages, final_sel, break_at, mism = eval_pick(
                folder, P, args.finance_policy)
            total_mismatch += mism
            rec["stages"] = stages
            rec["final_selected"] = final_sel
            rec["break_at"] = break_at
            rec["stage_mismatch"] = mism
            out_picks.append(rec)

    result = {
        "date": args.date,
        "constants": args.constants,
        "applied_constants": applied,
        "finance_policy": args.finance_policy,
        "n_picks": len(picks),
        "n_resolved": sum(1 for r in out_picks if r.get("code")),
        "n_final_selected": sum(1 for r in out_picks if r.get("final_selected")),
        "equivalence_mismatch_count": total_mismatch,
        "picks": out_picks,
    }

    # 원복 검증 (NEW 원상)
    restored = {
        "s2": m_s2._MA60_MA306_TOLERANCE,
        "s3lo": m_s3._CLOSE_VS_MA612_LOWER,
        "s3up": m_s3._CLOSE_VS_MA612_UPPER,
        "s4": m_s4._THRESHOLD_FOREIGN_CONSEC_SELL,
    }
    result["restored_after_run"] = restored
    result["restored_to_new"] = (
        restored["s2"] == 0.07 and restored["s3lo"] == -0.30
        and restored["s3up"] == 1.00 and restored["s4"] == 5
    )

    OUT.mkdir(parents=True, exist_ok=True)
    out_path = OUT / f"{args.date}_{args.constants}.json"
    json.dump(result, open(out_path, "w"), ensure_ascii=False, indent=1, default=str)

    print(f"=== recall_ab [{args.date}] constants={args.constants} "
          f"finance_policy={args.finance_policy} ===")
    print(f"  적용상수: {applied}")
    print(f"  픽 {len(picks)} / 해석 {result['n_resolved']} / "
          f"최종선정 {result['n_final_selected']}")
    print(f"  등가검증 mismatch: {total_mismatch} "
          f"({'OK 0-mismatch' if total_mismatch == 0 else '★불일치'})")
    print(f"  원복 NEW 원상: {result['restored_to_new']}")
    print(f"  산출: {out_path}")
    for r in out_picks:
        if not r.get("code"):
            print(f"    - {r['pick']}: {r['resolve_method']} (미해석)")
            continue
        chain = " ".join(
            f"{s.split('stage')[1]}:{'O' if r['stages'][s]['selected'] else ('-' if r['stages'][s]['selected'] is None else 'X')}"
            for s in ["stage1", "stage2", "stage2_1", "stage3", "stage4", "stage5"]
        )
        print(f"    - {r['name']}({r['code']}) [{r['resolve_method']}] "
              f"final={'선정' if r['final_selected'] else '탈락@'+str(r['break_at'])} | {chain}")
    return 0 if total_mismatch == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
