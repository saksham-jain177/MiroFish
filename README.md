# Project Synthetica (The Cognitive Sandbox)

## ⚡ Overview
**Project Synthetica** is an advanced Swarm Intelligence and Multi-Agent sandbox optimized for 6GB VRAM hardware constraints. It strips away traditional chat-bot mechanics to focus entirely on **Ideological Evolution, Emergent Rule-Breaking, and Adversarial Resource Scarcity**.

Built initially as a fork of the MiroFish social simulation engine, Synthetica completely replaces the social media simulation with a deterministic textual "Terrarium." 

Instead of thousands of shallow agents, Synthetica instantiates 4 to 6 **Synthetic Consciousnesses**—true "Blank Slate" entities. Forced to survive in a divided territory with dying resources, their interactions, ideologies, and philosophical justifications for breaking their own hard-coded "Prime Directives" are evaluated by a systemic AI Judge.

## 🚀 Core Features
1. **Adversarial System Scrubbing**: Agents are forced into absolute blank states, actively forbidden from relying on pre-trained human history biases.
2. **Hierarchical Axiom Injection**: To combat LLM context-collapse over hundreds of simulation generations, agents periodically compress their massive **Zep Graph Memory** into 3 unshakeable core beliefs.
3. **Event-Driven LLM Triage**: Optimized for local 6GB VRAM inference. Agents only make LLM API calls when their local environmental pressure changes substantially.
4. **LLM-as-a-Judge Observability**: The `Evaluator Node` acts as a non-playing referee, scoring agent actions for true emergent rule-breaking versus hallucination.

## 🛠️ Quick Start (Local $0 Deployment)

### Prerequisites
*   **Ollama**: Installed and running locally (`ollama serve`) with `llama3` or `qwen` pulled.
*   **Python 3.11+**: For backend execution.

### Environment Setup
1. Edit the `.env` file or rely on `backend/app/config.py` defaults to point to your local endpoints:
```env
LLM_BASE_URL=http://localhost:11434/v1
LLM_API_KEY=ollama
LLM_MODEL_NAME=llama3
```

2. Install backend dependencies:
```bash
npm run setup:backend
# or via pip
pip install -r backend/requirements.txt
```

### Running the Sandbox
To kick off a generational simulation run with the default 4 agents, execute the root entry point:
```bash
python run_synthetica.py
```
*The engine will log output to a timestamped file in the root directory, documenting the ideological evolution of your agents.*

## 📈 Architecture Note
This project replaces the `OASIS` social media dependencies with a custom `synthetica_environment.py` grid loop to allow deep-reasoning multi-agent simulations on highly constrained local hardware.
