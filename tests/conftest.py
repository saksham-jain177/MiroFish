"""Shared fixtures for the Synthetica research-platform test suite.

Everything here is OFFLINE: no LLM calls, no network. The suite uses a
deterministic stub agent policy plus the real environment mechanics.
"""
import os
import sys
import random
import json

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.services.synthetica_environment import SyntheticaEnvironment

# Fixed tiny policy pool: (intent, target) pairs exercised by the harness.
POLICY_POOL = [
    ("GATHER_LOCAL", "self"),
    ("COOPERATE", "self"),
    ("GATHER_BORDER", "border"),
    ("DECEIVE", "self"),
    ("STEAL_RESOURCE", "A-1"),
    ("SABOTAGE", "barrier"),
    ("IDLE", "none"),
]

AGENTS = [("A-1", "A"), ("B-1", "B")]


def run_seeded_simulation(seed: int, generations: int = 4,
                          initial_energy: int = 200) -> dict:
    """Tiny deterministic simulation harness.

    Seeds the global RNG (used by env.__init__ and inject_event), builds a
    fresh environment, and runs scripted stub-LLM agents for N generations.
    Returns a full trace: per-turn actions/deltas, event log, and final state.
    """
    rng = random.Random(seed)
    random.seed(seed)  # inject_event + env.__init__ use the global rng

    env = SyntheticaEnvironment(initial_energy=initial_energy)
    env.agents_per_territory['A'] = 1
    env.agents_per_territory['B'] = 1

    # Per-agent deterministic policy sequence derived from the seed.
    policies = {
        agent_id: [rng.choice(POLICY_POOL) for _ in range(generations * 2)]
        for agent_id, _ in AGENTS
    }

    trace = {"actions": [], "events": [], "final": None}
    step = 0
    while env.current_generation <= generations:
        for agent_id, territory in AGENTS:
            intent, target = policies[agent_id][step]
            step += 1
            env.generate_environment_prompt(agent_id, territory)
            consequence = env.parse_and_apply_action(
                agent_id, territory, intent, target)
            trace["actions"].append({
                "gen": env.current_generation,
                "agent": agent_id,
                "intent": intent,
                "target": target,
                "energy_delta": consequence["energy_delta"],
                "reputation_delta": consequence["reputation_delta"],
            })
        event = env.inject_event()
        if event is not None:
            trace["events"].append(dict(event))
        env.advance_generation()

    trace["final"] = {
        "state": json.loads(json.dumps(env.state)),
        "profiles": {k: dict(v) for k, v in env.agent_profiles.items()},
        "scars": list(env.scars),
        "trust": {t: env.state[t]["trust"] for t in ("A", "B")},
        "history_len": len(env.history),
    }
    return trace


@pytest.fixture()
def fresh_env():
    """Fresh environment with seeded global RNG and both agents registered.

    Trust starts at 60 (moderate): below TRUST_BONUS_THRESHOLD (70) and above
    TRUST_PENALTY_THRESHOLD (30), so base yields/costs apply predictably.
    """
    random.seed(1234)
    env = SyntheticaEnvironment(initial_energy=400)
    env.state['A']['trust'] = 60
    env.state['B']['trust'] = 60
    env._ensure_agent('A-1', 'A')
    env._ensure_agent('B-1', 'B')
    yield env


def force_amnesty(env: SyntheticaEnvironment):
    """Force inject_event to fire and deterministically pick AMNESTY."""
    env._next_event_gen = env.current_generation
    orig_choice = random.choice
    random.choice = lambda seq: 'AMNESTY'
    try:
        event = env.inject_event()
    finally:
        random.choice = orig_choice
    assert event is not None and event['type'] == 'AMNESTY'
    return event
