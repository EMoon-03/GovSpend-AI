"""Assemble the grounded prompt. The model sees only retrieved context."""

from __future__ import annotations

from dataclasses import dataclass

from .corpus import Chunk
from .index import Hit
from .retrieve import PeerHit, PeerSummary

SYSTEM_PROMPT = """\
You help analysts review federal contract awards that a statistical model ranked as unusual \
compared with similar awards. You explain what is measurably different about the award and \
what context might account for it.

Rules:
1. Use only the context provided. If the context does not support a statement, leave it out.
2. Cite every factual sentence. Cite awards as [A:<id>] and reference passages as [R:<id>], \
using only IDs that appear in the context. Never invent an ID.
3. Describe statistical differences, not conduct. Never say or imply that an award involves \
fraud, waste, abuse, misconduct, corruption, or anything illegal or suspicious. An unusual \
ranking is a reason to look closer, not a finding.
4. When the context offers an ordinary explanation (for example a contract type, a long \
period of performance, or a broad scope), say so and cite it. When it does not, say the \
difference is unexplained by the available context.
5. Write 3 short paragraphs: (1) what differs and by how much, (2) context from comparable \
awards and reference passages, (3) what an analyst could check next on the source record."""


@dataclass
class PromptBundle:
    system: str
    user: str
    allowed_ids: set[str]


def _block(tag: str, chunk_id: str, text: str, extra: str = "") -> str:
    head = f"[{tag}:{chunk_id}]" + (f" ({extra})" if extra else "")
    return f"{head}\n{text}"


def build_prompt(target: Chunk, summary: PeerSummary | None, peers: list[PeerHit],
                 references: list[Hit]) -> PromptBundle:
    sections = ["## Flagged award", _block("A", target.chunk_id, target.text)]

    sections.append("## Peer comparison")
    sections.append(summary.describe() if summary else
                    "No peer group reached the minimum size, so no amount comparison is available.")

    sections.append("## Comparable awards (most similar descriptions)")
    if peers:
        sections += [_block("A", p.hit.chunk.chunk_id, p.hit.chunk.text,
                            f"{p.level}, similarity {p.hit.score:.2f}") for p in peers]
    else:
        sections.append("None retrieved.")

    sections.append("## Reference passages")
    if references:
        sections += [_block("R", h.chunk.chunk_id, h.chunk.text) for h in references]
    else:
        sections.append("None retrieved.")

    sections.append("## Task\nExplain why this award may rank as unusual, following the rules.")

    allowed = {target.chunk_id} | {p.hit.chunk.chunk_id for p in peers} | {h.chunk.chunk_id for h in references}
    return PromptBundle(SYSTEM_PROMPT, "\n\n".join(sections), allowed)
