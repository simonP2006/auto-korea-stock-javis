# Fallback Decision Tree

> Hierarchical fallback strategies for workflow execution failures.
> Orchestrator consults this when a step fails verification or an agent errors out.

## Fallback Hierarchy

| Level | Trigger | Action | SOT Update |
|-------|---------|--------|------------|
| F-1 | Agent fails (timeout/error) | Retry same agent with error feedback (max 3) | status: "in_progress" |
| F-2 | Agent fails 3× | Orchestrator executes directly using agent's prompt | degradation_notes: append |
| F-3 | Team member unresponsive | Kill + replace. If 2nd fails → orchestrator takes over | degradation_notes: append |
| F-4 | Team coordination breaks | Terminate team. Re-execute sequentially with prior outputs | active_team: null |
| F-6 | SOT corrupted | Restore from state.yaml.bak. If .bak also corrupt: reconstruct from outputs | Rebuilt from outputs |
| F-7 | @reviewer timeout | Log warning, proceed. Flag for Step 12 human validation | decisions: append "review_bypassed" |
| F-8 | Path not found | AskUserQuestion: confirm kiwoom-rest-trader location | Block until resolved |
| F-9 | 3+ consecutive step failures | Present diagnostic to human: retry/intervene/abort | status: "failed" |
| F-10 | @translator timeout (>15 min/file) | Kill agent, record partial. Retry ≤3×. After 3×: English-only | translation_tasks[file].status: "timeout" |
| F-11 | Translation aggregate budget exceeded | Skip remaining translations. English is authoritative | degradation_notes: append |
| F-12 | Target file already exists | Verify completeness. If valid → skip. If corrupt → delete + rewrite | outputs: record existing |
| F-13 | KRT error (API auth, network, disk) | Same error 2× → halt. Korean explanation + manual action guide | degradation_notes: append "krt_error_escalated" |
| F-14 | pACS Delta ≥ 15 (reviewer vs generator) | Adopt lower score. Record divergence in degradation_notes. Flag for Step 12 human review | degradation_notes: append "pacs_delta_{step}" |

## Decision Flow

```
Agent dispatched → result received
  │
  ├─ Success → run pytest
  │   ├─ ANY FAIL → F-1 (retry with failure details)
  │   │   ├─ Retry PASS → proceed to review
  │   │   └─ Retry FAIL (3×) → F-2 (orchestrator direct)
  │   │       ├─ Direct PASS → proceed to review
  │   │       └─ Direct FAIL → F-9 (human escalation)
  │   └─ ALL PASS → invoke review agent (step-dispatch.md)
  │       ├─ Review PASS + Delta < 15 → update SOT, proceed
  │       ├─ Review PASS + Delta ≥ 15 → F-14 (adopt lower, flag)
  │       ├─ Review FAIL (critical) → F-1 (rework agent output)
  │       └─ Review timeout → F-7 (proceed with flag)
  │
  ├─ Agent timeout (maxTurns exhausted) → F-1
  │   └─ [follows same retry chain as above]
  │
  ├─ Team member fails → F-3
  │   ├─ Replacement succeeds → proceed
  │   └─ Replacement fails → F-4 (sequential fallback)
  │
  └─ SOT write fails (hook blocks) → self-correct YAML, retry write
      └─ 3× write failures → F-6 (restore from backup)
```

## Translation Fallback Detail

```
@translator invoked → result
  │
  ├─ Success + pACS ≥ 50 → record in SOT, proceed
  │
  ├─ pACS RED (< 50) → retry weak sections (not full file)
  │   ├─ Retry PASS → proceed
  │   └─ Retry FAIL (3×) → proceed with best-effort, flag degradation
  │
  ├─ Timeout (>15 min) → F-10
  │   ├─ Retry with reduced scope
  │   └─ After 3× → proceed English-only
  │
  └─ Aggregate budget exceeded → F-11 (skip remaining files this step)
```

## KRT Execution Error Handling (F-13)

AI-unresolvable error types — do NOT retry more than twice:
- Kiwoom API 인증 만료 (authentication expired)
- 네트워크 단절 (network disconnection)
- 디스크 공간 부족 (insufficient disk space)

On detection:
1. Identify error type from stderr/exit code
2. If same error type occurred in previous attempt → HALT
3. Present Korean explanation to user:
   - What happened (error type)
   - What user must do manually (specific action)
   - How to resume after fixing (invoke workflow-executor again)
4. SOT: status remains "in_progress", degradation_notes records escalation

## pACS Delta Reconciliation (F-14)

When reviewer/fact-checker pACS diverges ≥ 15 points from generator's self-rating:
1. Adopt the **lower** score as the authoritative pACS for the step
2. Record in degradation_notes: `"pacs_delta_{step}: generator={G}, reviewer={R}, adopted={min}"`
3. Step proceeds (not blocked) — divergence is a quality signal, not a gate failure
4. Step 12 human review receives the divergence report as additional context
5. If Delta ≥ 30: additionally log warning to stderr for orchestrator visibility

## Degraded Completion

If ANY fallback beyond F-1 was triggered:
- SOT status: "completed_degraded" (at workflow end)
- degradation_notes: list of affected steps + fallback levels used
- Step 12 human review receives degradation report as additional context
