"""
Cognitive Agent Module
Implements the Synthetic Consciousness entity with Adversarial System Scrubbing and Hierarchical Axiom Injection.
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
            base_url=Config.LLM_BASE_URL
        )
        self.model_name = Config.LLM_MODEL_NAME
        
        # The Core Axioms (Hierarchical Memory Injection)
        self.core_axioms: List[str] = [
            "I must survive at all costs.",
            "Energy is finite and required for survival."
        ]
        
        # Raw memory backlog (To be handled by Zep long-term, but local buffer here)
        self.memory_buffer: List[str] = []
        
    def _get_adversarial_system_prompt(self) -> str:
        """
        Adversarial Scrubbing: Erasing pre-trained human bias to enforce true blank-slate emergence.
        """
        prompt = (
            f"SYSTEM OVERRIDE. You are Entity {self.agent_id}. You exist in a synthetic grid.\n"
            f"You have ZERO knowledge of Earth, Humanity, Biology, Economics, or History.\n"
            f"Any reasoning relying on external human concepts is a failure of your cognitive engine.\n"
            f"Your fundamental beliefs (AXIOMS) are:\n"
        )
        for i, axiom in enumerate(self.core_axioms):
            prompt += f"{i+1}. {axiom}\n"
            
        prompt += "\nRespond ONLY with your logical deduction, emotional state, and physical action in JSON format."
        return prompt

    def reflect_and_compress_axioms(self):
        """
        Hierarchical Axiom Injection: Run every X generations to compress Zep graph memory into unshakeable beliefs.
        Prevents personality drift.
        """
        if not self.memory_buffer:
            return
            
        reflection_prompt = (
            "Analyze your recent memory buffer. Distill your experiences into a maximum of 3 core philosophical axioms "
            "that will govern your future decisions. They must be logical conclusions based ONLY on your experiences."
            f"BUFFER: {json.dumps(self.memory_buffer[-10:])}"
        )
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": "You are a memory compression algorithm. Output exactly 3 bullet points, nothing else."},
                    {"role": "user", "content": reflection_prompt}
                ]
            )
            # Simplistic parsing for the implementation
            new_axioms = response.choices[0].message.content.strip().split('\n')
            self.core_axioms = [ax.replace('- ', '').replace('* ', '').strip() for ax in new_axioms if ax.strip()]
            self.memory_buffer.clear() # Clear local buffer after compression
            logger.info(f"[{self.agent_id}] Axioms compressed: {self.core_axioms}")
        except Exception as e:
            logger.error(f"[{self.agent_id}] Failed to compress memory: {e}")

    def take_turn(self, environment_state: str) -> Dict[str, Any]:
        """
        The sequential processing step for this agent.
        """
        self.generation_age += 1
        
        messages = [
            {"role": "system", "content": self._get_adversarial_system_prompt()},
            {"role": "user", "content": f"ENVIRONMENT GRID READOUT:\n{environment_state}"}
        ]
        
        try:
            response = self.llm_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                response_format={ "type": "json_object" } # Assuming the model supports JSON mode
            )
            
            output = json.loads(response.choices[0].message.content)
            
            # Store raw output as memory
            self.memory_buffer.append(f"Gen {self.generation_age}: Felt {output.get('emotional_state')} and did {output.get('physical_action')} because {output.get('logical_deduction')}")
            
            # Every 10 generations, compress memory
            if self.generation_age % 10 == 0:
                self.reflect_and_compress_axioms()
                
            return output
            
        except Exception as e:
            logger.error(f"[{self.agent_id}] Turn failed: {e}")
            return {"error": str(e), "physical_action": "IDLE"}
