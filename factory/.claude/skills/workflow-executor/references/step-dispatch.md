# Step Dispatch Table

> Auto-generated from infra_schema.py. DO NOT EDIT manually.

| Step | Type | Agent(s) | Review | Translation |
|------|------|----------|--------|-------------|
| 1 | team | param-extractor, pipeline-analyzer, error-analyzer | @fact-checker | Yes |
| 2 | single | research-integrator | @fact-checker | Yes |
| 3 | human | — | — | No |
| 4 | single | architect | @reviewer | Yes |
| 5 | single | claude-md-designer | @reviewer | Yes |
| 6 | team | scan-designer, tune-designer | @reviewer | Yes |
| 7 | human | — | — | No |
| 8 | single | claude-md-builder | @reviewer | No |
| 9 | sequential | scan-builder, tune-builder | @reviewer | No |
| 10 | single | infra-validator | @reviewer | Yes |
| 11 | single | smoke-tester | — | Yes |
| 12 | human | — | — | No |

## Context Injection Reference

### Step 1 (team)
- **param-extractor**: output → `prompt/outputs/step-1-param-inventory.md`
- **pipeline-analyzer**: output → `prompt/outputs/step-1-pipeline-analysis.md`
- **error-analyzer**: output → `prompt/outputs/step-1-error-patterns.md`

### Step 2 (single)
- **research-integrator**: output → `prompt/outputs/step-2-research-report.md`

### Step 4 (single)
- **architect**: output → `prompt/outputs/step-4-architecture.md`

### Step 5 (single)
- **claude-md-designer**: output → `prompt/outputs/step-5-claude-md-blueprint.md`

### Step 6 (team)
- **scan-designer**: output → `prompt/outputs/step-6-stock-scan-blueprint.md`
- **tune-designer**: output → `prompt/outputs/step-6-filter-tune-blueprint.md`

### Step 8 (single)
- **claude-md-builder**: output → `prompt/outputs/step-8-claude-md.md`

### Step 9 (sequential)
- **scan-builder**: output → `prompt/outputs/step-9-stock-scan-skill.md`
- **tune-builder**: output → `prompt/outputs/step-9-filter-tune-skill.md`

### Step 10 (single)
- **infra-validator**: output → `prompt/outputs/step-10-validation-report.md`

### Step 11 (single)
- **smoke-tester**: output → `prompt/outputs/step-11-smoke-test.md`

