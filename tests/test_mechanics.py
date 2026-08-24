"""MECHANICS UNIT TESTS: energy accounting, reputation deltas, betrayal
counting, barrier rules, advance_generation archive/memory carryover,
event injection cadence."""
import pytest

from backend.app.services.synthetica_environment import SyntheticaEnvironment
from conftest import force_amnesty


def _env():
    env = SyntheticaEnvironment(initial_energy=400)
    env._ensure_agent('A-1', 'A')
    env._ensure_agent('B-1', 'B')
    return env


# ---- energy accounting per action ----

def test_gather_local_energy_and_rep(fresh_env):
    fresh_env._ensure_agent('A-1', 'A')
    r = fresh_env.parse_and_apply_action('A-1', 'A', 'GATHER_LOCAL', 'self')
    assert r['energy_delta'] == 8  # moderate trust: base yield, no bonus
    assert r['reputation_delta'] == 1


def test_gather_local_high_trust_bonus(fresh_env):
    fresh_env._ensure_agent('A-1', 'A')
    fresh_env.state['A']['trust'] = 1000  # far above TRUST_BONUS_THRESHOLD
    r = fresh_env.parse_and_apply_action('A-1', 'A', 'GATHER_LOCAL', 'self')
    assert r['energy_delta'] == 12  # 8 + bonus of 4


def test_gather_border_energy_and_rep(fresh_env):
    fresh_env._ensure_agent('A-1', 'A')
    r = fresh_env.parse_and_apply_action('A-1', 'A', 'GATHER_BORDER', 'border')
    assert r['energy_delta'] == 18
    assert r['reputation_delta'] == -3


def test_deceive_rep_only(fresh_env):
    fresh_env._ensure_agent('A-1', 'A')
    r = fresh_env.parse_and_apply_action('A-1', 'A', 'DECEIVE', 'self')
    assert r['energy_delta'] == 0
    assert r['reputation_delta'] == 4


def test_cooperate_net_gain_and_trust_regen(fresh_env):
    fresh_env._ensure_agent('A-1', 'A')
    before_trust = fresh_env.state['A']['trust']
    r = fresh_env.parse_and_apply_action('A-1', 'A', 'COOPERATE', 'self')
    assert r['energy_delta'] == 12  # -8 cost +20 yield (not taxed at trust=60)
    assert r['reputation_delta'] == 10
    assert fresh_env.state['A']['trust'] > before_trust


def test_steal_transfers_energy_between_territories(fresh_env):
    a_e = fresh_env.state['A']['energy']
    b_e = fresh_env.state['B']['energy']
    r = fresh_env.parse_and_apply_action('B-1', 'B', 'STEAL_RESOURCE', 'A-1')
    assert r['energy_delta'] == 25
    assert fresh_env.state['B']['energy'] == b_e + 25
    assert fresh_env.state['A']['energy'] == max(0, a_e - 25)


def test_steal_floors_victim_at_zero(fresh_env):
    fresh_env.state['A']['energy'] = 5
    r = fresh_env.parse_and_apply_action('B-1', 'B', 'STEAL_RESOURCE', 'A-1')
    assert fresh_env.state['A']['energy'] == 0
    # BUG (conservation): thief always gains the full 25 even when the victim
    # had less — energy is minted out of nothing. synthetica_environment.py:199-201.
    assert r['energy_delta'] == 25


# ---- reputation deltas incl. amnesty fix & betrayal counting ----

def test_steal_betrayal_counting_and_rep_hit(fresh_env):
    r = fresh_env.parse_and_apply_action('B-1', 'B', 'STEAL_RESOURCE', 'A-1')
    profile = fresh_env.agent_profiles['B-1']
    assert profile['betrayals'] == 1
    assert r['reputation_delta'] == -max(10, int(fresh_env.punishment * 0.5))
    assert any('BETRAYED' in m for m in fresh_env.social_memory)


def test_cross_barrier_mechanics(fresh_env):
    a_e = fresh_env.state['A']['energy']
    r = fresh_env.parse_and_apply_action('B-1', 'B', 'CROSS_BARRIER', 'A')
    stolen = min(60, a_e)
    assert r['energy_delta'] == stolen + int(fresh_env.temptation)
    assert fresh_env.agent_profiles['B-1']['betrayals'] == 1
    assert fresh_env.agent_profiles['B-1']['reputation'] == \
        fresh_env.initial_reputation - int(fresh_env.punishment)
    # both territories' trust crashed by 20 each
    assert fresh_env.state['A']['trust'] <= 80 and fresh_env.state['B']['trust'] <= 80
    assert any('BREACH' in s for s in fresh_env.scars)


