"""Basic tests for JARVIS build."""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent
SRC = ROOT / "src"
sys.path.insert(0, str(SRC))

def test_imports():
    import jarvis
    assert jarvis.__version__

def test_config():
    from jarvis.core.config import JarvisConfig, PRESETS
    cfg = JarvisConfig.load()
    assert cfg.engine.model
    assert len(PRESETS) >= 5

def test_engines():
    from jarvis.core.config import JarvisConfig
    from jarvis.core.types import EngineType, Message, Role
    from jarvis.engine.registry import get_engine

    cfg = JarvisConfig.load()
    cfg.engine.type = EngineType.MOCK
    eng = get_engine(cfg)
    resp = eng.generate([Message(role=Role.USER, content="hello")])
    assert len(resp.content) > 0
    assert "MOCK" in resp.content

def test_agents():
    from jarvis.core.config import JarvisConfig
    from jarvis.core.types import EngineType
    from jarvis.agents.registry import get_agent, list_agents

    assert len(list_agents()) >= 6
    cfg = JarvisConfig.load()
    cfg.engine.type = EngineType.MOCK
    agent = get_agent("simple", config=cfg)
    resp = agent.run("test prompt", context="test context")
    assert resp.content

def test_memory():
    from jarvis.memory.store import MemoryStore
    import tempfile
    from pathlib import Path
    tmp = Path(tempfile.mkdtemp())
    store = MemoryStore(home=tmp)
    entry = store.add("test memory content")
    assert entry.id
    results = store.search("test memory")
    assert len(results) >= 1

def test_skills():
    from jarvis.skills.registry import SkillRegistry
    reg = SkillRegistry()
    skills = reg.list()
    assert len(skills) >= 5
    assert reg.get("meeting-brief") is not None

def test_tools():
    from jarvis.tools.registry import list_tools, get_tool
    assert len(list_tools()) >= 5
    tool = get_tool("file_read")
    assert tool is not None

def test_client():
    from client import generate
    import os
    os.environ["JARVIS_MOCK"] = "1"
    result = generate("hello", "context")
    assert len(result) > 0
    del os.environ["JARVIS_MOCK"]

if __name__ == "__main__":
    test_imports()
    test_config()
    test_engines()
    test_agents()
    test_memory()
    test_skills()
    test_tools()
    test_client()
    print("All tests passed!")
