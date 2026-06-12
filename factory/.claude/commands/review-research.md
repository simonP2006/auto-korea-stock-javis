# /review-research — Research 결과 검토

Read the research integration report and present findings for human approval (Step 3 gate).

## Source Files
- Primary (user-facing): `prompt/outputs/step-2-research-report.ko.md` (한국어 번역)
- Reference (detail): `prompt/outputs/step-2-research-report.md` (영어 원본)
- Supporting: `prompt/outputs/step-1-param-inventory.ko.md`
- Supporting: `prompt/outputs/step-1-pipeline-analysis.ko.md`
- Supporting: `prompt/outputs/step-1-error-patterns.ko.md`

## Instructions
1. Read the Korean translation file (primary presentation to user)
2. Summarize key findings in Korean (3-5 bullet points):
   - Parameter inventory coverage (how many modules, how many params)
   - Pipeline architecture key insights
   - Error handling coverage
   - Any conflicts or open questions
3. Present verification status (all PRD C.2 items, workflow-idea C-6 items)
4. Note: "영어 원본: prompt/outputs/step-2-research-report.md 에서 확인 가능합니다."
5. Ask the user: "Research 결과를 승인하시겠습니까? Planning 단계로 진행합니다."
6. On approval: update state.yaml current_step to 4
7. On rejection: ask for specific concerns, prepare re-run of affected Step 1 teammates
