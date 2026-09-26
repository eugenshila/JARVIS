"""Tool registry — now with hybrid search, FAISS memory, Tavily, DDGS, Iron Man devices, vision, wakeword."""

from __future__ import annotations

from jarvis.tools.base import BaseTool
from jarvis.tools.builtins import (
    CalendarTool,
    FileReadTool,
    FileWriteTool,
    GmailTool,
    MemorySearchTool,
    MemoryWriteTool,
    ShellTool,
    WebSearchTool,
)

# Try import enhanced tools, fallback to builtins if missing deps
try:
    from jarvis.tools.search_tools import DDGSearchTool, HybridSearchTool, TavilySearchTool
    HAS_ENHANCED_SEARCH = True
except ImportError:
    HAS_ENHANCED_SEARCH = False
    HybridSearchTool = WebSearchTool  # type: ignore
    TavilySearchTool = WebSearchTool  # type: ignore
    DDGSearchTool = WebSearchTool  # type: ignore

try:
    from jarvis.tools.device_tools import LightsTool, MusicTool, ProjectTool, SystemTool
    HAS_DEVICE_TOOLS = True
except ImportError:
    HAS_DEVICE_TOOLS = False

try:
    from jarvis.tools.vision_tool import VisionTool
    HAS_VISION = True
except ImportError:
    HAS_VISION = False

try:
    from jarvis.tools.wakeword_tool import WakeWordTool
    HAS_WAKEWORD = True
except ImportError:
    HAS_WAKEWORD = False


REGISTRY: dict[str, type[BaseTool]] = {
    "file_read": FileReadTool,
    "file_write": FileWriteTool,
    "shell": ShellTool,
    "code_exec": ShellTool,
    "web_search": HybridSearchTool if HAS_ENHANCED_SEARCH else WebSearchTool,
    "tavily_search": TavilySearchTool if HAS_ENHANCED_SEARCH else WebSearchTool,
    "ddgs_search": DDGSearchTool if HAS_ENHANCED_SEARCH else WebSearchTool,
    "memory_search": MemorySearchTool,
    "memory_write": MemoryWriteTool,
    "calendar": CalendarTool,
    "gmail": GmailTool,
}

if HAS_DEVICE_TOOLS:
    REGISTRY.update({
        "lights": LightsTool,
        "music": MusicTool,
        "system": SystemTool,
        "project": ProjectTool,
    })

if HAS_VISION:
    REGISTRY["vision"] = VisionTool

if HAS_WAKEWORD:
    REGISTRY["wakeword"] = WakeWordTool


def get_tool(name: str) -> BaseTool | None:
    cls = REGISTRY.get(name)
    return cls() if cls else None


def list_tools() -> list[str]:
    return list(REGISTRY.keys())


def get_tools(names: list[str]) -> list[BaseTool]:
    tools: list[BaseTool] = []
    for n in names:
        t = get_tool(n)
        if t:
            tools.append(t)
    return tools
