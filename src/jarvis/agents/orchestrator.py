"""Orchestrator — multi-turn reasoning with automatic tool selection."""

from jarvis.agents.base import BaseAgent
from jarvis.agents.react import ReActAgent
from jarvis.core.types import AgentResponse


class OrchestratorAgent(ReActAgent):
    name = "orchestrator"
    description = "Multi-turn reasoning with automatic tool selection"

    def run(self, prompt: str, context: str = "", **kwargs) -> AgentResponse:
        # Orchestrator does planning then delegates
        planning_prompt = (
            f"Break down this task into steps and execute:\n{prompt}\n\n"
            f"Context: {context}\n\n"
            "Think step by step, use tools as needed, then give final answer."
        )
        return super().run(planning_prompt, context="", max_steps=8)
