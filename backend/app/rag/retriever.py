from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

from app.rag.indexer import VectorIndex, get_embeddings
from app.schemas.analysis import RagEvidenceItem

logger = logging.getLogger(__name__)


class DatasetRagRetriever:
    """Retrieves semantically relevant schema, category, or record evidence from vector index."""

    def __init__(self, index_file: Path, chunks_file: Path):
        self.index_file = Path(index_file)
        self.chunks_file = Path(chunks_file)
        self.index: VectorIndex | None = None
        self.chunks: list[dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if (self.index_file.exists() or self.index_file.with_suffix(".npz").exists()) and self.chunks_file.exists():
            try:
                self.index = VectorIndex.load(self.index_file)
                self.chunks = json.loads(self.chunks_file.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error("Failed to load vector index or chunks: %s", e)
                self.index = None
                self.chunks = []

    def search(
        self,
        query: str,
        top_k: int = 5,
        min_score: float = 0.15,
        chunk_types: list[str] | None = None,
    ) -> list[RagEvidenceItem]:
        """Perform semantic similarity search against the dataset's vector index."""
        if not self.index or not self.chunks:
            return []

        query_vec = get_embeddings([query])
        k = min(top_k * 3 if chunk_types else top_k, self.index.ntotal)
        if k <= 0:
            return []

        scores, indices = self.index.search(query_vec, k)
        results: list[RagEvidenceItem] = []

        for score, idx in zip(scores[0], indices[0]):
            if idx < 0 or idx >= len(self.chunks):
                continue
            if score < min_score:
                continue

            chunk = self.chunks[idx]
            ctype = chunk.get("chunk_type", "record_text")
            if chunk_types and ctype not in chunk_types:
                continue

            results.append(
                RagEvidenceItem(
                    chunk_id=chunk.get("chunk_id", f"chk_{idx}"),
                    chunk_type=ctype,
                    score=round(float(score), 4),
                    text=chunk.get("text", ""),
                    row_id=chunk.get("row_id"),
                    column_name=chunk.get("column_name"),
                )
            )
            if len(results) >= top_k:
                break

        return results
