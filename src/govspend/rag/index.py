"""A small on-disk vector index: exact cosine search with NumPy.

Exact search over a few thousand award documents and a few thousand reference
passages is fast enough and fully reproducible. Swap in FAISS or pgvector
behind the same interface if the corpus outgrows it.

On disk, an index is a folder:
  vectors.npy     (n, d) float32, L2-normalised
  chunks.jsonl    one Chunk per row, same order as vectors
  meta.json       embedder name, dimensions, count
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

import numpy as np

from .corpus import Chunk, read_jsonl, write_jsonl
from .embed import Embedder


@dataclass
class Hit:
    chunk: Chunk
    score: float


class VectorIndex:
    def __init__(self, embedder_name: str, chunks: list[Chunk], vectors: np.ndarray):
        if len(chunks) != len(vectors):
            raise ValueError("chunks and vectors must have the same length")
        self.embedder_name = embedder_name
        self.chunks = chunks
        self.vectors = np.asarray(vectors, dtype=np.float32)
        self._pos = {c.chunk_id: i for i, c in enumerate(chunks)}

    @classmethod
    def build(cls, chunks: list[Chunk], embedder: Embedder) -> "VectorIndex":
        vectors = embedder.embed([c.text for c in chunks]) if chunks else np.zeros((0, 1), np.float32)
        return cls(embedder.name, chunks, vectors)

    def __len__(self) -> int:
        return len(self.chunks)

    def get(self, chunk_id: str) -> Chunk | None:
        i = self._pos.get(chunk_id)
        return None if i is None else self.chunks[i]

    def vector(self, chunk_id: str) -> np.ndarray:
        return self.vectors[self._pos[chunk_id]]

    def search(self, query_vec: np.ndarray, k: int = 5,
               where: Callable[[Chunk], bool] | None = None,
               exclude: set[str] | None = None) -> list[Hit]:
        """Top-k chunks by cosine similarity, optionally filtered."""
        if not len(self):
            return []
        scores = self.vectors @ np.asarray(query_vec, dtype=np.float32).ravel()
        hits: list[Hit] = []
        for i in np.argsort(-scores, kind="stable"):
            chunk = self.chunks[i]
            if exclude and chunk.chunk_id in exclude:
                continue
            if where and not where(chunk):
                continue
            hits.append(Hit(chunk, float(scores[i])))
            if len(hits) == k:
                break
        return hits

    def search_text(self, embedder: Embedder, query: str, k: int = 5, **kwargs) -> list[Hit]:
        self.check_embedder(embedder)
        return self.search(embedder.embed([query])[0], k, **kwargs)

    def check_embedder(self, embedder: Embedder) -> None:
        if embedder.name != self.embedder_name:
            raise ValueError(f"Index was built with {self.embedder_name!r} but the query "
                             f"embedder is {embedder.name!r}; rebuild the index or switch embedders.")

    def save(self, folder: Path) -> None:
        folder.mkdir(parents=True, exist_ok=True)
        np.save(folder / "vectors.npy", self.vectors)
        write_jsonl(self.chunks, folder / "chunks.jsonl")
        (folder / "meta.json").write_text(json.dumps({
            "embedder": self.embedder_name,
            "count": len(self),
            "dims": int(self.vectors.shape[1]) if self.vectors.ndim == 2 else 0,
        }, indent=2))

    @classmethod
    def load(cls, folder: Path) -> "VectorIndex":
        meta = json.loads((folder / "meta.json").read_text())
        return cls(meta["embedder"], read_jsonl(folder / "chunks.jsonl"), np.load(folder / "vectors.npy"))
