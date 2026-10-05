"""Minimal per-user episodic + Feast profile memory for the Lab 19 bonus."""
from __future__ import annotations

import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from qdrant_client import QdrantClient, models

from app.embeddings import Embedder

COLLECTION = "bonus_episodic_memory"
PROFILE_FEATURES = [
    "user_profile_features:preferred_language",
    "user_profile_features:reading_speed_wpm",
    "user_profile_features:topic_affinity",
    "query_velocity_features:queries_last_hour",
    "query_velocity_features:distinct_topics_24h",
]


class HybridMemoryAgent:
    """Store episodic chunks and assemble them with online Feast features."""

    def __init__(self, user_id: str = "u_001", client: QdrantClient | None = None,
                 embedder: Any | None = None, feature_store: Any | None = None,
                 top_k: int = 3) -> None:
        self.default_user_id = user_id
        self.client = client or QdrantClient(":memory:")
        self.embedder = embedder or Embedder()
        self.feature_store = feature_store if feature_store is not None else self._load_feature_store()
        self.top_k = top_k
        self._next_id = 0
        self._memories: dict[int, dict[str, str]] = {}
        collections = {c.name for c in self.client.get_collections().collections}
        if COLLECTION not in collections:
            self.client.create_collection(collection_name=COLLECTION, vectors_config=models.VectorParams(
                size=self.embedder.dim, distance=models.Distance.COSINE))
        else:
            # Keep memories already stored in a shared client; allocate IDs after them.
            points, _ = self.client.scroll(
                collection_name=COLLECTION, limit=100_000, with_payload=False, with_vectors=False)
            self._next_id = max((int(point.id) for point in points), default=-1) + 1
    @staticmethod
    def _load_feature_store() -> Any | None:
        repo = Path(__file__).resolve().parent.parent / "app" / "feast_repo"
        if not (repo / "registry.db").exists():
            return None
        try:
            from feast import FeatureStore

            return FeatureStore(repo_path=str(repo))
        except Exception:  # Feast is optional until NB4 has been materialized.
            return None

    @staticmethod
    def _chunk(text: str, max_words: int = 80, overlap: int = 8) -> list[str]:
        words = text.split()
        if not words:
            return []
        chunks = []
        step = max(1, max_words - overlap)
        for start in range(0, len(words), step):
            chunk = " ".join(words[start:start + max_words]).strip()
            if chunk:
                chunks.append(chunk)
            if start + max_words >= len(words):
                break
        return chunks

    def remember(self, text: str, user_id: str = "u_001") -> None:
        """Chunk, embed, and store text under this user's Qdrant payload."""
        owner = user_id or self.default_user_id
        if not text.strip():
            raise ValueError("memory text must not be empty")
        for chunk_index, chunk in enumerate(self._chunk(text)):
            point_id = self._next_id
            vector = next(self.embedder.embed([chunk])).tolist()
            payload = {"user_id": owner, "text": chunk, "chunk_index": chunk_index,
                       "created_at": datetime.now(timezone.utc).isoformat()}
            point = models.PointStruct(id=point_id, vector=vector, payload=payload)
            self.client.upsert(collection_name=COLLECTION, points=[point])
            self._memories[point_id] = {"user_id": owner, "text": chunk}
            self._next_id += 1

    @staticmethod
    def _tokens(text: str) -> set[str]:
        return set(re.findall(r"[\w]+", text.lower(), flags=re.UNICODE))

    def _profile(self, user_id: str) -> dict[str, Any]:
        if self.feature_store is None:
            return {}
        try:
            rows = self.feature_store.get_online_features(
                features=PROFILE_FEATURES,
                entity_rows=[{"user_id": user_id}],
            ).to_dict()
        except Exception:
            return {}
        return {
            name: rows[name][0]
            for name in ("preferred_language", "reading_speed_wpm", "topic_affinity",
                         "queries_last_hour", "distinct_topics_24h")
            if name in rows and len(rows[name])
        }

    def recall(self, query: str, user_id: str = "u_001") -> str:
        """Return a context string from this user's memories and Feast features."""
        owner = user_id or self.default_user_id
        query_vector = next(self.embedder.embed([query])).tolist()
        user_filter = models.Filter(must=[models.FieldCondition(
            key="user_id", match=models.MatchValue(value=owner))])
        points = self.client.query_points(collection_name=COLLECTION, query=query_vector,
                                          query_filter=user_filter,
                                          limit=max(self.top_k * 5, 10)).points

        # Add a simple lexical rank and fuse by rank, avoiding incompatible raw scores.
        query_terms = self._tokens(query)
        lexical = []
        for point_id, memory in self._memories.items():
            if memory["user_id"] != owner:
                continue
            overlap = len(query_terms & self._tokens(memory["text"]))
            if overlap:
                lexical.append((point_id, overlap))
        lexical.sort(key=lambda row: (-row[1], row[0]))

        scores: dict[int, float] = {}
        text_by_id: dict[int, str] = {}
        for rank, point in enumerate(points, start=1):
            point_id = int(point.id)
            scores[point_id] = scores.get(point_id, 0.0) + 1.0 / (60 + rank)
            text_by_id[point_id] = point.payload["text"]
        for rank, (point_id, _overlap) in enumerate(lexical, start=1):
            scores[point_id] = scores.get(point_id, 0.0) + 1.0 / (60 + rank)
            text_by_id[point_id] = self._memories[point_id]["text"]
        top_ids = sorted(scores, key=lambda point_id: -scores[point_id])[:self.top_k]

        profile = self._profile(owner)
        profile_lines = [f"{key}: {value}" for key, value in profile.items() if value is not None]
        profile_context = "; ".join(profile_lines) if profile_lines else "unavailable (run NB4 materialization)"
        memory_context = "\n".join(f"- {text_by_id[point_id]}" for point_id in top_ids)
        if not memory_context:
            memory_context = "- No matching episodic memories yet."
        return (
            f"User: {owner}\nQuestion: {query}\n"
            f"Profile and recent activity: {profile_context}\n"
            f"Relevant memories (RRF):\n{memory_context}"
        )
