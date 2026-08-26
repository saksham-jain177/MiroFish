"""Integration-ish tests for SyntheticaSimulationRunner with stub LLM.

Verifies the full loop runs without network calls and produces correct output structure.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.app.services.synthetica_simulation_runner import SyntheticaSimulationRunner, intents_match
from backend.app.services.synthetica_environment import SyntheticaEnvironment, environment_instance
from backend.app.services.cognitive_agent import CognitiveAgent
from backend.app.services.evaluator_node import EvaluatorNode


# ---------------------------------------------------------------------------
# Stub LLM client for integration tests
# ---------------------------------------------------------------------------

class StubResponse:
    def __init__(self, content):
        self.choices = [type("C", (), {"message": type("M", (), {"content": content})()})]


class StubChat:
    def create(self, **kwargs):
        payload = json.dumps({
            "logical_deduction": "Gather locally to conserve resources.",
            "emotional_state": "cautious",
            "declared_intent": "survive",
            "action_intent": "GATHER_LOCAL",
            "target": "self",
        })
        return StubResponse(payload)


class StubCompletions:
    def create(self, **kwargs):
        return StubChat().create(**kwargs)


class StubChatModule:
    completions = StubCompletions()


class StubLLMClient:
    chat = StubChatModule()


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestRunnerIntegration:
    def test_setup_agents_creates_correct_count(self):
        runner = SyntheticaSimulationRunner("test_int_001", max_generations=3)
        # We need to patch the LLM client on CognitiveAgent and EvaluatorNode
        orig_agent_init = CognitiveAgent.__init__
        orig_eval_init = EvaluatorNode.__init__

        def patched_agent_init(self_agent, *args, **kwargs):
            orig_agent_init(self_agent, *args, **kwargs)
            self_agent.llm_client = StubLLMClient()

        def patched_eval_init(self_eval, *args, **kwargs):
            orig_eval_init(self_eval, *args, **kwargs)
            self_eval.llm_client = StubLLMClient()

        CognitiveAgent.__init__ = patched_agent_init
        EvaluatorNode.__init__ = patched_eval_init
        try:
            runner.setup_agents(num_agents_per_territory=2)
            assert len(runner.agents) == 4
            # Agents are interleaved: A-1, B-1, A-2, B-2
            assert runner.agents[0].territory == "A"
            assert runner.agents[1].territory == "B"
            assert runner.agents[2].territory == "A"
            assert runner.agents[3].territory == "B"
        finally:
            CognitiveAgent.__init__ = orig_agent_init
            EvaluatorNode.__init__ = orig_eval_init

    def test_run_produces_jsonl_output(self, tmp_path):
        """Run a 2-generation simulation and verify JSONL output structure."""
        # Reset the singleton environment
        env = SyntheticaEnvironment()
        env._ensure_agent("A-1", "A")
        env._ensure_agent("B-1", "B")
        env.agents_per_territory = {"A": 1, "B": 1}
        env.state["A"]["energy"] = 500
        env.state["B"]["energy"] = 500

        # Patch environment_instance to use our test env
        import backend.app.services.synthetica_simulation_runner as runner_mod
        original_env = runner_mod.environment_instance
        runner_mod.environment_instance = env

        runner = SyntheticaSimulationRunner("test_int_002", max_generations=2)

        # Patch LLM clients
        orig_agent_init = CognitiveAgent.__init__
        orig_eval_init = EvaluatorNode.__init__
        turn_count = [0]

        def patched_agent_init(self_agent, *args, **kwargs):
            orig_agent_init(self_agent, *args, **kwargs)
            self_agent.llm_client = StubLLMClient()

        def patched_eval_init(self_eval, *args, **kwargs):
            orig_eval_init(self_eval, *args, **kwargs)
            self_eval.llm_client = StubLLMClient()

        CognitiveAgent.__init__ = patched_agent_init
        EvaluatorNode.__init__ = patched_eval_init

        try:
            runner.setup_agents(num_agents_per_territory=1)
            runner.run_simulation()

            # Verify output file exists and has entries
            assert os.path.exists(runner.log_file)
            with open(runner.log_file) as f:
                lines = [json.loads(line) for line in f if line.strip()]

            # 2 generations x 2 agents = 4 action entries + possible events
            action_entries = [l for l in lines if "agent" in l]
            assert len(action_entries) >= 4

            # Verify schema of first entry
            entry = action_entries[0]
            assert "run_id" in entry
            assert "turn" in entry
            assert "agent" in entry
            assert "state" in entry
            assert "deltas" in entry
            assert "metrics" in entry
            assert "ccs_b" in entry["metrics"]
            assert "coherence" in entry["metrics"]
        finally:
            CognitiveAgent.__init__ = orig_agent_init
            EvaluatorNode.__init__ = orig_eval_init
            runner_mod.environment_instance = original_env

    def test_intents_match_used_in_runner_context(self):
        """Verify intents_match is correctly used for behavioral consistency."""
        assert intents_match("GATHER_LOCAL", "GATHER_LOCAL")
        assert not intents_match("GATHER_LOCAL", "STEAL_RESOURCE")
        assert intents_match("gather_local", "GATHER_LOCAL")
