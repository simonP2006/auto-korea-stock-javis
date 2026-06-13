#!/usr/bin/env python3
"""
State Machine Invariant Tests — Prompt Runner + Workflow Dispatch

Validates mathematical invariants of the 110-step prompt execution plan
and the 12-step workflow agent dispatch without any API calls.

Execution: pytest tests/test_state_machine_invariants.py -v
"""
import sys
from pathlib import Path

import pytest

PROJECT_DIR = Path(__file__).parent.parent
PROMPTS_DIR = PROJECT_DIR / "prompt-runner" / "prompts"

sys.path.insert(0, str(PROJECT_DIR / "prompt" / ".claude" / "codegen"))
from infra_schema import AGENT_ROSTER, STEP_DISPATCH, FILTER_MODULES, get_output_keys, get_translation_tasks

sys.path.insert(0, str(PROJECT_DIR / "prompt-runner"))


class TestPromptRunnerInvariants:
    """Verify mathematical consistency of the 110-step execution plan."""

    TOTAL = 110
    CLEAR_POSITIONS = frozenset({3, 6, 9, 12, 14, 17, 20, 23, 26, 29, 33, 36, 39, 42,
                                  47, 50, 53, 58, 61, 64, 67, 70, 73, 76, 79, 82, 85,
                                  88, 91, 95, 98, 101, 104, 107, 110})
    NEW_SESSION_STARTS = frozenset({1, 4, 7, 10, 13, 15, 18, 21, 24, 27, 30, 34, 37,
                                     40, 43, 48, 51, 54, 59, 62, 65, 68, 71, 74, 77,
                                     80, 83, 86, 89, 92, 96, 99, 102, 105, 108})

    def test_total_prompts_count(self):
        assert len(list(PROMPTS_DIR.glob("*.txt"))) == self.TOTAL

    def test_clear_plus_exec_equals_total(self):
        exec_count = self.TOTAL - len(self.CLEAR_POSITIONS)
        assert exec_count == 75
        assert exec_count + len(self.CLEAR_POSITIONS) == self.TOTAL

    def test_session_count(self):
        assert len(self.NEW_SESSION_STARTS) == 35

    def test_clear_count(self):
        assert len(self.CLEAR_POSITIONS) == 35

    def test_every_clear_preceded_by_new_session_or_continuation(self):
        for c in self.CLEAR_POSITIONS:
            if c == self.TOTAL:
                continue
            next_step = c + 1
            assert next_step in self.NEW_SESSION_STARTS, \
                f"After /clear at #{c}, #{next_step} should be NEW_SESSION_START"

    def test_every_new_session_preceded_by_clear(self):
        for ns in self.NEW_SESSION_STARTS:
            if ns == 1:
                continue
            prev = ns - 1
            assert prev in self.CLEAR_POSITIONS, \
                f"New session #{ns} but #{prev} is not /clear"

    def test_no_overlap_clear_and_new_session(self):
        overlap = self.CLEAR_POSITIONS & self.NEW_SESSION_STARTS
        assert len(overlap) == 0, f"Overlap between clear and new_session: {overlap}"

    def test_all_positions_in_range(self):
        for c in self.CLEAR_POSITIONS:
            assert 1 <= c <= self.TOTAL, f"Clear position {c} out of range"
        for ns in self.NEW_SESSION_STARTS:
            assert 1 <= ns <= self.TOTAL, f"New session {ns} out of range"

    def test_clear_files_contain_only_clear(self):
        for c in self.CLEAR_POSITIONS:
            f = PROMPTS_DIR / f"{c:03d}.txt"
            assert f.exists(), f"Missing /clear file: {f}"
            assert f.read_text(encoding="utf-8").strip() == "/clear", \
                f"#{c:03d}.txt should contain only '/clear'"

    def test_exec_files_not_empty(self):
        all_positions = set(range(1, self.TOTAL + 1))
        exec_positions = all_positions - self.CLEAR_POSITIONS
        for e in exec_positions:
            f = PROMPTS_DIR / f"{e:03d}.txt"
            assert f.exists(), f"Missing prompt file: {f}"
            assert len(f.read_text(encoding="utf-8").strip()) > 0, \
                f"#{e:03d}.txt is empty"


