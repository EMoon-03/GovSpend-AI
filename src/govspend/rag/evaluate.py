"""Retrieval evaluation: recall@k and MRR over hand-labeled queries.

Query file (JSON lines; format in docs/rag.md):
  {"query": "...", "index": "reference" | "award", "relevant": ["FAR-6.302-1", ...]}

Usage:
  python -m govspend.rag.evaluate data/eval/retrieval_queries.jsonl --k 5
  python -m govspend.rag.evaluate data/eval/retrieval_queries.jsonl --embedder hashing   # lexical baseline

A window ID such as FAR-6.302-1#2 counts as a hit for the label FAR-6.302-1.
"""

from __future__ import annotations

import argparse
import json
from collections import defaultdict
from pathlib import Path

from .corpus import RAG_DIR
from .embed import Embedder, get_embedder
from .index import VectorIndex


def base_id(chunk_id: str) -> str:
    return chunk_id.split("#", 1)[0]


def score_query(retrieved: list[str], relevant: set[str]) -> tuple[float, float]:
    """(recall@k, reciprocal rank) for one query, at section level."""
    seen: list[str] = list(dict.fromkeys(base_id(r) for r in retrieved))
    found = relevant & set(seen)
    recall = len(found) / len(relevant) if relevant else 0.0
    rr = next((1.0 / (i + 1) for i, cid in enumerate(seen) if cid in relevant), 0.0)
    return recall, rr


def evaluate(queries: list[dict], indexes: dict[str, VectorIndex], embedder: Embedder,
             k: int = 5) -> dict[str, dict[str, float]]:
    per_index: dict[str, list[tuple[float, float]]] = defaultdict(list)
    for q in queries:
        index = indexes[q["index"]]
        # Over-fetch so several windows of one section don't crowd out others.
        hits = index.search_text(embedder, q["query"], k * 3)
        retrieved = list(dict.fromkeys(base_id(h.chunk.chunk_id) for h in hits))[:k]
        per_index[q["index"]].append(score_query(retrieved, {base_id(r) for r in q["relevant"]}))
    return {
        name: {"queries": len(scores),
               f"recall@{k}": sum(s[0] for s in scores) / len(scores),
               "mrr": sum(s[1] for s in scores) / len(scores)}
        for name, scores in per_index.items()
    }


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("queries", type=Path)
    p.add_argument("--k", type=int, default=5)
    p.add_argument("--index-dir", type=Path, default=RAG_DIR)
    p.add_argument("--embedder", help="override (indexes must have been built with it)")
    args = p.parse_args(argv)

    queries = [json.loads(line) for line in args.queries.read_text().splitlines() if line.strip()]
    needed = {q["index"] for q in queries}
    indexes = {name: VectorIndex.load(args.index_dir / name) for name in needed}
    embedder = get_embedder(args.embedder or next(iter(indexes.values())).embedder_name)

    for name, metrics in evaluate(queries, indexes, embedder, args.k).items():
        print(f"{name:>10}: " + ", ".join(f"{m}={v:.3f}" if isinstance(v, float) else f"{m}={v}"
                                          for m, v in metrics.items()))


if __name__ == "__main__":
    main()
