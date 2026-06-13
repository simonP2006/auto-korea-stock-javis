# Workflow Executor — Stock Filter Orchestration Build

## Purpose
Orchestrate the 12-step build workflow defined in prompt/workflow.md.
This skill is the single entry point for executing the infrastructure build.

## Trigger
- User invokes directly or orchestrator session begins
- Session start: read state.yaml to determine resume point

## Core Loop

```
ON INVOCATION (including re-entry after context compaction):

  0. [RE-ENTRY PROTOCOL]
     Read prompt/.claude/state.yaml → get current_step, status, last_completed_substep
     This skill is ALWAYS the first action after session start/resume.
     Context Preservation ensures state.yaml persists across compactions.
     After PreCompact/clear/resume: re-read state.yaml, continue from exact point.

  1. Read prompt/.claude/state.yaml → get current_step, status
  2. If status == "completed" → report final state in Korean, exit
  3. If status == "failed" → present recovery options to user in Korean
  4. Dispatch current_step:
     - Look up references/step-dispatch.md for: agent(s), context files, verification
     - Spawn agent(s) via Agent tool:
       • team steps (1, 6): parallel Agent calls
       • sequential step (9): scan-builder FIRST, then tune-builder
       • single steps (2, 4, 5, 8, 10, 11): one Agent call
     - On completion: run pytest test_step_{N}*.py -v
     - On ANY FAIL: trigger fallback (see references/fallback-paths.md)
  4b. [REVIEW GATE] (after pytest PASS — per step-dispatch.md):
     - Steps 1, 2: invoke @fact-checker (Agent tool, subagent_type: "fact-checker")
     - Steps 4, 5, 6, 8, 9, 10: invoke @reviewer (Agent tool, subagent_type: "reviewer")
     - Steps 3, 7, 11, 12: no review (human gates or final verification)
     - Review agent produces independent pACS (F, C, L dimensions)
     - On PASS: proceed to SOT update (4c)
     - On FAIL (critical issue): trigger fallback F-1 for agent rework
     - On pACS Delta ≥ 15 (vs generator): apply F-14 reconciliation
     - On @reviewer/@fact-checker timeout: apply F-7 (proceed with flag)
  4c. [SOT UPDATE] (after review PASS or F-7 bypass):
       → Backup state.yaml to state.yaml.bak (cp command)
       → Update state.yaml (current_step += 1, record output path)
  5. After SOT update — Translation dispatch (steps 1,2,4,5,6,10,11):
     - Invoke @translator (Agent tool, subagent_type: "translator") sequentially per file
     - Record in SOT: translation_tasks[key].status, pacs_score, duration_sec
     - Run P1 validate_translation.py --step N
     - On pACS RED (< 50): retry up to 3×, then proceed with best-effort
  6. If next step is (human): invoke slash command, present in Korean, await user
     - Step 12 ALWAYS requires human — never auto-approve regardless of autopilot
  7. Loop until completed or human-blocked
```

## Constraints
- SOLE SOT WRITER — no agent writes state.yaml
- Team steps 1, 6: parallel Agent calls. Step 9: SEQUENTIAL
- Human steps: present in Korean, await approval
- Step 12: ALWAYS human-verified — never auto-approve regardless of autopilot
- Every agent spawn includes full context injection (no assumptions about prior context)
- All agents that produce output files have Write tool — they write their own output
- Before every state.yaml write: backup to state.yaml.bak
- KRT long-running commands (run_prefetch, run_full_research_flow): Bash timeout=600000ms
- Log files (masterReference.log, tuning-log.md): Edit append-only, never Write overwrite
- KRT error retry budget: same error type 2× → halt + escalate to user with Korean guide

## Context Overflow Handling
- Each step completion writes state.yaml — serves as durable checkpoint
- If PreCompact fires mid-step: substep progress tracked in state.yaml
- On session resume: model reads this SKILL.md + state.yaml → determines exact resume point
- SessionStart hook provides RLM pointers to this skill

## Autopilot Continuity
- After compaction, autopilot.mode remains in state.yaml (persistent)
- Orchestrator re-reads it and continues auto-approving per protocol
- Exception: Step 12 — hard block regardless of autopilot state

## Cross-References
- Workflow spec: prompt/workflow.md
- SOT: prompt/.claude/state.yaml
- Tests: prompt/.claude/tests/
- Fallback: references/fallback-paths.md
- Step dispatch: references/step-dispatch.md
