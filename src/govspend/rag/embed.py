"""Text embedders. Every embedder has a `name`, saved with the index it builds."""

from __future__ import annotations

from typing import Protocol

import numpy as np

DEFAULT_MODEL = "sentence-transformers/all-MiniLM-L6-v2"


class Embedder(Protocol):
    name: str

    def embed(self, texts: list[str]) -> np.ndarray:
        """Return an (n, d) float32 array of L2-normalised vectors."""
        ...


def _normalise(vectors: np.ndarray) -> np.ndarray:
    vectors = np.asarray(vectors, dtype=np.float32)
    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    return vectors / np.where(norms == 0, 1.0, norms)


class SentenceTransformerEmbedder:
    """Default semantic embedder. Runs locally; downloads the model once."""

    def __init__(self, model: str = DEFAULT_MODEL, batch_size: int = 64):
        from sentence_transformers import SentenceTransformer  # heavy import, keep lazy

        self.name = f"st:{model}"
        self.batch_size = batch_size
        self._model = SentenceTransformer(model)

    def embed(self, texts: list[str]) -> np.ndarray:
        vecs = self._model.encode(texts, batch_size=self.batch_size, show_progress_bar=len(texts) > 500,
                                  convert_to_numpy=True, normalize_embeddings=True)
        return _normalise(vecs)


class HashingEmbedder:
    """Keyword-overlap embedder with no model download.

    Used by the tests and as a lexical baseline for retrieval evaluation —
    not as the production embedder.
    """

    def __init__(self, n_features: int = 2**12):
        from sklearn.feature_extraction.text import HashingVectorizer

        self.name = f"hashing:{n_features}"
        self._vec = HashingVectorizer(n_features=n_features, alternate_sign=False,
                                      ngram_range=(1, 2), stop_words="english", norm=None)

    def embed(self, texts: list[str]) -> np.ndarray:
        return _normalise(self._vec.transform(texts).toarray())


def get_embedder(name: str) -> Embedder:
    """Rebuild an embedder from the name stored with an index."""
    if name.startswith("st:"):
        return SentenceTransformerEmbedder(name[3:])
    if name.startswith("hashing:"):
        return HashingEmbedder(int(name.split(":", 1)[1]))
    if name in ("st", "sentence-transformers"):
        return SentenceTransformerEmbedder()
    if name == "hashing":
        return HashingEmbedder()
    raise ValueError(f"Unknown embedder {name!r}; use 'st[:<model>]' or 'hashing[:<n_features>]'")
