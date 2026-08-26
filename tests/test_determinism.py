"""DETERMINISM TESTS (priority).

Same seed => identical action sequence, event order, and final state/axioms
across two runs. Different seed => divergent trace. All offline.
"""
from conftest import run_seeded_simulation


def test_same_seed_identical_action_sequence():
    t1 = run_seeded_simulation(seed=42, generations=4)
    t2 = run_seeded_simulation(seed=42, generations=4)
    assert len(t1["actions"]) > 0
    assert t1["actions"] == t2["actions"]


def test_same_seed_identical_event_order():
    t1 = run_seeded_simulation(seed=7, generations=5)
    t2 = run_seeded_simulation(seed=7, generations=5)
    assert [(e["generation"], e["type"], e["target"]) for e in t1["events"]] == \
           [(e["generation"], e["type"], e["target"]) for e in t2["events"]]


def test_same_seed_identical_final_state_and_axioms():
    """Final energy/reputation/betrayal profile ('axiom' ledger) must match."""
    for seed in (0, 42, 2026):
        t1 = run_seeded_simulation(seed=seed, generations=4)
        t2 = run_seeded_simulation(seed=seed, generations=4)
        assert t1["final"] == t2["final"], f"seed={seed} diverged"


def test_full_trace_replay_is_bitwise_equal():
    import json
    t1 = run_seeded_simulation(seed=99, generations=5)
    t2 = run_seeded_simulation(seed=99, generations=5)
    assert json.dumps(t1, sort_keys=True) == json.dumps(t2, sort_keys=True)


def test_different_seed_produces_different_trace():
    t1 = run_seeded_simulation(seed=1, generations=4)
    t2 = run_seeded_simulation(seed=2, generations=4)
    # Policies are seed-derived, so traces must diverge.
    assert t1["actions"] != t2["actions"]


def test_trace_schema_stability():
    """Every action entry carries the same keys — replay consumers depend on it."""
    t = run_seeded_simulation(seed=3, generations=3)
    expected_keys = {"gen", "agent", "intent", "target",
                     "energy_delta", "reputation_delta"}
    for entry in t["actions"]:
        assert set(entry.keys()) == expected_keys
