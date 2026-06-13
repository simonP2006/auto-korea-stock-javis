#!/usr/bin/env python3
"""
Filter-parameter value-equality oracle (Candidate #1 / MISS #4).

THE core-purpose guard the system was missing. PG-2 (filter tuning) is the
paramount objective; "a wrong filter parameter value misleads the user's tuning."
The deployed filter-tune reference docs embed ~75 hardcoded current values that
D-4/ADR-010 declares "documentation only — always Read live code", yet the only
guards are (a) the LLM remembering to re-grep, (b) a Step-10 LLM grep that checks
NAMES not VALUES, and (c) a structural pytest that asserts a literal merely
appears SOMEWHERE. An LLM regenerating the catalog can fabricate a
plausible-but-wrong value (0.025 vs 0.015) that passes every existing gate.

This oracle closes that gap: it AST-extracts every numeric `Final` constant from
the product code (param_ast.py) and asserts that every value CLAIMED for that
constant in the value-bearing reference docs EXACTLY equals the code value.
This is the literal embodiment of the project's P1 gene ("code doesn't lie").

Design (false-positive-averse — a noisy oracle erodes trust = harms quality):
  * HARD GATE  — value-bearing Markdown tables (a column header matching
                 현재값|raw). Column-precise: subject var from the row, value
                 from the value column. Exit 1 on any disagreement.
  * INFO ONLY  — heuristic inline line-scan (single-var lines w/ backticked
                 numbers) and catalog coverage. Never hard-fails.
  * EXCLUDED   — range-map.md states physical RANGES, not current values, so it
                 is coverage-only and NEVER value-checked (would false-fail).

Read-only: reads product .py + deployed .md; writes nothing.
  Exit 0 = every claimed value matches code.
  Exit 1 = at least one claimed value disagrees with code.
  Exit 2 = environment error (paths missing).
"""
import os
import re
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from param_ast import extract_dir  # noqa: E402


def _resolve_paths():
    """Portable resolution so this file is byte-identical in both locations:
      * deployed at <KRT>/.claude/skills/filter-tune/scripts/  → derive from __file__
      * source at  <AW>/prompt/.claude/codegen/                → import infra_schema."""
    refs = HERE.parent / "references"
    if refs.is_dir() and (HERE.parents[3] / "src" / "kiwoom").is_dir():
        return HERE.parents[3], refs            # deployed-in-product layout
    from infra_schema import KRT_ROOT           # AgenticWorkflow source layout
    krt = Path(KRT_ROOT)
    return krt, krt / ".claude" / "skills" / "filter-tune" / "references"


KRT, REFS = _resolve_paths()
FILTERS = KRT / "src" / "kiwoom" / "itemFilter"

# Docs that state CURRENT values → eligible for value-equality.
VALUE_DOCS = ["parameter-catalog.md", "unit-conversion.md", "shared-constants.md"]
# Docs that state RANGES, not current values → coverage only, NEVER value-checked.
COVERAGE_ONLY = ["range-map.md"]
# The doc whose catalog is meant to be complete (for the coverage report).
CANONICAL_CATALOG = "parameter-catalog.md"

NAME_RE = re.compile(r"_[A-Z][A-Z0-9_]*")
NUM_RE = re.compile(r"-?\d+(?:\.\d+)?")
BACKTICK_RE = re.compile(r"`([^`]*)`")
HDR_VALUE_RE = re.compile(r"현재\s*값|raw", re.IGNORECASE)  # catalog header is "현재 값" (with space)
EPS = 1e-9

mismatches = []   # hard failures (exit 1)
warnings = []     # informational
matches = 0


def first_number(text):
    m = NUM_RE.search(text)
    return float(m.group()) if m else None


def _eq(a, vals):
    return any(abs(a - v) < EPS for v in vals)


def parse_tables(text):
    """Yield (header_cells, [row_cells, ...]) for each GitHub-style Markdown table."""
    lines = text.splitlines()
    i = 0
    sep = re.compile(r"^\s*\|[\s:|\-]+\|\s*$")
    while i < len(lines):
        line = lines[i]
        if line.lstrip().startswith("|") and i + 1 < len(lines) and sep.match(lines[i + 1]):
            header = [c.strip() for c in line.strip().strip("|").split("|")]
            rows = []
            j = i + 2
            while j < len(lines) and lines[j].lstrip().startswith("|"):
                rows.append([c.strip() for c in lines[j].strip().strip("|").split("|")])
                j += 1
            yield header, rows
            i = j
        else:
            i += 1


