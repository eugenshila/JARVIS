"""ReAct agent with tool loop."""

from __future__ import annotations

import json
import re

from jarvis.agents.base import BaseAgent
from jarvis.core.types import AgentResponse, Message, Role
from jarvis.tools.registry import get_tool


class ReActAgent(BaseAgent):
    name = "native_react"
    description = "ReAct (Thought-Action-Observation) loop agent"

    def run(self, prompt: str, context: str = "", max_steps: int = 6, **kwargs) -> AgentResponse:
        messages = self._build_messages(prompt, context)
        # Add ReAct instruction
        react_instruction = (
            "\n\nYou can use tools. When you need to use a tool, respond in this format:\n"
            "Thought: <your reasoning>\n"
            "Action: <tool_name> {\"arg\": \"value\"}\n"
            "After receiving Observation, continue.\n"
            "When done, give final answer without Action.\n"
            f"Available tools: {', '.join([t.spec.name for t in self.tools])}"
        )
        messages[0].content += react_instruction

        for step in range(max_steps):
            resp = self.engine.generate(messages)
            content = resp.content

            # Try to parse Action
            action_match = re.search(r"Action:\s*(\w+)\s*(\{.*\})?", content, re.DOTALL)
            if not action_match:
                # No tool call, return
                return resp

            tool_name = action_match.group(1)
            args_str = action_match.group(2) or "{}"
            try:
                args = json.loads(args_str)
            except Exception:
                args = {}

            tool = get_tool(tool_name)
            if not tool:
                observation = f"Error: tool {tool_name} not found"
            else:
                try:
                    observation = tool.run(**args)
                except Exception as e:
                    observation = f"Tool error: {e}"

            messages.append(Message(role=Role.ASSISTANT, content=content))
            messages.append(Message(role=Role.USER, content=f"Observation: {observation}\n\nContinue reasoning. If task complete, give final answer."))

        # Final call without tool parsing
        return self.engine.generate(messages)
