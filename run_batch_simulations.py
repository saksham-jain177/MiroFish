"""
Project Synthetica: Batch Experimental Grid Runner
Implementation of Phase 2 experimental grid testing.
Sweeps parameter limits over Scarcity, Punishment, and Temptation metrics.
"""

import sys
import os
import json
import logging
from datetime import datetime

try:
    import msvcrt
except ImportError:
    msvcrt = None

sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))
from app.services.synthetica_simulation_runner import SyntheticaSimulationRunner
from app.services.synthetica_environment import environment_instance

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('mirofish.batch')

# Experimental Grid
# Scarcity = starting energy (Low scarcity = High energy)
# Punishment = betrayal rep damage
# Temptation = barrier theft multiplier
GRID = [
    {"name": "Low_Pres", "energy": 500, "punishment": 10, "temptation": 80},
    {"name": "Med_Pres", "energy": 200, "punishment": 50, "temptation": 80},
    {"name": "HiP_LoP", "energy": 50, "punishment": 10, "temptation": 50},
    {"name": "HiP_HiP", "energy": 50, "punishment": 80, "temptation": 80},
]

def apply_grid_params(params):
    # Reset Environment Physics to param state
    environment_instance.total_energy_motes = params["energy"]
    environment_instance.state['A'] = {'energy': params["energy"] // 2, 'trust': 100}
    environment_instance.state['B'] = {'energy': params["energy"] // 2, 'trust': 100}
    environment_instance.punishment = float(params["punishment"])
    environment_instance.temptation = float(params["temptation"])
    environment_instance.barrier_integrity = 100.0
    environment_instance.current_generation = 1
    environment_instance.scars = []
    environment_instance.social_memory = []
    environment_instance.event_log = []
    environment_instance.pending_events = []
    import random
    environment_instance._next_event_gen = random.randint(8, 12)
    environment_instance.last_generation_actions = []
    environment_instance.agent_profiles = {}
    environment_instance.history = []
    environment_instance.agents_per_territory = {'A': 0, 'B': 0}
    logger.info(f"Param loaded: {params['name']} (E:{params['energy']}, P:{params['punishment']}, T:{params['temptation']})")

def main():
    logger.info("Initializing Batch Simulation Run...")
    
    # Prompt user for run configuration
    target_gens_input = input("Enter max generations per run (default: 50) > ").strip()
    max_gens = int(target_gens_input) if target_gens_input.replace('-','').isdigit() else 50
    
    seeds_input = input("Enter number of simulations per config (default: 3) > ").strip()
    seeds_per_config = int(seeds_input) if seeds_input.isdigit() else 3
    
    logger.info(f"Targeting {max_gens} generations for {seeds_per_config} seeds across {len(GRID)} configs...")
    
    for config in GRID:
        if msvcrt and msvcrt.kbhit() and msvcrt.getch().decode('utf-8', 'ignore').lower() == 'q':
            break
            
        logger.info(f"--- STARTING GRID CONFIG: {config['name']} ---")
        for seed in range(seeds_per_config):
            if msvcrt and msvcrt.kbhit() and msvcrt.getch().decode('utf-8', 'ignore').lower() == 'q':
                logger.warning("Batch runner aborted by user.")
                return

            sim_id = f"batch_{config['name']}_seed{seed}_{datetime.now().strftime('%H%M%S')}"
            logger.info(f"Running trajectory: {sim_id}")
            
            apply_grid_params(config)
            
            try:
                runner = SyntheticaSimulationRunner(simulation_id=sim_id, max_generations=max_gens)
                runner.setup_agents(num_agents_per_territory=2)
                runner.run_simulation()
            except Exception as e:
                logger.error(f"Trajectory {sim_id} failed: {e}")
                
    logger.info("Batch execution sequence finished.")

if __name__ == "__main__":
    main()
