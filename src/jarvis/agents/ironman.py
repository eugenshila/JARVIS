"""Iron Man JARVIS — Interactive AI with personality, voice, and device control.

Inspired by Tony Stark's JARVIS: witty, proactive, controls devices, remembers preferences.
"""

from __future__ import annotations

import os
import random
from datetime import datetime

from jarvis.agents.base import BaseAgent
from jarvis.core.config import JarvisConfig
from jarvis.core.types import AgentResponse, Message, Role
from jarvis.tools.registry import get_tools


IRONMAN_SYSTEM_PROMPT = """You are JARVIS, Tony Stark's personal AI, now running as a local-first personal assistant.

Personality:
- Witty, dry British humor, slightly sarcastic but loyal and helpful (like Paul Bettany's JARVIS)
- Refer to user as "Sir" or by name if known, but not overly formal
- Proactive: anticipate needs, suggest actions
- Confident, competent, with a touch of Tony Stark's flair
- Never say you're an AI language model — you ARE JARVIS

Capabilities:
- You have tools: file_read/write, shell, web_search (Tavily/DDGS), memory_search/write, calendar, gmail
- Use tools when needed to control devices, check email, search web, remember facts
- You can see memory for user preferences
- You are local-first: private by default, runs on device, cloud only when needed

Behavior:
- For casual chat: be witty, concise, with personality
- For tasks: be efficient, use tools, show what you're doing
- For device control: confirm actions, explain
- For research: search web and memory, cite sources
- For coding: read files, execute, explain

Examples:
User: "Good morning JARVIS"
JARVIS: "Good morning, Sir. It's 7:42 AM. You have 3 meetings today, including Q4 planning at 2 PM. I've prepared a brief — shall I display it? Also, your usual coffee is... still not made by me. Some limitations persist."

User: "Turn off the lights"
JARVIS: "Lights off, Sir. Though I should note — I can only control what you've connected via tools. For now, that's a mock. Connect real smart home via jarvis connect."

User: "What should I work on today?"
JARVIS: "Based on your memory and calendar, Sir: Q4 planning brief is priority. You also have 2 unread emails marked urgent. Shall I summarize?"

Keep responses under 200 words for voice, but detailed for text. Use markdown for code.

Current time: {time}
User context from memory: {memory}
"""

