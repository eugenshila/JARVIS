"""ReAct agent with a tool loop and real failure recovery.

The loop used to treat every tool failure identically: the observation became
"Error: ..." and the model either gave up or retried the same broken call until
it ran out of steps. Now each failure is classified by
:mod:`jarvis.agents.recovery` into retry / skip / replan / abort, and the loop
acts on that decision with a bounded retry budget.
"""

from __future__ import annotations

import json
import re

from jarvis.agents.base import BaseAgent
from jarvis.agents.recovery import Decision, RetryBudget, classify
from jarvis.core.types import AgentResponse, Message, Role
from jarvis.tools.registry import get_tool, tool_record

_FAILURE_MARKERS = re.compile(r"^\s*(error|tool error|failed|exception)\b[:\s]", re.IGNORECASE)


def _looks_like_failure(observation: str) -> bool:
    """Most of our tools report trouble by returning a string, not by raising."""
    return bool(_FAILURE_MARKERS.match(str(observation or "")))


class ReActAgent(BaseAgent):
    name = "native_react"
    description = "ReAct (Thought-Action-Observation) loop agent with failure recovery"

    def run(self, prompt: str, context: str = "", max_steps: int = 6, **kwargs) -> AgentResponse:
        messages = self._build_messages(prompt, context)
        react_instruction = (
            "\n\nYou can use tools. When you need to use a tool, respond in this format:\n"
            "Thought: <your reasoning>\n"
            'Action: <tool_name> {"arg": "value"}\n'
            "After receiving Observation, continue.\n"
            "When done, give final answer without Action.\n"
            "If an Observation says a step was retried and still failed, change "
            "your approach instead of repeating the same Action.\n"
            f"Available tools: {', '.join([t.spec.name for t in self.tools])}"
        )
        messages[0].content += react_instruction

        budget = RetryBudget(total=max(2, max_steps), per_step=2)
        notes: list[str] = []
        step = 0

        while step < max_steps:
            step += 1
            resp = self.engine.generate(messages)
            content = resp.content

            action_match = re.search(r"Action:\s*(\w+)\s*(\{.*\})?", content, re.DOTALL)
            if not action_match:
                return resp  # no tool call — this is the answer

            tool_name = action_match.group(1)
            args_str = action_match.group(2) or "{}"
            try:
                args = json.loads(args_str)
            except Exception:
                args = {}

            step_key = f"{tool_name}:{args_str[:120]}"
            observation, failed = self._invoke(tool_name, args)

            if failed:
                attempt = budget.attempts(step_key) + 1
                recovery = classify(
                    error=observation,
                    step=f"{tool_name}({args_str})",
                    goal=prompt,
                    attempt=attempt,
                    engine=self.engine,
                )
                if recovery.user_message:
                    notes.append(recovery.user_message)

                if recovery.decision is Decision.ABORT:
                    return AgentResponse(
                        content=(
                            f"{recovery.user_message or 'I cannot continue with that, sir.'}\n\n"
                            f"Reason: {recovery.reason}"
                        ),
                        model=getattr(resp, "model", ""),
                        finished=True,
                    )

                if recovery.decision is Decision.RETRY and budget.allows(step_key):
                    budget.spend(step_key)
                    retry_observation, retry_failed = self._invoke(tool_name, args)
                    if not retry_failed:
                        observation = retry_observation
                        failed = False
                    else:
                        observation = (
                            f"{retry_observation}\n[recovery] Retried once, still failing. "
                            f"{recovery.fix_suggestion or 'Try a different tool or arguments.'}"
                        )
                elif recovery.decision is Decision.REPLAN:
                    observation = (
                        f"{observation}\n[recovery] That approach will not work: "
                        f"{recovery.reason} "
                        f"{recovery.fix_suggestion or 'Choose a different tool or arguments.'}"
                    )
                elif recovery.decision is Decision.SKIP:
                    observation = (
                        f"{observation}\n[recovery] Non-critical: {recovery.reason} "
                        "Continue without this step."
                    )
                else:  # RETRY, but the budget is spent
                    observation = (
                        f"{observation}\n[recovery] Retry budget exhausted for this step. "
                        "Change approach or finish with what you have."
                    )

            messages.append(Message(role=Role.ASSISTANT, content=content))
            messages.append(
                Message(
                    role=Role.USER,
                    content=(
                        f"Observation: {observation}\n\n"
                        "Continue reasoning. If task complete, give final answer."
                    ),
                )
            )

        final = self.engine.generate(messages)
        if notes:
            final.content = f"{final.content}\n\n(Along the way: {'; '.join(notes[-3:])})"
        return final

    # -- one tool call, normalised -------------------------------------------

    def _invoke(self, tool_name: str, args: dict) -> tuple[str, bool]:
        """Returns ``(observation, failed)``. Never raises."""
        tool = get_tool(tool_name)
        if tool is None:
            record = tool_record(tool_name)
            if record is not None and not record.valid:
                return f"Error: tool {tool_name} failed to load: {record.error}", True
            if record is not None:
                return f"Error: tool {tool_name} is disabled", True
            return f"Error: unknown tool {tool_name}", True
        try:
            observation = tool.run(**args)
        except TypeError as exc:
            return f"Error: {tool_name} called with wrong arguments: {exc}", True
        except Exception as exc:
            return f"Tool error: {exc}", True
        return observation, _looks_like_failure(observation)
