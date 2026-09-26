"""Code assistant agent."""

from jarvis.agents.react import ReActAgent
from jarvis.core.types import AgentResponse


class CodeAssistantAgent(ReActAgent):
    name = "code_assistant"
    description = "Agent with code execution, file I/O, and shell access"

    def run(self, prompt: str, context: str = "", **kwargs) -> AgentResponse:
        code_prompt = (
            f"Code task: {prompt}\n"
            f"Context/files: {context}\n\n"
            "You can read/write files and run shell commands. "
            "Provide runnable code, explain changes, and test when possible."
        )
        return super().run(code_prompt, context="", max_steps=8)
