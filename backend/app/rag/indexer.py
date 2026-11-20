from __future__ import annotations

import csv
import hashlib
import json
import logging
import re
from pathlib import Path
from typing import Any

import numpy as np

from app.core.config import get_settings

logger = logging.getLogger(__name__)

# Global embedding settings
_VECTOR_DIM = 384


def get_gemini_embeddings(texts: list[str]) -> np.ndarray | None:
    """Lightweight external embedding via Gemini API without loading models locally."""
    settings = get_settings()
    if not settings.gemini_api_key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=settings.gemini_api_key)
        all_vecs = []
        for i in range(0, len(texts), 50):
            batch = texts[i : i + 50]
            resp = client.models.embed_content(
                model="text-embedding-004",
                contents=batch,
            )
            for emb in getattr(resp, "embeddings", []):
                all_vecs.append(emb.values)
        if all_vecs:
            arr = np.array(all_vecs, dtype=np.float32)
            norms = np.linalg.norm(arr, axis=1, keepdims=True)
            norms[norms == 0] = 1.0
            return arr / norms
    except Exception as e:
        logger.warning("Gemini embedding API call failed: %s, falling back to deterministic projection", e)
    return None


def get_token_count(text: str) -> int:
    """Accurate token counting with offline fallback heuristic."""
    try:
        import tiktoken
        enc = tiktoken.get_encoding("cl100k_base")
        return len(enc.encode(text))
    except Exception:
        # 1 token ~= 4 characters / 0.75 words
        return max(1, len(text) // 4)


def deterministic_embedding(text: str, dim: int = _VECTOR_DIM) -> np.ndarray:
    """
    Deterministic normalized projection vectorizer.
    Used for local testing or when external model weights are offline.
    """
    words = re.findall(r"\w+", text.lower())
    vec = np.zeros(dim, dtype=np.float32)
    if not words:
        vec[0] = 1.0
        return vec
    for w in words:
        # Hash 3-grams
        h = int(hashlib.md5(w.encode("utf-8")).hexdigest(), 16)
        idx = h % dim
        sign = 1.0 if (h >> 16) % 2 == 0 else -1.0
        vec[idx] += sign
    norm = np.linalg.norm(vec)
    if norm > 0:
        vec /= norm
    return vec


def get_embeddings(texts: list[str]) -> np.ndarray:
    """
    Batch embed text strings into normalized float32 vectors.
    Optimized for low-memory cloud runtimes (e.g., Render 512MB RAM):
    Uses external Gemini embeddings if configured, or fast deterministic hash-projection.
    Never attempts to download Hugging Face models or load PyTorch locally.
    """
    if not texts:
        return np.zeros((0, _VECTOR_DIM), dtype=np.float32)

    settings = get_settings()
    provider = getattr(settings, "embedding_provider", "deterministic").lower()

    if provider == "gemini":
        gemini_vecs = get_gemini_embeddings(texts)
        if gemini_vecs is not None:
            return gemini_vecs

    vecs = [deterministic_embedding(t, dim=_VECTOR_DIM) for t in texts]
    return np.array(vecs, dtype=np.float32)


class VectorIndex:
    """FAISS vector index with deterministic NumPy cosine fallback for Windows DLL resilience."""

    def __init__(self, dim: int = _VECTOR_DIM):
        self.dim = dim
        self._faiss_index = None
        self._vectors: np.ndarray = np.zeros((0, dim), dtype=np.float32)
        try:
            import faiss
            self._faiss_index = faiss.IndexFlatIP(dim)
        except Exception:
            self._faiss_index = None

    @property
    def ntotal(self) -> int:
        if self._faiss_index is not None:
            return self._faiss_index.ntotal
        return len(self._vectors)

    def add(self, vectors: np.ndarray) -> None:
        vecs = np.array(vectors, dtype=np.float32)
        if self._faiss_index is not None:
            try:
                self._faiss_index.add(vecs)
                return
            except Exception:
                self._faiss_index = None
        if len(self._vectors) == 0:
            self._vectors = vecs
        else:
            self._vectors = np.vstack([self._vectors, vecs])

    def search(self, query_vec: np.ndarray, k: int) -> tuple[np.ndarray, np.ndarray]:
        if self._faiss_index is not None:
            try:
                return self._faiss_index.search(query_vec, k)
            except Exception:
                self._faiss_index = None
        if len(self._vectors) == 0:
            return np.zeros((1, 0), dtype=np.float32), np.zeros((1, 0), dtype=np.int64)
        scores = np.dot(self._vectors, query_vec[0])
        k = min(k, len(scores))
        top_indices = np.argsort(-scores)[:k]
        top_scores = scores[top_indices]
        return np.array([top_scores], dtype=np.float32), np.array([top_indices], dtype=np.int64)

    def save(self, bin_path: Path) -> None:
        bin_path = Path(bin_path)
        saved_faiss = False
        if self._faiss_index is not None:
            try:
                import faiss
                faiss.write_index(self._faiss_index, str(bin_path))
                saved_faiss = True
            except Exception:
                pass
        # Also persist npz vectors for portability
        npz_path = bin_path.with_suffix(".npz")
        np.savez_compressed(npz_path, vectors=self._vectors)
        if not saved_faiss and not bin_path.exists():
            bin_path.write_bytes(b"FAISS_NPZ_FALLBACK")

    @classmethod
    def load(cls, bin_path: Path, dim: int = _VECTOR_DIM) -> "VectorIndex":
        idx = cls(dim)
        bin_path = Path(bin_path)
        npz_path = bin_path.with_suffix(".npz")
        
        # Try loading FAISS binary index first
        if bin_path.exists() and bin_path.stat().st_size > 100:
            try:
                import faiss
                idx._faiss_index = faiss.read_index(str(bin_path))
                return idx
            except Exception:
                idx._faiss_index = None

        # Fallback to NumPy npz
        if npz_path.exists():
            try:
                data = np.load(npz_path)
                idx._vectors = data["vectors"]
            except Exception:
                pass
        return idx


class DatasetRagIndexer:
    """Extracts semantic context from tabular datasets and builds a local vector index."""

    def __init__(self, dataset_id: str, csv_path: Path, index_dir: Path | None = None):
        self.dataset_id = dataset_id
        self.csv_path = Path(csv_path)
        self.index_dir = Path(index_dir or self.csv_path.parent)
        self.index_file = self.index_dir / "faiss_index.bin"
        self.chunks_file = self.index_dir / "chunks.json"
        self.meta_file = self.index_dir / "rag_meta.json"

    def is_indexed(self, expected_sha256: str | None = None) -> bool:
        """Check if index already exists and matches content hash."""
        if not (self.index_file.exists() and self.chunks_file.exists() and self.meta_file.exists()):
            return False
        if expected_sha256:
            try:
                meta = json.loads(self.meta_file.read_text(encoding="utf-8"))
                return meta.get("content_sha256") == expected_sha256
            except Exception:
                return False
        return True

    def build_index(self, profile: dict[str, Any], content_sha256: str = "") -> dict[str, Any]:
        """Prepare context chunks, embed them, and save vector index."""
        chunks = self._prepare_chunks(profile)
        if not chunks:
            chunks = [{
                "chunk_id": "meta_0",
                "chunk_type": "schema",
                "text": f"Dataset {self.dataset_id} contains tabular records.",
                "row_id": None,
                "column_name": None,
            }]

        texts = [c["text"] for c in chunks]
        embeddings = get_embeddings(texts)

        dim = embeddings.shape[1]
        index = VectorIndex(dim)
        index.add(embeddings)
        index.save(self.index_file)

        self.chunks_file.write_text(json.dumps(chunks, indent=2), encoding="utf-8")
        meta = {
            "dataset_id": self.dataset_id,
            "content_sha256": content_sha256,
            "chunk_count": len(chunks),
            "vector_dim": dim,
        }
        self.meta_file.write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return meta

    def _prepare_chunks(self, profile: dict[str, Any]) -> list[dict[str, Any]]:
        """Context preparation stage extracting schema, categories, and textual record rows."""
        chunks: list[dict[str, Any]] = []

        # 1. Dataset Overview Chunk
        col_names = [c["name"] for c in profile.get("columns", [])]
        overview_text = (
            f"Dataset Overview:\n"
            f"- Total Rows: {profile.get('row_count', 0)}\n"
            f"- Total Columns: {profile.get('column_count', 0)}\n"
            f"- Available Columns: {', '.join(col_names)}"
        )
        chunks.append({
            "chunk_id": "overview",
            "chunk_type": "schema",
            "text": overview_text,
            "row_id": None,
            "column_name": None,
        })

        # 2. Column Description Chunks
        for col in profile.get("columns", []):
            name = col.get("name", "")
            inferred = col.get("inferred_type", "unknown")
            null_pct = col.get("null_percentage", 0.0)
            distinct_cnt = col.get("distinct_count", 0)
            desc_text = (
                f"Column Definition: '{name}' | Inferred Type: {inferred} | "
                f"Distinct Values: {distinct_cnt} | Null Percentage: {null_pct:.1f}%"
            )
            chunks.append({
                "chunk_id": f"col_{name}",
                "chunk_type": "column_desc",
                "text": desc_text,
                "row_id": None,
                "column_name": name,
            })

        # 3. Categorical Values Summary
        for col in profile.get("columns", []):
            unique_vals = col.get("sample_unique_values") or []
            if unique_vals and col.get("distinct_count", 0) <= 60:
                cat_text = f"Categorical Column '{col['name']}' contains values: {', '.join(str(v) for v in unique_vals[:30])}"
                chunks.append({
                    "chunk_id": f"cat_{col['name']}",
                    "chunk_type": "categorical_summary",
                    "text": cat_text,
                    "row_id": None,
                    "column_name": col["name"],
                })

        # 4. Textual Observations from Records
        if self.csv_path.exists():
            try:
                with self.csv_path.open("r", encoding="utf-8-sig", newline="", errors="replace") as f:
                    reader = csv.DictReader(f)
                    if reader.fieldnames:
                        # Identify columns likely containing descriptive text, comments, complaints, or feedback
                        text_cols = []
                        for h in reader.fieldnames:
                            hl = h.lower()
                            if any(k in hl for k in [
                                "comment", "feedback", "complaint", "issue", "note", "reason",
                                "description", "review", "summary", "problem", "ticket", "product", "name", "title"
                            ]):
                                text_cols.append(h)
                        
                        # If no obvious text column names found, take string-type columns
                        if not text_cols:
                            text_cols = [c["name"] for c in profile.get("columns", []) if c.get("inferred_type") == "string"][:3]

                        row_id = 1
                        for row in reader:
                            row_snippets = []
                            for col_name in text_cols:
                                val = (row.get(col_name) or "").strip()
                                if val:
                                    row_snippets.append(f"{col_name}: {val}")
                            
                            if row_snippets:
                                snippet_text = f"[Record #{row_id}] " + " | ".join(row_snippets)
                                chunks.append({
                                    "chunk_id": f"row_{row_id}",
                                    "chunk_type": "record_text",
                                    "text": snippet_text,
                                    "row_id": row_id,
                                    "column_name": text_cols[0] if len(text_cols) == 1 else None,
                                })
                            row_id += 1
                            if row_id > 2000:  # Bound max record chunks for fast local indexing
                                break
            except Exception as e:
                logger.warning("Error extracting record text chunks: %s", e)

        return chunks
