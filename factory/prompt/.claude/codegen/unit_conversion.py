#!/usr/bin/env python3
"""
Unit-conversion SOT + round-trip oracle (Candidate #2 / MISS #2).

filter-tune converts a user's spoken percentage into a `Final` literal before
Edit-ing production code. A wrong conversion silently writes 0.95 where the user
meant 0.05 — corrupting the live filter — and NO current test exercises this
(the structural pytest layer never runs the tuning path). This module is the
deterministic reference implementation + a round-trip assertion.

Canonical invariant (unifies loosening/tightening and the signed-literal case):

        multiplier = 1 + signed_pct / 100
        signed_pct = (multiplier - 1) * 100
        raw_magnitude = |signed_pct| / 100

  -5%  -> 0.95   |  -1.5% -> 0.985  |  -15% -> 0.85
  +45% -> 1.45   |  +50%  -> 1.50

It also VALIDATES the deployed unit-conversion.md "Examples (tolerance)" table:
for every row, multiplier MUST equal 1 + signed_pct/100 and the raw magnitude
MUST equal |signed_pct|/100 — catching doc drift deterministically.

Read-only. Exit 0 = self-test + doc-validation pass. Exit 1 = mismatch.

NOTE: wiring this into the filter-tune skill at Edit time (so it runs for the
real user) is the DEFERRED 유용 item — a product (kiwoom-rest-trader) change
under CCP that requires SEPARATE approval. It is intentionally NOT applied here.
"""
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))


def _resolve_doc():
    """Portable so this file is byte-identical in both locations (see param_ast)."""
    local = HERE.parent / "references" / "unit-conversion.md"
    if local.exists():
        return local                            # deployed-in-product layout
    try:
        from infra_schema import KRT_ROOT       # AgenticWorkflow source layout
        return Path(KRT_ROOT) / ".claude" / "skills" / "filter-tune" / "references" / "unit-conversion.md"
    except Exception:
        return local


DOC = _resolve_doc()
EPS = 1e-9


# === Canonical conversions (the SOT) ======================================
def multiplier_from_signed_pct(signed_pct: float) -> float:
    return 1.0 + signed_pct / 100.0


def signed_pct_from_multiplier(multiplier: float) -> float:
    return (multiplier - 1.0) * 100.0


def raw_magnitude_from_pct(signed_pct: float) -> float:
    return abs(signed_pct) / 100.0


def round_trip_ok(signed_pct: float) -> bool:
    return abs(signed_pct_from_multiplier(multiplier_from_signed_pct(signed_pct)) - signed_pct) < EPS


# === Self-test over the documented examples ===============================
# (signed_pct, raw_magnitude, multiplier) — verbatim from unit-conversion.md
EXAMPLES = [
    (-5.0, 0.05, 0.95),
    (-3.0, 0.03, 0.97),
    (-1.5, 0.015, 0.985),
    (-3.5, 0.035, 0.965),
    (-15.0, 0.15, 0.85),
    (45.0, 0.45, 1.45),
    (50.0, 0.50, 1.50),
]


def self_test():
    errors = []
    for signed_pct, raw, mult in EXAMPLES:
        if abs(multiplier_from_signed_pct(signed_pct) - mult) > EPS:
            errors.append(f"multiplier({signed_pct}%) = {multiplier_from_signed_pct(signed_pct)} != {mult}")
        if abs(raw_magnitude_from_pct(signed_pct) - raw) > EPS:
            errors.append(f"raw_magnitude({signed_pct}%) = {raw_magnitude_from_pct(signed_pct)} != {raw}")
        if not round_trip_ok(signed_pct):
            errors.append(f"round-trip failed for {signed_pct}%")
    # Signed-literal edge case: _CLOSE_VS_MA612_LOWER raw -0.15 -> display ×0.85
    if abs(multiplier_from_signed_pct(-15.0) - 0.85) > EPS:
        errors.append("signed-literal edge case (-0.15 -> ×0.85) failed")
    return errors


# === Deterministic validation of the deployed doc =========================
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")


def _num(cell):
    m = NUM_RE.search(cell)
    return float(m.group()) if m else None


