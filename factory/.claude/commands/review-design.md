# /review-design — 설계 검토

Read all planning outputs and present for human approval (Step 7 gate).

## Source Files
- Architecture: `prompt/outputs/step-4-architecture.ko.md` / English: `prompt/outputs/step-4-architecture.md`
- CLAUDE.md blueprint: `prompt/outputs/step-5-claude-md-blueprint.ko.md` / English: `prompt/outputs/step-5-claude-md-blueprint.md`
- stock-scan blueprint: `prompt/outputs/step-6-stock-scan-blueprint.ko.md` / English: `prompt/outputs/step-6-stock-scan-blueprint.md`
- filter-tune blueprint: `prompt/outputs/step-6-filter-tune-blueprint.ko.md` / English: `prompt/outputs/step-6-filter-tune-blueprint.md`

## Instructions
1. Read all Korean translation files (primary for user presentation)
2. Present concise design summary in Korean per file:
   - Architecture: deployment targets, key paths, screener_state.json schema
   - CLAUDE.md blueprint: section count, intent clusters, safety rules
   - stock-scan: 8 chains summary, pre-flight checks
   - filter-tune: 8-step sequence, 6 branches, backup protocol
3. Note: "각 영어 원본은 위 경로에서 확인 가능합니다."
4. Ask: "설계를 승인하시겠습니까? Implementation 단계로 진행합니다."
5. On approval: update state.yaml current_step to 8
6. On rejection: identify specific blueprint(s) for rework, ask which step to re-run
