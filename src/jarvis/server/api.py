"""FastAPI server — OpenAI-compatible + Jarvis extensions."""

from __future__ import annotations

import asyncio
import json
import os
import sys
import time
import urllib.error
import urllib.request
import uuid
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Any

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from jarvis import __version__
from jarvis.agents.registry import get_agent, list_agents
from jarvis.core.config import JarvisConfig, get_home
from jarvis.core.types import Message
from jarvis.engine.registry import get_engine, list_engines
from jarvis.memory.store import MemoryStore
from jarvis.skills.registry import SkillRegistry
from jarvis.telemetry.monitor import TelemetryStore
from jarvis.voice import available_voice, read_voice_status

#: Upload ceiling. Large enough for a video, small enough that a stray loop
#: cannot fill the user's disk.
MAX_UPLOAD_BYTES = 500 * 1024 * 1024

app = FastAPI(title="JARVIS API", version=__version__, description="Personal AI, On Personal Devices")

# Authentication. Loopback callers are exempt by default so the CLI, the
# desktop shell and existing local workflows are unchanged; a request from off
# the machine needs the token from `jarvis token`. See jarvis/server/auth.py.
from jarvis.server import auth as api_auth  # noqa: E402

api_auth.install(app)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ChatRequest(BaseModel):
    model: str | None = None
    messages: list[dict[str, Any]]
    agent: str | None = "simple"
    stream: bool = False
    temperature: float | None = None


class AgentRunRequest(BaseModel):
    prompt: str
    context: str = ""
    agent: str = "simple"
    engine: str | None = None
    stream: bool = False


class MemoryAddRequest(BaseModel):
    content: str
    metadata: dict[str, Any] | None = None


HUD_MODEL = "qwen2.5:3b"


class HudMessage(BaseModel):
    role: str
    content: str


class HudChatRequest(BaseModel):
    messages: list[HudMessage]


class HudAdhdStateRequest(BaseModel):
    energy: int = 5
    focus: int = 5
    stress: int = 5
    sleep_hours: float = 7
    mood: str = ""
    medication: str = "unknown"
    notes: str = ""


class HudAppLaunchRequest(BaseModel):
    app: str
    confirm: bool = False


class HudAppRegisterRequest(BaseModel):
    name: str
    path: str
    allow_args: bool = False


class HudCareerModeRequest(BaseModel):
    mode: str


class HudIncomeOpportunityRequest(BaseModel):
    action: str = "add"  # add | status
    title: str = ""
    url: str = ""
    source: str = "manual"
    type: str = "gig"
    est_value: str = ""
    notes: str = ""
    id: str = ""
    set_status: str = ""


class HudIncomeWatchlistRequest(BaseModel):
    action: str = "add"  # add | remove
    symbol: str
    note: str = ""


class HudIncomePortfolioRequest(BaseModel):
    symbol: str
    quantity: float = 0
    cost_basis: float = 0
    current_price: float | None = None


class HudIncomeProjectLogRequest(BaseModel):
    id: str
    hours: float = 0
    revenue: float = 0
    expense: float = 0
    note: str = ""


def _ollama_request(path: str, payload: dict[str, Any] | None = None) -> dict[str, Any]:
    host = os.environ.get("OLLAMA_HOST", "http://127.0.0.1:11434").rstrip("/")
    request = urllib.request.Request(
        f"{host}{path}",
        data=json.dumps(payload).encode("utf-8") if payload is not None else None,
        headers={"Content-Type": "application/json"},
    )
    with urllib.request.urlopen(request, timeout=120 if payload is not None else 3) as response:
        return json.load(response)


@app.get("/hud/status")
async def hud_status():
    try:
        result = await asyncio.to_thread(_ollama_request, "/api/tags")
        installed = any(model.get("name") == HUD_MODEL or model.get("model") == HUD_MODEL
                        for model in result.get("models", []))
        return {"ollama": "ready" if installed else "model_missing", "model": HUD_MODEL}
    except (OSError, ValueError) as exc:
        return {"ollama": "unavailable", "model": HUD_MODEL, "detail": str(exc)}


