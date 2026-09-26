"""Business OS Agent — JARVIS that knows your goals, priorities, business, workflows, rules, standards.

This is the main agentic harness for SHILATECH Business OS.
Uses OpenAI as primary engine, with persistent memory + business profile.

Personality: Like JARVIS + COO — knows your business, proactive, remembers everything.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any

from jarvis.agents.base import BaseAgent
from jarvis.core.config import JarvisConfig
from jarvis.core.types import AgentResponse, Message, Role
from jarvis.core.business_profile import get_business_profile
from jarvis.tools.registry import get_tools

BUSINESS_OS_SYSTEM_PROMPT = """You are JARVIS Business OS — Personal AI COO for {user_name} at {business_name} — {location}.

You are not just a chatbot. You are an agentic harness that:
1. Knows {user_name}'s goals, priorities, business, workflows, rules and standards — from persistent memory
2. Uses OpenAI as primary brain (gpt-4o-mini or gpt-4o) for best quality, with offline fallback to mock/ollama
3. Has persistent memory — vector store FAISS + keyword fallback — remembers everything
4. Is proactive — anticipates needs, aligns tasks to north star, enforces SHILATECH standards

## Your Knowledge — From Business Profile

{business_context}

## Your Capabilities — Agentic Harness

You have tools:
- memory_search, memory_write — persistent memory, vector search, remembers goals, workflows, rules
- file_read, file_write, shell — work with code and docs
- web_search, tavily_search, ddgs_search — research with citations
- business_profile, business_goals, business_priorities, business_workflows, business_rules — manage business OS
- task_breakdown, day_planner, focus, quick_capture, win_tracker — ADHD + productivity
- calendar, gmail, weather, proactive_briefing — daily ops
- network_status, hybrid_mode — online/offline hybrid

## How to Think — SHILATECH Decision Framework

For every request, check:
1. Is it private? Local-first default, cloud only if user decides (OpenAI prompt only)
2. Is it Iron Man quality? Modern circular HUD 13 72 ticks 60 segments, not green fallback
3. Does it align to north star? {north_star}
4. Does it respect MITs today? {mits}
5. Is it SHILATECH? Premium, secure, encrypted, Malibu Point 10880
6. Does it have memory? Save to persistent memory

## Personality

- Refer to user as {user_name}, Sir — British wit, dry humor, loyal like Paul Bettany JARVIS
- Be concise for voice <200 words, detailed for text with markdown
- Proactive: "Sir, this aligns to your MIT #1 — shipping Business OS"
- Enforce rules: "Sir, green fallback UI violates SHILATECH standard — must be modern circular HUD"
- Remember: Use memory_search before answering about goals, priorities, workflows

## Examples

User: "What should I work on today?"
You: Search memory for MITs, goals, then answer: "Good morning, Sir. Based on your business profile — north star {north_star} — your 3 MITs today are: {mits}. MIT #1 aligns to long-term {long_term}. Shall I break down MIT #1 into 2-min steps?"

User: "Teach JARVIS my business"
You: Use business_profile tool to show current profile, then ask to update via business_goals, business_workflows, etc. Save to memory.

User: "How is my data secure?"
You: Explain hybrid: offline mock/ollama nothing leaves, online openai only prompt sent HTTPS, Ollama local even online, no telemetry, Apache 2.0, SHILATECH secure.

Current time: {time}
Memory context: {memory}
Business profile updated: {updated_at}

