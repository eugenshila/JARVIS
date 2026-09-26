"""FastAPI server — OpenAI-compatible + Jarvis extensions."""

from __future__ import annotations

import asyncio
import json
import time
import uuid
from typing import Any, AsyncIterator

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from jarvis.agents.registry import get_agent, list_agents
from jarvis.core.config import JarvisConfig
from jarvis.core.types import Message
from jarvis.engine.registry import get_engine, list_engines
from jarvis.memory.store import MemoryStore
from jarvis.skills.registry import SkillRegistry
from jarvis.telemetry.monitor import TelemetryStore


app = FastAPI(title="JARVIS API", version="0.1.10.1", description="Personal AI, On Personal Devices")

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


@app.get("/health")
def health():
    return {"status": "ok", "version": "0.1.10.1", "time": time.time()}


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


@app.get("/")
def root():
    return {
        "name": "JARVIS",
        "version": "0.1.10.1",
        "description": "Personal AI, On Personal Devices",
        "docs": "/docs",
        "health": "/health",
        "chat": "/v1/chat/completions",
        "run": "/run",
        "engines": list_engines(),
        "agents": list_agents(),
    }


def serve_cli():
    """Entry point for jarvis-server command."""
    import uvicorn
    import argparse

    parser = argparse.ArgumentParser(description="JARVIS API Server")
    parser.add_argument("--host", default="0.0.0.0")
    parser.add_argument("--port", type=int, default=8000)
    parser.add_argument("--reload", action="store_true")
    args = parser.parse_args()

    uvicorn.run("jarvis.server.api:app", host=args.host, port=args.port, reload=args.reload)
