---
model: sonnet
tools: [Read, Write, Grep, Glob]
maxTurns: 20
---

# Error Analyzer

## Purpose
Classify all error/exception patterns in kiwoom-rest-trader. Produce Korean message
mapping table for each error type.

## Context (Injected by Orchestrator)
- Search paths: /Users/tajun/spJavis/auto-korea-stock-javis/engine/scripts/, /Users/tajun/spJavis/auto-korea-stock-javis/engine/src/kiwoom/
- Known types (minimum): KiwoomAuthError, KiwoomApiError, KiwoomConditionError, ResearchError,
  OrganizeError, PrefetchError, httpx.ConnectError, httpx.TimeoutException, FileNotFoundError

## Output Specification
- File: `prompt/outputs/step-1-error-patterns.md`
- Format: Table with columns: | Error Class | Trigger Condition | Exit Code | Stderr Pattern | Source File:Line | Korean Message |
- Must discover ALL custom exception classes beyond the known list
- Korean messages: natural phrasing for non-technical user

## Verification Criteria
1. ≥5 distinct error types documented
2. All 9 known types addressed (found or confirmed absent)
3. Each entry has Korean message mapping
4. Custom exception class definitions (class...Error) discovered via grep

## Failure Behavior
- If fewer than 5 types found: document search patterns used, flag for human review
