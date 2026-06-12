"""Blocking gate over the deployed deterministic parameter-value guards.

Wires Candidate #1 (validate_param_values) and Candidate #2 (unit_conversion)
into the test suite as a regression gate:
  * runs the DEPLOYED product copies and asserts they pass (live-user path),
  * asserts deployed == source so the two locations never silently diverge
    (single-SOT discipline — the product copy is `cp`-deployed from codegen),
  * embeds the negative test (a wrong %→literal must be rejected).

All guard scripts are stdlib-only, so the pytest runner's interpreter suffices.
"""
import filecmp
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from conftest import KRT_ROOT, AW_ROOT

CODEGEN = AW_ROOT / "prompt" / ".claude" / "codegen"
DEPLOYED = KRT_ROOT / ".claude" / "skills" / "filter-tune" / "scripts"
SCRIPTS = ["param_ast.py", "validate_param_values.py", "unit_conversion.py"]


def _run(path, *args):
    return subprocess.run([sys.executable, str(path), *args],
                          capture_output=True, text=True)


def test_guard_scripts_deployed():
    for s in SCRIPTS:
        assert (DEPLOYED / s).exists(), f"deployed guard missing: {s}"


def test_deployed_matches_source():
    # single SOT: deployed product copies must be byte-identical to codegen source
    for s in SCRIPTS:
        assert filecmp.cmp(CODEGEN / s, DEPLOYED / s, shallow=False), \
            f"drift between codegen source and deployed product copy: {s}"


def test_param_values_oracle_passes():
    r = _run(DEPLOYED / "validate_param_values.py")
    assert r.returncode == 0, f"value-equality oracle FAILED:\n{r.stdout}\n{r.stderr}"


def test_unit_conversion_gate_passes():
    r = _run(DEPLOYED / "unit_conversion.py")
    assert r.returncode == 0, f"unit-conversion gate FAILED:\n{r.stdout}\n{r.stderr}"


def test_unit_conversion_verify_catches_bad_literal():
    # "-5%" must map to 0.05 (or -0.05), NEVER 0.95 — the classic silent-corruption bug
    good = _run(DEPLOYED / "unit_conversion.py", "--verify", "0.05", "-5")
    bad = _run(DEPLOYED / "unit_conversion.py", "--verify", "0.95", "-5")
    assert good.returncode == 0, f"correct literal wrongly rejected:\n{good.stdout}"
    assert bad.returncode == 1, f"WRONG literal NOT caught (gate is a no-op):\n{bad.stdout}"
