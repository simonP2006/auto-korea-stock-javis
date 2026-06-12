"""
Infrastructure Build-Time SOT (Source of Truth).

All structured data that appears in 2+ generated files is defined here once.
Consumed by generate_infra.py (Phase 0) and validate_state_yaml.py (runtime).

Authoritative for: agent roster, step dispatch, status enums, path constants,
filter modules, output keys, translation eligibility.
"""

# === Status Enums (single definition — imported by validate_state_yaml.py) ===
WORKFLOW_STATUS_ENUM = {"not_started", "in_progress", "completed", "completed_degraded", "failed"}
TRANSLATION_STATUS_ENUM = {"pending", "in_progress", "completed", "retry", "timeout", "degraded"}

# === Path Constants ===
KRT_ROOT = "/Users/tajun/spJavis/kiwoom-rest-trader"
AW_ROOT = "/Users/tajun/spJavis/AgenticWorkflow-main-stock-filtering-collector"

# === Agent Roster (13 agents — authoritative for teammate configuration) ===
AGENT_ROSTER = [
    {"name": "param-extractor",     "model": "opus",   "tools": ["Read", "Write", "Grep", "Glob"],                       "maxTurns": 30, "phase": "Research",       "step": 1,  "output_key": "step-1-param-inventory",      "translate": True},
    {"name": "pipeline-analyzer",   "model": "opus",   "tools": ["Read", "Write", "Grep", "Glob", "Bash"],               "maxTurns": 40, "phase": "Research",       "step": 1,  "output_key": "step-1-pipeline-analysis",    "translate": True},
    {"name": "error-analyzer",      "model": "sonnet", "tools": ["Read", "Write", "Grep", "Glob"],                       "maxTurns": 20, "phase": "Research",       "step": 1,  "output_key": "step-1-error-patterns",       "translate": True},
    {"name": "research-integrator", "model": "opus",   "tools": ["Read", "Write", "Grep", "Glob", "Bash"],               "maxTurns": 25, "phase": "Research",       "step": 2,  "output_key": "step-2-research-report",      "translate": True},
    {"name": "architect",           "model": "opus",   "tools": ["Read", "Write", "Grep", "Glob", "Bash"],               "maxTurns": 25, "phase": "Planning",       "step": 4,  "output_key": "step-4-architecture",         "translate": True},
    {"name": "claude-md-designer",  "model": "opus",   "tools": ["Read", "Write", "Grep", "Glob"],                       "maxTurns": 30, "phase": "Planning",       "step": 5,  "output_key": "step-5-claude-md-blueprint",  "translate": True},
    {"name": "scan-designer",       "model": "opus",   "tools": ["Read", "Write", "Grep", "Glob"],                       "maxTurns": 35, "phase": "Planning",       "step": 6,  "output_key": "step-6-stock-scan-blueprint", "translate": True},
    {"name": "tune-designer",       "model": "opus",   "tools": ["Read", "Write", "Grep", "Glob"],                       "maxTurns": 40, "phase": "Planning",       "step": 6,  "output_key": "step-6-filter-tune-blueprint", "translate": True},
    {"name": "claude-md-builder",   "model": "opus",   "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],       "maxTurns": 25, "phase": "Implementation", "step": 8,  "output_key": "step-8-claude-md",            "translate": False},
    {"name": "scan-builder",        "model": "opus",   "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],       "maxTurns": 40, "phase": "Implementation", "step": 9,  "output_key": "step-9-stock-scan-skill",     "translate": False},
    {"name": "tune-builder",        "model": "opus",   "tools": ["Read", "Write", "Edit", "Bash", "Glob", "Grep"],       "maxTurns": 50, "phase": "Implementation", "step": 9,  "output_key": "step-9-filter-tune-skill",    "translate": False},
    {"name": "infra-validator",     "model": "opus",   "tools": ["Read", "Write", "Edit", "Grep", "Glob", "Bash"],       "maxTurns": 30, "phase": "Implementation", "step": 10, "output_key": "step-10-validation-report",   "translate": True},
    {"name": "smoke-tester",        "model": "opus",   "tools": ["Read", "Grep", "Glob", "Bash"],                        "maxTurns": 25, "phase": "Implementation", "step": 11, "output_key": "step-11-smoke-test",          "translate": True},
]

# === Step Dispatch (12 steps — authoritative for orchestration) ===
STEP_DISPATCH = [
    {"step": 1,  "type": "team",       "agents": ["param-extractor", "pipeline-analyzer", "error-analyzer"], "review": "fact-checker", "translate": True},
    {"step": 2,  "type": "single",     "agents": ["research-integrator"],                                    "review": "fact-checker", "translate": True},
    {"step": 3,  "type": "human",      "agents": [],                                                         "review": None,           "translate": False},
    {"step": 4,  "type": "single",     "agents": ["architect"],                                              "review": "reviewer",     "translate": True},
    {"step": 5,  "type": "single",     "agents": ["claude-md-designer"],                                     "review": "reviewer",     "translate": True},
    {"step": 6,  "type": "team",       "agents": ["scan-designer", "tune-designer"],                         "review": "reviewer",     "translate": True},
    {"step": 7,  "type": "human",      "agents": [],                                                         "review": None,           "translate": False},
    {"step": 8,  "type": "single",     "agents": ["claude-md-builder"],                                      "review": "reviewer",     "translate": False},
    {"step": 9,  "type": "sequential", "agents": ["scan-builder", "tune-builder"],                           "review": "reviewer",     "translate": False},
    {"step": 10, "type": "single",     "agents": ["infra-validator"],                                        "review": "reviewer",     "translate": True},
    {"step": 11, "type": "single",     "agents": ["smoke-tester"],                                           "review": None,           "translate": True},
    {"step": 12, "type": "human",      "agents": [],                                                         "review": None,           "translate": False},
]

# === Filter Modules (kiwoom-rest-trader — verified against actual code) ===
FILTER_MODULES = [
    "chart60_120Filter", "chart240Filter", "chartDayPreFilter",
    "chartDayFilter", "investorFilter", "financeFilter", "chart60Filter",
]

# === Derived Constants (computed from above — do not edit directly) ===
def get_output_keys():
    """All output keys for state.yaml (English + Korean translations)."""
    keys = []
    for agent in AGENT_ROSTER:
        keys.append(agent["output_key"])
        if agent["translate"]:
            keys.append(agent["output_key"] + "-ko")
    return keys

def get_translation_tasks():
    """All translation task entries for state.yaml."""
    return [a["output_key"] for a in AGENT_ROSTER if a["translate"]]

def get_agents_for_step(step_num):
    """Get agent names dispatched for a given step."""
    for s in STEP_DISPATCH:
        if s["step"] == step_num:
            return s["agents"]
    return []