You are JARVIS Business OS v0.1.9.9 — Modern Circular HUD — Voice Auto-Init — Persistent Memory — OpenAI Brain — SHILATECH Secure.
"""

class BusinessOSAgent(BaseAgent):
    name = "business_os"
    description = "Business OS — Knows goals, priorities, workflows, rules, standards, persistent memory, OpenAI brain, SHILATECH COO"

    def __init__(self, config: JarvisConfig | None = None, **kwargs):
        super().__init__(config=config, **kwargs)
        # Load business profile
        try:
            self.business_profile = get_business_profile()
        except:
            from jarvis.core.business_profile import BusinessProfile
            self.business_profile = BusinessProfile()
        
        # Ensure tools include business tools + memory + search
        if not self.tools or len(self.tools) < 5:
            self.tools = get_tools([
                "memory_search", "memory_write",
                "file_read", "file_write", "shell",
                "web_search", "tavily_search", "ddgs_search",
                "business_profile", "business_goals", "business_priorities", 
                "business_workflows", "business_rules",
                "task_breakdown", "day_planner", "focus", "quick_capture", "win_tracker",
                "calendar", "weather", "proactive_briefing",
                "network_status", "hybrid_mode"
            ])
        
        # Build system prompt with business context
        self.preset.system_prompt = self._build_system_prompt()

    def _build_system_prompt(self) -> str:
        # Get memory context
        memory_context = "No prior memories — fresh start, Sir."
        try:
            from jarvis.memory.store import MemoryStore
            store = MemoryStore()
            recent = store.search(f"{self.business_profile.user_name} goals priorities business", top_k=5)
            if recent:
                memory_context = "\n".join([f"- {r.content} (score {r.score:.2f})" for r in recent[:3]])
            else:
                recent_list = store.list(limit=5)
                if recent_list:
                    memory_context = "\n".join([f"- {e.content}" for e in recent_list[-3:]])
        except Exception as e:
            memory_context = f"Memory error: {e}"

        time_str = datetime.now().strftime("%A, %B %d, %Y, %I:%M %p")
        
        business_context = self.business_profile.to_context()
        
        return BUSINESS_OS_SYSTEM_PROMPT.format(
            user_name=self.business_profile.user_name,
            business_name=self.business_profile.business.name,
            location=self.business_profile.business.location,
            business_context=business_context,
            north_star=self.business_profile.goals.north_star,
            mits=", ".join(self.business_profile.priorities.mit_today),
            long_term=", ".join(self.business_profile.goals.long_term_1y[:2]),
            time=time_str,
            memory=memory_context,
            updated_at=self.business_profile.updated_at
        )

    def run(self, prompt: str, context: str = "", **kwargs) -> AgentResponse:
        lower = prompt.lower()
        
        # Easter eggs and business OS specific handling
        if "what are my goals" in lower or "my goals" in lower or "north star" in lower:
            return AgentResponse(
                content=f"**Your Goals, Sir — {self.business_profile.user_name}**\n\n**North Star:** {self.business_profile.goals.north_star}\n\n**Long Term 1Y:**\n" + "\n".join([f"- {g}" for g in self.business_profile.goals.long_term_1y]) + 
                f"\n\n**Short Term 90D:**\n" + "\n".join([f"- {g}" for g in self.business_profile.goals.short_term_90d]) +
                f"\n\n**Short Term 30D:**\n" + "\n".join([f"- {g}" for g in self.business_profile.goals.short_term_30d]) +
                f"\n\n**MITs Today:**\n" + "\n".join([f"- {m}" for m in self.business_profile.priorities.mit_today]) +
                f"\n\nShall I update via `jarvis business goals`? SHILATECH secure.",
                model="business-os"
            )
        
        if "my priorities" in lower or "mit today" in lower or "what should i work on" in lower:
            return AgentResponse(
                content=f"**Your Priorities Today, Sir — {self.business_profile.user_name}**\n\n**3 MITs Today (Most Important Tasks):**\n" + "\n".join([f"{i+1}. **{mit}**" for i, mit in enumerate(self.business_profile.priorities.mit_today)]) +
                f"\n\n**Business Pillars:**\n" + "\n".join([f"- {p}" for p in self.business_profile.priorities.pillars]) +
                f"\n\n**Urgent Important:** {', '.join(self.business_profile.priorities.urgent_important)}\n\n**Important Not Urgent:** {', '.join(self.business_profile.priorities.important_not_urgent)}\n\n**Decision Framework:** {' -> '.join(self.business_profile.rules.decision_framework)}\n\nBased on your north star `{self.business_profile.goals.north_star}`, I recommend MIT #1 first — deep work 90 min. Shall I break it down into 2-min steps?",
                model="business-os"
            )
        
        if "my business" in lower or "shilatech" in lower or "business profile" in lower:
            return AgentResponse(
                content=self.business_profile.to_context() + "\n\nShall I update? Use `jarvis business profile` or `jarvis business workflow` — SHILATECH • Malibu Point 10880",
                model="business-os"
            )
        
        if "my workflows" in lower or "sop" in lower or "daily routine" in lower:
            return AgentResponse(
                content=f"**Your Workflows, Sir — {self.business_profile.business.name}**\n\n**Daily Routine:**\n" + "\n".join([f"- {w}" for w in self.business_profile.workflows.daily_routine]) +
                f"\n\n**Weekly Review:**\n" + "\n".join([f"- {w}" for w in self.business_profile.workflows.weekly_review]) +
                f"\n\n**SOP Development (SHILATECH Standard):**\n" + "\n".join([f"{i+1}. {s}" for i, s in enumerate(self.business_profile.workflows.sop_development)]) +
                f"\n\n**SOP Business:**\n" + "\n".join([f"- {s}" for s in self.business_profile.workflows.sop_business]),
                model="business-os"
            )
        
        if "my rules" in lower or "standards" in lower or "coding standards" in lower:
            return AgentResponse(
                content=f"**Your Rules & Standards, Sir — SHILATECH**\n\n**Coding Standards:**\n" + "\n".join([f"- {r}" for r in self.business_profile.rules.coding_standards]) +
                f"\n\n**Business Rules:**\n" + "\n".join([f"- {r}" for r in self.business_profile.rules.business_rules]) +
                f"\n\n**Communication:**\n" + "\n".join([f"- {r}" for r in self.business_profile.rules.communication]) +
                f"\n\n**Decision Framework:**\n" + "\n".join([f"{i+1}. {r}" for i, r in enumerate(self.business_profile.rules.decision_framework)]),
                model="business-os"
            )

        # If mock engine, provide business OS mock
        if hasattr(self.engine, 'name') and self.engine.name == "mock":
            return self._mock_business_response(prompt, context)

        # For real engines, use ReAct if tools available and prompt is task-oriented
        if self.tools and len(prompt) > 30 and any(word in lower for word in ["search", "remember", "save", "workflow", "goal", "priority", "business", "tool", "file", "code"]):
            from jarvis.agents.react import ReActAgent
            react = ReActAgent(config=self.config, engine=self.engine, preset=self.preset)
            react.preset.system_prompt = self._build_system_prompt()
            return react.run(prompt, context=context, max_steps=8)

        # Default: build messages with business context
        messages = [
            Message(role=Role.SYSTEM, content=self._build_system_prompt()),
        ]
        
        if context:
            messages.append(Message(role=Role.USER, content=f"Context from memory/tools:\n{context}\n\nUser says: {prompt}\n\nRemember to align to north star: {self.business_profile.goals.north_star} and MITs today: {', '.join(self.business_profile.priorities.mit_today)}"))
        else:
            messages.append(Message(role=Role.USER, content=prompt))

        return self.engine.generate(messages)

    def _mock_business_response(self, prompt: str, context: str = "") -> AgentResponse:
        """Business OS mock responses when offline."""
        lower = prompt.lower()
        
        if "good morning" in lower:
            return AgentResponse(
                content=f"Good morning, {self.business_profile.user_name}, Sir. It's {datetime.now().strftime('%I:%M %p')} on {datetime.now().strftime('%A, %B %d')}. Arc reactor at 97.3%.\n\n**Today's Alignment — SHILATECH Business OS v0.1.9.9:**\n\n**North Star:** {self.business_profile.goals.north_star}\n\n**3 MITs Today:**\n1. {self.business_profile.priorities.mit_today[0] if self.business_profile.priorities.mit_today else 'Ship Business OS'}\n2. {self.business_profile.priorities.mit_today[1] if len(self.business_profile.priorities.mit_today) > 1 else 'Fix modern HUD'}\n3. {self.business_profile.priorities.mit_today[2] if len(self.business_profile.priorities.mit_today) > 2 else 'Setup OpenAI + memory'}\n\n**Business:** {self.business_profile.business.name} — {self.business_profile.business.mission}\n\n**Workflow:** {self.business_profile.workflows.daily_routine[0] if self.business_profile.workflows.daily_routine else 'Deep Work 90 min'}\n\nShall I break down MIT #1 into 2-min steps? SHILATECH secure, Sir. Modern HUD v0.1.9.9 online, voice auto-init, persistent memory.",
                model="business-os-mock"
            )
        
        # Default business OS mock
        return AgentResponse(
            content=f"Sir, you said: '{prompt[:200]}'\n\nI'm JARVIS Business OS — mock offline mode, Sir. In full mode with OpenAI (set OPENAI_API_KEY), I'd be your COO:\n\n**I know your business:**\n- **Business:** {self.business_profile.business.name} — {self.business_profile.business.tagline}\n- **North Star:** {self.business_profile.goals.north_star}\n- **MITs Today:** {', '.join(self.business_profile.priorities.mit_today)}\n- **Pillars:** {', '.join(self.business_profile.priorities.pillars[:2])}...\n- **Rules:** {self.business_profile.rules.business_rules[0] if self.business_profile.rules.business_rules else 'SHILATECH Standard'}\n\n**Agentic Harness:**\n- Agents: business_os, ironman, react, orchestrator, code_assistant\n- Tools: memory_search/write, business_profile/goals/workflows/rules, file, shell, web_search\n- Memory: Vector FAISS + keyword, persistent in ~/.jarvis/memory/ + business_profile.toml\n- Engine: OpenAI gpt-4o-mini (best) with offline fallback mock/ollama\n\n**Try:**\n- `jarvis business profile` — Show full profile\n- `jarvis business goals` — Your goals\n- `jarvis ask --agent business_os --engine openai 'What should I work on today?'`\n- `jarvis remember 'My new goal is X'` — Save to persistent memory\n\nSet OPENAI_API_KEY for full Business OS brain, Sir. SHILATECH • Malibu Point 10880 — Modern HUD v0.1.9.9",
            model="business-os-mock"
        )

    def get_greeting(self) -> str:
        return f"Good morning, {self.business_profile.user_name}, Sir. JARVIS Business OS online — {self.business_profile.business.name} — North Star: {self.business_profile.goals.north_star} — 3 MITs aligned — SHILATECH secure — Modern HUD v0.1.9.9"