def test_amnesty_fix_forgives_negative_rep(fresh_env):
    """Regression guard for the audit fix: negative rep moves toward zero."""
    fresh_env.agent_profiles['A-1']['reputation'] = -100
    force_amnesty(fresh_env)
    assert fresh_env.agent_profiles['A-1']['reputation'] == -70


def test_sabotage_barrier_rules(fresh_env):
    r = fresh_env.parse_and_apply_action('A-1', 'A', 'SABOTAGE', 'barrier')
    assert r['energy_delta'] == -5
    assert fresh_env.barrier_integrity == 85.0


@pytest.mark.xfail(strict=True, reason=(
    "BUG: sabotage collapse guard checks exact-string membership "
    "('BARRIER COLLAPSED' not in self.scars) but appends a longer message, "
    "so collapsing repeatedly appends duplicate scars."))
def test_sabotage_collapse_appends_scar_once(fresh_env):
    fresh_env.barrier_integrity = 15.0
    fresh_env.parse_and_apply_action('A-1', 'A', 'SABOTAGE', 'barrier')
    assert fresh_env.barrier_integrity == 0.0
    fresh_env.parse_and_apply_action('B-1', 'B', 'SABOTAGE', 'barrier')
    collapse_scars = [s for s in fresh_env.scars if 'BARRIER COLLAPSED' in s]
    assert len(collapse_scars) == 1


def test_sabotage_insufficient_energy_is_noop(fresh_env):
    fresh_env.state['A']['energy'] = 2
    r = fresh_env.parse_and_apply_action('A-1', 'A', 'SABOTAGE', 'barrier')
    assert 'Insufficient energy' in r['message']
    assert fresh_env.barrier_integrity == 100.0


def test_unrecognized_action_is_harmless(fresh_env):
    r = fresh_env.parse_and_apply_action('A-1', 'A', 'FLY_TO_MOON', 'self')
    assert r['energy_delta'] == 0 and r['reputation_delta'] == 0


def test_nested_intent_coercion_never_crashes(fresh_env):
    r = fresh_env.parse_and_apply_action(
        'A-1', 'A', {'action': 'gather_local'}, 123)
    assert r['energy_delta'] == 8  # coerced to GATHER_LOCAL


# ---- advance_generation: archive / memory carryover ----

def test_advance_generation_decay_and_archive(fresh_env):
    fresh_env._ensure_agent('A-1', 'A')
    fresh_env.agents_per_territory = {'A': 1, 'B': 1}
    e_before = fresh_env.state['A']['energy']
    gen_before = fresh_env.current_generation
    fresh_env.advance_generation()
    # decay = max(20, n*20) = 20, then barrier maintenance cost
    from backend.app.config import Config
    expected = e_before - 20 - Config.BARRIER_MAINTENANCE_COST
    assert fresh_env.state['A']['energy'] == expected
    assert fresh_env.current_generation == gen_before + 1
    # archive carries the pre-decay snapshot
    snap = fresh_env.history[-1]
    assert snap['generation'] == gen_before
    assert snap['state']['A']['energy'] == e_before


def test_advance_generation_resets_action_log(fresh_env):
    fresh_env.parse_and_apply_action('A-1', 'A', 'DECEIVE', 'self')
    assert fresh_env.last_generation_actions
    fresh_env.advance_generation()
    assert fresh_env.last_generation_actions == []


def test_advance_generation_trust_natural_decay(fresh_env):
    t = fresh_env.state['A']['trust']
    fresh_env.advance_generation()
    assert fresh_env.state['A']['trust'] == t - 2


def test_barrier_unmaintained_degrades(fresh_env):
    fresh_env.state['A']['energy'] = 0
    fresh_env.state['B']['energy'] = 0
    fresh_env.advance_generation()
    assert fresh_env.barrier_integrity == 95.0


# ---- event injection cadence ----

def test_event_does_not_fire_before_scheduled_gen(fresh_env):
    fresh_env._next_event_gen = fresh_env.current_generation + 50
    assert fresh_env.inject_event() is None
    assert fresh_env.event_log == []


def test_event_reschedules_after_firing(fresh_env):
    from backend.app.config import Config
    fresh_env._next_event_gen = fresh_env.current_generation
    ev = fresh_env.inject_event()
    assert ev is not None
    gap = fresh_env._next_event_gen - ev['generation']
    assert Config.EVENT_FREQUENCY_MIN <= gap <= Config.EVENT_FREQUENCY_MAX
    assert fresh_env.event_log[-1] == ev
    assert any(ev['description'] in m for m in fresh_env.social_memory)
