"""Morning digest agent."""

from jarvis.agents.base import BaseAgent
from jarvis.core.types import AgentResponse, Message, Role
from jarvis.tools.registry import get_tools


class MorningDigestAgent(BaseAgent):
    name = "morning_digest"
    description = "Daily briefing from email, calendar, health, news — with TTS audio"

    def run(self, prompt: str = "Generate my morning digest", context: str = "", **kwargs) -> AgentResponse:
        # Gather tool outputs
        tool_outputs = []
        for tool in get_tools(["gmail", "calendar", "web_search", "memory_search"]):
            try:
                if tool.spec.name in ("gmail", "web_search", "memory_search"):
                    out = tool.run(query="today")
                else:
                    out = tool.run()
                tool_outputs.append(f"[{tool.spec.name}]\n{out}")
            except Exception as e:
                tool_outputs.append(f"[{tool.spec.name}] error: {e}")

        combined_context = "\n\n".join(tool_outputs)
        if context:
            combined_context += f"\n\nUser context:\n{context}"

        messages = [
            Message(role=Role.SYSTEM, content=self.preset.system_prompt),
            Message(role=Role.USER, content=f"Generate morning digest based on:\n{combined_context}\n\nUser request: {prompt}"),
        ]
        return self.engine.generate(messages)
