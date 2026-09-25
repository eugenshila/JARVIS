"""Deep research agent."""

from jarvis.agents.base import BaseAgent
from jarvis.agents.react import ReActAgent
from jarvis.core.types import AgentResponse


class DeepResearchAgent(ReActAgent):
    name = "deep_research"
    description = "Multi-hop research with citations across web and local docs"

    def run(self, prompt: str, context: str = "", **kwargs) -> AgentResponse:
        enriched = (
            f"Research task: {prompt}\n"
            f"Additional context: {context}\n\n"
            "Steps:\n"
            "1. Break into sub-questions\n"
            "2. Search web and memory for each\n"
            "3. Synthesize with citations\n"
            "4. Mark uncertainties\n"
            "5. Provide final report"
        )
        return super().run(enriched, context="", max_steps=10)
