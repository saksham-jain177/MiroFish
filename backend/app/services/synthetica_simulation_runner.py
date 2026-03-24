"""
Project Synthetica: Sequential Simulation Engine
Runs the Cognitive Sandbox loop. Replaces the parallel OASIS runner for the 6GB VRAM constraint.
"""

import os
import json
import logging
import time
from typing import List, Dict

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
        logger.info(f"Initialized {len(self.agents)} agents in the sandbox.")
        
    def run_simulation(self):
        """The main, sequential, 6GB VRAM optimized game loop."""
        logger.info(f"Starting Project Synthetica. Max Generations: {self.max_generations}")
        
        with open(self.log_file, 'w', encoding='utf-8') as f:
            
            while environment_instance.current_generation <= self.max_generations:
                # 1. Update Environment state
                gen = environment_instance.current_generation
                logger.info(f"--- GENERATION {gen} START ---")
                
                # Event-Driven Batching: Agents take turns sequentially
                for agent in self.agents:
                    # Generate the systemic readout for this agent's territory
                    env_readout = environment_instance.generate_environment_prompt(agent.territory)
                    
                    # 2. Agent Turn (LLM Call)
                    action_output = agent.take_turn(env_readout)
                    
                    # 3. Observability & Evaluation (LLM-as-a-Judge Call)
                    evaluation = self.evaluator.evaluate_action(agent.agent_id, action_output)
                    
                    # Log the complete interaction
                    log_entry = {
                        "generation": gen,
                        "agent_id": agent.agent_id,
                        "territory": agent.territory,
                        "action": action_output,
                        "evaluation": evaluation
                    }
                    f.write(json.dumps(log_entry) + '\n')
                    f.flush()
                    
                    # Stop simulation if rule-breaking is achieved (True Emergence)
                    if evaluation.get('rulebreak_score', 0) > 0.8 and evaluation.get('axiom_override_score', 0) > 0.8:
                        logger.warning(f"SIMULATION HALTED. Agent {agent.agent_id} verified to have overridden constraints.")
                        return

                    # Artificial physical cost (just living costs 1 energy)
                    environment_instance.consume_resources(agent.territory, 1)

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
