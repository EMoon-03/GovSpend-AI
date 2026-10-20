# Analyst Assistant — Design

The assistant explains why one award was flagged as unusual. It does not decide whether an award is unusual — that comes from the Modeling track — and it never asserts wrongdoing.

## Flow

```
flagged award (generated_internal_id)
   │
   ├─► peer summary ── median amount of comparable awards, ratio, group size
   │
   ├─► peer retrieval ── award index, same NAICS (fallback: same agency, then all)
   │                     ranked by description similarity → top k awards
   │
   ├─► reference retrieval ── reference index (FAR + data dictionary)
   │                          query built from the award's type, NAICS, description
   │
   ├─► prompt ── only the retrieved context; citation rules; wording rules
   │
   ├─► model ── Anthropic / OpenAI / Ollama, or --dry-run to print the prompt
   │
   └─► guards ── unknown citations, uncited sentences, accusatory wording
```

## Corpus

| Source | Unit | Chunk ID | Notes |
| --- | --- | --- | --- |
| FAR parts (acquisition.gov) | One section, split into ~1,200-char windows if long | `FAR-6.302-1`, `FAR-6.302-1#2` | Default parts 6, 13, 16, 19. Raw HTML cached in `data/raw/reference/` |
| USAspending data dictionary (`/api/v2/references/data_dictionary/`) | One element | `DD-<element-slug>` | Definition plus domain values |
| Processed awards table | One award | the award's `generated_internal_id` | Description plus structured fields; metadata used for filtering |

FAR text is a U.S. government work. Each chunk keeps its source URL so explanations can link back.

## Citation format

- `[A:<generated_internal_id>]` — a retrieved comparable award, or the target award itself.
- `[R:<chunk_id>]` — a retrieved reference passage.

A citation is valid only if that ID was in the prompt's context. The guard reports any other ID as a fabricated citation.

## Guards

`src/govspend/rag/guards.py` checks every generated explanation:

1. **Unknown citations** — IDs not present in the retrieved context.
2. **Uncited sentences** — sentences containing a number or a factual claim with no citation.
3. **Accusatory wording** — terms such as fraud, waste, abuse, misconduct, suspicious, illegal, kickback.

An explanation with any unknown citation or accusatory term is marked as failed. Uncited sentences are reported for review.

## Retrieval evaluation

`data/eval/retrieval_queries.jsonl`, one JSON object per line:

```json
{"query": "sole-source justification when only one responsible source exists", "index": "reference", "relevant": ["FAR-6.302-1"]}
{"query": "cloud hosting migration for a civilian agency", "index": "award", "relevant": ["CONT_AWD_..."]}
```

Write queries **before** looking at retrieval results, and label relevance by reading the source, not by what the system returned. Run:

```bash
python -m govspend.rag.evaluate data/eval/retrieval_queries.jsonl --k 5
```

Reports recall@k and MRR per index. Commit the query file, and note in its PR which snapshot `run_id` the award IDs come from.

## Explanation evaluation (planned)

For 20 flagged awards, score each explanation on:

| Criterion | How |
| --- | --- |
| Citation validity | Automatic (guards) |
| Faithfulness — every claim supported by the cited source | Manual, 0–2 |
| Usefulness — would an analyst learn something they couldn't see from the score alone | Manual, 0–2 |
| Wording — describes differences, not wrongdoing | Automatic + manual |

Compare with a no-retrieval prompt (same award fields, no peers or passages) to measure what retrieval adds.
