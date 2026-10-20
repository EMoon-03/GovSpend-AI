"""Build the assistant's two indexes from the reference sources and the awards table.

Usage (from the repo root):
  python -m govspend.rag.build                          # fetch references, newest awards CSV
  python -m govspend.rag.build --far-parts 6 16         # only some FAR parts
  python -m govspend.rag.build --skip-reference         # rebuild the award index only
  python -m govspend.rag.build --embedder hashing       # offline, no model download

Writes:
  data/raw/reference/                cached FAR HTML and data-dictionary JSON
  data/processed/rag/reference/      reference index
  data/processed/rag/award/          award index
  data/processed/rag/manifest.json   sources, counts, embedder, timestamps
"""

from __future__ import annotations

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd

from .corpus import (DEFAULT_FAR_PARTS, RAG_DIR, REFERENCE_RAW_DIR, REPO_ROOT, award_chunks,
                     fetch_data_dictionary, fetch_far_part, parse_data_dictionary, parse_far_html)
from .embed import get_embedder
from .index import VectorIndex

PROCESSED_DIR = REPO_ROOT / "data" / "processed"
CODE_COLUMNS = {"naics_code": str, "psc_code": str, "award_id": str,
                "generated_internal_id": str, "recipient_uei": str}


def load_awards(path: Path) -> pd.DataFrame:
    """Read a processed awards CSV, keeping codes as strings (no '541512.0')."""
    return pd.read_csv(path, dtype=CODE_COLUMNS)


def latest_awards_csv() -> Path:
    files = sorted(PROCESSED_DIR.glob("awards_*.csv"))
    if not files:
        raise FileNotFoundError("No data/processed/awards_*.csv. Run collect + flatten first.")
    return files[-1]


def build_reference_chunks(far_parts: list[int], refresh: bool, cache_dir: Path = REFERENCE_RAW_DIR):
    chunks, sources = [], []
    for part in far_parts:
        part_chunks = parse_far_html(fetch_far_part(part, cache_dir=cache_dir, refresh=refresh), part)
        if not part_chunks:
            raise RuntimeError(f"Parsed 0 sections from FAR part {part}; the page layout may have "
                               f"changed. Inspect {cache_dir / f'far_part_{part}.html'}.")
        chunks += part_chunks
        sources.append({"source": f"FAR part {part}", "chunks": len(part_chunks)})
    dd_chunks = parse_data_dictionary(fetch_data_dictionary(cache_dir=cache_dir, refresh=refresh))
    chunks += dd_chunks
    sources.append({"source": "USAspending data dictionary", "chunks": len(dd_chunks)})
    return chunks, sources


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--awards", type=Path, help="processed awards CSV (default: newest)")
    p.add_argument("--far-parts", type=int, nargs="+", default=DEFAULT_FAR_PARTS)
    p.add_argument("--embedder", default="st", help="'st[:<model>]' (default) or 'hashing'")
    p.add_argument("--refresh", action="store_true", help="re-download cached reference pages")
    p.add_argument("--skip-reference", action="store_true")
    p.add_argument("--skip-awards", action="store_true")
    p.add_argument("--out", type=Path, default=RAG_DIR)
    args = p.parse_args(argv)

    embedder = get_embedder(args.embedder)
    manifest = {"built_at_utc": datetime.now(timezone.utc).isoformat(), "embedder": embedder.name}

    if not args.skip_reference:
        chunks, sources = build_reference_chunks(args.far_parts, args.refresh)
        VectorIndex.build(chunks, embedder).save(args.out / "reference")
        manifest["reference"] = {"chunks": len(chunks), "sources": sources}
        print(f"Reference index: {len(chunks)} passages")

    if not args.skip_awards:
        awards_csv = args.awards or latest_awards_csv()
        chunks = award_chunks(load_awards(awards_csv))
        VectorIndex.build(chunks, embedder).save(args.out / "award")
        no_desc = sum(not c.metadata["has_description"] for c in chunks)
        manifest["award"] = {"chunks": len(chunks), "source_csv": awards_csv.name,
                             "without_description": no_desc}
        print(f"Award index: {len(chunks)} awards ({no_desc} without a description) from {awards_csv.name}")

    args.out.mkdir(parents=True, exist_ok=True)
    manifest_path = args.out / "manifest.json"
    if manifest_path.exists():  # keep the other index's entry when rebuilding one
        manifest = {**json.loads(manifest_path.read_text()), **manifest}
    manifest_path.write_text(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    main()
