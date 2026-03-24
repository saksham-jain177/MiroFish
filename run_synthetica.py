"""
Project Synthetica Entry Point
Run this script to launch the Cognitive Sandbox locally on a 6GB VRAM GPU.
Make sure Ollama is running (`ollama serve`) with the `llama3` or `qwen` model pulled.
"""

import sys
import os
import logging
from datetime import datetime

# Add the backend to path to import app modules
sys.path.append(os.path.join(os.path.dirname(__file__), 'backend'))

from app.services.synthetica_simulation_runner import SyntheticaSimulationRunner

# Setup robust logging to track the emergent behavior
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(f"synthetica_run_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
    ]
)
logger = logging.getLogger('mirofish.main')

def main():
    logger.info("===============================================")
    logger.info("Initializing Project Synthetica Cognitive Sandbox")
    logger.info("Hardware Target: 6GB VRAM VRAM Constraints Active")
    logger.info("===============================================")
    
    # Generate a unique ID for this simulation run
    sim_id = f"sandbox_alpha_{datetime.now().strftime('%H%M%S')}"
    
    try:
        # Initialize Runner with 150 generations
        runner = SyntheticaSimulationRunner(simulation_id=sim_id, max_generations=150)
        
        # Setup 4 distinct agents (2 per territory) for the adversarial scarcity test
        runner.setup_agents(num_agents_per_territory=2)
        
        # Begin the sequential LLM-triage loop
        logger.info(f"Starting execution loop for simulation: {sim_id}. Awaiting emergent behavior...")
        runner.run_simulation()
        
    except Exception as e:
        logger.error(f"FATAL ERROR in Sandbox Simulation: {e}")
        logger.error("Please verify that Ollama is running locally on port 11434 and 'llama3' is pulled.")
        sys.exit(1)

if __name__ == "__main__":
    main()