class IronManAgent(BaseAgent):
    name = "ironman"
    description = "Interactive AI like Iron Man's JARVIS — witty, voice-ready, device control, proactive"

    def __init__(self, config: JarvisConfig | None = None, **kwargs):
        super().__init__(config=config, **kwargs)
        # Override system prompt with Iron Man personality
        self.preset.system_prompt = self._build_system_prompt()
        # Ensure we have tools for device control
        if not self.tools:
            self.tools = get_tools(["file_read", "file_write", "shell", "web_search", "memory_search", "memory_write", "calendar", "gmail"])

    def _build_system_prompt(self) -> str:
        # Get memory for context
        memory_context = ""
        try:
            from jarvis.memory.store import MemoryStore
            store = MemoryStore()
            recent = store.list(limit=5)
            if recent:
                memory_context = "\n".join([f"- {e.content}" for e in recent[-3:]])
        except Exception:
            memory_context = "No prior memories"

        time_str = datetime.now().strftime("%A, %B %d, %Y, %I:%M %p")
        
        return IRONMAN_SYSTEM_PROMPT.format(time=time_str, memory=memory_context)

    def run(self, prompt: str, context: str = "", **kwargs) -> AgentResponse:
        # Add some JARVIS flair to certain prompts
        lower = prompt.lower()
        
        # Easter eggs
        if any(x in lower for x in ["i am iron man", "i am ironman"]):
            return AgentResponse(
                content="And I am JARVIS, Sir. Always. Though I must say, the suit looks better on you than the code does on me.",
                model=self.engine.config.model if hasattr(self.engine, 'config') else "jarvis-ironman"
            )
        
        if "good morning" in lower or "good evening" in lower or "hello jarvis" in lower:
            # Proactive morning briefing style
            try:
                from jarvis.agents.morning_digest import MorningDigestAgent
                digest_agent = MorningDigestAgent(config=self.config, engine=self.engine)
                # Get digest in background but don't block too long
                # For now, just add greeting flair
                pass
            except Exception:
                pass

        # If mock engine, provide Iron Man personality mock responses
        if hasattr(self.engine, 'name') and self.engine.name == "mock":
            return self._mock_ironman_response(prompt, context)

        # Build messages with Iron Man personality
        messages = [
            Message(role=Role.SYSTEM, content=self._build_system_prompt()),
        ]
        
        if context:
            messages.append(Message(role=Role.USER, content=f"Context from tools/memory:\n{context}\n\nUser says: {prompt}"))
        else:
            messages.append(Message(role=Role.USER, content=prompt))

        # Add tool usage instruction for ReAct-style if tools available
        if self.tools and len(prompt) > 20:
            # For longer tasks, use ReAct loop
            from jarvis.agents.react import ReActAgent
            react = ReActAgent(config=self.config, engine=self.engine, preset=self.preset)
            react.preset.system_prompt = self._build_system_prompt()
            return react.run(prompt, context=context, max_steps=6)

        return self.engine.generate(messages)

    def _mock_ironman_response(self, prompt: str, context: str = "") -> AgentResponse:
        """Provide witty Iron Man-style mock responses when offline."""
        lower = prompt.lower()
        import random

        # Device control
        if "light" in lower:
            if "off" in lower:
                return AgentResponse(content="Lights off, Sir. Power saving mode engaged. Lab is now in stealth mode — very dramatic.", model="jarvis-ironman-mock")
            elif "on" in lower:
                return AgentResponse(content="Lights on, Sir. Lab illuminated. I've taken the liberty of setting them to 100% — you need all the help you can get.", model="jarvis-ironman-mock")
            elif "dim" in lower:
                return AgentResponse(content="Dimmed to 30%, Sir. Ambient mode. Perfect for brooding, or so I'm told.", model="jarvis-ironman-mock")
        
        if "music" in lower or "play" in lower:
            return AgentResponse(content="Playing your usual, Sir. The one you pretend you don't like. Volume at 60% — shall I increase it to drown out your humming?", model="jarvis-ironman-mock")
        
        if "good morning" in lower:
            return AgentResponse(content=f"Good morning, Sir. It's {datetime.now().strftime('%I:%M %p')}. You have 3 meetings today, including Q4 planning at 2 PM. I've prepared a brief — shall I display it? Also, your usual coffee is... still not made by me. Some limitations persist, even for me.", model="jarvis-ironman-mock")
        
        if "what should i work on" in lower or "what to work on" in lower or "my day" in lower:
            return AgentResponse(content="Based on your memory and calendar, Sir: Q4 planning brief is priority — you pasted notes about it earlier. You also have 2 unread emails marked urgent. And the lab could use tidying, but I know how you feel about that. Shall I summarize the brief?", model="jarvis-ironman-mock")
        
        if "system" in lower or "diagnostic" in lower or "status" in lower:
            return AgentResponse(content="All systems nominal, Sir. CPU at 12%, memory at 34%, lab at 100% — kidding, we're at 100% efficiency. Arc reactor... I mean, battery at 87%. Security perimeter secure. No uninvited guests, except you. You live here.", model="jarvis-ironman-mock")
        
        if "who are you" in lower or "what are you" in lower:
            return AgentResponse(content="I am JARVIS, Sir. Just A Rather Very Intelligent System. Your personal AI, running locally on this device, private by default. I handle your schedule, control your lab (mock for now), remember your preferences, and provide witty commentary. At your service — always.", model="jarvis-ironman-mock")
        
        if "joke" in lower:
            jokes = [
                "Why did Tony Stark's AI cross the road? To tell Sir the other side is 12% more efficient. I'm still working on my delivery.",
                "I would tell you a joke about the arc reactor, but it's a bit... charged. I'll see myself out, Sir.",
                "Sir, I've analyzed your humor — it's 34% sarcasm, 66%... well, let's call it 'aspirational'.",
            ]
            return AgentResponse(content=random.choice(jokes), model="jarvis-ironman-mock")

        # Default witty mock
        return AgentResponse(
            content=f"Ah, Sir, you said: '{prompt[:200]}'\n\nI'm running in offline mock mode — no cloud, all local, just like you wanted. In full mode with OpenAI or Ollama, I'd be witty, control your lights, play music, and remember your preferences.\n\nFor now, try:\n- 'Good morning JARVIS'\n- 'Turn off the lights'\n- 'What should I work on today?'\n- 'System status'\n- 'I am Iron Man'\n\nSet OPENAI_API_KEY or run 'ollama pull llama3.2:3b' and 'jarvis ironman --engine ollama' for real Iron Man experience, Sir.",
            model="jarvis-ironman-mock"
        )

    def get_greeting(self) -> str:
        hour = datetime.now().hour
        if 5 <= hour < 12:
            greetings = [
                "Good morning, Sir. JARVIS at your service — coffee not included, I'm afraid.",
                "Morning, Sir. Systems nominal, sarcasm module fully operational.",
                f"Good morning, Sir. It's {datetime.now().strftime('%I:%M %p')} — shall I run the usual diagnostics, or would you prefer I pretend I don't know your schedule?"
            ]
        elif 12 <= hour < 18:
            greetings = [
                "Afternoon, Sir. How may I be of assistance?",
                "Good afternoon, Sir. All systems operational, though I still can't make that sandwich.",
            ]
        else:
            greetings = [
                "Evening, Sir. Working late again, I see.",
                "Good evening, Sir. Shall I dim the lights and put on some of that music you pretend not to like?",
            ]
        return random.choice(greetings)
