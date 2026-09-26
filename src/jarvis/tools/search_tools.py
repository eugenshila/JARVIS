"""Real web search tools — Tavily + DDGS (DuckDuckGo) with fallback."""

from __future__ import annotations

import os
from typing import Any

from jarvis.tools.base import BaseTool, ToolSpec


class TavilySearchTool(BaseTool):
    spec = ToolSpec(
        name="tavily_search",
        description="Real web search via Tavily API. Needs TAVILY_API_KEY env. Returns top results with content.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Search query"},
                "max_results": {"type": "integer", "description": "Max results (1-10)", "default": 5},
                "search_depth": {"type": "string", "enum": ["basic", "advanced"], "default": "basic"},
            },
            "required": ["query"],
        },
    )

    def run(self, query: str, max_results: int = 5, search_depth: str = "basic", **kwargs) -> str:
        api_key = os.environ.get("TAVILY_API_KEY")
        if not api_key:
            return (
                "[Tavily] TAVILY_API_KEY not set. Get key at https://tavily.com\n"
                "Fallback: Use ddgs_search or set key and pip install tavily-python.\n"
                f"Query was: {query}"
            )
        try:
            from tavily import TavilyClient  # type: ignore

            client = TavilyClient(api_key=api_key)
            resp = client.search(query, max_results=max_results, search_depth=search_depth, include_answer=True)
            # Format results
            lines = [f"Answer: {resp.get('answer','')}\n"] if resp.get("answer") else []
            for i, r in enumerate(resp.get("results", []), 1):
                lines.append(
                    f"{i}. {r.get('title','')}\n   URL: {r.get('url','')}\n   {r.get('content','')[:500]}...\n"
                )
            return "\n".join(lines) if lines else "No results"
        except ImportError:
            return "tavily-python not installed. Run: pip install -e .[tools-search]"
        except Exception as e:
            return f"Tavily search error: {e}"


class DDGSearchTool(BaseTool):
    spec = ToolSpec(
        name="ddgs_search",
        description="Free web search via DuckDuckGo (DDGS). No API key needed. Good fallback.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    )

    def run(self, query: str, max_results: int = 5, **kwargs) -> str:
        try:
            from ddgs import DDGS  # type: ignore

            results = []
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(r)

            if not results:
                return f"No DDGS results for: {query}"

            lines = []
            for i, r in enumerate(results, 1):
                lines.append(
                    f"{i}. {r.get('title','')}\n   URL: {r.get('href','')}\n   {r.get('body','')[:400]}\n"
                )
            return "\n".join(lines)
        except ImportError:
            try:
                # Try old import name
                from duckduckgo_search import DDGS  # type: ignore

                results = []
                with DDGS() as ddgs:
                    for r in ddgs.text(query, max_results=max_results):
                        results.append(r)
                lines = []
                for i, r in enumerate(results, 1):
                    lines.append(f"{i}. {r.get('title','')}\n   URL: {r.get('href','')}\n   {r.get('body','')[:400]}\n")
                return "\n".join(lines) if lines else "No results"
            except ImportError:
                return "ddgs not installed. Run: pip install -e .[tools-search]"
        except Exception as e:
            return f"DDGS search error: {e}"


class HybridSearchTool(BaseTool):
    spec = ToolSpec(
        name="web_search",
        description="Hybrid web search — tries Tavily (if API key), then DDGS, then mock. Best for agents.",
        parameters={
            "type": "object",
            "properties": {
                "query": {"type": "string"},
                "max_results": {"type": "integer", "default": 5},
            },
            "required": ["query"],
        },
    )

    def run(self, query: str, max_results: int = 5, **kwargs) -> str:
        # Try Tavily first if key set
        if os.environ.get("TAVILY_API_KEY"):
            tavily = TavilySearchTool()
            result = tavily.run(query, max_results=max_results)
            if "TAVILY_API_KEY not set" not in result and "error" not in result.lower()[:100]:
                return f"[Tavily]\n{result}"

        # Try DDGS
        ddgs = DDGSearchTool()
        result = ddgs.run(query, max_results=max_results)
        if "not installed" not in result and "error" not in result.lower()[:50]:
            return f"[DuckDuckGo]\n{result}"

        # Fallback mock
        return (
            f"[MOCK WEB SEARCH for: {query}]\n"
            "To enable real search:\n"
            "1. Free (no key): pip install -e .[tools-search] then web_search uses DuckDuckGo\n"
            "2. Better quality: set TAVILY_API_KEY (get at tavily.com) + pip install tavily-python\n"
            "For now, answer from knowledge cutoff and ask user for more context if needed."
        )
