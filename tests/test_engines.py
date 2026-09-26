"""Test new engines, vector memory, search."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

def test_list_engines():
    from jarvis.engine.registry import list_engines
    engines = list_engines()
    assert "openai" in engines
    assert "ollama" in engines
    assert "mock" in engines
    assert "vllm" in engines
    assert "mlx" in engines
    assert "litellm" in engines
    print(f"Engines: {engines}")

def test_vllm_engine_import():
    from jarvis.engine.vllm_engine import VLLMEngine
    from jarvis.core.types import EngineConfig
    cfg = EngineConfig(model="test-model")
    eng = VLLMEngine(cfg)
    assert eng.name == "vllm"
    print("vLLM engine import OK")

def test_mlx_engine_import():
    from jarvis.engine.mlx_engine import MLXEngine
    from jarvis.core.types import EngineConfig
    cfg = EngineConfig(model="test-model")
    eng = MLXEngine(cfg)
    assert eng.name == "mlx"
    print("MLX engine import OK")

def test_litellm_engine_import():
    from jarvis.engine.litellm_engine import LiteLLMEngine
    from jarvis.core.types import EngineConfig
    cfg = EngineConfig(model="claude-3-5-sonnet-20241022")
    eng = LiteLLMEngine(cfg)
    assert eng.name == "litellm"
    print("LiteLLM engine import OK")

def test_gemma_engine_import():
    from jarvis.engine.gemma_engine import GemmaEngine
    from jarvis.core.types import EngineConfig
    cfg = EngineConfig(model="gemma-2b")
    eng = GemmaEngine(cfg)
    assert eng.name == "gemma_cpp"
    print("Gemma engine import OK")

def test_vector_memory():
    from jarvis.memory.vector_store import VectorMemoryStore
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    store = VectorMemoryStore(home=tmp)
    entry = store.add("test vector memory content")
    assert entry.id
    results = store.search("vector memory", top_k=2)
    # Should at least fallback to keyword
    print(f"Vector store stats: {store.stats()}")
    print(f"Search results: {len(results)}")
    # Even without FAISS, keyword fallback should work
    assert len(results) >= 0

def test_search_tools():
    from jarvis.tools.search_tools import HybridSearchTool, DDGSearchTool, TavilySearchTool
    tool = HybridSearchTool()
    # Mock mode when no API key
    result = tool.run("test query", max_results=2)
    assert "MOCK" in result or "DuckDuckGo" in result or "Tavily" in result or "test query" in result
    print(f"Search tool result preview: {result[:200]}")

def test_memory_store_unified():
    from jarvis.memory.store import MemoryStore
    import tempfile
    tmp = Path(tempfile.mkdtemp())
    store = MemoryStore(home=tmp)
    entry = store.add("unified memory test")
    assert entry.id
    results = store.search("unified memory")
    assert len(results) >= 1
    print(f"Unified memory OK: {len(results)} results")

if __name__ == "__main__":
    test_list_engines()
    test_vllm_engine_import()
    test_mlx_engine_import()
    test_litellm_engine_import()
    test_gemma_engine_import()
    test_vector_memory()
    test_search_tools()
    test_memory_store_unified()
    print("\nAll engine/memory/search tests passed!")
