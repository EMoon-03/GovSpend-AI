"""Build the retrievable corpus: FAR sections, data-dictionary elements, and awards.

Every chunk keeps a stable ID, its source URL, and metadata, so an explanation
can cite it as [R:<chunk_id>] or [A:<generated_internal_id>].
"""

from __future__ import annotations

import json
import math
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[3]
REFERENCE_RAW_DIR = REPO_ROOT / "data" / "raw" / "reference"
RAG_DIR = REPO_ROOT / "data" / "processed" / "rag"

FAR_PART_URL = "https://www.acquisition.gov/far/part-{part}"
DATA_DICTIONARY_URL = "https://api.usaspending.gov/api/v2/references/data_dictionary/"
AWARD_URL = "https://www.usaspending.gov/award/{gid}"

# 6 competition, 13 simplified acquisition, 16 contract types, 19 small business
DEFAULT_FAR_PARTS = [6, 13, 16, 19]
MAX_CHUNK_CHARS = 1200

# "6.302-1 Only one responsible source..." / "19.1305 ..." / "52.212-4 ..."
SECTION_RE = re.compile(r"^(\d{1,2}\.\d{3,4}(?:-\d+)?)\s+(\S.*)$")
HEADING_RE = re.compile(r"^h[1-6]$")
BLOCK_TAGS = {"p", "li", "div", "br", "tr", "dd", "dt", "blockquote", "section", "table"}


@dataclass
class Chunk:
    chunk_id: str
    source: str  # "far" | "data_dictionary" | "award"
    title: str
    text: str
    url: str
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Chunk":
        return cls(**d)


def write_jsonl(chunks: Iterable[Chunk], path: Path) -> int:
    path.parent.mkdir(parents=True, exist_ok=True)
    n = 0
    with path.open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c.to_dict(), ensure_ascii=False) + "\n")
            n += 1
    return n


def read_jsonl(path: Path) -> list[Chunk]:
    with path.open(encoding="utf-8") as f:
        return [Chunk.from_dict(json.loads(line)) for line in f if line.strip()]


# --------------------------------------------------------------------------- FAR


def _clean_lines(raw: str) -> list[str]:
    lines = (re.sub(r"[ \t ]+", " ", ln).strip() for ln in raw.split("\n"))
    return [ln for ln in lines if ln]


def _section_text(heading) -> str:
    """Text after a heading, up to the next heading, with block breaks kept."""
    from bs4 import NavigableString, Tag  # imported lazily: only needed for FAR parsing

    parts: list[str] = []
    for el in heading.next_elements:
        if isinstance(el, Tag):
            if HEADING_RE.match(el.name or ""):
                break
            if el.name in BLOCK_TAGS:
                parts.append("\n")
        elif isinstance(el, NavigableString):
            if heading in el.parents or el.parent.name in ("script", "style"):
                continue
            parts.append(re.sub(r"\s+", " ", str(el)))  # source line wraps aren't paragraph breaks
    return "\n".join(_clean_lines("".join(parts)))


def _windows(paragraphs: list[str], max_chars: int) -> list[str]:
    """Pack paragraphs into windows of at most max_chars, splitting huge ones."""
    pieces: list[str] = []
    for p in paragraphs:
        if len(p) <= max_chars:
            pieces.append(p)
            continue
        sentence_buf = ""
        for s in re.split(r"(?<=[.;:])\s+", p):
            if sentence_buf and len(sentence_buf) + len(s) + 1 > max_chars:
                pieces.append(sentence_buf)
                sentence_buf = ""
            sentence_buf = f"{sentence_buf} {s}".strip()
            while len(sentence_buf) > max_chars:  # a single run-on "sentence"
                pieces.append(sentence_buf[:max_chars])
                sentence_buf = sentence_buf[max_chars:]
        if sentence_buf:
            pieces.append(sentence_buf)

    windows, buf = [], ""
    for piece in pieces:
        if buf and len(buf) + len(piece) + 1 > max_chars:
            windows.append(buf)
            buf = ""
        buf = f"{buf}\n{piece}".strip()
    if buf:
        windows.append(buf)
    return windows


def parse_far_html(html: str, part: int | str, max_chars: int = MAX_CHUNK_CHARS) -> list[Chunk]:
    """One chunk per FAR section (split into windows if long)."""
    from bs4 import BeautifulSoup

    soup = BeautifulSoup(html, "html.parser")
    url = FAR_PART_URL.format(part=part)
    chunks: list[Chunk] = []
    seen: set[str] = set()

    for heading in soup.find_all(HEADING_RE):
        m = SECTION_RE.match(" ".join(heading.get_text(" ").split()))
        if not m:
            continue
        number, title = m.group(1), m.group(2).rstrip(".")
        if not number.startswith(f"{part}."):
            continue  # cross-referenced heading from another part
        if number in seen:
            continue
        seen.add(number)

        body = _section_text(heading)
        if not body:
            continue
        anchor = "#FAR_" + number.replace(".", "_").replace("-", "_")
        windows = _windows(body.split("\n"), max_chars)
        for i, window in enumerate(windows, start=1):
            chunk_id = f"FAR-{number}" if i == 1 else f"FAR-{number}#{i}"
            chunks.append(Chunk(
                chunk_id=chunk_id,
                source="far",
                title=f"FAR {number} {title}",
                text=f"FAR {number} {title}\n{window}",
                url=url + anchor,
                metadata={"part": int(part), "section": number, "window": i, "windows": len(windows)},
            ))
    return chunks


