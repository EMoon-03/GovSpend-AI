"""Explain one flagged award with retrieved, cited context.

Usage (from the repo root, after `python -m govspend.rag.build`):
  python -m govspend.rag.explain CONT_AWD_XXXX --dry-run            # print the prompt only
  python -m govspend.rag.explain CONT_AWD_XXXX                      # Anthropic (ANTHROPIC_API_KEY)
  python -m govspend.rag.explain CONT_AWD_XXXX --provider ollama --model llama3.1:8b

Saves reports/explanations/<id>.md with the explanation, guard result, and sources.
"""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from . import guards
from .corpus import RAG_DIR, REPO_ROOT, Chunk
from .embed import Embedder, get_embedder
from .index import Hit, VectorIndex
from .llm import generate
from .prompt import PromptBundle, build_prompt
from .retrieve import MIN_PEER_GROUP, PeerHit, PeerSummary, peer_summary, retrieve_peers, retrieve_references

EXPLANATIONS_DIR = REPO_ROOT / "reports" / "explanations"


@dataclass
class Context:
    target: Chunk
    summary: PeerSummary | None
    peers: list[PeerHit]
    references: list[Hit]
    prompt: PromptBundle


def gather_context(award_id: str, awards: VectorIndex, references: VectorIndex, embedder: Embedder,
                   *, k_peers: int = 5, k_far: int = 4, k_dd: int = 2,
                   min_group: int = MIN_PEER_GROUP) -> Context:
    target = awards.get(award_id)
    if target is None:
        raise KeyError(f"{award_id} is not in the award index. Check the generated_internal_id "
                       f"and that the index was built from the right snapshot.")
    summary = peer_summary(target, awards, min_group)
    peers = retrieve_peers(target, awards, k_peers)
    refs = retrieve_references(target, references, embedder, k_far, k_dd)
    return Context(target, summary, peers, refs, build_prompt(target, summary, peers, refs))


def render_markdown(ctx: Context, explanation: str, report: guards.GuardReport, provider: str,
                    model: str | None) -> str:
    lookup = {ctx.target.chunk_id: ctx.target}
    lookup |= {p.hit.chunk.chunk_id: p.hit.chunk for p in ctx.peers}
    lookup |= {h.chunk.chunk_id: h.chunk for h in ctx.references}
    cited = [cid for cid in dict.fromkeys(report.citations) if cid in lookup]

    lines = [
        f"# {ctx.target.title}",
        "",
        f"Generated {datetime.now(timezone.utc):%Y-%m-%d %H:%M} UTC · {provider} `{model or 'default'}`",
        "",
        "> An unusual ranking describes a statistical difference. It is not a finding of wrongdoing.",
        "",
        explanation.strip(),
        "",
        "## Guard check",
        "",
        "```",
        report.summary(),
        "```",
        "",
        "## Sources cited",
        "",
    ]
    lines += [f"- `{cid}` — [{lookup[cid].title}]({lookup[cid].url})" for cid in cited] or ["- none"]
    return "\n".join(lines) + "\n"


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("award_id", help="generated_internal_id of the flagged award")
    p.add_argument("--index-dir", type=Path, default=RAG_DIR)
    p.add_argument("--k-peers", type=int, default=5)
    p.add_argument("--k-far", type=int, default=4)
    p.add_argument("--k-dd", type=int, default=2)
    p.add_argument("--min-group", type=int, default=MIN_PEER_GROUP)
    p.add_argument("--provider", default="anthropic", choices=["anthropic", "openai", "ollama"])
    p.add_argument("--model")
    p.add_argument("--dry-run", action="store_true", help="print the prompt; don't call a model")
    p.add_argument("--out-dir", type=Path, default=EXPLANATIONS_DIR)
    args = p.parse_args(argv)

    awards = VectorIndex.load(args.index_dir / "award")
    references = VectorIndex.load(args.index_dir / "reference")
    if awards.embedder_name != references.embedder_name:
        raise SystemExit("The award and reference indexes use different embedders; rebuild one.")
    embedder = get_embedder(references.embedder_name)

    ctx = gather_context(args.award_id, awards, references, embedder, k_peers=args.k_peers,
                         k_far=args.k_far, k_dd=args.k_dd, min_group=args.min_group)

    if args.dry_run:
        print("=== SYSTEM ===\n" + ctx.prompt.system + "\n\n=== USER ===\n" + ctx.prompt.user)
        return

    explanation = generate(ctx.prompt.system, ctx.prompt.user, provider=args.provider, model=args.model)
    report = guards.check(explanation, ctx.prompt.allowed_ids)
    print(explanation.strip() + "\n\n" + report.summary())

    args.out_dir.mkdir(parents=True, exist_ok=True)
    out = args.out_dir / f"{args.award_id}.md"
    out.write_text(render_markdown(ctx, explanation, report, args.provider, args.model), encoding="utf-8")
    print(f"\nSaved {out}")


if __name__ == "__main__":
    main()
