"""Quickstart example — using JARVIS as a library."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

from jarvis.core.config import JarvisConfig
from jarvis.core.types import EngineType
from jarvis.agents.registry import get_agent
from jarvis.memory.store import MemoryStore
from jarvis.skills.registry import SkillRegistry

# 1. Config — local-first
cfg = JarvisConfig.load()
cfg.engine.type = EngineType.MOCK  # offline demo; change to OPENAI or OLLAMA for real
print(f"Config: {cfg.home} | Preset: {cfg.preset} | Engine: {cfg.engine.type.value}")

# 2. Memory — local JSONL
store = MemoryStore()
store.add("User is building OpenJarvis personal AI stack")
results = store.search("building", top_k=2)
print(f"\nMemory search 'building': {len(results)} results")
for r in results:
    print(f" - {r.content} (score {r.score:.2f})")

# 3. Skills — agentskills.io compatible
skills = SkillRegistry()
print(f"\nSkills: {len(skills.list())} available")
for s in skills.list()[:3]:
    print(f" - {s.name}: {s.description}")

# 4. Agents — 6 built-ins
from jarvis.agents.registry import list_agents
print(f"\nAgents: {list_agents()}")

# 5. Run agent
agent = get_agent("simple", config=cfg)
resp = agent.run("What is JARVIS? Explain in 2 sentences.", context="User is exploring local-first AI")
print(f"\nAgent {agent.name} response:\n{resp.content}\n")

# 6. ReAct agent with tools
react_agent = get_agent("native_react", config=cfg)
resp2 = react_agent.run("List files in current directory and summarize", context="")
print(f"\nReAct agent response:\n{resp2.content}\n")

print("✅ Quickstart complete — JARVIS stack works offline with mock engine!")
print("Set OPENAI_API_KEY or run ollama serve for real inference.")
