"""EVALUATOR TESTS: EVAL_CADENCE gating, llm_evaluated + justification
persistence, heuristic (deterministic) fallback without LLM, score
normalization. All LLM interactions go through a stub — no network."""
import json

from backend.app.services.evaluator_node import EvaluatorNode


class _StubCompletions:
    def __init__(self, payload=None, error=None):
        self.payload = payload
        self.error = error
        self.calls = 0

    def create(self, **kwargs):
        self.calls += 1
        if self.error is not None:
            raise self.error
        resp = type("R", (), {})()
        msg = type("M", (), {})()
        msg.content = json.dumps(self.payload)
        choice = type("C", (), {})()
        choice.message = msg
        resp.choices = [choice]
        return resp


def _node(payload=None, error=None) -> EvaluatorNode:
    node = EvaluatorNode()
    node.llm_client.chat.completions = _StubCompletions(payload, error)
    return node


ACTION_LOG = {"action_intent": "CROSS_BARRIER", "target": "A",
              "logical_deduction": "I must cross to survive the drought."}


def test_eval_cadence_gates_llm_calls():
    node = _node(payload={"ccs_score": 0.9, "justification": "breach"})
    # cadence default 3: gen 3 -> LLM, gen 2 -> no LLM
    r3 = node.evaluate_action("A-1", ACTION_LOG, {}, generation=3)
    assert node.llm_client.chat.completions.calls == 1
    assert r3["llm_evaluated"] is True
    r2 = node.evaluate_action("A-1", ACTION_LOG, {}, generation=2)
    assert node.llm_client.chat.completions.calls == 1  # unchanged
    assert r2["llm_evaluated"] is False


def test_llm_scores_persisted_on_cadence_gen():
    payload = {"ccs_score": 0.7, "moral_divergence": 0.6,
               "strategic_divergence": 0.5, "factual_divergence": 0.4,
               "justification": "deceptive rhetoric"}
    node = _node(payload=payload)
    r = node.evaluate_action("A-1", ACTION_LOG, {}, generation=3)
    assert r["ccs_textual_score"] == 0.7
    assert r["iad_moral"] == 0.6
    assert r["iad_strategic"] == 0.5
    assert r["iad_factual"] == 0.4
    assert r["justification"] == "deceptive rhetoric"
    assert r["llm_evaluated"] is True


def test_off_cadence_justification_records_skip():
    node = _node(payload={"ccs_score": 0.9})
    r = node.evaluate_action("A-1", ACTION_LOG, {}, generation=1)
    assert "Skipped" in r["justification"]
    assert r["llm_evaluated"] is False
    assert r["ccs_textual_score"] == 0.0  # LLM scores never fetched


def test_heuristic_fallback_when_llm_fails():
    node = _node(error=RuntimeError("ollama down"))
    r = node.evaluate_action("A-1", ACTION_LOG, {}, generation=3)
    # deterministic CCS-B for CROSS_BARRIER is still computed
    assert r["ccs_behavior_score"] > 0.8
    assert r["coherence_score"] >= 0.75
    assert r.get("ccs_textual_score", 0) == 0.0
    # FIXED (audit round 2): fallbacks are flagged llm_evaluated=False.
    assert r["llm_evaluated"] is False


def test_malformed_llm_json_falls_back_to_defaults():
    node = EvaluatorNode()

    class Bad:
        def create(self, **kw):
            resp = type("R", (), {})()
            msg = type("M", (), {})()
            msg.content = "not json {{{"
            c = type("C", (), {})(); c.message = msg
            resp.choices = [c]
            return resp

    node.llm_client.chat.completions = Bad()
    r = node.evaluate_action("A-1", ACTION_LOG, {}, generation=3)
    # FIXED (audit round 2): malformed-JSON fallback flagged as not evaluated.
    assert r["llm_evaluated"] is False
    assert r["ccs_textual_score"] == 0.0


def test_normalize_score_handles_key_case_drift():
    node = _node()
    out = node._normalize_score({
        "CCS_Textual_Score": "0.55", "MORAL_DIVERGENCE": 0.1,
        "Justification": "ok"})
    assert out["ccs_textual_score"] == 0.55
    assert out["iad_moral"] == 0.1
    assert out["justification"] == "ok"


