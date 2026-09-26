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

try:
    from jarvis.tools.adhd_tools import (
        BrainDumpTool,
        DayPlannerTool,
        DistractionLogTool,
        EnergyCheckTool,
        FocusTool,
        OverwhelmTool,
        QuickCaptureTool,
        TaskBreakdownTool,
        TimeEstimatorTool,
        WinTrackerTool,
    )
    HAS_ADHD_TOOLS = True
except ImportError:
    HAS_ADHD_TOOLS = False

try:
    from jarvis.tools.adhd_advanced import (
        DopamineMenuTool,
        HabitStackTool,
        IfThenTool,
        ShutdownRitualTool,
        TransitionTool,
        WeeklyReviewTool,
    )
    HAS_ADHD_ADVANCED = True
except ImportError:
    HAS_ADHD_ADVANCED = False

try:
    from jarvis.tools.startup_tools import AutostartTool, GreetingTool, TaskAlignmentTool
    HAS_STARTUP = True
except ImportError:
    HAS_STARTUP = False


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

if HAS_ADHD_TOOLS:
    REGISTRY.update({
        "brain_dump": BrainDumpTool,
        "task_breakdown": TaskBreakdownTool,
        "day_planner": DayPlannerTool,
        "focus": FocusTool,
        "quick_capture": QuickCaptureTool,
        "energy_check": EnergyCheckTool,
        "win_tracker": WinTrackerTool,
        "overwhelm": OverwhelmTool,
        "time_estimator": TimeEstimatorTool,
        "distraction_log": DistractionLogTool,
    })

if HAS_ADHD_ADVANCED:
    REGISTRY.update({
        "habit_stack": HabitStackTool,
        "transition": TransitionTool,
        "if_then": IfThenTool,
        "weekly_review": WeeklyReviewTool,
        "dopamine_menu": DopamineMenuTool,
        "shutdown_ritual": ShutdownRitualTool,
    })

if HAS_STARTUP:
    REGISTRY.update({
        "autostart": AutostartTool,
        "greeting": GreetingTool,
        "task_alignment": TaskAlignmentTool,
    })

try:
    from jarvis.tools.calendar_tools import CalendarToolEnhanced, TaskLearningTool, WeatherTool
    HAS_CALENDAR_ENHANCED = True
except ImportError:
    HAS_CALENDAR_ENHANCED = False

if HAS_CALENDAR_ENHANCED:
    REGISTRY.update({
        "calendar_enhanced": CalendarToolEnhanced,
        "weather": WeatherTool,
        "task_learning": TaskLearningTool,
    })

try:
    from jarvis.tools.email_tools import EmailEnhancedTool, ProactiveBriefingTool
    HAS_EMAIL_ENHANCED = True
except ImportError:
    HAS_EMAIL_ENHANCED = False

if HAS_EMAIL_ENHANCED:
    REGISTRY.update({
        "email_enhanced": EmailEnhancedTool,
        "proactive_briefing": ProactiveBriefingTool,
    })

try:
    from jarvis.tools.focus_enhanced import (
        WebsiteBlockerTool,
        FocusSoundsTool,
        HyperfocusGuardTool,
        FocusSessionEnhancedTool,
    )
    HAS_FOCUS_ENHANCED = True
except ImportError:
    HAS_FOCUS_ENHANCED = False

if HAS_FOCUS_ENHANCED:
    REGISTRY.update({
        "website_blocker": WebsiteBlockerTool,
        "focus_sounds": FocusSoundsTool,
        "hyperfocus_guard": HyperfocusGuardTool,
        "focus_enhanced": FocusSessionEnhancedTool,
    })

try:
    from jarvis.tools.face_tool import FaceRecognitionTool, VoiceCloningTool
    HAS_FACE = True
except ImportError:
    HAS_FACE = False

if HAS_FACE:
    REGISTRY.update({
        "face_recognition": FaceRecognitionTool,
        "voice_cloning": VoiceCloningTool,
    })

try:
    from jarvis.connectors.google import GoogleConnector
    HAS_GOOGLE = True
except ImportError:
    HAS_GOOGLE = False

try:
    from jarvis.tools.network_tools import NetworkStatusTool, HybridModeTool
    HAS_NETWORK = True
except ImportError:
    HAS_NETWORK = False

if HAS_NETWORK:
    REGISTRY.update({
        "network_status": NetworkStatusTool,
        "online_status": NetworkStatusTool,
        "hybrid_mode": HybridModeTool,
    })

try:
    from jarvis.tools.business_tools import (
        BusinessProfileTool,
        BusinessGoalsTool,
        BusinessPrioritiesTool,
        BusinessWorkflowsTool,
        BusinessRulesTool,
        BusinessMemoryTool,
    )
    HAS_BUSINESS = True
except ImportError:
    HAS_BUSINESS = False

if HAS_BUSINESS:
    REGISTRY.update({
        "business_profile": BusinessProfileTool,
        "business_goals": BusinessGoalsTool,
        "business_priorities": BusinessPrioritiesTool,
        "business_workflows": BusinessWorkflowsTool,
        "business_rules": BusinessRulesTool,
        "business_memory": BusinessMemoryTool,
    })


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
