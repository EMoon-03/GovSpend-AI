# GovSpend AI

## Federal Contract Spending Analysis

**Status: setup — repository scaffold and collector in place; first real data pull pending.**

GovSpend AI is a planned data-mining project for CS 513. The goal is to analyze federal contract awards, discover spending patterns, and rank unusual awards for human review.

## Research question

> Which contract awards look unusual compared with suitable peer awards, and what measurable characteristics help explain those differences?

An unusual award does not establish fraud, waste, or misconduct. Model outputs will describe statistical differences and provide context for review.

## Initial scope

- **Source:** [USAspending](https://www.usaspending.gov/) and its [API documentation](https://api.usaspending.gov/docs/).
- **Unit of analysis:** one prime contract award, using the values available when data is collected.
- **Starting cohort:** contracts associated with activity in FY2025, using NAICS prefix `5415` as an initial IT-related filter to validate during data exploration.
- **First collection:** approximately 100–300 records to learn the schema and check the ingestion process.
- **Class study:** a documented cohort or sampling design, expanding toward 5,000–10,000 records only if coverage and available time support it.

An award-level amount must be interpreted according to the source definition. A date filter does not automatically turn that amount into spending within the selected year.

## Planned methods

1. Data collection and source documentation.
2. Cleaning, duplicate handling, and exploratory analysis.
3. Features describing award size and peer-group differences.
4. A simple statistical baseline and Isolation Forest.
5. Review of ranked examples and sensitivity to modeling choices.
6. A reproducible report describing findings and limitations.

The stack is Python, Pandas, NumPy, scikit-learn, Matplotlib, and Jupyter.

## Getting started

```bash
python -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate
pip install -r requirements.txt
pip install -e .

python -m govspend.collect --max-records 200   # raw snapshot -> data/raw/<run_id>/
python -m govspend.flatten                     # flat table  -> data/processed/awards_<run_id>.csv
pytest                                         # offline checks: pagination, parsing, dedup
jupyter notebook notebooks/00_first_look.ipynb
```

Raw snapshots and processed tables stay local (gitignored). Each snapshot carries a `collection_notes.json` with the exact request, timestamps, and stop reason. Column definitions are in [docs/data_dictionary.md](docs/data_dictionary.md).

| Path | Purpose |
| --- | --- |
| `src/govspend/collect.py` | Pages through `spending_by_award` and saves untouched responses |
| `src/govspend/flatten.py` | Flattens a snapshot, parses amounts/dates, dedups on `generated_internal_id` |
| `notebooks/` | Exploration (`00_first_look.ipynb` first) |
| `tests/` | Network-free checks for collection and flattening |
| `docs/` | Data dictionary and study notes |
| `reports/` | Figures and the final report |

## Development roadmap

| Stage | Planned deliverable |
| --- | --- |
| Define | Research question, scope, and data dictionary |
| Collect | Small source snapshot and collection notes |
| Explore | Data-quality summary and 4–5 meaningful charts |
| Model | Statistical baseline and Isolation Forest ranking |
| Evaluate | Reviewed examples and ranking stability comparison |
| Present | Reproducible workflow, final report, and project demo |

See [PLAN.md](PLAN.md) for the detailed plan, weekly milestones, and completion checks. All implementation milestones are currently upcoming.

## Planned extensions

After the CS 513 study: SQL storage, a prediction/scoring API, an analyst dashboard, and automated data refreshes. Transaction-based features such as modification counts require a separate data collection step.

## Results

Results will be added after the experiments are completed. No model performance claims are available yet.
