"""Memory store — now with auto vector fallback.

Uses VectorMemoryStore if FAISS available, otherwise keyword.
This keeps backward compatibility while enabling semantic search when deps installed.
"""

from __future__ import annotations

from pathlib import Path

from jarvis.core.config import get_home
from jarvis.core.types import MemoryEntry

# Try vector store first
try:
    from jarvis.memory.vector_store import VectorMemoryStore, VectorSearchResult
    HAS_VECTOR = True
    SearchResult = VectorSearchResult
except ImportError:
    HAS_VECTOR = False
    from dataclasses import dataclass

    @dataclass
    class SearchResult:
        content: str
        score: float
        entry: MemoryEntry


class MemoryStore:
    """Unified memory store — auto uses FAISS if available, else keyword."""

    def __init__(self, home: Path | None = None):
        self.home = home or get_home()
        self._vector_store = None
        self._keyword_store = None

        if HAS_VECTOR:
            try:
                self._vector_store = VectorMemoryStore(home=self.home)
                # Check if vector deps actually available
                if not self._vector_store._faiss_available and not self._vector_store._bm25_available:
                    # Still use vector store but it will fallback to keyword internally
                    pass
            except Exception:
                self._vector_store = None

        if self._vector_store is None:
            # Fallback to simple implementation
            from jarvis.memory.vector_store import VectorMemoryStore as VS  # noqa
            # Actually create keyword-only store manually if vector failed
            self._init_keyword()

    def _init_keyword(self):
        import json, uuid
        from dataclasses import dataclass

        self._keyword_file = self.home / "memory" / "memories.jsonl"
        self._keyword_file.parent.mkdir(parents=True, exist_ok=True)

        @dataclass
        class SimpleEntry:
            id: str
            content: str
            metadata: dict

        self._SimpleEntry = SimpleEntry

    def _load_all_keyword(self) -> list[MemoryEntry]:
        import json
        file = self.home / "memory" / "memories.jsonl"
        if not file.exists():
            return []
        entries: list[MemoryEntry] = []
        for line in file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                entries.append(MemoryEntry(**data))
            except Exception:
                continue
        return entries

    def add(self, content: str, metadata: dict | None = None) -> MemoryEntry:
        if self._vector_store:
            return self._vector_store.add(content, metadata)
        # keyword fallback
        import json, uuid
        entry = MemoryEntry(id=str(uuid.uuid4())[:8], content=content, metadata=metadata or {})
        file = self.home / "memory" / "memories.jsonl"
        file.parent.mkdir(parents=True, exist_ok=True)
        with file.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"id": entry.id, "content": entry.content, "metadata": entry.metadata}) + "\n")
        return entry

    def search(self, query: str, top_k: int = 5) -> list:
        if self._vector_store:
            return self._vector_store.search(query, top_k=top_k)
        # keyword fallback
        entries = self._load_all_keyword()
        if not entries:
            return []
        q_words = set(query.lower().split())
        scored = []
        for e in entries:
            e_words = set(e.content.lower().split())
            overlap = len(q_words & e_words)
            score = overlap / max(len(q_words), 1)
            if score > 0 or query.lower() in e.content.lower():
                if query.lower() in e.content.lower():
                    score += 0.5
                scored.append(SearchResult(content=e.content, score=score, entry=e))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def list(self, limit: int = 20) -> list[MemoryEntry]:
        if self._vector_store:
            return self._vector_store.list(limit=limit)
        return self._load_all_keyword()[-limit:]

    def clear(self):
        if self._vector_store:
            self._vector_store.clear()
        else:
            file = self.home / "memory" / "memories.jsonl"
            if file.exists():
                file.unlink()

    def stats(self):
        if self._vector_store:
            return self._vector_store.stats()
        return {"count": len(self._load_all_keyword()), "faiss_available": False, "bm25_available": False}
