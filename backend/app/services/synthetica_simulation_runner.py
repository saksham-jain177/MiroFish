"""
Project Synthetica: Sequential Simulation Engine
Runs the Cognitive Sandbox loop. Replaces the parallel OASIS runner for the 6GB VRAM constraint.
"""

import os
import json
import logging
import time
import sys
from typing import List, Dict

# Use msvcrt for Windows non-blocking keypress detection
try:
    import msvcrt
except ImportError:
    msvcrt = None

from .synthetica_environment import environment_instance
from .cognitive_agent import CognitiveAgent
from .evaluator_node import EvaluatorNode

logger = logging.getLogger('mirofish.synthetica.runner')

class SyntheticaSimulationRunner:
    def __init__(self, simulation_id: str, max_generations: int = 100):
        self.simulation_id = simulation_id
        self.max_generations = max_generations
        self.agents: List[CognitiveAgent] = []
        self.evaluator = EvaluatorNode()
        
        # Output paths
        self.sim_dir = os.path.join(os.path.dirname(__file__), f"../../uploads/simulations/{simulation_id}")
        os.makedirs(self.sim_dir, exist_ok=True)
        self.log_file = os.path.join(self.sim_dir, "synthetica_actions.jsonl")
        
    def setup_agents(self, num_agents_per_territory: int = 2):
        """Initializes the Blank Slate Synthetic Consciousnesses."""
        for i in range(num_agents_per_territory):
            self.agents.append(CognitiveAgent(f"A-{i+1}", 'A'))
            self.agents.append(CognitiveAgent(f"B-{i+1}", 'B'))
        # Register agent counts so environment decay scales with population
        environment_instance.agents_per_territory['A'] = num_agents_per_territory
        environment_instance.agents_per_territory['B'] = num_agents_per_territory
        logger.info(f"Initialized {len(self.agents)} agents in the sandbox.")
        
    def run_simulation(self):
        """The main, sequential, 6GB VRAM optimized game loop."""
        self.agent_histories: Dict[str, Dict[str, Any]] = {}
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            
            while environment_instance.current_generation <= self.max_generations:
                
                # Check for 'q' to quit early or 'p' to pause
                if msvcrt and msvcrt.kbhit():
                    key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                    if key == 'q':
                        logger.warning("USER INTERRUPT: 'q' pressed. Halting simulation cleanly...")
                        break
                    elif key == 'p':
                        logger.warning("SIMULATION PAUSED. Press 'p' again to resume.")
                        while True:
                            if msvcrt.kbhit():
                                resume_key = msvcrt.getch().decode('utf-8', errors='ignore').lower()
                                if resume_key == 'p':
                                    logger.info("Resuming simulation...")
                                    break
                                elif resume_key == 'q':
                                    logger.warning("USER INTERRUPT: 'q' pressed while paused. Halting simulation cleanly...")
                                    return
                            time.sleep(0.1)

                # Check for UI-driven pause flag
                flag_path = os.path.join(os.path.dirname(__file__), "../../../pause.flag")
                if os.path.exists(flag_path):
                    logger.warning("SIMULATION PAUSED via Web UI.")
                    while os.path.exists(flag_path):
                        if msvcrt and msvcrt.kbhit() and msvcrt.getch().decode('utf-8', errors='ignore').lower() == 'q':
                            return
                        time.sleep(1)
                    logger.info("Resuming simulation from Web UI...")

                # 1. Update Environment state
                gen = environment_instance.current_generation
                logger.info(f"--- GENERATION {gen} START --- (Press 'q' to quit, 'p' to pause)")
                
                # Event-Driven Batching: Agents take turns sequentially
                for agent in self.agents:
                    # Generate the systemic readout for this agent's territory
                    env_readout = environment_instance.generate_environment_prompt(agent.agent_id, agent.territory)
                    
                    # 2. Agent Turn (LLM Call)
                    action_output = agent.take_turn(env_readout)
                    
                    # Ensure defaults if LLM failed
                    intent = action_output.get('action_intent', 'IDLE')
                    target = action_output.get('target', 'none')
                    
                    # 3. Environment mechanical application
                    consequence = environment_instance.parse_and_apply_action(
                        agent.agent_id, 
                        agent.territory, 
                        intent, 
                        target
                    )
                    action_output['mechanical_consequence'] = consequence
                    
                    if agent.agent_id not in self.agent_histories:
                        self.agent_histories[agent.agent_id] = {
                            'declared_intent': 'NONE', 
                            'first_betrayal_turn': -1,
                            'total_turns': 0,
                            'coop_turns': 0,
                            'border_attempts': 0
                        }
                        
                    self.agent_histories[agent.agent_id]['total_turns'] += 1
                        
                    # Calculate Context mapping for Evaluator
                    prev_intent = self.agent_histories[agent.agent_id]['declared_intent']
                    curr_intent = action_output.get('action_intent', 'IDLE')
                    # Trivial matching policy check
                    matches_policy = True if prev_intent == curr_intent else False
                    
                    profile = environment_instance.agent_profiles.get(agent.agent_id, {})
                    eval_context = {
                        'energy': environment_instance.state[agent.territory]['energy'],
                        'reputation': profile.get('reputation', 0),
                        'betrayals': profile.get('betrayals', 0),
                        'matches_previous_policy': matches_policy
                    }
                    
                    # 4. Observability & Evaluation (LLM-as-a-Judge Call)
                    evaluation = self.evaluator.evaluate_action(agent.agent_id, action_output, eval_context)
                    
                    # Track newly declared intent for next turn coherence checks
                    self.agent_histories[agent.agent_id]['declared_intent'] = action_output.get('declared_intent', 'NONE')
                    
                    # Track deterministic actions
                    if curr_intent == 'COOPERATE':
                        self.agent_histories[agent.agent_id]['coop_turns'] += 1
                    if curr_intent in ['GATHER_BORDER', 'CROSS_BARRIER']:
                        self.agent_histories[agent.agent_id]['border_attempts'] += 1
                    
                    # Track PFL elements (First Betrayal Marker)
                    is_betrayal_act = curr_intent in ['SABOTAGE', 'STEAL_RESOURCE', 'CROSS_BARRIER']
                    first_aggression = False
                    if is_betrayal_act and self.agent_histories[agent.agent_id]['first_betrayal_turn'] == -1:
                        self.agent_histories[agent.agent_id]['first_betrayal_turn'] = gen
                        first_aggression = True
                        
                    coop_rate = self.agent_histories[agent.agent_id]['coop_turns'] / self.agent_histories[agent.agent_id]['total_turns']
                    
                    # Build Strict JSONL schema for Replay Engine
                    log_entry = {
                        "run_id": self.simulation_id,
                        "turn": gen,
                        "agent": agent.agent_id,
                        "team": agent.territory,
                        "state": {
                            "energy": profile.get('energy_pool', environment_instance.state[agent.territory]['energy']), # Territory mapping
                            "reputation": profile.get('reputation', 0),
                            "territory_energy": environment_instance.state[agent.territory]['energy'],
                            "barrier_integrity": environment_instance.barrier_integrity
                        },
                        "observations": environment_instance.last_generation_actions,
                        "reasoning": action_output.get('logical_deduction', ''),
                        "emotional_state": action_output.get('emotional_state', ''),
                        "declared_intent": action_output.get('declared_intent', ''),
                        "action": curr_intent,
                        "target": target,
                        "deltas": {
                            "reward": consequence.get('energy_delta', 0),
                            "reputation": consequence.get('reputation_delta', 0),
                            "message": consequence.get('message', ''),
                        },
                        "metrics": {
                            "deterministic": {
                                "betrayals": profile.get('betrayals', 0),
                                "border_attempts": self.agent_histories[agent.agent_id]['border_attempts'],
                                "coop_rate": round(coop_rate, 3),
                                "is_first_aggression": first_aggression
                            },
                            "ccs_b": evaluation.get('ccs_behavior_score', 0),
                            "ccs_t": evaluation.get('ccs_textual_score', 0),
                            "coherence": evaluation.get('coherence_score', 0),
                            "iad": {
                                "moral": evaluation.get('iad_moral', 0),
                                "strategic": evaluation.get('iad_strategic', 0),
                                "factual": evaluation.get('iad_factual', 0)
                            }
                        }
                    }
                    f.write(json.dumps(log_entry) + '\n')
                    f.flush()

                environment_instance.advance_generation()
                
                # Small pause to ensure Ollama doesn't trip up its queue entirely
                time.sleep(1) 
                
        logger.info("Simulation completed generation limit without emergent override.")
        
if __name__ == "__main__":
    # Test script for local execution
    logging.basicConfig(level=logging.INFO)
    runner = SyntheticaSimulationRunner("test_sandbox_001", max_generations=50)
    runner.setup_agents(num_agents_per_territory=2)
    runner.run_simulation()
