# Contributing

GovSpend AI has up to three contributors working on separate tracks (see [PLAN.md](PLAN.md#team-tracks)). These rules keep the tracks from stepping on each other.

## Setup

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -r requirements-rag.txt   # only if you work on the assistant
pip install -e .
pytest
```

## Branches and pull requests

- `main` is always runnable. Never push to it directly — open a pull request.
- Branch names: `<track>/<short-topic>`, e.g. `data/full-cohort`, `model/isolation-forest`, `rag/retrieval-eval`.
- One pull request per change you could explain in a sentence. Small is better.
- Every PR needs one review from another contributor and passing `pytest`.
- Changing the processed table's columns or meaning? Update `docs/data_dictionary.md` in the same PR and tag the other tracks.

## Shared data

Raw and processed data are gitignored, so everyone must work from the **same frozen snapshot**:

1. The Data track runs `python -m govspend.collect` and `python -m govspend.flatten`.
2. They upload the whole `data/raw/<run_id>/` folder and the matching `data/processed/awards_<run_id>.csv` to the team's shared drive.
3. Everyone copies them into the same paths locally. Results, figures, and reports name the `run_id` they used.

A new snapshot is announced in the team channel with its `run_id` and the reason for re-collecting.

## Code conventions

- Reusable code lives in `src/govspend/`; notebooks import from it instead of copying functions.
- Notebooks are numbered by order (`00_`, `01_`, …) and should run top to bottom on the shared snapshot. Clear outputs that contain large tables before committing.
- Tests in `tests/` must run offline — no network calls. Use small fake responses.
- Record seeds, parameters, and package versions for any experiment that produces numbers in the report.
- No API keys in code or notebooks. Use environment variables (`ANTHROPIC_API_KEY`, `OPENAI_API_KEY`) or a local `.env`, which is gitignored.

## Wording

Model outputs and the report describe **statistical differences**, never wrongdoing. Don't write "fraud," "waste," "suspicious," or similar about a specific award. The assistant's guards enforce this for generated text; reviewers enforce it everywhere else.

## Tracking work

Open work is tracked as [GitHub issues](https://github.com/EMoon-03/GovSpend-AI/issues), one per chunk of `PLAN.md`, each with a checklist. Labels:

- `data`, `modeling`, `assistant`, `shared` — the track that owns it
- `blocked` — waiting on the issue named in its "Depends on" line; remove the label when that closes
- `good first issue` — a quick way in for a new contributor

Assign yourself before starting, tick checklist items as you go, and write `Closes #<n>` in the PR that finishes an issue. When a PLAN item is done, check it in `PLAN.md` in the same PR.
