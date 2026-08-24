"""
Axiom Tracker Module (Phase 3)
Tracks the evolution of agent core beliefs across generations.
Logs compressed axioms to a dedicated JSONL file per simulation run.
"""

import os
import json
import logging
from typing import Dict, Any

logger = logging.getLogger('mirofish.synthetica.axioms')

class AxiomTracker:
    @staticmethod
    def base_dir() -> str:
        """Canonical root directory for all axiom logs (per-run subdirs)."""
        return os.path.abspath(
            os.path.join(os.path.dirname(__file__), "../../uploads/simulations")
        )

    def __init__(self, simulation_id: str):
        self.simulation_id = simulation_id
        self.sim_dir = os.path.join(AxiomTracker.base_dir(), simulation_id)
        os.makedirs(self.sim_dir, exist_ok=True)
        self.log_file = os.path.join(self.sim_dir, "axioms.jsonl")
        
    def log_compression(self, record: Dict[str, Any]):
        """Logs a before/after axiom compression event."""
        if not record:
            return
            
        try:
            with open(self.log_file, 'a', encoding='utf-8') as f:
                f.write(json.dumps(record) + '\n')
        except Exception as e:
            logger.error(f"[AXIOM TRACKER] Failed to log compression: {e}")
            
    @staticmethod
    def read_axioms(simulation_id: str) -> list:
        """Reads all axiom compression events for a specific run."""
        log_file = os.path.join(AxiomTracker.base_dir(), simulation_id, "axioms.jsonl")
        if not os.path.exists(log_file):
            return []
            
        records = []
        try:
            with open(log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    if line.strip():
                        records.append(json.loads(line))
        except Exception as e:
            logger.error(f"[AXIOM TRACKER] Failed to read axioms for {simulation_id}: {e}")
            
        return records
