"""Vector memory — FAISS + sentence-transformers + BM25 fallback.

Implements local-first semantic search. Falls back gracefully if deps missing.
"""

from __future__ import annotations

import json
import uuid
from pathlib import Path
from dataclasses import dataclass
from typing import Any

from jarvis.core.config import get_home
from jarvis.core.types import MemoryEntry


@dataclass
class VectorSearchResult:
    content: str
    score: float
    entry: MemoryEntry
    source: str = "vector"  # vector, bm25, keyword


class VectorMemoryStore:
    """Enhanced memory with FAISS vector search + BM25 + keyword fallback."""

    def __init__(self, home: Path | None = None, embedding_model: str = "all-MiniLM-L6-v2"):
        self.home = home or get_home()
        self.dir = self.home / "memory"
        self.dir.mkdir(parents=True, exist_ok=True)
        self.file = self.dir / "memories.jsonl"
        self.faiss_index_path = self.dir / "faiss.index"
        self.meta_path = self.dir / "faiss_meta.json"
        self.embedding_model_name = embedding_model

        self._embedder = None
        self._faiss_index = None
        self._faiss_available = False
        self._bm25_available = False
        self._check_deps()

    def _check_deps(self):
        try:
            import faiss  # type: ignore
            import sentence_transformers  # type: ignore
            self._faiss_available = True
        except ImportError:
            self._faiss_available = False

        try:
            import rank_bm25  # type: ignore
            self._bm25_available = True
        except ImportError:
            self._bm25_available = False

    def _load_embedder(self):
        if self._embedder is not None:
            return self._embedder
        if not self._faiss_available:
            return None
        try:
            from sentence_transformers import SentenceTransformer
            self._embedder = SentenceTransformer(self.embedding_model_name)
            return self._embedder
        except Exception:
            return None

    def _load_all(self) -> list[MemoryEntry]:
        if not self.file.exists():
            return []
        entries: list[MemoryEntry] = []
        for line in self.file.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                entries.append(MemoryEntry(**data))
            except Exception:
                continue
        return entries

    def add(self, content: str, metadata: dict | None = None) -> MemoryEntry:
        entry = MemoryEntry(id=str(uuid.uuid4())[:8], content=content, metadata=metadata or {})
        with self.file.open("a", encoding="utf-8") as f:
            f.write(json.dumps({"id": entry.id, "content": entry.content, "metadata": entry.metadata}) + "\n")

        # Invalidate FAISS index to force rebuild next search
        if self.faiss_index_path.exists():
            try:
                self.faiss_index_path.unlink()
                self.meta_path.unlink(missing_ok=True)
            except Exception:
                pass
        return entry

    def _build_faiss_index(self, entries: list[MemoryEntry]):
        if not self._faiss_available:
            return None
        embedder = self._load_embedder()
        if embedder is None:
            return None
        try:
            import faiss
            import numpy as np

            texts = [e.content for e in entries]
            embeddings = embedder.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            # Normalize for cosine similarity
            faiss.normalize_L2(embeddings)

            dim = embeddings.shape[1]
            index = faiss.IndexFlatIP(dim)  # cosine similarity via inner product on normalized
            index.add(embeddings)

            # Save
            faiss.write_index(index, str(self.faiss_index_path))
            self.meta_path.write_text(json.dumps([e.id for e in entries]), encoding="utf-8")
            self._faiss_index = index
            return index
        except Exception as e:
            print(f"FAISS build failed: {e}")
            return None

    def _load_faiss_index(self):
        if not self._faiss_available:
            return None
        if self._faiss_index is not None:
            return self._faiss_index
        if not self.faiss_index_path.exists():
            return None
        try:
            import faiss
            index = faiss.read_index(str(self.faiss_index_path))
            self._faiss_index = index
            return index
        except Exception:
            return None

    def search(self, query: str, top_k: int = 5, method: str = "auto") -> list[VectorSearchResult]:
        """
        Search with auto fallback: faiss -> bm25 -> keyword
        method: auto, vector, bm25, keyword
        """
        entries = self._load_all()
        if not entries:
            return []

        # Try vector search first
        if method in ("auto", "vector") and self._faiss_available:
            results = self._vector_search(query, entries, top_k)
            if results:
                return results

        # Try BM25
        if method in ("auto", "bm25") and self._bm25_available:
            results = self._bm25_search(query, entries, top_k)
            if results:
                return results

        # Fallback keyword
        return self._keyword_search(query, entries, top_k)

    def _vector_search(self, query: str, entries: list[MemoryEntry], top_k: int) -> list[VectorSearchResult]:
        try:
            import numpy as np
            embedder = self._load_embedder()
            if embedder is None:
                return []

            index = self._load_faiss_index()
            if index is None:
                index = self._build_faiss_index(entries)
            if index is None:
                return []

            q_emb = embedder.encode([query], convert_to_numpy=True, show_progress_bar=False)
            import faiss
            faiss.normalize_L2(q_emb)

            scores, ids = index.search(q_emb, min(top_k, len(entries)))
            results: list[VectorSearchResult] = []
            for score, idx in zip(scores[0], ids[0]):
                if idx == -1 or idx >= len(entries):
                    continue
                e = entries[idx]
                results.append(VectorSearchResult(content=e.content, score=float(score), entry=e, source="vector"))
            return results
        except Exception as e:
            print(f"Vector search failed: {e}")
            return []

    def _bm25_search(self, query: str, entries: list[MemoryEntry], top_k: int) -> list[VectorSearchResult]:
        try:
            from rank_bm25 import BM25Okapi

            tokenized_corpus = [e.content.lower().split() for e in entries]
            bm25 = BM25Okapi(tokenized_corpus)
            tokenized_query = query.lower().split()
            scores = bm25.get_scores(tokenized_query)

            # Get top k
            scored = sorted(enumerate(scores), key=lambda x: x[1], reverse=True)[:top_k]
            results = []
            for idx, score in scored:
                if score > 0:
                    e = entries[idx]
                    results.append(VectorSearchResult(content=e.content, score=float(score), entry=e, source="bm25"))
            return results
        except Exception as e:
            print(f"BM25 search failed: {e}")
            return []

    def _keyword_search(self, query: str, entries: list[MemoryEntry], top_k: int) -> list[VectorSearchResult]:
        q_words = set(query.lower().split())
        scored: list[VectorSearchResult] = []
        for e in entries:
            e_words = set(e.content.lower().split())
            overlap = len(q_words & e_words)
            score = overlap / max(len(q_words), 1)
            if score > 0 or query.lower() in e.content.lower():
                if query.lower() in e.content.lower():
                    score += 0.5
                scored.append(VectorSearchResult(content=e.content, score=score, entry=e, source="keyword"))
        scored.sort(key=lambda x: x.score, reverse=True)
        return scored[:top_k]

    def list(self, limit: int = 20) -> list[MemoryEntry]:
        return self._load_all()[-limit:]

    def clear(self):
        if self.file.exists():
            self.file.unlink()
        if self.faiss_index_path.exists():
            self.faiss_index_path.unlink()
        if self.meta_path.exists():
            self.meta_path.unlink()

    def stats(self) -> dict[str, Any]:
        entries = self._load_all()
        return {
            "count": len(entries),
            "faiss_available": self._faiss_available,
            "bm25_available": self._bm25_available,
            "faiss_index_exists": self.faiss_index_path.exists(),
            "embedding_model": self.embedding_model_name,
        }
