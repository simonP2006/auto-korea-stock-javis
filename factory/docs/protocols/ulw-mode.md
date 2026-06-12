# ULW (Ultrawork) Mode

> Detailed specification for ULW mode.
> Separated from CLAUDE.md — referenced when ULW is active.

## Overview

When the prompt contains `ulw`, **Ultrawork mode** activates. ULW is a **thoroughness intensity overlay orthogonal to Autopilot**.

- **Autopilot** = automation axis (HOW) — skip `(human)` approvals
- **ULW** = thoroughness axis (HOW THOROUGHLY) — complete everything exhaustively, resolve all errors

The two axes are independent; any combination is valid:

|  | **ULW OFF** (normal) | **ULW ON** (max thoroughness) |
|---|---|---|
| **Autopilot OFF** | Standard interactive | Interactive + Sisyphus Persistence (3 retries) + mandatory task decomposition |
| **Autopilot ON** | Standard auto workflow | Auto workflow + Sisyphus enhanced (3 retries) + team thoroughness |

## Two-Axis Comparison

| Axis | Concern | Activation | Deactivation | Scope |
|------|---------|-----------|--------------|-------|
| **Autopilot** | Automation (HOW) | SOT `autopilot.enabled: true` | SOT change | Workflow steps |
| **ULW** | Thoroughness (HOW THOROUGHLY) | `ulw` in prompt | Implicit (new session without `ulw` → inactive) | All work (interactive + workflow) |

## Activation Patterns

| User Command | Behavior |
|-------------|----------|
| "ulw do this", "ulw refactor this" | Detect `ulw` in transcript → activate ULW mode |
| New session prompt without `ulw` | ULW inactive (implicit deactivation — no explicit deactivation needed) |

## 3 Intensifier Rules

When ULW activates, these 3 intensifier rules **overlay the current context**:

| Intensifier | Description | Interactive Effect | Autopilot Combined Effect |
|------------|-------------|-------------------|--------------------------|
| **I-1. Sisyphus Persistence** | Max 3 retries, each with a different approach. 100% completion or impossibility report | Up to 3 alternative attempts on error | Quality gate (Verification/pACS) retry limit raised 10→15 |
| **I-2. Mandatory Task Decomposition** | TaskCreate → TaskUpdate → TaskList mandatory | Forced task decomposition for non-trivial work | No change (Autopilot already uses SOT-based tracking) |
| **I-3. Bounded Retry Escalation** | Max 3 consecutive retries on same target prohibited (quality gates have separate budget) — exceed → user escalation | Infinite loop prevention | Safety Hook blocks always respected |

## Runtime Enforcement Mechanisms

| Layer | Mechanism | Enforcement |
|-------|-----------|-------------|
| **Hook** (deterministic) | `_context_lib.py` — `detect_ulw_mode()` | Regex detection of `ulw` in transcript |
| **Hook** (deterministic) | `generate_snapshot_md()` — snapshot | ULW state section preserved at IMMORTAL priority |
| **Hook** (deterministic) | `extract_session_facts()` — Knowledge Archive | Tagged `ulw_active: true` → RLM queryable |
| **Hook** (deterministic) | `restore_context.py` — SessionStart | When ULW active, inject 3 intensifier rules into context (excluded from startup source — implicit deactivation) |
| **Hook** (deterministic) | `_context_lib.py` — `check_ulw_compliance()` | Deterministic verification of 3 intensifier rules → warnings in snapshot IMMORTAL |
| **Hook** (deterministic) | `generate_context_summary.py` — Stop | ULW Compliance safety net — stderr warning on violation |

## NEVER DO
- Exceed 3 consecutive retries on same target (quality gates have separate budget) — I-3 violation, user escalation mandatory
- Override Safety Hook (`(hook)` exit code 2) blocks under ULW pretext
- Leave Tasks as "partially complete" while ULW active — I-1 violation
- Give up on error without attempting alternatives — I-1 violation
- Proceed implicitly without TaskCreate for non-trivial work — I-2 violation