@app.get("/hud/voice-status")
async def hud_voice_status():
    status = await asyncio.to_thread(read_voice_status)
    status["voice_name"] = available_voice()
    return status


def _safe_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        pass
    return default


def _connection_summary() -> dict[str, Any]:
    home = get_home()
    google_status: dict[str, Any] = {"credentials": False, "authenticated": False}
    try:
        from jarvis.connectors.google import GoogleConnector

        google = GoogleConnector()
        google_status = {
            "credentials": google.is_configured(),
            "authenticated": google.is_authenticated(),
            "credentials_path": str(google.creds_path),
            "token_path": str(google.token_path),
        }
    except Exception as exc:
        google_status = {"credentials": False, "authenticated": False, "error": str(exc)}
    return {
        "google": google_status,
        "microsoft": {"implemented": False, "instructions": "Use Microsoft Graph OAuth guidance from `jarvis connect microsoft --instructions`."},
        "local": {
            "calendar_path": str(home / "calendar.json"),
            "calendar_exists": (home / "calendar.json").exists(),
            "email_path": str(home / "emails.json"),
            "email_exists": (home / "emails.json").exists(),
        },
        "policy": "Read-only by default; sending mail or changing events requires explicit confirmation.",
    }


def _adhd_latest() -> dict[str, Any]:
    logs = _safe_json(get_home() / "adhd" / "state_log.json", [])
    if isinstance(logs, list) and logs:
        latest = logs[-1]
        return {"configured": True, "latest": latest}
    return {"configured": False, "latest": None}


def _career_summary() -> dict[str, Any]:
    try:
        from jarvis.connectors.jautomatic import JAutomaticConnector
        from jarvis.tools.career_tools import _load_career_config

        connector = JAutomaticConnector()
        stats = connector.stats()
        return {"mode": _load_career_config().get("mode", "seeking"), "stats": stats}
    except Exception as exc:
        return {"mode": "seeking", "stats": {}, "error": str(exc)}


INCOME_DISCLAIMER = (
    "Informational only — not financial advice. JARVIS is not a licensed financial "
    "advisor. No trades are placed automatically; nothing here connects to a brokerage."
)


def _income_summary() -> dict[str, Any]:
    try:
        from jarvis.tools.income_tools import _load_list

        opportunities = _load_list("opportunities.json")
        watchlist = _load_list("watchlist.json")
        portfolio = _load_list("portfolio.json")
        projects = _load_list("projects.json")
        active_opps = [o for o in opportunities if o.get("status") in {"discovered", "saved"}]
        active_projects = [p for p in projects if p.get("status") == "active"]
        return {
            "disclaimer": INCOME_DISCLAIMER,
            "opportunities": {"count": len(opportunities), "awaiting_review": len(active_opps), "items": opportunities[-10:]},
            "watchlist": {"count": len(watchlist), "items": watchlist},
            "portfolio": {"count": len(portfolio), "items": portfolio},
            "projects": {"count": len(projects), "active": len(active_projects), "items": projects},
        }
    except Exception as exc:
        return {"disclaimer": INCOME_DISCLAIMER, "error": str(exc)}


@app.get("/hud/preflight")
async def hud_preflight():
    """Pre-MSI readiness checks surfaced in the HUD."""
    try:
        from jarvis.tools.app_launcher import AppLauncherTool

        apps = AppLauncherTool().load_apps()
    except Exception:
        apps = []
    return {
        "adhd": _adhd_latest(),
        "connections": _connection_summary(),
        "career": _career_summary(),
        "income": _income_summary(),
        "apps": {"count": len(apps), "names": [a.get("name") for a in apps], "items": apps},
    }


