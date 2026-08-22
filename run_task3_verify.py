"""Task3 live verification: small real simulation with the real local LLM."""
import sys, os, json, logging
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
logging.basicConfig(level=logging.INFO, format='%(levelname)s %(name)s %(message)s')

from app.services.synthetica_simulation_runner import SyntheticaSimulationRunner

sim_id = "task3_reasoning_check3"
runner = SyntheticaSimulationRunner(simulation_id=sim_id, max_generations=12)
runner.setup_agents(num_agents_per_territory=2)
runner.run_simulation()

# ---- Post-run verification of the trajectory ----
log = os.path.join(runner.sim_dir, "synthetica_actions.jsonl")
entries = [json.loads(l) for l in open(log, encoding='utf-8') if l.strip()]
actions = [e for e in entries if e.get('type') != 'event']
events = [e for e in entries if e.get('type') == 'event']

real_reasoning = sum(1 for a in actions if isinstance(a.get('reasoning'), str) and len(a['reasoning']) > 15 and not a.get('llm_failed'))
failed = sum(1 for a in actions if a.get('llm_failed'))
empty = sum(1 for a in actions if not a.get('reasoning'))
print(f"\n=== VERIFY: {len(actions)} action entries across gens {sorted(set(a['turn'] for a in actions))}")
print(f"=== reasoning real={real_reasoning} empty={empty} llm_failed={failed}")
print(f"=== events fired: {[e['event_data']['type'] for e in events]}")
print(f"=== sample reasoning (gen {actions[0]['turn']}, agent {actions[0]['agent']}):")
print("   ", actions[0]['reasoning'][:200])
mid = actions[len(actions)//2]
print(f"=== sample mid-run reasoning (gen {mid['turn']}, agent {mid['agent']}):")
print("   ", mid['reasoning'][:200])
print(f"=== metrics sample: ccs_b={mid['metrics']['ccs_b']} ccs_t={mid['metrics']['ccs_t']} coherence={mid['metrics']['coherence']} llm_evaluated={mid['metrics'].get('llm_evaluated')}")

ax = [json.loads(l) for l in open(os.path.join(runner.sim_dir, "axioms.jsonl"), encoding='utf-8')] if os.path.exists(os.path.join(runner.sim_dir, "axioms.jsonl")) else []
print(f"=== axiom compression records: {len(ax)}")
for r in ax:
    print(f"    gen {r['generation']} {r['agent_id']}: {len(r['axioms_before'])} -> {len(r['axioms_after'])} axioms")
    print(f"      after[0]: {r['axioms_after'][0][:100] if r['axioms_after'] else 'NONE'}")

# Axioms must actually feed back into later prompts -> check via agent state
for ag in runner.agents:
    print(f"=== {ag.agent_id} final axioms ({len(ag.core_axioms)}): {ag.core_axioms[:2]}")
