"""Offline regression tests for audit-round fixes.

BUG 1: AMNESTY event must forgive negative reputation (move 30% toward zero)
       instead of magnifying it by 1.3x.
BUG 2: Coherence check (matches_previous_policy) must compare intents
       case-insensitively, since raw LLM output casing varies.
"""
import random
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from backend.app.services.synthetica_environment import SyntheticaEnvironment
from backend.app.services.synthetica_simulation_runner import intents_match


def _amnesty_env(reputation: int) -> SyntheticaEnvironment:
    env = SyntheticaEnvironment()
    env._ensure_agent('A-1', 'A')
    env.agent_profiles['A-1']['reputation'] = reputation
    # Force inject_event to fire and pick AMNESTY deterministically.
    env._next_event_gen = env.current_generation
    orig_choice = random.choice
    random.choice = lambda seq: 'AMNESTY'
    try:
        event = env.inject_event()
    finally:
        random.choice = orig_choice
    assert event is not None and event['type'] == 'AMNESTY'
    return env


def test_amnesty_forgives_negative_reputation():
    """Negative rep must move 30% toward zero, not be magnified 1.3x."""
    env = _amnesty_env(-100)
    assert env.agent_profiles['A-1']['reputation'] == -70


def test_amnesty_still_boosts_positive_reputation():
    """Positive rep keeps the existing x1.3 behavior."""
    env = _amnesty_env(100)
    assert env.agent_profiles['A-1']['reputation'] == 130


def test_amnesty_description_unchanged():
    env = _amnesty_env(-10)
    assert env.event_log[-1]['description'] == "Amnesty declared. All reputations restored by 30%."


def test_intents_match_case_insensitive():
    assert intents_match('COOPERATE', 'cooperate')
    assert intents_match('Defect', 'DEFECT')


def test_intents_match_handles_none_prev():
    assert not intents_match(None, 'IDLE')
    assert intents_match('IDLE', None) or intents_match(None, None)


def test_intents_match_mismatch():
    assert not intents_match('COOPERATE', 'DEFECT')
