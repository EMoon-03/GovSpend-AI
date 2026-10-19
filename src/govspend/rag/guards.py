"""Checks run on every generated explanation (see docs/rag.md, "Guards")."""

from __future__ import annotations

import re
from dataclasses import dataclass, field

CITATION_RE = re.compile(r"\[(A|R):([^\]\s]+)\]")

# Words that describe conduct rather than statistics. Matched as whole words,
# case-insensitive, with common inflections. Bare "waste" is left out on purpose:
# it appears in ordinary contract descriptions ("hazardous waste removal").
ACCUSATORY_TERMS = [
    r"fraud\w*", r"wasteful\w*", r"abus\w*", r"misconduct", r"corrupt\w*",
    r"illegal\w*", r"unlawful\w*", r"suspicious\w*", r"suspect(?:ed)?", r"kickbacks?",
    r"bribe\w*", r"embezzl\w*", r"collu\w*", r"rigged", r"improper\w*", r"wrongdoing",
]
ACCUSATORY_RE = re.compile(r"\b(" + "|".join(ACCUSATORY_TERMS) + r")\b", re.IGNORECASE)

# A sentence "makes a claim" if it contains a number, a dollar sign, or a percent.
CLAIM_RE = re.compile(r"[$%]|\d")
SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+(?=[A-Z(\[])")


@dataclass
class GuardReport:
    citations: list[str] = field(default_factory=list)
    unknown_citations: list[str] = field(default_factory=list)
    uncited_claims: list[str] = field(default_factory=list)
    accusatory_terms: list[str] = field(default_factory=list)

    @property
    def passed(self) -> bool:
        """Fails on fabricated citations, accusatory wording, or no citations at all."""
        return bool(self.citations) and not self.unknown_citations and not self.accusatory_terms

    def summary(self) -> str:
        lines = [f"Guard result: {'PASS' if self.passed else 'FAIL'}",
                 f"  citations: {len(self.citations)} ({len(set(self.citations))} unique)"]
        if not self.citations:
            lines.append("  no citations found")
        if self.unknown_citations:
            lines.append(f"  unknown citations: {', '.join(self.unknown_citations)}")
        if self.accusatory_terms:
            lines.append(f"  accusatory wording: {', '.join(self.accusatory_terms)}")
        if self.uncited_claims:
            lines.append(f"  sentences with figures but no citation ({len(self.uncited_claims)}):")
            lines += [f"    - {s}" for s in self.uncited_claims]
        return "\n".join(lines)


def extract_citations(text: str) -> list[str]:
    """Citation IDs in order of appearance (prefix dropped: 'A:x' -> 'x')."""
    return [m.group(2) for m in CITATION_RE.finditer(text)]


def split_sentences(text: str) -> list[str]:
    out = []
    for para in text.split("\n"):
        out += [s.strip() for s in SENTENCE_SPLIT_RE.split(para) if s.strip()]
    return out


def check(text: str, allowed_ids: set[str]) -> GuardReport:
    cites = extract_citations(text)
    report = GuardReport(citations=cites)
    report.unknown_citations = sorted({c for c in cites if c not in allowed_ids})
    report.accusatory_terms = sorted({m.group(0).lower() for m in ACCUSATORY_RE.finditer(text)})
    for sentence in split_sentences(text):
        body = CITATION_RE.sub("", sentence)
        if CLAIM_RE.search(body) and not CITATION_RE.search(sentence):
            report.uncited_claims.append(sentence)
    return report
