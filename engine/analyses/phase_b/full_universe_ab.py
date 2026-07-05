"""Phase B — 전체 수집 유니버스 OLD/NEW 상수 A/B 재평가 드라이버 (as-shipped).

목적
----
각 거래일 ``reports/<date>/organizedCompany.md`` 의 **전체 수집 종목**을 프로덕션
``filter_today`` 와 동일한 as-shipped 6-stage 파이프라인(per-stock 독립·finance
_policy="require")에 통과시켜, OLD 상수·NEW 상수 각각에 대해 stage별 누적
생존수(파이프라인 단락) + 최종수를 산출한다.

검증완료 driver ``analyses/phase_b/recall_ab.py`` 의 아래를 **그대로 재사용**한다:
  - in-process ``ConstantOverride`` (4상수 모듈전역 재대입, __exit__ NEW 원복)
  - ``eval_pick`` — 실제 엔진 evaluate_*(오라클) + margin mirror 등가검증
  - ``resolve_pick`` / ``_folder_map`` — 엔진 name_resolver 코드해석
  - ``OLD`` / ``NEW`` 상수 SOT, ``_p_dict``

픽 대신 organizedCompany.md 전체 종목을 순회한다. 픽 부분집합으로 교집합하면
recall_ab.py 의 per_pick 결과와 정확히 일치해야 한다(동일 eval_pick·per-stock 독립).

4상수 (recall_ab SOT 와 동일)::
  chart240Filter._MA60_MA306_TOLERANCE      OLD 0.025 ↔ NEW 0.07
  chartDayFilter._CLOSE_VS_MA612_LOWER      OLD -0.15 ↔ NEW -0.30
  chartDayFilter._CLOSE_VS_MA612_UPPER      OLD 0.50  ↔ NEW 1.00
  investorFilter._THRESHOLD_FOREIGN_CONSEC_SELL  OLD 2 ↔ NEW 5

Stage (facade._run_filter_pipeline 순서)::
  s1   chart60_120  (비튜닝)
  s2   chart240     (튜닝)
  s2_1 chartDayPre  (비튜닝)
  s3   chartDay     (튜닝)
  s4   investor     (튜닝)
  s5   finance      (비튜닝·require) = final

산출: analyses/phase_b/out/full_ab/<date>.json  (골든 reports/ 무접촉).
메인트리 필터소스 무수정(런타임 오버라이드는 in-process). API 0회(순수 디스크).

사용::
  .venv/bin/python -m analyses.phase_b.full_universe_ab 20260703
  .venv/bin/python -m analyses.phase_b.full_universe_ab --all
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ENGINE = Path("/Users/tajun/spJavis/auto-korea-stock-javis/engine")
if str(ENGINE) not in sys.path:
    sys.path.insert(0, str(ENGINE))

# ── 검증완료 recall_ab driver 재사용 (재구현 금지) ──
from analyses.phase_b.recall_ab import (
    OLD, NEW, ConstantOverride, _p_dict, eval_pick, resolve_pick, _folder_map,
    m_s2, m_s3, m_s4,
)
from src.kiwoom.researchFlow.facade import _load_stock_names, _ORGANIZED_FILE
from src.kiwoom.researchFlow.name_resolver import build_name_to_code_map
from src.kiwoom.researchFlow.expert_backfill import build_disk_name_to_code_map

REPORTS = ENGINE / "reports"
OUT = ENGINE / "analyses/phase_b/out/full_ab"
HEAD = "f0aafbd"

ORDER = ["stage1", "stage2", "stage2_1", "stage3", "stage4", "stage5"]
STAGE_KEY = {"stage1": "s1", "stage2": "s2", "stage2_1": "s2_1",
             "stage3": "s3", "stage4": "s4", "stage5": "s5"}


def _reached_count(final_selected: bool, break_at: str | None) -> int:
    """파이프라인에서 통과(survive)한 stage 수 (0..6).

    break_at 은 eval_pick 이 반환하는 첫 탈락 지점 ("stageX" 또는 "stageX:데이터부재").
    final_selected → 6 stage 전부 survive. 아니면 break stage 이전까지만 survive.
    """
    if final_selected:
        return len(ORDER)
    if not break_at:
        return 0
    base = break_at.split(":")[0]
    return ORDER.index(base) if base in ORDER else 0


def _classify_s5(final_selected: bool, break_at: str | None,
                 stages: dict) -> str | None:
    """stage5(=final) 도달 종목의 판정 분류.

    반환: "reached_pass" | "reached_fail_적자" | "reached_fail_nodata" | None(미도달).
    """
    reached_s5 = final_selected or (break_at is not None
                                    and break_at.split(":")[0] == "stage5")
    if not reached_s5:
        return None
    if final_selected:
        return "reached_pass"
    reason = (stages.get("stage5", {}) or {}).get("reason", "") or ""
    if "적자" in reason:
        return "reached_fail_적자"
    if "부재" in reason or "결측" in reason:
        return "reached_fail_nodata"
    # evaluate_finance 는 present-invalid/None 을 통과시키므로 여기 오면 안 됨.
    return "reached_fail_기타"


def evaluate_universe(date: str, consts: dict, finance_policy: str = "require"):
    """단일 상수셋으로 전체 유니버스 6-stage 평가 → 집계 + per_stock.

    ConstantOverride 하에서 recall_ab.eval_pick 을 전 종목에 적용(프로덕션
    filter_today 와 동일 per-stock 독립 경로). API 0회.
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

    P = _p_dict(consts)
    surv = {s: 0 for s in ORDER}
    final_n = 0
    evaluated_n = 0
    unresolved = []
    finance_present_n = 0
    s5b = {"reached": 0, "pass": 0, "fail_적자": 0, "fail_nodata": 0, "fail_기타": 0}
    total_mismatch = 0
    per_stock = {}

    with ConstantOverride(consts):
        applied = {
            "s2_MA60_MA306_TOLERANCE": m_s2._MA60_MA306_TOLERANCE,
            "s3_CLOSE_VS_MA612_LOWER": m_s3._CLOSE_VS_MA612_LOWER,
            "s3_CLOSE_VS_MA612_UPPER": m_s3._CLOSE_VS_MA612_UPPER,
            "s4_THRESHOLD_FOREIGN_CONSEC_SELL": m_s4._THRESHOLD_FOREIGN_CONSEC_SELL,
        }
        assert applied == consts, f"오버라이드 불일치: {applied} != {consts}"

        for nm in names:
            _nm, cd, folder, method = resolve_pick(
                nm, ddir, folder_map, name_to_code, union_map)
            if folder is None or not folder.exists():
                unresolved.append(nm)
                per_stock.setdefault(cd or f"UNRESOLVED::{nm}", {})
                per_stock[cd or f"UNRESOLVED::{nm}"] = {
                    "name": _nm, "code": cd, "resolve_method": method,
                    "final": None, "break_at": None, "stage_selected": None,
                    "error": "폴더 미해석/부재",
                }
                continue
            evaluated_n += 1
            if (folder / "finance.md").exists():
                finance_present_n += 1
            try:
                stages, final_sel, break_at, mism = eval_pick(
                    folder, P, finance_policy)
            except Exception as exc:  # noqa: BLE001
                # 프로덕션 filter_today 는 _run_filter_pipeline 전체를 try/except 로
                # 감싸 어떤 stage 예외든 stages=[] · final_selected=False 로 스킵한다
                # (facade.py). 손상된 md(파싱 실패) 종목이 여기 해당 → reached 0.
                per_stock[cd] = {
                    "name": _nm, "code": cd, "resolve_method": method,
                    "final": False, "break_at": "예외스킵",
                    "stage_selected": {s: None for s in ORDER},
                    "error": f"{type(exc).__name__}: {exc}",
                }
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

            per_stock[cd] = {
                "name": _nm, "code": cd, "resolve_method": method,
                "final": final_sel, "break_at": break_at,
                "stage_selected": {s: stages[s]["selected"] for s in ORDER},
            }

    agg = {STAGE_KEY[s]: surv[s] for s in ORDER}
    agg["final"] = final_n
    agg["s5_breakdown"] = s5b
    return {
        "applied_constants": applied,
        "universe_n": universe_n,
        "evaluated_n": evaluated_n,
        "unresolved_n": len(unresolved),
        "finance_present_n": finance_present_n,
        "agg": agg,
        "equivalence_mismatch_count": total_mismatch,
        "unresolved": unresolved,
        "per_stock": per_stock,
    }


