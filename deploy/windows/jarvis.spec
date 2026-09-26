# PyInstaller spec for JARVIS — Windows EXE + MSI
# Run: pyinstaller deploy/windows/jarvis.spec

# -*- mode: python ; coding: utf-8 -*-

import sys
from pathlib import Path

block_cipher = None

# Root
root = Path(__file__).parent.parent.parent
src = root / "src"

a = Analysis(
    [str(src / "jarvis" / "cli" / "main.py")],
    pathex=[str(src)],
    binaries=[],
    datas=[
        (str(root / "configs"), "configs"),
        (str(src / "jarvis"), "jarvis"),
    ],
    hiddenimports=[
        "jarvis.core.config",
        "jarvis.core.types",
        "jarvis.engine.base",
        "jarvis.engine.openai",
        "jarvis.engine.ollama",
        "jarvis.engine.vllm_engine",
        "jarvis.engine.mlx_engine",
        "jarvis.engine.litellm_engine",
        "jarvis.engine.gemma_engine",
        "jarvis.engine.registry",
        "jarvis.agents.base",
        "jarvis.agents.simple",
        "jarvis.agents.react",
        "jarvis.agents.orchestrator",
        "jarvis.agents.morning_digest",
        "jarvis.agents.deep_research",
        "jarvis.agents.code_assistant",
        "jarvis.agents.registry",
        "jarvis.tools.base",
        "jarvis.tools.builtins",
        "jarvis.tools.search_tools",
        "jarvis.tools.registry",
        "jarvis.memory.store",
        "jarvis.memory.vector_store",
        "jarvis.skills.base",
        "jarvis.skills.registry",
        "jarvis.server.api",
        "jarvis.telemetry.monitor",
        "faiss",
        "sentence_transformers",
        "tavily",
        "ddgs",
        "rank_bm25",
        "numpy",
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="jarvis",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(root / "assets" / "icon.ico") if (root / "assets" / "icon.ico").exists() else None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="jarvis",
)
