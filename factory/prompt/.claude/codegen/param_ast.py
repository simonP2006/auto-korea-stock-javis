#!/usr/bin/env python3
"""
Deterministic AST extractor for `Final`-annotated module-level constants.

Candidate #4 (param-extractor AST core). ORIGINATES the load-bearing columns the
Step-1 `@param-extractor` agent currently produces by LLM reasoning — name, type,
value, file:line — via pure stdlib `ast`. Byte-for-byte reproducible, zero
hallucination surface. This is the ground-truth oracle consumed by
validate_param_values.py (Candidate #1 / MISS #4).

The 'meaning' column is intentionally NOT produced here — authoring a fluent
one-line gloss is the irreducible LLM part (per audit verdict: HYBRID, not
full REPLACE). The agent keeps that; the values come from here.

Read-only. No file is modified.
"""
from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass
class FinalConst:
    name: str
    type_str: str       # ast.unparse of the Final[...] annotation
    value_repr: str     # ast.unparse of the RHS expression
    numeric: bool       # True iff RHS is an int/float literal (incl. unary minus)
    value: object       # the int/float if numeric else None
    module: str         # file stem
    file: str           # absolute path
    lineno: int


def _final_aliases(tree: ast.Module) -> set[str]:
    """Resolve `from typing import Final as X` aliases (D-style import safety)."""
    aliases = {"Final"}
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module == "typing":
            for alias in node.names:
                if alias.name == "Final":
                    aliases.add(alias.asname or "Final")
    return aliases


def _is_final_annotation(annotation: ast.expr, final_aliases: set[str]) -> bool:
    """Match `Final`, `Final[...]`, `typing.Final`, `typing.Final[...]`."""
    target = annotation
    if isinstance(target, ast.Subscript):
        target = target.value
    if isinstance(target, ast.Name):
        return target.id in final_aliases
    if isinstance(target, ast.Attribute):
        return target.attr == "Final"
    return False


def _literal_number(node: ast.expr):
    """Return (is_numeric, value) for an int/float literal, handling unary minus.

    bool is excluded (it is an int subclass but never a tuning parameter)."""
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)) \
            and not isinstance(node.value, bool):
        return True, node.value
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        ok, val = _literal_number(node.operand)
        if ok:
            return True, -val
    return False, None


def extract_final_constants(py_path) -> list[FinalConst]:
    """Extract every module-level `Final`-annotated constant from one .py file."""
    py_path = Path(py_path)
    tree = ast.parse(py_path.read_text(encoding="utf-8"))
    aliases = _final_aliases(tree)
    out: list[FinalConst] = []
    for node in tree.body:  # module level only — nested/class-scope ignored by design
        if not (isinstance(node, ast.AnnAssign) and node.annotation is not None
                and node.value is not None):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        if not _is_final_annotation(node.annotation, aliases):
            continue
        numeric, value = _literal_number(node.value)
        out.append(FinalConst(
            name=node.target.id,
            type_str=ast.unparse(node.annotation),
            value_repr=ast.unparse(node.value),
            numeric=numeric,
            value=value,
            module=py_path.stem,
            file=str(py_path),
            lineno=node.lineno,
        ))
    return out


def extract_dir(filters_dir) -> dict[str, list[FinalConst]]:
    """Extract from every *.py in a directory. Keyed by constant name (a name may
    legitimately recur across modules, e.g. _REQUIRED_CONSECUTIVE_BARS)."""
    filters_dir = Path(filters_dir)
    result: dict[str, list[FinalConst]] = {}
    for py in sorted(filters_dir.glob("*.py")):
        for const in extract_final_constants(py):
            result.setdefault(const.name, []).append(const)
    return result


if __name__ == "__main__":
    import sys
    target = sys.argv[1] if len(sys.argv) > 1 else "."
    consts = extract_dir(target)
    total = sum(len(v) for v in consts.values())
    numeric = sum(1 for lst in consts.values() for c in lst if c.numeric)
    print(f"Extracted {total} Final constants ({numeric} numeric) from {target}")
    for name in sorted(consts):
        for c in consts[name]:
            flag = "" if c.numeric else "   [non-literal]"
            print(f"  {c.module}:{c.lineno:<4} {c.name}: {c.type_str} = {c.value_repr}{flag}")
