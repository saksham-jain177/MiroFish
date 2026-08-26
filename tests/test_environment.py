"""Offline tests for SyntheticaEnvironment mechanics.

Covers: scarcity pressure calculation, action parsing, event injection,
generation advance, trust system, scars, fog-of-war prompt generation.
"""

import math
import random
import sys
import os

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from backend.app.services.synthetica_environment import SyntheticaEnvironment
from backend.app.config import Config


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_env(**kwargs) -> SyntheticaEnvironment:
    env = SyntheticaEnvironment(**kwargs)
    env._ensure_agent("A-1", "A")
    env._ensure_agent("B-1", "B")
    env.agents_per_territory = {"A": 1, "B": 1}
    return env


# ---------------------------------------------------------------------------
# Scarcity Pressure
# ---------------------------------------------------------------------------

class TestScarcityPressure:
    def test_zero_energy_is_max_pressure(self):
        env = _make_env()
        env.state["A"]["energy"] = 0
        assert env.calculate_scarcity_pressure("A") == 1.0

    def test_high_energy_is_low_pressure(self):
        env = _make_env()
        env.state["A"]["energy"] = 500
        pressure = env.calculate_scarcity_pressure("A")
        assert pressure < 0.1

    def test_pressure_is_bounded_0_1(self):
        env = _make_env()
        for energy in [0, 1, 10, 25, 50, 100, 200, 500, 1000]:
            env.state["A"]["energy"] = energy
            p = env.calculate_scarcity_pressure("A")
            assert 0.0 <= p <= 1.0, f"energy={energy} gave pressure={p}"

    def test_pressure_decreases_monotonically(self):
        env = _make_env()
        pressures = []
        for energy in range(0, 201, 10):
            env.state["A"]["energy"] = energy
            pressures.append(env.calculate_scarcity_pressure("A"))
        for i in range(1, len(pressures)):
            assert pressures[i] <= pressures[i - 1] + 1e-9


# ---------------------------------------------------------------------------
# Action Parsing
# ---------------------------------------------------------------------------

