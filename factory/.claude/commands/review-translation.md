# /review-translation — 번역 현황 대시보드

Read the SOT and all translation outputs to present comprehensive translation status.

## Instructions
1. Read `prompt/.claude/state.yaml` → extract `translation_tasks` and `outputs.*-ko` keys
2. For each translation-eligible step (1, 2, 4, 5, 6, 10, 11):
   a. Check if English source exists in `prompt/outputs/`
   b. Check if `.ko.md` translation exists
   c. Read pACS score from `pacs-logs/step-N-translation-pacs.md` (if exists)
   d. Check glossary.yaml last modification time
3. Present summary table in Korean:

| 단계 | 영어 원본 | 한국어 번역 | pACS 점수 | 상태 |
|------|----------|-----------|----------|------|
| 1-a  | step-1-param-inventory.md | .ko.md | — | — |
| 1-b  | step-1-pipeline-analysis.md | .ko.md | — | — |
| 1-c  | step-1-error-patterns.md | .ko.md | — | — |
| 2    | step-2-research-report.md | .ko.md | — | — |
| 4    | step-4-architecture.md | .ko.md | — | — |
| 5    | step-5-claude-md-blueprint.md | .ko.md | — | — |
| 6-a  | step-6-stock-scan-blueprint.md | .ko.md | — | — |
| 6-b  | step-6-filter-tune-blueprint.md | .ko.md | — | — |
| 10   | step-10-validation-report.md | .ko.md | — | — |
| 11   | step-11-smoke-test.md | .ko.md | — | — |

4. Highlight with status indicators:
   - Missing: 미완료
   - pACS < 70: 저품질 (재번역 권장)
   - pACS >= 70: 양호
5. Report glossary.yaml statistics:
   - Total terms: N
   - Recently added terms (if trackable)
6. If any translations are missing or low-quality:
   - Ask: "재번역을 실행하시겠습니까?" with step selection
   - On approval: trigger @translator for selected steps
7. Note: "이 명령은 Human Gate (Step 3, 7, 12) 전에 사용하면 번역 품질을 사전 확인할 수 있습니다."
