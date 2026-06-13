"""ONE-OFF AUDIT (temp): masterReference 종목 × 6-Stage 통과/탈락 정밀 평가.

각 날짜의 masterReference.md 종목을 현재 Final 상수(=현재 filtering 조건)로
6개 Stage 필터에 **독립 재평가**한다. 캐시된 prefetch 데이터만 사용(API 無).
종목은 6개 Stage 전부 selected=True 일 때만 최종 통과로 간주한다.

출력: JSON(stdout) — date → stock → {stages, overall_pass}.
"""
from __future__ import annotations

import json
import sys
import traceback
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from src.kiwoom.itemFilter import (  # noqa: E402
    chart60_120_filter_stock,
    chart240_filter_stock,
    chartday_filter_stock,
    chartday_pre_filter_stock,
    finance_filter_stock,
    investor_filter_stock,
)
from src.kiwoom.researchFlow.name_resolver import build_name_to_code_map  # noqa: E402

REPORTS = Path("reports")

STAGES = [
    ("Stage 1", "chart60_120", chart60_120_filter_stock),
    ("Stage 2", "chart240", chart240_filter_stock),
    ("Stage 2-1", "chartDayPre", chartday_pre_filter_stock),
    ("Stage 3", "chartDay", chartday_filter_stock),
    ("Stage 4", "investor", investor_filter_stock),
    ("Stage 5", "finance", finance_filter_stock),
]

# 비어있지 않은 reference 날짜 (20260516/26/27/0602 = 빈 파일 제외).
DATES = [
    "20260514", "20260515", "20260518", "20260519", "20260520",
    "20260521", "20260522", "20260528", "20260529", "20260601",
]


def parse_entry(line: str):
    s = line.strip()
    if s.endswith(")") and "(" in s:
        nm, _, rest = s.rpartition("(")
        cd = rest[:-1]
        if cd.isdigit():
            return nm.strip(), cd
    return s, ""


def read_master(date: str):
    p = REPORTS / date / "masterReference.md"
    if not p.exists():
        return []
    out = []
    for raw in p.read_text(encoding="utf-8").splitlines():
        if raw.strip():
            out.append(parse_entry(raw))
    return out


def resolve_ident(name: str, code: str, code_map: dict) -> str:
    if code:
        return code
    return code_map.get(name, "") or name


def eval_stage(filter_fn, ident: str, date: str):
    try:
        r = filter_fn(ident, date_dir=date, reports_root=REPORTS)
    except FileNotFoundError as exc:
        return {"selected": None, "category": "DATA_MISSING",
                "reason": f"입력 데이터 없음: {exc}", "error": True}
    except Exception as exc:  # noqa: BLE001
        return {"selected": None, "category": "EVAL_ERROR",
                "reason": f"{type(exc).__name__}: {exc}", "error": True}
    return {
        "selected": bool(getattr(r, "selected", False)),
        "category": str(getattr(r, "category", "")),
        "reason": str(getattr(r, "reason", "")),
        "error": False,
    }


def main() -> int:
    result = {}
    for date in DATES:
        date_dir = REPORTS / date
        code_map = build_name_to_code_map(date_dir) if date_dir.exists() else {}
        stocks = read_master(date)
        date_block = {"reference_count": len(stocks), "stocks": {}}
        for nm, cd in stocks:
            ident = resolve_ident(nm, cd, code_map)
            disp = f"{nm}({cd})" if cd else nm
            stage_results = {}
            for label, sname, fn in STAGES:
                stage_results[label] = {"stage_name": sname,
                                        **eval_stage(fn, ident, date)}
            sel_flags = [stage_results[l]["selected"] for l, _, _ in STAGES]
            any_missing = any(s is None for s in sel_flags)
            overall = (not any_missing) and all(s for s in sel_flags)
            fail_stages = [
                l for l, _, _ in STAGES
                if stage_results[l]["selected"] is False
            ]
            missing_stages = [
                l for l, _, _ in STAGES
                if stage_results[l]["selected"] is None
            ]
            date_block["stocks"][disp] = {
                "ident": ident,
                "name": nm,
                "code": cd,
                "overall_pass": overall,
                "has_missing_data": any_missing,
                "fail_stages": fail_stages,
                "missing_stages": missing_stages,
                "stages": stage_results,
            }
        result[date] = date_block
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except Exception:
        traceback.print_exc()
        raise SystemExit(2)