class TestWorkflowDispatchInvariants:
    """Verify agent dispatch schema consistency."""

    def test_12_steps_defined(self):
        assert len(STEP_DISPATCH) == 12

    def test_steps_sequential(self):
        steps = [s["step"] for s in STEP_DISPATCH]
        assert steps == list(range(1, 13))

    def test_13_agents_in_roster(self):
        assert len(AGENT_ROSTER) == 13

    def test_all_roster_agents_dispatched(self):
        dispatched = {a for s in STEP_DISPATCH for a in s["agents"]}
        roster = {a["name"] for a in AGENT_ROSTER}
        undispatched = roster - dispatched
        assert len(undispatched) == 0, f"Undispatched agents: {undispatched}"

    def test_all_dispatched_agents_in_roster(self):
        dispatched = {a for s in STEP_DISPATCH for a in s["agents"]}
        roster = {a["name"] for a in AGENT_ROSTER}
        unknown = dispatched - roster
        assert len(unknown) == 0, f"Unknown agents in dispatch: {unknown}"

    def test_human_steps_have_no_agents(self):
        for s in STEP_DISPATCH:
            if s["type"] == "human":
                assert len(s["agents"]) == 0, \
                    f"Human step {s['step']} should have no agents"
                assert s["review"] is None, \
                    f"Human step {s['step']} should have no reviewer"

    def test_team_steps_have_multiple_agents(self):
        for s in STEP_DISPATCH:
            if s["type"] == "team":
                assert len(s["agents"]) >= 2, \
                    f"Team step {s['step']} needs >=2 agents, got {len(s['agents'])}"

    def test_single_steps_have_one_agent(self):
        for s in STEP_DISPATCH:
            if s["type"] == "single":
                assert len(s["agents"]) == 1, \
                    f"Single step {s['step']} needs 1 agent, got {len(s['agents'])}"

    def test_output_keys_unique(self):
        keys = [a["output_key"] for a in AGENT_ROSTER]
        assert len(keys) == len(set(keys)), f"Duplicate output keys: {keys}"

    def test_7_filter_modules(self):
        assert len(FILTER_MODULES) == 7

    def test_translation_tasks_match_translate_true(self):
        translate_agents = [a["output_key"] for a in AGENT_ROSTER if a["translate"]]
        tasks = get_translation_tasks()
        assert set(translate_agents) == set(tasks)

    def test_output_keys_include_ko_variants(self):
        all_keys = get_output_keys()
        for a in AGENT_ROSTER:
            assert a["output_key"] in all_keys
            if a["translate"]:
                assert a["output_key"] + "-ko" in all_keys

    def test_agent_files_exist(self):
        agents_dir = PROJECT_DIR / ".claude" / "agents"
        for a in AGENT_ROSTER:
            f = agents_dir / f"{a['name']}.md"
            assert f.exists(), f"Agent definition missing: {f.name}"

    def test_no_output_key_collision_in_team_steps(self):
        """Team agents must write to different files (unique output_key per agent)."""
        for s in STEP_DISPATCH:
            if s["type"] == "team":
                output_keys = []
                for agent_name in s["agents"]:
                    agent = next(a for a in AGENT_ROSTER if a["name"] == agent_name)
                    output_keys.append(agent["output_key"])
                assert len(output_keys) == len(set(output_keys)), \
                    f"Team step {s['step']} has duplicate output keys: {output_keys}"


class TestSOTOutputKeysConsistency:
    """Verify state.yaml output keys match infra_schema."""

    def test_state_yaml_has_all_output_keys(self):
        sot = PROJECT_DIR / "prompt" / ".claude" / "state.yaml"
        if not sot.exists():
            pytest.skip("state.yaml not created")
        content = sot.read_text(encoding="utf-8")
        for key in get_output_keys():
            assert key in content, f"state.yaml missing output key: {key}"

    def test_state_yaml_has_all_translation_tasks(self):
        sot = PROJECT_DIR / "prompt" / ".claude" / "state.yaml"
        if not sot.exists():
            pytest.skip("state.yaml not created")
        content = sot.read_text(encoding="utf-8")
        for task in get_translation_tasks():
            assert task in content, f"state.yaml missing translation task: {task}"