def strip_names(text):
    """Remove constant-name tokens so their embedded digits (MA60, MA306, ...)
    are not mistaken for value claims."""
    return NAME_RE.sub("", text)


def check_value_tables(doc, text, known_numeric):
    """HARD-GATE: column-precise value equality over value-bearing tables."""
    global matches
    for header, rows in parse_tables(text):
        vcol = next((k for k, h in enumerate(header) if HDR_VALUE_RE.search(h)), None)
        if vcol is None:
            continue  # not a value-bearing table (e.g. range tables, transposed tables)
        for row in rows:
            if vcol >= len(row):
                continue
            # subject = first cell containing a known numeric constant name
            subj = None
            for cell in row:
                for m in NAME_RE.findall(cell):
                    if m in known_numeric:
                        subj = m
                        break
                if subj:
                    break
            if subj is None:
                continue
            claimed = first_number(strip_names(row[vcol]))
            if claimed is None:
                continue
            if _eq(claimed, known_numeric[subj]):
                matches += 1
            else:
                mismatches.append(
                    f"{doc}: '{subj}' claims {claimed} but code has "
                    f"{sorted(known_numeric[subj])}")


def check_inline_lines(doc, text, known_numeric):
    """INFO-ONLY: single-var lines that state a backticked number."""
    for line in text.splitlines():
        present = {m for m in NAME_RE.findall(line) if m in known_numeric}
        if len(present) != 1:
            continue
        subj = next(iter(present))
        rem = strip_names(line)
        bt_nums = []
        for span in BACKTICK_RE.findall(rem):
            sp = span.strip()
            # only spans that START with a (signed) digit are value claims —
            # this rejects code spans like `_is_4ma_aligned(b, ...)` whose digits
            # ("4") would otherwise be mistaken for a value.
            if not re.match(r"^-?\d", sp):
                continue
            n = first_number(sp)
            if n is not None:
                bt_nums.append(n)
        if not bt_nums:
            continue
        if not any(_eq(b, known_numeric[subj]) for b in bt_nums):
            warnings.append(
                f"{doc} (inline): '{subj}' line states {bt_nums}, "
                f"code has {sorted(known_numeric[subj])} — verify manually")


def main():
    if not FILTERS.is_dir():
        print(f"ERROR: filters dir not found: {FILTERS}", file=sys.stderr)
        return 2
    if not REFS.is_dir():
        print(f"ERROR: filter-tune references dir not found: {REFS}", file=sys.stderr)
        return 2

    consts = extract_dir(FILTERS)
    known_numeric = {
        name: {c.value for c in lst if c.numeric}
        for name, lst in consts.items()
        if any(c.numeric for c in lst)
    }

    print("validate_param_values.py — filter-parameter value-equality oracle")
    print("=" * 70)
    print(f"Code: {sum(len(v) for v in consts.values())} Final constants "
          f"({len(known_numeric)} distinct numeric) in {FILTERS}")

    for doc in VALUE_DOCS:
        path = REFS / doc
        if not path.exists():
            warnings.append(f"{doc}: value doc not found")
            continue
        text = path.read_text(encoding="utf-8")
        check_value_tables(doc, text, known_numeric)
        check_inline_lines(doc, text, known_numeric)

    # Coverage (info): which numeric constants are absent from the canonical catalog?
    cat = REFS / CANONICAL_CATALOG
    if cat.exists():
        cat_text = cat.read_text(encoding="utf-8")
        absent = sorted(n for n in known_numeric if n not in cat_text)
        if absent:
            warnings.append(
                f"{CANONICAL_CATALOG} coverage: {len(absent)} numeric constants "
                f"not mentioned (may be intentionally out of tuning scope): {absent}")

    print(f"\nHARD value-equality checks passed: {matches}")
    if warnings:
        print(f"\nWarnings (informational, non-blocking) — {len(warnings)}:")
        for w in warnings:
            print(f"  ⚠ {w}")
    if mismatches:
        print(f"\nFAILED — {len(mismatches)} value MISMATCH(es):\n")
        for m in mismatches:
            print(f"  ✗ {m}")
        return 1
    print("\nPASSED — every claimed filter-parameter value matches the live code.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