def validate_doc():
    """Assert the deployed Examples table obeys the canonical invariant."""
    errors = []
    if not DOC.exists():
        return [f"unit-conversion.md not found at {DOC}"]
    lines = DOC.read_text(encoding="utf-8").splitlines()
    sep = re.compile(r"^\s*\|[\s:|\-]+\|\s*$")
    i = 0
    checked = 0
    while i < len(lines):
        if lines[i].lstrip().startswith("|") and i + 1 < len(lines) and sep.match(lines[i + 1]):
            header = [c.strip().lower() for c in lines[i].strip().strip("|").split("|")]
            # Only the table whose columns are raw / multiplier / display
            mult_col = next((k for k, h in enumerate(header) if "multiplier" in h), None)
            raw_col = next((k for k, h in enumerate(header) if "raw" in h), None)
            disp_col = next((k for k, h in enumerate(header) if "display" in h or "percent" in h), None)
            j = i + 2
            if mult_col is not None and raw_col is not None and disp_col is not None:
                while j < len(lines) and lines[j].lstrip().startswith("|"):
                    cells = [c.strip() for c in lines[j].strip().strip("|").split("|")]
                    if max(mult_col, raw_col, disp_col) < len(cells):
                        # cell is backtick-wrapped (e.g. `-5.0% (×0.95)`) — strip
                        # backticks/space before reading the leading sign.
                        disp = cells[disp_col]
                        disp_clean = disp.strip().strip("`").strip()
                        sign = -1.0 if disp_clean.startswith("-") else 1.0
                        pct_m = NUM_RE.search(disp_clean)
                        raw = _num(cells[raw_col])
                        mult = _num(cells[mult_col])
                        if pct_m and raw is not None and mult is not None:
                            signed_pct = sign * abs(float(pct_m.group()))
                            if abs(multiplier_from_signed_pct(signed_pct) - mult) > EPS:
                                errors.append(
                                    f"row '{disp}': multiplier {mult} != 1+({signed_pct})/100")
                            elif abs(raw_magnitude_from_pct(signed_pct) - abs(raw)) > EPS:
                                errors.append(
                                    f"row '{disp}': raw {raw} != |{signed_pct}|/100")
                            else:
                                checked += 1
                    j += 1
            i = j
        else:
            i += 1
    if checked == 0 and not errors:
        errors.append("no Examples (raw/multiplier/display) rows found to validate")
    return errors, checked


def literal_for_pct(signed_pct: float) -> dict:
    return {
        "magnitude_literal": round(abs(signed_pct) / 100.0, 12),
        "signed_literal": round(signed_pct / 100.0, 12),
        "multiplier": round(1.0 + signed_pct / 100.0, 12),
    }


def verify_literal(raw: float, signed_pct: float):
    """A proposed `Final` literal `raw` is consistent with the user's stated
    signed percent if it equals either the signed form (e.g. -0.15) or the
    magnitude form (e.g. 0.15). Catches the 0.05↔0.95 class of Edit error."""
    if abs(raw - signed_pct / 100.0) < EPS:
        return True, "signed"
    if abs(raw - abs(signed_pct) / 100.0) < EPS:
        return True, "magnitude"
    return False, None


def main():
    print("unit_conversion.py — conversion SOT + round-trip + doc validation")
    print("=" * 70)
    st_errors = self_test()
    print(f"Self-test over {len(EXAMPLES)} documented examples: "
          f"{'PASS' if not st_errors else 'FAIL'}")
    for e in st_errors:
        print(f"  ✗ {e}")

    doc_errors, checked = validate_doc()
    print(f"Deployed unit-conversion.md rows validated: {checked} — "
          f"{'PASS' if not doc_errors else 'FAIL'}")
    for e in doc_errors:
        print(f"  ✗ {e}")

    if st_errors or doc_errors:
        return 1
    print("\nPASSED — conversion invariant holds in code and in the deployed doc.")
    return 0


if __name__ == "__main__":
    argv = sys.argv[1:]
    if not argv:
        sys.exit(main())                         # no args → full gate (self-test + doc)
    if argv[0] == "--pct" and len(argv) == 2:
        p = float(argv[1])
        info = literal_for_pct(p)
        ok = round_trip_ok(p)
        print(f"signed_pct = {p}")
        print(f"  raw literal (magnitude)  = {info['magnitude_literal']}")
        print(f"  raw literal (signed)     = {info['signed_literal']}")
        print(f"  multiplier (×)           = {info['multiplier']}")
        print(f"  round-trip               = {'OK' if ok else 'FAIL'}")
        sys.exit(0 if ok else 1)
    if argv[0] == "--verify" and len(argv) == 3:
        raw, p = float(argv[1]), float(argv[2])
        ok, conv = verify_literal(raw, p)
        if ok:
            print(f"OK — literal {raw} matches {p}% ({conv} convention)")
        else:
            print(f"FAIL — literal {raw} does NOT match stated {p}% "
                  f"(expected {abs(p)/100.0} or {p/100.0})")
        sys.exit(0 if ok else 1)
    print("usage: unit_conversion.py [--pct SIGNED_PCT | --verify RAW SIGNED_PCT]",
          file=sys.stderr)
    sys.exit(2)
