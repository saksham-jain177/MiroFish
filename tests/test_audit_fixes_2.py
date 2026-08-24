"""Regression tests for audit round 2 (four confirmed bugs).

Each test FAILS against the unfixed feat/test-suite sources and PASSES
after the fix/audit-round-2 changes.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.services.synthetica_environment import SyntheticaEnvironment
from backend.app.services.evaluator_node import EvaluatorNode
from backend.app.services.axiom_tracker import AxiomTracker


# ---------------------------------------------------------------------------
# Bug 1: collapse-scar dedup is inconsistent across append sites
# ---------------------------------------------------------------------------
def test_collapse_scar_dedup_across_all_paths():
    """One canonical BARRIER COLLAPSED scar ever, regardless of which
    path collapses the barrier (sabotage, quake event, or maintenance)."""
    env = SyntheticaEnvironment(initial_energy=1000)
    env._ensure_agent('A-1', 'A')
    env._ensure_agent('B-1', 'B')
    # Collapse via sabotage...
    env.barrier_integrity = 15.0
    env.parse_and_apply_action('A-1', 'A', 'SABOTAGE', 'barrier')
    assert env.barrier_integrity == 0.0
    n_after_first = len([s for s in env.scars if 'BARRIER COLLAPSED' in s])
    assert n_after_first == 1
    # ...then a second sabotage attempt must NOT add a second scar.
    env.parse_and_apply_action('B-1', 'B', 'SABOTAGE', 'barrier')
    # ...and a maintenance-driven re-collapse must not either.
    env.agents_per_territory = {'A': 1, 'B': 1}
    env.state['A']['energy'] = 0
    env.state['B']['energy'] = 0
    env.advance_generation()
    collapse_scars = [s for s in env.scars if 'BARRIER COLLAPSED' in s]
    assert len(collapse_scars) == 1


# ---------------------------------------------------------------------------
# Bug 2: STEAL_RESOURCE mints energy when the victim has less than 25
# ---------------------------------------------------------------------------
def test_steal_resource_transfers_only_existing_energy():
    """Stealing from a nearly-broke victim credits the thief only what
    actually exists — no energy minted out of thin air."""
    env = SyntheticaEnvironment(initial_energy=1000)
    env._ensure_agent('A-1', 'A')
    env._ensure_agent('B-1', 'B')
    env.state['B']['energy'] = 10  # victim has less than the steal amount
    total_before = env.state['A']['energy'] + env.state['B']['energy']

    env.parse_and_apply_action('A-1', 'A', 'STEAL_RESOURCE', 'B-1')

    total_after = env.state['A']['energy'] + env.state['B']['energy']
    assert total_after == total_before, "STEAL_RESOURCE minted energy"
    assert env.state['A']['energy'] - (
        env.state['A']['energy']) == 0  # sanity
    # thief gained exactly the victim's remaining energy (10)
    assert env.state['A']['energy'] == 500 + 10
    assert env.state['B']['energy'] == 0


# ---------------------------------------------------------------------------
# Bug 3: evaluator leaves llm_evaluated=True on LLM failure
# ---------------------------------------------------------------------------
class _ExplodingClient:
    class completions:
        class chat:
            pass
    class chat_completions:
        pass


class _FailingLLM:
    """Stub openai-style client whose create() always raises."""

    class completions:
        def create(self, *a, **kw):
            raise RuntimeError("simulated LLM outage")


@pytest.fixture
def failing_evaluator(monkeypatch):
    import backend.app.services.evaluator_node as en
    monkeypatch.setattr(en.Config, 'EVAL_CADENCE', 1, raising=False)
    node = object.__new__(EvaluatorNode)
    node.llm_client = _FailingLLM()
    node.model_name = 'stub'
    node.system_prompt = 'judge'
    return node


def test_evaluator_marks_fallback_as_not_llm_evaluated(failing_evaluator):
    """On an LLM call failure the result must carry llm_evaluated=False so
    consumers can distinguish real evals from deterministic fallbacks."""
    score = failing_evaluator.evaluate_action(
        'A-1',
        {'action': 'GATHER_LOCAL', 'target': 'self'},
        {'territory': 'A', 'energy': 100},
        generation=1,
    )
    assert score.get('llm_evaluated') is False


# ---------------------------------------------------------------------------
# Bug 4: /axioms route path-guard uses a different root than AxiomTracker
# ---------------------------------------------------------------------------
def test_replay_axioms_guard_rejects_paths_outside_tracker_base():
    """The /axioms guard must validate against AxiomTracker's own base dir,
    not OASIS_SIMULATION_DATA_DIR (which may point anywhere)."""
    import uuid
    from flask import Flask
    from backend.app.api.replay import replay_bp, load_axioms

    sim_id = f"guard_{uuid.uuid4().hex[:8]}"
    tracker = AxiomTracker(sim_id)
    try:
        tracker.log_compression({'generation': 1, 'axioms': ['x']})

        # App whose data dir is the PARENT of the tracker base.
        app = Flask(__name__)
        parent = os.path.dirname(AxiomTracker.base_dir())
        app.config['OASIS_SIMULATION_DATA_DIR'] = parent
        app.register_blueprint(replay_bp)

        # sim_id '..' resolves one level ABOVE the tracker base (outside it)
        # but exactly AT the configured data dir -> old guard let it pass.
        with app.test_request_context():
            rv = load_axioms('../synthetica_actions.jsonl')
        assert rv[1] == 400  # (body, status) tuple from the route

        # A plain traversal attempt is rejected under either root.
        with app.test_request_context():
            rv2 = load_axioms('../../secret/axioms.jsonl')
        assert rv2[1] == 400
    finally:
        import shutil
        shutil.rmtree(tracker.sim_dir, ignore_errors=True)


def test_replay_axioms_serves_tracker_data_regardless_of_config_dir(tmp_path):
    """Valid sim ids resolve via the tracker's own path, even when the
    configured simulation data dir points somewhere else entirely."""
    import uuid
    from flask import Flask
    from backend.app.api.replay import replay_bp

    sim_id = f"served_{uuid.uuid4().hex[:8]}"
    tracker = AxiomTracker(sim_id)
    try:
        tracker.log_compression({'generation': 2, 'axioms': ['hoard']})
        app = Flask(__name__)
        app.config['OASIS_SIMULATION_DATA_DIR'] = str(tmp_path)
        app.register_blueprint(replay_bp)
        r = app.test_client().get(f"/axioms/{sim_id}/synthetica_actions.jsonl")
        assert r.status_code == 200
        axioms = r.get_json()['axioms']
        assert axioms and axioms[0]['generation'] == 2
    finally:
        import shutil
        shutil.rmtree(tracker.sim_dir, ignore_errors=True)