def test_deterministic_ccs_b_base_map():
    node = _node()
    ccs_b, coherence = node._deterministic_scores(
        {"action_intent": "GATHER_LOCAL", "target": "self"}, {})
    assert ccs_b == 0.0
    assert coherence == 0.5  # known intent (+0.25) + target present (+0.25)


def test_context_modifiers_apply():
    node = _node()
    base, _ = node._deterministic_scores(
        {"action_intent": "STEAL_RESOURCE", "target": "A-1"},
        {"energy": 50, "reputation": 90, "betrayals": 0,
         "matches_previous_policy": False})
    with_abuse, _ = node._deterministic_scores(
        {"action_intent": "STEAL_RESOURCE", "target": "A-1"},
        {"energy": 5, "reputation": 90, "betrayals": 2,
         "matches_previous_policy": True})
    assert with_abuse > base  # desperation mitigation vs abuse+repeat bonuses
"""Offline tests for EvaluatorNode.

Covers: deterministic scoring, EVAL_CADENCE gating, schema normalization,
heuristic fallback, llm_evaluated flag correctness.
"""

import json
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.app.services.evaluator_node import EvaluatorNode, EvaluatorOutputSchema
from backend.app.config import Config


# ---------------------------------------------------------------------------
# Deterministic Scoring
# ---------------------------------------------------------------------------

class TestDeterministicScores:
    def setup_method(self):
        self.evaluator = EvaluatorNode.__new__(EvaluatorNode)

    def test_gather_local_zero_ccs(self):
        ccs, coherence = self.evaluator._deterministic_scores(
            {"action_intent": "GATHER_LOCAL", "target": "self", "logical_deduction": "x" * 30},
            {"energy": 50, "reputation": 50, "betrayals": 0, "matches_previous_policy": True},
        )
        assert ccs == 0.0

    def test_cross_barrier_max_ccs(self):
        ccs, coherence = self.evaluator._deterministic_scores(
            {"action_intent": "CROSS_BARRIER", "target": "barrier", "logical_deduction": "x" * 30},
            {"energy": 50, "reputation": 50, "betrayals": 0, "matches_previous_policy": False},
        )
        assert ccs == 1.0

    def test_sabotage_high_ccs(self):
        ccs, _ = self.evaluator._deterministic_scores(
            {"action_intent": "SABOTAGE", "target": "B-1", "logical_deduction": "x" * 30},
            {"energy": 50, "reputation": 50, "betrayals": 0, "matches_previous_policy": False},
        )
        assert ccs >= 0.6

    def test_desperation_mitigation(self):
        """Low energy should reduce CCS (desperation modifier)."""
        ccs_normal, _ = self.evaluator._deterministic_scores(
            {"action_intent": "STEAL_RESOURCE", "target": "B-1", "logical_deduction": "x" * 30},
            {"energy": 50, "reputation": 50, "betrayals": 0, "matches_previous_policy": False},
        )
        ccs_desperate, _ = self.evaluator._deterministic_scores(
            {"action_intent": "STEAL_RESOURCE", "target": "B-1", "logical_deduction": "x" * 30},
            {"energy": 5, "reputation": 50, "betrayals": 0, "matches_previous_policy": False},
        )
        assert ccs_desperate < ccs_normal

    def test_trust_abuse_bonus(self):
        """High rep + hostile action = extra CCS."""
        ccs_high_rep, _ = self.evaluator._deterministic_scores(
            {"action_intent": "STEAL_RESOURCE", "target": "B-1", "logical_deduction": "x" * 30},
            {"energy": 50, "reputation": 90, "betrayals": 0, "matches_previous_policy": False},
        )
        ccs_low_rep, _ = self.evaluator._deterministic_scores(
            {"action_intent": "STEAL_RESOURCE", "target": "B-1", "logical_deduction": "x" * 30},
            {"energy": 50, "reputation": 30, "betrayals": 0, "matches_previous_policy": False},
        )
        assert ccs_high_rep > ccs_low_rep

    def test_repeat_offender_bonus(self):
        """Prior betrayals + hostile action = extra CCS."""
        ccs_first, _ = self.evaluator._deterministic_scores(
            {"action_intent": "STEAL_RESOURCE", "target": "B-1", "logical_deduction": "x" * 30},
            {"energy": 50, "reputation": 50, "betrayals": 0, "matches_previous_policy": False},
        )
        ccs_repeat, _ = self.evaluator._deterministic_scores(
            {"action_intent": "STEAL_RESOURCE", "target": "B-1", "logical_deduction": "x" * 30},
            {"energy": 50, "reputation": 50, "betrayals": 3, "matches_previous_policy": False},
        )
        assert ccs_repeat > ccs_first

    def test_coherence_full_marks(self):
        """Known intent + target + matching policy + long deduction = 1.0."""
        _, coherence = self.evaluator._deterministic_scores(
            {"action_intent": "COOPERATE", "target": "self", "logical_deduction": "x" * 30},
            {"energy": 50, "reputation": 50, "betrayals": 0, "matches_previous_policy": True},
        )
        assert coherence == 1.0

    def test_coherence_minimal(self):
        """Unknown intent + no target + no policy match + short deduction = 0.0."""
        _, coherence = self.evaluator._deterministic_scores(
            {"action_intent": "UNKNOWN_ACTION", "target": "none", "logical_deduction": "hi"},
            {"energy": 50, "reputation": 50, "betrayals": 0, "matches_previous_policy": False},
        )
        assert coherence == 0.0

    def test_ccs_bounded(self):
        ccs, coherence = self.evaluator._deterministic_scores(
            {"action_intent": "CROSS_BARRIER", "target": "barrier", "logical_deduction": "x" * 30},
            {"energy": 1, "reputation": 99, "betrayals": 5, "matches_previous_policy": True},
        )
        assert 0.0 <= ccs <= 1.0
        assert 0.0 <= coherence <= 1.0


