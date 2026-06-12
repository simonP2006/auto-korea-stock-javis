#!/usr/bin/env python3
"""CLI runner for workflow step verification tests.

Usage:
  python run_tests.py --step N     Run tests for step N
  python run_tests.py --all        Run all tests
  python run_tests.py              Run all tests (default)
"""

import subprocess
import sys
from pathlib import Path

TESTS_DIR = Path(__file__).parent


def main():
    args = sys.argv[1:]

    if "--step" in args:
        idx = args.index("--step")
        step_num = args[idx + 1] if idx + 1 < len(args) else None
        if not step_num or not step_num.isdigit():
            print("Usage: python run_tests.py --step N")
            sys.exit(1)
        pattern = f"test_step_{int(step_num):02d}*.py"
        test_files = list(TESTS_DIR.glob(pattern))
        if not test_files:
            print(f"No test files found matching {pattern}")
            sys.exit(1)
        cmd = ["python3", "-m", "pytest"] + [str(f) for f in test_files] + ["-v"]
    else:
        cmd = ["python3", "-m", "pytest", str(TESTS_DIR), "-v"]

    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd, cwd=str(TESTS_DIR))
    sys.exit(result.returncode)


if __name__ == "__main__":
    main()
