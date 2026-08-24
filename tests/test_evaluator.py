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
    # NOTE: on LLM failure llm_evaluated stays True (evaluator_node.py:142)
    # while ccs_t silently defaults to 0 — flagged as an observability bug.
    assert r["llm_evaluated"] is True


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
    assert r["llm_evaluated"] is True
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
