"""Engine registry — now with vLLM, MLX, LiteLLM, Gemma."""

from __future__ import annotations

from jarvis.core.config import JarvisConfig
from jarvis.core.types import EngineConfig, EngineType
from jarvis.engine.base import BaseEngine
from jarvis.engine.ollama import OllamaEngine
from jarvis.engine.openai import MockEngine, OpenAICompatibleEngine


def _try_import_vllm(cfg):
    try:
        from jarvis.engine.vllm_engine import VLLMEngine
        return VLLMEngine(cfg)
    except Exception as e:
        raise RuntimeError(f"vLLM engine unavailable: {e}")


def _try_import_mlx(cfg):
    try:
        from jarvis.engine.mlx_engine import MLXEngine
        return MLXEngine(cfg)
    except Exception as e:
        raise RuntimeError(f"MLX engine unavailable: {e}")


def _try_import_litellm(cfg):
    try:
        from jarvis.engine.litellm_engine import LiteLLMEngine
        return LiteLLMEngine(cfg)
    except Exception as e:
        raise RuntimeError(f"LiteLLM engine unavailable: {e}")


def _try_import_gemma(cfg):
    try:
        from jarvis.engine.gemma_engine import GemmaEngine
        return GemmaEngine(cfg)
    except Exception as e:
        raise RuntimeError(f"Gemma engine unavailable: {e}")


def _try_import_auto(cfg, online_engine="auto", offline_engine="mock"):
    try:
        from jarvis.engine.auto_engine import AutoEngine
        return AutoEngine(cfg, online_engine=online_engine, offline_engine=offline_engine)
    except Exception as e:
        raise RuntimeError(f"Auto engine unavailable: {e}")


def get_engine(config: JarvisConfig | EngineConfig | None = None, engine_type: str | None = None, online_engine: str = "auto", offline_engine: str = "mock") -> BaseEngine:
    if isinstance(config, JarvisConfig):
        eng_cfg = config.engine
    elif isinstance(config, EngineConfig):
        eng_cfg = config
    else:
        eng_cfg = JarvisConfig.load().engine

    if engine_type:
        try:
            eng_cfg.type = EngineType(engine_type)
        except ValueError:
            # Allow custom types not in enum yet — treat as openai-compatible
            if engine_type in ("vllm", "mlx", "litellm", "gemma_cpp", "gemma"):
                # create temp enum-like handling
                pass

    # Resolve type string
    t = eng_cfg.type.value if hasattr(eng_cfg.type, "value") else str(eng_cfg.type)
    if engine_type:
        t = engine_type

    if t == "ollama":
        return OllamaEngine(eng_cfg)
    if t == "mock":
        return MockEngine(model=eng_cfg.model)
    if t == "vllm":
        return _try_import_vllm(eng_cfg)
    if t in ("mlx", "mlx_lm"):
        return _try_import_mlx(eng_cfg)
    if t == "litellm":
        return _try_import_litellm(eng_cfg)
    if t in ("gemma_cpp", "gemma"):
        return _try_import_gemma(eng_cfg)
    if t == "auto":
        return _try_import_auto(eng_cfg, online_engine=online_engine, offline_engine=offline_engine)

    # default openai-compatible (also handles anthropic via compatible endpoint)
    return OpenAICompatibleEngine(eng_cfg)


def list_engines() -> list[str]:
    base = [e.value for e in EngineType]
    extra = ["vllm", "mlx", "litellm", "gemma_cpp"]
    # dedupe while preserving
    seen = set()
    out = []
    for x in base + extra:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
