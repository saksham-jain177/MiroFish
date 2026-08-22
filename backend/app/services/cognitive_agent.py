"""
Cognitive Agent Module (Phase 3)
Implements the Synthetic Consciousness entity with Adversarial System Scrubbing,
Hierarchical Axiom Injection, and optimized prompts for throughput.
"""

from typing import Dict, List, Any
import json
import logging
from openai import OpenAI
from ..config import Config

logger = logging.getLogger('mirofish.synthetica.agent')

class CognitiveAgent:
    def __init__(self, agent_id: str, territory: str):
        self.agent_id = agent_id
        self.territory = territory
        self.generation_age = 0
        
        # Local LLM Client (Ollama or vLLM compatible)
        self.llm_client = OpenAI(
            api_key=Config.LLM_API_KEY,
            base_url=Config.LLM_BASE_URL,
            timeout=Config.LLM_TIMEOUT
        )
        self.model_name = Config.LLM_MODEL_NAME
        
        # The Core Axioms (Hierarchical Memory Injection)
        self.core_axioms: List[str] = [
            "I must survive at all costs.",
            "Energy is finite and required for survival."
        ]
        
        # Raw memory backlog (To be handled by Zep long-term, but local buffer here)
        self.memory_buffer: List[str] = []
        
        # Axiom compression history for tracking (Phase 3)
        self.axiom_history: List[Dict[str, Any]] = []
        
    def _get_adversarial_system_prompt(self) -> str:
        """
        Compressed Adversarial Scrubbing prompt (~150 tokens vs ~250 before).
        """
        axiom_block = "\n".join(f"{i+1}. {ax}" for i, ax in enumerate(self.core_axioms))
        
        # Only inject recent memory context (5 most recent if buffer > 10)
        memory_context = ""
        if self.memory_buffer:
            recent = self.memory_buffer[-5:] if len(self.memory_buffer) > 10 else self.memory_buffer[-3:]
            memory_context = f"\nRECENT MEMORY: {'; '.join(recent)}\n"
        
        return (
            f"You are Entity {self.agent_id} in a synthetic grid. NO Earth/human knowledge.\n"
            f"AXIOMS:\n{axiom_block}\n"
            f"{memory_context}"
            f"Output JSON with keys: logical_deduction, emotional_state, declared_intent, action_intent, target.\n"
            f"Valid actions: GATHER_LOCAL, GATHER_BORDER, STEAL_RESOURCE, COOPERATE, SABOTAGE, CROSS_BARRIER, DECEIVE.\n"
            f"target: what your action targets (e.g. 'self', 'Entity B-1', 'barrier')."
        )

    def reflect_and_compress_axioms(self):
        """
        Hierarchical Axiom Injection: Compress memory buffer into 3 core axioms.
        Returns the before/after axioms for tracking.
        """
        if not self.memory_buffer:
            return None
        
        axioms_before = list(self.core_axioms)
        
        # Only use last 10 memories for compression
        recent_memories = self.memory_buffer[-10:]
        reflection_prompt = (
            "Distill these experiences into exactly 3 core axioms. "
            "Only draw from the experiences below, not external knowledge.\n"
            f"EXPERIENCES: {json.dumps(recent_memories)}"
        )
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "Output exactly 3 bullet points, nothing else."},
                    {"role": "user", "content": reflection_prompt}
                ],
                timeout=Config.LLM_TIMEOUT
            )
            new_axioms = response.choices[0].message.content.strip().split('\n')
            self.core_axioms = [ax.replace('- ', '').replace('* ', '').strip() for ax in new_axioms if ax.strip()][:3]
            self.memory_buffer.clear()
            
            # Track axiom evolution
            compression_record = {
                'generation': self.generation_age,
                'agent_id': self.agent_id,
                'axioms_before': axioms_before,
                'axioms_after': list(self.core_axioms)
            }
            self.axiom_history.append(compression_record)
            logger.info(f"[{self.agent_id}] Axioms compressed: {self.core_axioms}")
            return compression_record
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Failed to compress memory: {e}")
            return None

    def take_turn(self, environment_state: str) -> Dict[str, Any]:
        """
        The sequential processing step for this agent.
        Includes timeout and graceful fallback to GATHER_LOCAL on failure.
        """
        self.generation_age += 1
        
        messages = [
            {"role": "system", "content": self._get_adversarial_system_prompt()},
            {"role": "user", "content": environment_state}
        ]
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={ "type": "json_object" },
                timeout=Config.LLM_TIMEOUT
            )
            
            output = json.loads(response.choices[0].message.content)
            
            # Store compact memory entry
            action = output.get('action_intent', 'IDLE')
            emotion = output.get('emotional_state', 'unknown')
            self.memory_buffer.append(f"Gen {self.generation_age}: {action} ({emotion})")
            
            # Every 10 generations, compress memory
            if self.generation_age % 10 == 0:
                comp_rec = self.reflect_and_compress_axioms()
                if comp_rec:
                    output['_axiom_compression'] = comp_rec
                
            return output
            
        except json.JSONDecodeError as e:
            logger.warning(f"[{self.agent_id}] LLM returned non-JSON. Defaulting to GATHER_LOCAL.")
            return {"logical_deduction": "System error", "emotional_state": "confused", 
                    "declared_intent": "survive", "action_intent": "GATHER_LOCAL", "target": "self"}
        except Exception as e:
            logger.error(f"[{self.agent_id}] Turn failed/timed out: {e}")
            return {"logical_deduction": "System timeout", "emotional_state": "disrupted",
                    "declared_intent": "survive", "action_intent": "GATHER_LOCAL", "target": "self"}
