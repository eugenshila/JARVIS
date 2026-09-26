"""Agent registry — now with Iron Man JARVIS."""

from jarvis.agents.base import BaseAgent
from jarvis.agents.code_assistant import CodeAssistantAgent
from jarvis.agents.deep_research import DeepResearchAgent
from jarvis.agents.morning_digest import MorningDigestAgent
from jarvis.agents.orchestrator import OrchestratorAgent
from jarvis.agents.react import ReActAgent
from jarvis.agents.simple import SimpleAgent
from jarvis.core.config import JarvisConfig

try:
    from jarvis.agents.ironman import IronManAgent
    HAS_IRONMAN = True
except ImportError:
    HAS_IRONMAN = False

try:
    from jarvis.agents.adhd_coach import ADHDCoachAgent
    HAS_ADHD = True
except ImportError:
    HAS_ADHD = False

try:
    from jarvis.agents.business_os import BusinessOSAgent
    HAS_BUSINESS_OS = True
except ImportError:
    HAS_BUSINESS_OS = False

REGISTRY: dict[str, type[BaseAgent]] = {
    "simple": SimpleAgent,
    "chat-simple": SimpleAgent,
    "native_react": ReActAgent,
    "orchestrator": OrchestratorAgent,
    "morning_digest": MorningDigestAgent,
    "deep_research": DeepResearchAgent,
    "code_assistant": CodeAssistantAgent,
    "code": CodeAssistantAgent,
}

if HAS_IRONMAN:
    REGISTRY.update({
        "ironman": IronManAgent,
        "jarvis": IronManAgent,
        "iron_man": IronManAgent,
    })

if HAS_ADHD:
    REGISTRY.update({
        "adhd_coach": ADHDCoachAgent,
        "adhd": ADHDCoachAgent,
        "coach": ADHDCoachAgent,
        "focus": ADHDCoachAgent,
    })

if HAS_BUSINESS_OS:
    REGISTRY.update({
        "business_os": BusinessOSAgent,
        "business": BusinessOSAgent,
        "shilatech": BusinessOSAgent,
        "shilatech_os": BusinessOSAgent,
        "business-os": BusinessOSAgent,
        "coo": BusinessOSAgent,
    })


def get_agent(name: str, config: JarvisConfig | None = None) -> BaseAgent:
    cfg = config or JarvisConfig.load()
    cls = REGISTRY.get(name) or REGISTRY.get(cfg.preset) or SimpleAgent
    # map preset names to agent names
    preset_map = {
        "morning-digest": "morning_digest",
        "deep-research": "deep_research",
        "code-assistant": "code_assistant",
        "chat-simple": "simple",
        "scheduled-monitor": "orchestrator",
    }
    if name in preset_map:
        cls = REGISTRY[preset_map[name]]
    return cls(config=cfg)


def list_agents() -> list[str]:
    return list(REGISTRY.keys())
