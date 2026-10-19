"""Retrieve the context for one flagged award: peer summary, peer awards, reference passages."""

from __future__ import annotations

import statistics
from dataclasses import dataclass

from .corpus import Chunk
from .embed import Embedder
from .index import Hit, VectorIndex

MIN_PEER_GROUP = 20  # PLAN.md section 6 starting value


@dataclass
class PeerSummary:
    group: str  # human-readable description of the comparison group
    n: int  # awards in the group with a positive amount, excluding the target
    median_amount: float
    target_amount: float | None

    @property
    def ratio(self) -> float | None:
        if self.target_amount is None or self.median_amount <= 0:
            return None
        return self.target_amount / self.median_amount

    def describe(self) -> str:
        text = f"Peer group: {self.group}; {self.n} awards; median award amount ${self.median_amount:,.0f}."
        if self.ratio is not None:
            text += f" Target award amount is {self.ratio:.1f} times that median."
        return text


@dataclass
class PeerHit:
    hit: Hit
    level: str  # which filter matched: "same NAICS", "same agency", "any"


def peer_summary(target: Chunk, awards: VectorIndex, min_group: int = MIN_PEER_GROUP) -> PeerSummary | None:
    """Median-amount comparison against same NAICS + agency, falling back to NAICS only.

    Returns None when no group reaches min_group — a comparison is then unavailable
    rather than built on too few awards. Only positive amounts enter the median.
    """
    tm = target.metadata
    groups = [
        (f"NAICS {tm.get('naics_code')} at {tm.get('awarding_agency')}",
         lambda m: m.get("naics_code") == tm.get("naics_code")
         and m.get("awarding_agency") == tm.get("awarding_agency")),
        (f"NAICS {tm.get('naics_code')}, all agencies in the cohort",
         lambda m: m.get("naics_code") == tm.get("naics_code")),
    ]
    for label, match in groups:
        amounts = [c.metadata["award_amount"] for c in awards.chunks
                   if c.chunk_id != target.chunk_id and match(c.metadata)
                   and (c.metadata.get("award_amount") or 0) > 0]
        if len(amounts) >= min_group:
            return PeerSummary(label, len(amounts), statistics.median(amounts), tm.get("award_amount"))
    return None


def retrieve_peers(target: Chunk, awards: VectorIndex, k: int = 5) -> list[PeerHit]:
    """Most similar awards by description, preferring same NAICS, then same agency."""
    tm = target.metadata
    query = awards.vector(target.chunk_id)
    levels = [
        ("same NAICS", lambda c: tm.get("naics_code") and c.metadata.get("naics_code") == tm.get("naics_code")),
        ("same agency", lambda c: tm.get("awarding_agency")
         and c.metadata.get("awarding_agency") == tm.get("awarding_agency")),
        ("any", None),
    ]
    taken: set[str] = {target.chunk_id}
    peers: list[PeerHit] = []
    for label, where in levels:
        for hit in awards.search(query, k - len(peers), where=where, exclude=taken):
            peers.append(PeerHit(hit, label))
            taken.add(hit.chunk.chunk_id)
        if len(peers) >= k:
            break
    return peers


def reference_queries(target: Chunk) -> dict[str, str]:
    """Queries for the reference index, built only from the award's own fields."""
    tm = target.metadata
    award_type = (tm.get("contract_award_type") or "contract").lower()
    return {
        "far": f"{award_type} acquisition rules\n{target.text}",
        "data_dictionary": f"definition of award amount and {award_type} fields used to describe a contract award",
    }


def retrieve_references(target: Chunk, references: VectorIndex, embedder: Embedder,
                        k_far: int = 4, k_dd: int = 2) -> list[Hit]:
    """FAR passages related to the award, plus data-dictionary definitions."""
    queries = reference_queries(target)
    far = references.search_text(embedder, queries["far"], k_far, where=lambda c: c.source == "far")
    dd = references.search_text(embedder, queries["data_dictionary"], k_dd,
                                where=lambda c: c.source == "data_dictionary")
    return far + dd