def run_date(date: str, finance_policy: str = "require", write: bool = True):
    ddir = REPORTS / date
    if not (ddir / _ORGANIZED_FILE).exists():
        raise FileNotFoundError(f"organizedCompany.md 없음: {ddir}")

    old_r = evaluate_universe(date, OLD, finance_policy)
    new_r = evaluate_universe(date, NEW, finance_policy)

    # 원복 검증 (NEW 원상)
    restored = {
        "s2": m_s2._MA60_MA306_TOLERANCE, "s3lo": m_s3._CLOSE_VS_MA612_LOWER,
        "s3up": m_s3._CLOSE_VS_MA612_UPPER, "s4": m_s4._THRESHOLD_FOREIGN_CONSEC_SELL,
    }
    restored_to_new = (restored["s2"] == 0.07 and restored["s3lo"] == -0.30
                       and restored["s3up"] == 1.00 and restored["s4"] == 5)

    universe_n = old_r["universe_n"]
    fin_present = old_r["finance_present_n"]
    result = {
        "date": date,
        "head": HEAD,
        "driver": str(ENGINE / "analyses/phase_b/full_universe_ab.py"),
        "finance_policy": finance_policy,
        "constants": {"OLD": OLD, "NEW": NEW},
        "stage_map": {"s1": "chart60_120(비튜닝)", "s2": "chart240(튜닝)",
                      "s2_1": "chartDayPre(비튜닝)", "s3": "chartDay(튜닝)",
                      "s4": "investor(튜닝)", "s5": "finance(비튜닝·require)=final"},
        "universe_n": universe_n,
        "evaluated_n": old_r["evaluated_n"],
        "unresolved_n": old_r["unresolved_n"],
        "finance_coverage": {
            "finance_md_present": fin_present,
            "universe_n": universe_n,
            "pct": round(100.0 * fin_present / universe_n, 2) if universe_n else 0.0,
        },
        "old": old_r["agg"],
        "new": new_r["agg"],
        "equivalence_mismatch_count": (old_r["equivalence_mismatch_count"]
                                       + new_r["equivalence_mismatch_count"]),
        "restored_after_run": restored,
        "restored_to_new": restored_to_new,
        "unresolved": old_r["unresolved"],
        "per_stock": {"old": old_r["per_stock"], "new": new_r["per_stock"]},
    }

    if write:
        OUT.mkdir(parents=True, exist_ok=True)
        out_path = OUT / f"{date}.json"
        json.dump(result, open(out_path, "w"), ensure_ascii=False, indent=1,
                  default=str)
        result["_out_path"] = str(out_path)

    o, n = result["old"], result["new"]
    print(f"=== full_universe_ab [{date}] fp={finance_policy} ===")
    print(f"  universe={universe_n} evaluated={result['evaluated_n']} "
          f"unresolved={result['unresolved_n']} "
          f"finance={fin_present}/{universe_n} "
          f"({result['finance_coverage']['pct']}%)")
    print(f"  OLD funnel s1={o['s1']} s2={o['s2']} s2_1={o['s2_1']} "
          f"s3={o['s3']} s4={o['s4']} s5={o['s5']} FINAL={o['final']}")
    print(f"      s5_breakdown={o['s5_breakdown']}")
    print(f"  NEW funnel s1={n['s1']} s2={n['s2']} s2_1={n['s2_1']} "
          f"s3={n['s3']} s4={n['s4']} s5={n['s5']} FINAL={n['final']}")
    print(f"      s5_breakdown={n['s5_breakdown']}")
    print(f"  등가 mismatch={result['equivalence_mismatch_count']} "
          f"원복 NEW 원상={restored_to_new}")
    if write:
        print(f"  산출: {result['_out_path']}")
    return result


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("date", nargs="?", default=None, help="YYYYMMDD")
    ap.add_argument("--all", action="store_true",
                    help="reports/ 하위 organizedCompany.md 보유 전 거래일 실행")
    ap.add_argument("--finance-policy", default="require",
                    choices=["require", "skip_na"])
    args = ap.parse_args()

    if args.all:
        dates = sorted(p.parent.name for p in REPORTS.glob("*/organizedCompany.md")
                       if p.parent.name.isdigit())
        rc = 0
        for d in dates:
            try:
                r = run_date(d, args.finance_policy)
                if r["equivalence_mismatch_count"] != 0 or not r["restored_to_new"]:
                    rc = 1
            except Exception as exc:  # noqa: BLE001
                print(f"[{d}] 실패: {exc}", file=sys.stderr)
                rc = 1
        return rc

    if not args.date:
        print("[오류] <YYYYMMDD> 또는 --all 필요", file=sys.stderr)
        return 2
    r = run_date(args.date, args.finance_policy)
    return 0 if r["equivalence_mismatch_count"] == 0 and r["restored_to_new"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