def fetch_far_part(part: int, *, session=None, cache_dir: Path = REFERENCE_RAW_DIR,
                   refresh: bool = False) -> str:
    """Download one FAR part page, caching the raw HTML."""
    cache = cache_dir / f"far_part_{part}.html"
    if cache.exists() and not refresh:
        return cache.read_text(encoding="utf-8")
    import requests

    session = session or requests.Session()
    resp = session.get(FAR_PART_URL.format(part=part), timeout=60,
                       headers={"User-Agent": "govspend-ai research project (CS 513)"})
    resp.raise_for_status()
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(resp.text, encoding="utf-8")
    return resp.text


# ------------------------------------------------------------ data dictionary


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def parse_data_dictionary(payload: dict[str, Any]) -> list[Chunk]:
    """One chunk per USAspending data element."""
    doc = payload["document"]
    keys = [h["raw"] for h in doc["headers"]]
    chunks: list[Chunk] = []
    used: dict[str, int] = {}

    for values in doc["rows"]:
        row = dict(zip(keys, values))
        element = (row.get("element") or "").strip()
        definition = (row.get("definition") or "").strip()
        if not element or not definition:
            continue
        slug = _slug(element)
        used[slug] = used.get(slug, 0) + 1
        if used[slug] > 1:
            slug = f"{slug}-{used[slug]}"

        lines = [f"USAspending data element: {element}", f"Definition: {definition}"]
        for key, label in [("fpds_data_dictionary_element", "FPDS element"),
                           ("domain_values", "Domain values"),
                           ("domain_values_code_description", "Domain value descriptions")]:
            if row.get(key):
                lines.append(f"{label}: {str(row[key]).strip()}")
        chunks.append(Chunk(
            chunk_id=f"DD-{slug}",
            source="data_dictionary",
            title=f"Data dictionary: {element}",
            text="\n".join(lines),
            url="https://www.usaspending.gov/data-dictionary",
            metadata={"element": element, "grouping": row.get("grouping"),
                      "award_element": row.get("award_element")},
        ))
    return chunks


def fetch_data_dictionary(*, session=None, cache_dir: Path = REFERENCE_RAW_DIR,
                          refresh: bool = False) -> dict[str, Any]:
    cache = cache_dir / "usaspending_data_dictionary.json"
    if cache.exists() and not refresh:
        return json.loads(cache.read_text(encoding="utf-8"))
    import requests

    session = session or requests.Session()
    resp = session.get(DATA_DICTIONARY_URL, timeout=60)
    resp.raise_for_status()
    cache.parent.mkdir(parents=True, exist_ok=True)
    cache.write_text(resp.text, encoding="utf-8")
    return resp.json()


# ---------------------------------------------------------------------- awards


def _clean(value: Any) -> str | None:
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return None
    text = str(value).strip()
    return text or None


def award_chunk(row: dict[str, Any]) -> Chunk:
    """Describe one award as text for semantic matching; keep fields as metadata.

    The recipient name is deliberately left out of the text so peers are matched
    on what was bought, not who sold it.
    """
    gid = row["generated_internal_id"]
    amount = row.get("award_amount")
    amount = None if amount is None or (isinstance(amount, float) and math.isnan(amount)) else float(amount)
    start = _clean(row.get("start_date"))
    start = start[:10] if start else None

    lines = [_clean(row.get("description")) or "(no description)"]
    agency = " / ".join(x for x in [_clean(row.get("awarding_agency")),
                                    _clean(row.get("awarding_sub_agency"))] if x)
    if agency:
        lines.append(f"Agency: {agency}")
    for label, code_key, desc_key in [("NAICS", "naics_code", "naics_description"),
                                      ("PSC", "psc_code", "psc_description")]:
        code, desc = _clean(row.get(code_key)), _clean(row.get(desc_key))
        if code or desc:
            lines.append(f"{label}: {' '.join(x for x in [code, desc] if x)}")
    if _clean(row.get("contract_award_type")):
        lines.append(f"Type: {_clean(row.get('contract_award_type'))}")
    if amount is not None:
        lines.append(f"Award amount: ${amount:,.0f}")
    if start:
        lines.append(f"Start date: {start}")

    return Chunk(
        chunk_id=gid,
        source="award",
        title=f"Award {_clean(row.get('award_id')) or gid}",
        text="\n".join(lines),
        url=AWARD_URL.format(gid=gid),
        metadata={
            "award_id": _clean(row.get("award_id")),
            "recipient_name": _clean(row.get("recipient_name")),
            "awarding_agency": _clean(row.get("awarding_agency")),
            "naics_code": _clean(row.get("naics_code")),
            "psc_code": _clean(row.get("psc_code")),
            "contract_award_type": _clean(row.get("contract_award_type")),
            "award_amount": amount,
            "start_date": start,
            "has_description": bool(_clean(row.get("description"))),
        },
    )


def award_chunks(df: pd.DataFrame) -> list[Chunk]:
    df = df.astype(object).where(pd.notna(df), None)
    return [award_chunk(r) for r in df.to_dict("records") if r.get("generated_internal_id")]