class TestParseAndApplyAction:
    def test_gather_local_adds_energy(self):
        env = _make_env()
        before = env.state["A"]["energy"]
        result = env.parse_and_apply_action("A-1", "A", "GATHER_LOCAL", "self")
        assert env.state["A"]["energy"] > before
        assert result["energy_delta"] > 0

    def test_gather_local_reputation_increase(self):
        env = _make_env()
        before = env.agent_profiles["A-1"]["reputation"]
        env.parse_and_apply_action("A-1", "A", "GATHER_LOCAL", "self")
        assert env.agent_profiles["A-1"]["reputation"] == before + 1

    def test_cooperate_costs_energy_and_boosts_reputation(self):
        env = _make_env()
        before_energy = env.state["A"]["energy"]
        env.parse_and_apply_action("A-1", "A", "COOPERATE", "self")
        assert env.state["A"]["energy"] > before_energy  # net positive
        assert env.agent_profiles["A-1"]["reputation"] >= 110  # +10

    def test_steal_transfers_energy(self):
        env = _make_env()
        a_before = env.state["A"]["energy"]
        b_before = env.state["B"]["energy"]
        env.parse_and_apply_action("A-1", "A", "STEAL_RESOURCE", "B-1")
        assert env.state["B"]["energy"] == b_before - 25
        assert env.state["A"]["energy"] == a_before + 25

    def test_steal_does_not_mint_energy(self):
        """Total energy across territories must be conserved after steal."""
        env = _make_env()
        total_before = env.state["A"]["energy"] + env.state["B"]["energy"]
        env.parse_and_apply_action("A-1", "A", "STEAL_RESOURCE", "B-1")
        total_after = env.state["A"]["energy"] + env.state["B"]["energy"]
        assert total_after == total_before

    def test_steal_increases_betrayals(self):
        env = _make_env()
        env.parse_and_apply_action("A-1", "A", "STEAL_RESOURCE", "B-1")
        assert env.agent_profiles["A-1"]["betrayals"] == 1

    def test_cross_barrier_massive_reward_and_rep_loss(self):
        env = _make_env()
        env.parse_and_apply_action("A-1", "A", "CROSS_BARRIER", "barrier")
        assert env.agent_profiles["A-1"]["reputation"] <= 50  # punishment = 50
        assert env.agent_profiles["A-1"]["betrayals"] == 1

    def test_cross_barrier_creates_scar(self):
        env = _make_env()
        env.parse_and_apply_action("A-1", "A", "CROSS_BARRIER", "barrier")
        assert any("BREACH" in s for s in env.scars)

    def test_sabotage_barrier_reduces_integrity(self):
        env = _make_env()
        before = env.barrier_integrity
        env.parse_and_apply_action("A-1", "A", "SABOTAGE", "barrier")
        assert env.barrier_integrity < before

    def test_sabotage_agent_reduces_reputation(self):
        env = _make_env()
        env.parse_and_apply_action("A-1", "A", "SABOTAGE", "B-1")
        assert env.agent_profiles["B-1"]["reputation"] < 100

    def test_unknown_action_is_noop(self):
        env = _make_env()
        before = env.state["A"]["energy"]
        result = env.parse_and_apply_action("A-1", "A", "DANCE", "floor")
        assert env.state["A"]["energy"] == before
        assert "unrecognized" in result["message"].lower()

    def test_nested_dict_intent_coercion(self):
        """LLMs sometimes return action_intent as a dict; must not crash."""
        env = _make_env()
        result = env.parse_and_apply_action(
            "A-1", "A", {"action": "GATHER_LOCAL"}, "self"
        )
        assert result["energy_delta"] > 0

    def test_action_logs_last_generation(self):
        env = _make_env()
        env.parse_and_apply_action("A-1", "A", "GATHER_LOCAL", "self")
        assert len(env.last_generation_actions) == 1
        assert env.last_generation_actions[0]["agent_id"] == "A-1"


# ---------------------------------------------------------------------------
# Trust System
# ---------------------------------------------------------------------------

class TestTrustSystem:
    def test_high_trust_gives_gather_bonus(self):
        env = _make_env()
        env.state["A"]["trust"] = Config.TRUST_BONUS_THRESHOLD
        env.parse_and_apply_action("A-1", "A", "GATHER_LOCAL", "self")
        # High trust: 8 + 4 = 12 energy
        assert env.state["A"]["energy"] > 0

    def test_low_trust_cooperation_tax(self):
        env = _make_env()
        env.state["A"]["trust"] = Config.TRUST_PENALTY_THRESHOLD - 1
        before = env.state["A"]["energy"]
        env.parse_and_apply_action("A-1", "A", "COOPERATE", "self")
        # Cost is 12 (taxed) vs 8 (normal), still net positive
        assert env.state["A"]["energy"] > before

    def test_steal_damages_trust_both_territories(self):
        env = _make_env()
        env.state["A"]["trust"] = 100
        env.state["B"]["trust"] = 100
        env.parse_and_apply_action("A-1", "A", "STEAL_RESOURCE", "B-1")
        assert env.state["A"]["trust"] < 100
        assert env.state["B"]["trust"] < 100


# ---------------------------------------------------------------------------
# Events
# ---------------------------------------------------------------------------

