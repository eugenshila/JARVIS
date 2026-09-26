"""Simple single-turn agent."""

from jarvis.agents.base import BaseAgent
from jarvis.core.types import AgentResponse


class SimpleAgent(BaseAgent):
    name = "simple"
    description = "Single-turn chat, no tools"

    def run(self, prompt: str, context: str = "", **kwargs) -> AgentResponse:
        messages = self._build_messages(prompt, context)
        return self.engine.generate(messages)
