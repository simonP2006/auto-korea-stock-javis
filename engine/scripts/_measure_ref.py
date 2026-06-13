"""Measure which masterReference stocks pass run_filters (in researchedCompany.md)."""
import sys, re
from pathlib import Path
REPORTS = Path(__file__).resolve().parents[1] / "reports"
NAMECODE = re.compile(r"^(?P<nm>.*?)\((?P<cd>\d{4,6})\)\s*$")

def ref_names(date):
    p = REPORTS/date/"masterReference.md"
    out=[]
    if p.exists():
        for ln in p.read_text(encoding="utf-8").splitlines():
            s=ln.strip()
            if not s: continue
            m=NAMECODE.match(s)
            out.append(m.group("nm").strip() if m else s)
    return out

def researched(date):
    p = REPORTS/date/"researchedCompany.md"
    if not p.exists(): return set()
    return {ln.strip() for ln in p.read_text(encoding="utf-8").splitlines() if ln.strip()}

dates = sys.argv[1:] or ["20260518","20260519","20260520","20260521","20260522","20260528","20260529","20260601"]
tot_p=tot=0
for d in dates:
    rc=researched(d); refs=ref_names(d)
    passed=[n for n in refs if n in rc]
    failed=[n for n in refs if n not in rc]
    tot+=len(refs); tot_p+=len(passed)
    print(f"[{d}] ref={len(refs)} PASS={len(passed)} FAIL={len(failed)} | researched_total={len(rc)}")
    if passed: print(f"    ✅ {', '.join(passed)}")
    if failed: print(f"    ❌ {', '.join(failed)}")
print(f"TOTAL ref={tot} PASS={tot_p} FAIL={tot-tot_p}")