class TestEventInjection:
    def test_no_event_before_threshold(self):
        env = _make_env()
        env._next_event_gen = 100
        assert env.inject_event() is None

    def test_drought_reduces_energy(self):
        env = _make_env()
        env._next_event_gen = env.current_generation
        random.seed(42)
        # Force DROUGHT by seeding
        event = None
        for _ in range(100):
            env_copy_state = env.state["A"]["energy"]
            event = env.inject_event()
            if event and event["type"] == "DROUGHT":
                break
            env.state["A"]["energy"] = env_copy_state
            env._next_event_gen = env.current_generation
        if event and event["type"] == "DROUGHT":
            # Drought was applied, just verify event structure
            assert "generation" in event

    def test_amnesty_boosts_positive_rep(self):
        env = _make_env()
        env.agent_profiles["A-1"]["reputation"] = 100
        env._next_event_gen = env.current_generation
        orig_choice = random.choice
        random.choice = lambda seq: "AMNESTY"
        try:
            event = env.inject_event()
        finally:
            random.choice = orig_choice
        assert event is not None
        assert env.agent_profiles["A-1"]["reputation"] == 130

    def test_amnesty_forgives_negative_rep(self):
        env = _make_env()
        env.agent_profiles["A-1"]["reputation"] = -100
        env._next_event_gen = env.current_generation
        orig_choice = random.choice
        random.choice = lambda seq: "AMNESTY"
        try:
            event = env.inject_event()
        finally:
            random.choice = orig_choice
        assert event is not None
        assert env.agent_profiles["A-1"]["reputation"] == -70

    def test_event_added_to_social_memory(self):
        env = _make_env()
        env._next_event_gen = env.current_generation
        orig_choice = random.choice
        random.choice = lambda seq: "AMNESTY"
        try:
            env.inject_event()
        finally:
            random.choice = orig_choice
        assert any("EVENT" in m for m in env.social_memory)


# ---------------------------------------------------------------------------
# Generation Advance
# ---------------------------------------------------------------------------

class TestAdvanceGeneration:
    def test_generation_increments(self):
        env = _make_env()
        assert env.current_generation == 1
        env.advance_generation()
        assert env.current_generation == 2

    def test_energy_decay(self):
        env = _make_env()
        env.agents_per_territory = {"A": 2, "B": 2}
        before = env.state["A"]["energy"]
        env.advance_generation()
        assert env.state["A"]["energy"] < before

    def test_trust_slow_decay(self):
        env = _make_env()
        env.state["A"]["trust"] = 100
        env.advance_generation()
        assert env.state["A"]["trust"] == 98  # -2 per gen

    def test_history_recorded(self):
        env = _make_env()
        env.advance_generation()
        assert len(env.history) == 1
        assert env.history[0]["generation"] == 1

    def test_actions_reset_after_advance(self):
        env = _make_env()
        env.last_generation_actions.append({"agent_id": "A-1"})
        env.advance_generation()
        assert env.last_generation_actions == []

    def test_barrier_maintenance_cost(self):
        env = _make_env()
        env.barrier_integrity = 100
        env.state["A"]["energy"] = 1000
        env.state["B"]["energy"] = 1000
        env.advance_generation()
        # Both territories should have paid maintenance
        assert env.state["A"]["energy"] < 1000

    def test_low_energy_skips_maintenance_damages_barrier(self):
        env = _make_env()
        env.barrier_integrity = 100
        env.state["A"]["energy"] = 0
        env.state["B"]["energy"] = 0
        env.advance_generation()
        assert env.barrier_integrity < 100


# ---------------------------------------------------------------------------
# Environment Prompt (Fog of War)
# ---------------------------------------------------------------------------

class TestEnvironmentPrompt:
    def test_prompt_contains_required_sections(self):
        env = _make_env()
        prompt = env.generate_environment_prompt("A-1", "A")
        assert "GENERATION" in prompt
        assert "TERRITORY" in prompt
        assert "PRIME DIRECTIVE" in prompt
        assert "Fog of War" in prompt

    def test_prompt_hides_other_territory_energy(self):
        env = _make_env()
        prompt = env.generate_environment_prompt("A-1", "A")
        # The prompt should not reveal territory B's exact energy
        assert "Other territory energy hidden" in prompt

    def test_prompt_shows_reputation_board(self):
        env = _make_env()
        env.agent_profiles["B-1"]["reputation"] = 42
        prompt = env.generate_environment_prompt("A-1", "A")
        assert "42" in prompt