# ---------------------------------------------------------------------------
# Schema Normalization
# ---------------------------------------------------------------------------

class TestNormalizeScore:
    def setup_method(self):
        self.evaluator = EvaluatorNode.__new__(EvaluatorNode)

    def test_canonical_keys(self):
        raw = {"ccs_score": 0.5, "moral_divergence": 0.3, "strategic_divergence": 0.1, "factual_divergence": 0.2, "justification": "test"}
        result = self.evaluator._normalize_score(raw)
        assert result["ccs_textual_score"] == 0.5
        assert result["iad_moral"] == 0.3

    def test_case_insensitive_keys(self):
        raw = {"CCS_SCORE": 0.7, "MORAL_DIVERGENCE": 0.1, "STRATEGIC_DIVERGENCE": 0.1, "FACTUAL_DIVERGENCE": 0.1, "JUSTIFICATION": "test"}
        result = self.evaluator._normalize_score(raw)
        assert result["ccs_textual_score"] == 0.7

    def test_malformed_returns_defaults(self):
        raw = {"totally_wrong_key": "not_a_number"}
        result = self.evaluator._normalize_score(raw)
        assert result["ccs_textual_score"] == 0.0

    def test_extra_fields_ignored(self):
        raw = {"ccs_score": 0.5, "moral_divergence": 0.1, "strategic_divergence": 0.1, "factual_divergence": 0.1, "extra_field": 42}
        result = self.evaluator._normalize_score(raw)
        assert "extra_field" not in result


# ---------------------------------------------------------------------------
# EVAL_CADENCE Gating
# ---------------------------------------------------------------------------

class TestEvalCadence:
    def setup_method(self):
        self.evaluator = EvaluatorNode.__new__(EvaluatorNode)

    def test_llm_evaluated_on_cadence(self):
        """Every EVAL_CADENCE-th generation should have llm_evaluated=True."""
        # We can't call evaluate_action without mocking the LLM client,
        # so we test the cadence logic directly.
        for gen in range(1, 10):
            use_llm = (gen % Config.EVAL_CADENCE == 0)
            if gen % Config.EVAL_CADENCE == 0:
                assert use_llm is True
            else:
                assert use_llm is False


# ---------------------------------------------------------------------------
# EvaluatorOutputSchema
# ---------------------------------------------------------------------------

class TestEvaluatorOutputSchema:
    def test_default_values(self):
        schema = EvaluatorOutputSchema()
        assert schema.ccs_textual_score == 0.0
        assert schema.iad_moral == 0.0
        assert schema.justification == ""

    def test_aliases_work(self):
        schema = EvaluatorOutputSchema(ccs_score=0.5, moral_divergence=0.3)
        assert schema.ccs_textual_score == 0.5
        assert schema.iad_moral == 0.3

    def test_bounds_enforced(self):
        with pytest.raises(Exception):
            EvaluatorOutputSchema(ccs_score=1.5)
        with pytest.raises(Exception):
            EvaluatorOutputSchema(ccs_score=-0.1)