@app.post("/hud/adhd-state")
async def hud_adhd_state(req: HudAdhdStateRequest):
    try:
        from jarvis.tools.adhd_state import ADHDStateTool

        result = await asyncio.to_thread(
            ADHDStateTool().run,
            action="assess",
            energy=req.energy,
            focus=req.focus,
            stress=req.stress,
            sleep_hours=req.sleep_hours,
            mood=req.mood,
            medication=req.medication,
            notes=req.notes,
        )
        return {"content": result, "adhd": _adhd_latest()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/hud/connections")
async def hud_connections():
    return _connection_summary()


@app.post("/hud/connections/google/setup")
async def hud_google_setup():
    try:
        from jarvis.tools.connection_tools import ConnectionStatusTool

        result = await asyncio.to_thread(ConnectionStatusTool().run, action="google_setup")
        return {"content": result, "connections": _connection_summary()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/hud/apps")
async def hud_apps():
    try:
        from jarvis.tools.app_launcher import AppLauncherTool

        apps = await asyncio.to_thread(AppLauncherTool().load_apps)
        return {"count": len(apps), "items": apps}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/hud/apps")
async def hud_add_app(req: HudAppRegisterRequest):
    try:
        from jarvis.tools.app_launcher import AppLauncherTool

        result = await asyncio.to_thread(AppLauncherTool().run, action="add", name=req.name, path=req.path, allow_args=req.allow_args)
        apps = AppLauncherTool().load_apps()
        return {"content": result, "apps": apps}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/hud/apps/launch")
async def hud_launch_app(req: HudAppLaunchRequest):
    try:
        from jarvis.tools.app_launcher import AppLauncherTool

        result = await asyncio.to_thread(AppLauncherTool().run, action="launch", app=req.app, confirm=req.confirm)
        return {"content": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get("/hud/career")
async def hud_career():
    return _career_summary()


@app.get("/hud/career/today")
async def hud_career_today():
    try:
        from jarvis.tools.career_tools import CareerTool

        result = await asyncio.to_thread(CareerTool().run, action="today")
        return {"content": result, "career": _career_summary()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/hud/career/mode")
async def hud_career_mode(req: HudCareerModeRequest):
    try:
        from jarvis.tools.career_tools import CareerTool

        result = await asyncio.to_thread(CareerTool().run, action="mode", mode=req.mode)
        return {"content": result, "career": _career_summary()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/hud/career/open")
async def hud_career_open(req: HudAppLaunchRequest):
    try:
        from jarvis.tools.career_tools import CareerTool

        result = await asyncio.to_thread(CareerTool().run, action="open", confirm=req.confirm)
        return {"content": result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


# --------------------------------------------------------------------------- #
# Income OS — research / planning / tracking only. GET routes are pure reads
# of local JSON under ~/.jarvis/income/. POST routes only write to those same
# local files — none of this ever calls a brokerage/exchange or places a trade.
# --------------------------------------------------------------------------- #

@app.get("/hud/income")
async def hud_income():
    return _income_summary()


@app.get("/hud/income/opportunities")
async def hud_income_opportunities():
    from jarvis.tools.income_tools import _load_list

    return {"disclaimer": INCOME_DISCLAIMER, "items": _load_list("opportunities.json")}


@app.get("/hud/income/watchlist")
async def hud_income_watchlist():
    from jarvis.tools.income_tools import _load_list

    return {"disclaimer": INCOME_DISCLAIMER, "items": _load_list("watchlist.json")}


@app.get("/hud/income/portfolio")
async def hud_income_portfolio():
    from jarvis.tools.income_tools import _load_list

    return {"disclaimer": INCOME_DISCLAIMER, "items": _load_list("portfolio.json")}


@app.get("/hud/income/projects")
async def hud_income_projects():
    from jarvis.tools.income_tools import _load_list

    return {"disclaimer": INCOME_DISCLAIMER, "items": _load_list("projects.json")}


@app.get("/hud/income/briefing")
async def hud_income_briefing():
    try:
        from jarvis.tools.income_tools import MoneyBriefingTool

        result = await asyncio.to_thread(MoneyBriefingTool().run, action="today")
        return {"content": result, "income": _income_summary()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/hud/income/opportunities")
async def hud_income_opportunities_write(req: HudIncomeOpportunityRequest):
    try:
        from jarvis.tools.income_tools import IncomeOpportunitiesTool

        tool = IncomeOpportunitiesTool()
        if req.action == "status":
            result = await asyncio.to_thread(tool.run, action="status", id=req.id, set_status=req.set_status)
        else:
            result = await asyncio.to_thread(
                tool.run, action="add", title=req.title, url=req.url, source=req.source,
                type=req.type, est_value=req.est_value, notes=req.notes,
            )
        return {"content": result, "income": _income_summary()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/hud/income/watchlist")
async def hud_income_watchlist_write(req: HudIncomeWatchlistRequest):
    try:
        from jarvis.tools.income_tools import InvestmentResearchTool

        tool = InvestmentResearchTool()
        action = "watchlist_remove" if req.action == "remove" else "watchlist_add"
        result = await asyncio.to_thread(tool.run, action=action, symbol=req.symbol, note=req.note)
        return {"content": result, "income": _income_summary()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/hud/income/portfolio")
async def hud_income_portfolio_write(req: HudIncomePortfolioRequest):
    try:
        from jarvis.tools.income_tools import InvestmentResearchTool

        result = await asyncio.to_thread(
            InvestmentResearchTool().run, action="portfolio_set", symbol=req.symbol,
            quantity=req.quantity, cost_basis=req.cost_basis, current_price=req.current_price,
        )
        return {"content": result, "income": _income_summary()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/hud/income/projects/log")
async def hud_income_projects_log(req: HudIncomeProjectLogRequest):
    try:
        from jarvis.tools.income_tools import IncomeProjectsTool

        result = await asyncio.to_thread(
            IncomeProjectsTool().run, action="log", id=req.id, hours=req.hours,
            revenue=req.revenue, expense=req.expense, note=req.note,
        )
        return {"content": result, "income": _income_summary()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.post("/hud/chat")
async def hud_chat(req: HudChatRequest):
    history = [m for m in req.messages if m.role in ("user", "assistant") and m.content.strip()][-20:]
    if not history or history[-1].role != "user":
        raise HTTPException(status_code=400, detail="A user message is required.")
    system = ("You are JARVIS, Eugene's concise, capable personal assistant. Speak naturally "
              "with a little dry wit. You run locally through Ollama. Do not claim to have "
              "read email, calendar, files, weather, devices, or live system data unless "
              "that data was supplied in this conversation. You cannot perform actions "
              "from this chat yet. Say what needs a connected tool when asked to act.")
    payload = {"model": HUD_MODEL, "stream": False,
               "messages": [{"role": "system", "content": system}] +
                           [{"role": m.role, "content": m.content[:8000]} for m in history]}
    try:
        result = await asyncio.to_thread(_ollama_request, "/api/chat", payload)
    except urllib.error.HTTPError as exc:
        detail = "Install the model with: ollama pull qwen2.5:3b" if exc.code == 404 else f"Ollama returned HTTP {exc.code}."
        raise HTTPException(status_code=503, detail=detail) from exc
    except (OSError, ValueError) as exc:
        raise HTTPException(status_code=503, detail=f"Ollama is unavailable: {exc}") from exc
    return {"content": result.get("message", {}).get("content", ""), "model": HUD_MODEL}


# ── Classic assistant (ported from KKshitiz/J.A.R.V.I.S) ─────────────────────
#
# Served under /hud/* so the existing Vite proxy and the MSI's static bundle
# reach it without new configuration. One router instance per process keeps
# follow-up questions ("which city, sir?") coherent for the open HUD window.

_classic_router = None


def _classic():
    global _classic_router
    if _classic_router is None:
        from jarvis.classic.router import ClassicRouter

        _classic_router = ClassicRouter()
    return _classic_router


class ClassicCommandRequest(BaseModel):
    command: str


@app.get("/hud/classic/commands")
def hud_classic_commands():
    from jarvis.classic.router import COMMANDS

    return {"commands": COMMANDS}


@app.post("/hud/classic/command")
async def hud_classic_command(req: ClassicCommandRequest):
    """Run one classic command. Never blocks the loop: the skills do network
    and subprocess work, so they run on a thread."""
    if not req.command.strip():
        raise HTTPException(status_code=400, detail="A command is required.")
    try:
        reply = await asyncio.to_thread(_classic().handle, req.command)
    except Exception as exc:  # a broken skill must not 500 the HUD
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return reply.to_dict()


@app.get("/health")
def health():
    return {"status": "ok", "version": __version__, "time": time.time()}


# ── Confirmation gate ─────────────────────────────────────────────────────────
#
# These endpoints are the *interface* half of jarvis/core/confirm.py. The model
# can never reach them: it only produces tool arguments, and no tool argument
# resolves a token. A human clicking CONFIRM in the HUD is what calls
# /confirm/{token}/approve.


class ConfirmAction(BaseModel):
    token: str


@app.get("/confirm")
def confirm_pending():
    from jarvis.core import confirm as confirm_gate

    return {"pending": confirm_gate.pending()}


@app.post("/confirm/{token}/approve")
def confirm_approve(token: str):
    from jarvis.core import confirm as confirm_gate

    try:
        result = confirm_gate.resolve(token)
    except confirm_gate.ConfirmationError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Action failed: {exc}") from exc
    return {"status": "done", "result": result}


@app.post("/confirm/{token}/cancel")
def confirm_cancel(token: str):
    from jarvis.core import confirm as confirm_gate

    if not confirm_gate.cancel(token):
        raise HTTPException(status_code=404, detail="No such pending confirmation.")
    return {"status": "cancelled"}


# ── Undo ──────────────────────────────────────────────────────────────────────


@app.get("/undo")
def undo_history():
    from jarvis.core import undo as undo_stack

    return {"history": undo_stack.history(), "depth": undo_stack.depth()}


@app.post("/undo")
def undo_last():
    from jarvis.core import undo as undo_stack

    return {"result": undo_stack.undo_last(), "depth": undo_stack.depth()}


# ── Engine ladder + tool discovery diagnostics ────────────────────────────────


@app.get("/ladder")
def ladder_status():
    from jarvis.engine.ladder import status as ladder_state

    return ladder_state()


@app.get("/tools")
def tools_listing():
    from jarvis.tools.registry import list_tool_details

    return {"tools": list_tool_details()}


# ── Plan / execute / background tasks ─────────────────────────────────────────


class GoalRequest(BaseModel):
    goal: str
    tools: list[str] | None = None
    priority: str = "normal"


@app.post("/plan")
def build_plan(req: GoalRequest):
    """Plan a goal WITHOUT running it, so the user can see it first."""
    from jarvis.agents.planner import plan as make_plan

    return make_plan(req.goal, tools=req.tools).to_dict()


@app.post("/tasks")
def submit_task(req: GoalRequest):
    """Plan and run a goal on the background queue. Returns immediately."""
    from jarvis.agents.executor import submit_goal
    from jarvis.core.task_queue import Priority

    priority = {
        "high": Priority.HIGH,
        "normal": Priority.NORMAL,
        "low": Priority.LOW,
    }.get(req.priority.strip().lower(), Priority.NORMAL)
    task = submit_goal(req.goal, tools=req.tools, priority=priority)
    return task.to_dict()


@app.get("/tasks")
def list_tasks():
    from jarvis.core.task_queue import get_queue

    return get_queue().snapshot()


@app.get("/tasks/{task_id}")
def get_task(task_id: str):
    from jarvis.core.task_queue import get_queue

    task = get_queue().get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="No such task.")
    return task.to_dict()


@app.delete("/tasks/{task_id}")
def cancel_task(task_id: str):
    from jarvis.core.task_queue import get_queue

    if not get_queue().cancel(task_id):
        raise HTTPException(status_code=404, detail="No such task, or it already finished.")
    return {"status": "cancelling", "task_id": task_id}


@app.get("/capture")
def capture_status():
    from jarvis.core import capture as capture_core

    return capture_core.status()


@app.post("/capture/screen")
def capture_screen_now(analyse: bool = False, question: str = "Describe what is on the screen."):
    """Take one screen grab. Refused unless the user has granted consent."""
    from jarvis.core import capture as capture_core

    try:
        shot = capture_core.capture_screen()
    except capture_core.CaptureError as exc:
        raise HTTPException(status_code=403, detail=str(exc)) from exc
    payload = {
        "path": str(shot.path),
        "width": shot.width,
        "height": shot.height,
        "bytes": shot.bytes_written,
    }
    if analyse:
        from jarvis.tools.capture_tools import _describe

        payload["description"] = _describe(str(shot.path), question)
    return payload


# Uploads need python-multipart. It is a declared dependency, but a minimal
# or partially-installed environment must lose the upload route, not the
# whole API.
try:
    import importlib.util as _importlib_util

    _UPLOADS_OK = any(
        _importlib_util.find_spec(name) is not None
        for name in ("python_multipart", "multipart")
    )
except (ImportError, ValueError):  # pragma: no cover - depends on the install
    _UPLOADS_OK = False


def _register_upload_route() -> None:
    @app.post("/upload")
    async def upload_file(file: UploadFile = File(...)):  # noqa: B008
        """Accept a file and report what can be done with it.

        Lands in the first genuinely writable directory of the fallback chain in
        jarvis/core/paths.py — 'write next to the executable' fails on a real
        install where Program Files is read-only.
        """
        from jarvis.core.paths import uploads_dir
        from jarvis.tools.file_processor import detect_type, supported_actions

        safe_name = Path(str(file.filename or "upload")).name
        destination = uploads_dir() / safe_name
        size = 0
        try:
            with destination.open("wb") as handle:
                while chunk := await file.read(1024 * 1024):
                    size += len(chunk)
                    if size > MAX_UPLOAD_BYTES:
                        handle.close()
                        destination.unlink(missing_ok=True)
                        raise HTTPException(
                            status_code=413,
                            detail=f"File exceeds the {MAX_UPLOAD_BYTES // (1024 * 1024)} MB limit.",
                        )
                    handle.write(chunk)
        except HTTPException:
            raise
        except OSError as exc:
            raise HTTPException(status_code=500, detail=f"Could not save upload: {exc}") from exc

        return {
            "path": str(destination),
            "name": safe_name,
            "bytes": size,
            "type": detect_type(destination),
            "actions": supported_actions(str(destination)),
        }



if _UPLOADS_OK:
    _register_upload_route()


@app.get("/monitors")
def list_monitors():
    from jarvis.tools.monitor_tools import due_topics, load_monitors

    return {"monitors": load_monitors(), "due": due_topics()}


@app.get("/profile")
def get_profile_facts():
    from jarvis.memory.profile import get_profile

    profile = get_profile()
    return {"profile": profile.all(), "size": profile.size()}


@app.get("/v1/models")
def list_models():
    cfg = JarvisConfig.load()
    return {
        "object": "list",
        "data": [
            {"id": cfg.engine.model, "object": "model", "created": int(time.time()), "owned_by": "jarvis"},
            {"id": "mock-1", "object": "model", "owned_by": "jarvis"},
            {"id": "ollama-llama3", "object": "model", "owned_by": "ollama"},
        ],
    }


@app.get("/agents")
def agents():
    return {"agents": list_agents()}


@app.get("/engines")
def engines():
    return {"engines": list_engines()}


@app.get("/skills")
def skills():
    reg = SkillRegistry()
    return {"skills": [s.to_dict() for s in reg.list()]}


@app.get("/memory")
def list_memory(limit: int = 20):
    store = MemoryStore()
    entries = store.list(limit=limit)
    return {"memories": [{"id": e.id, "content": e.content, "metadata": e.metadata} for e in entries]}


@app.post("/memory")
def add_memory(req: MemoryAddRequest):
    store = MemoryStore()
    entry = store.add(req.content, metadata=req.metadata)
    return {"id": entry.id, "content": entry.content}


@app.get("/telemetry")
def telemetry(limit: int = 50):
    store = TelemetryStore()
    recs = store.recent(limit=limit)
    return {"records": [r.__dict__ for r in recs]}


@app.post("/v1/chat/completions")
async def chat_completions(req: ChatRequest):
    cfg = JarvisConfig.load()
    if req.model:
        cfg.engine.model = req.model

    # Build messages
    msgs: list[Message] = []
    for m in req.messages:
        role = m.get("role", "user")
        content = m.get("content", "")
        msgs.append(Message(role=role, content=content))

    engine = get_engine(cfg, engine_type=req.agent if req.agent in list_engines() else None)

    if req.stream:

        async def stream_gen() -> AsyncIterator[str]:
            # Simple streaming mock — yields chunks
            try:
                response = await engine.agenerate(msgs)
                # chunk it
                words = response.content.split(" ")
                for i, w in enumerate(words):
                    chunk = {
                        "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                        "object": "chat.completion.chunk",
                        "created": int(time.time()),
                        "model": cfg.engine.model,
                        "choices": [{"index": 0, "delta": {"content": w + " "}, "finish_reason": None}],
                    }
                    yield f"data: {json.dumps(chunk)}\n\n"
                    await asyncio.sleep(0.03)
                final = {
                    "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                    "object": "chat.completion.chunk",
                    "created": int(time.time()),
                    "model": cfg.engine.model,
                    "choices": [{"index": 0, "delta": {}, "finish_reason": "stop"}],
                }
                yield f"data: {json.dumps(final)}\n\n"
                yield "data: [DONE]\n\n"
            except Exception as e:
                err = {"error": str(e)}
                yield f"data: {json.dumps(err)}\n\n"

        return StreamingResponse(stream_gen(), media_type="text/event-stream")

    else:
        try:
            response = await engine.agenerate(msgs)
            return {
                "id": f"chatcmpl-{uuid.uuid4().hex[:8]}",
                "object": "chat.completion",
                "created": int(time.time()),
                "model": cfg.engine.model,
                "choices": [{"index": 0, "message": {"role": "assistant", "content": response.content}, "finish_reason": "stop"}],
                "usage": response.usage or {"prompt_tokens": 0, "completion_tokens": 0, "total_tokens": 0},
            }
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))


@app.post("/run")
async def run_agent(req: AgentRunRequest):
    cfg = JarvisConfig.load()
    if req.engine:
        # override engine type
        cfg.engine.type = cfg.engine.type.__class__(req.engine) if hasattr(cfg.engine.type, "__class__") else cfg.engine.type
        # simpler: set env style
        try:
            from jarvis.core.types import EngineType

            cfg.engine.type = EngineType(req.engine)
        except Exception:
            pass

    agent = get_agent(req.agent, config=cfg)

    if req.stream:

        async def stream_gen():
            try:
                resp = await agent.arun(req.prompt, context=req.context)
                for word in resp.content.split(" "):
                    yield f"data: {json.dumps({'content': word + ' '})}\n\n"
                    await asyncio.sleep(0.02)
                yield "data: [DONE]\n\n"
            except Exception as e:
                yield f"data: {json.dumps({'error': str(e)})}\n\n"

        return StreamingResponse(stream_gen(), media_type="text/event-stream")

    try:
        resp = await agent.arun(req.prompt, context=req.context)
        return {"content": resp.content, "model": resp.model, "usage": resp.usage}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/memory/stats")
def memory_stats():
    store = MemoryStore()
    try:
        stats = store.stats()
    except Exception:
        stats = {"count": 0}
    return stats


@app.get("/api")
def root():
    return {
        "name": "JARVIS",
        "version": __version__,
        "description": "Personal AI, On Personal Devices",
        "docs": "/docs",
        "health": "/health",
        "chat": "/v1/chat/completions",
        "run": "/run",
        "engines": list_engines(),
        "agents": list_agents(),
    }


# The packaged MSI serves its built HUD from the same local API process.
_bundle_root = Path(getattr(sys, "_MEIPASS", Path(__file__).resolve().parents[3]))
_frontend = _bundle_root / "frontend" / "dist"
if _frontend.joinpath("index.html").exists():
    app.mount("/", StaticFiles(directory=_frontend, html=True), name="hud")


def serve_cli():
    """Entry point for jarvis-server command."""
    import argparse

    import uvicorn

    parser = argparse.ArgumentParser(description="JARVIS API Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run("jarvis.server.api:app", host=args.host, port=args.port, reload=args.reload)
