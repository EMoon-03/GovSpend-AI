# GovSpend AI — Plan from Scratch

**Starting point:** an empty repository. All tasks below are upcoming.

**Project goal:** build a CS 513 data-mining study that identifies and explains unusual federal contract awards relative to suitable peers.

**First finish line:** a reproducible collection and analysis workflow, exploratory charts, a simple comparison baseline, an Isolation Forest ranking, and a report grounded in reviewed examples.

## 1. Define the study

Write a one-page project proposal before implementing a model.

- [ ] State the question: “Which awards are unusual relative to comparable awards, and what measurable differences support that ranking?”
- [ ] Check the CS 513 project rubric and align the required techniques and deliverables.
- [ ] Use one prime contract award as the initial unit of analysis.
- [ ] Start with FY2025: October 1, 2024 through September 30, 2025.
- [ ] Validate NAICS prefix `5415` as a manageable starting filter for the chosen IT-related scope.
- [ ] Explain whether the source filter selects awards by transaction activity, start date, or another definition.
- [ ] Document that downloaded award values describe the available snapshot. Do not present current totals as historical values known at an earlier date.

**Done when:** the research question, cohort, unit of analysis, and source definitions fit on one page.

## 2. Set up the repository and environment

Create a GitHub repository named `govspend-ai` and add `README.md` and this `PLAN.md`. Keep the README status at “planning” until working code is added.

| Path | Purpose |
| --- | --- |
| `README.md` | Project overview, current status, and eventual run instructions |
| `PLAN.md` | Roadmap and completion checks |
| `data/raw/` | Original downloaded snapshots, excluded from Git |
| `data/processed/` | Cleaned records and derived features, excluded from Git |
| `notebooks/` | Exploration and experiments |
| `src/` | Reusable collection and analysis code as it develops |
| `reports/` | Figures, experiment summaries, and the final report |
| `.gitignore` | Exclude the virtual environment, caches, local data, and credentials |
| `requirements.txt` | Record the packages used once the environment is working |

Start with Python, Pandas, NumPy, Matplotlib, Jupyter, requests, and scikit-learn. Create a project-specific virtual environment. On Windows it uses `.venv/Scripts/`; on Linux/macOS it uses `.venv/bin/`.

- [x] Create the repository and folders.
- [ ] Create the virtual environment and confirm a notebook runs.
- [x] Make the first commit with the project documents and `.gitignore`.

**Done when:** the repository is organized and a notebook can import Pandas. A model is not required for this milestone.

## 3. Collect a small dataset

Use the [official USAspending API documentation](https://api.usaspending.gov/docs/) and the [spending-by-award contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md) to implement the first request.

Begin with approximately **100–300 records**. This is a development sample; describe the request order and limits when exploring it.

| Field to investigate | Why it matters |
| --- | --- |
| Generated internal award identifier | Deduplication and source traceability |
| Display award ID | Human-readable reference |
| Recipient name and UEI, when supplied | Recipient identification and grouping |
| Award amount | Size comparisons; verify its precise source meaning |
| Awarding agency | Peer comparisons |
| Start date | Descriptive timing; verify what the date represents |
| NAICS and PSC | Industry and product/service context |

- [ ] Save the original response before transforming it.
- [ ] Save the request filters, sort order, record cap, retrieval timestamp, and source URL in collection notes.
- [ ] Flatten nested fields into a readable table.
- [ ] Write a data dictionary with definitions, units, missing-value handling, and source references.
- [ ] Check several downloaded records against their source entries.

**Done when:** a notebook loads the data and you can explain every retained column.

## 4. Build a defensible study dataset

The first API request is a smoke test. For the class analysis, define a collection method whose limitations can be explained.

- [ ] Prefer a narrow cohort that can be retrieved completely within the project budget.
- [ ] If sampling is needed, specify the sampling frame and selection process. A capped list sorted by amount overrepresents large awards.
- [ ] Retrieve all required pages or document exactly where collection stopped.
- [ ] Deduplicate with the source's stable award identifier.
- [ ] Use recipient UEI where available; document how missing identifiers and name variants are handled.
- [ ] Audit missing values, invalid dates, duplicated IDs, and inconsistent categories.
- [ ] Inspect zero and negative amounts before deciding how to model them. Record any exclusion and its effect on coverage.
- [ ] Summarize coverage by agency and NAICS code.

**Target scale:** 5,000–10,000 records is a possible class scope, not a requirement. A smaller complete cohort with well-supported peer groups can be sufficient.

**Done when:** collection can be reproduced and every exclusion has a documented reason.

## 5. Explore the data

Create `notebooks/01_exploration.ipynb` and produce four or five useful figures.

- [ ] Award amount distribution, using a suitable log view for positive values.
- [ ] Counts and amount distributions by agency.
- [ ] Counts and amount distributions by NAICS code.
- [ ] Recipient concentration within the collected cohort.
- [ ] A missing-data or coverage chart.

Write a few sentences beneath each chart: what it shows, which records it represents, and any limitation that changes interpretation. Distinguish counts of awards from dollar amounts.

**Done when:** you can describe the dataset without referring to a machine-learning result.

## 6. Build the first comparison and model

### Statistical baseline

Construct simple comparisons such as award amount relative to a peer-group median or a robust deviation measure. Start with agency and NAICS as candidate peer dimensions. Examine whether those peers are actually comparable in contract purpose and size.

- [ ] Define a minimum peer-group size before analyzing results; test a starting value such as 20.
- [ ] Use a documented broader-group fallback or leave a comparison unavailable when a group is too small.
- [ ] Record peer-group size alongside each comparison.
- [ ] Keep descriptive notes factual, such as “3.2 times the median of 42 awards in this group.”

### Isolation Forest

Start with a small, documented feature set, such as transformed award amount and peer-size differences. Treat recipient frequency as frequency in the collected cohort. Add features only when their meaning can be explained.

- [ ] Record preprocessing decisions, feature definitions, parameters, package versions, and the random seed.
- [ ] Produce a ranked table with raw values, source IDs, comparison context, and anomaly scores.
- [ ] Compare its top results with the statistical baseline.
- [ ] Keep review percentiles clearly labeled as relative rankings, not probabilities of wrongdoing.

**Done when:** you can trace each result back to a source record and explain the inputs used to rank it.

## 7. Evaluate and explain the results

The initial task is exploratory ranking of a snapshot. It does not measure future prediction performance. Trustworthy outcome labels would be required for claims such as fraud-detection accuracy.

- [ ] Review a manageable set, such as the top 20 awards, plus several middle-ranked and randomly chosen awards.
- [ ] Record whether each apparent difference has an ordinary explanation, reflects a data-quality issue, or remains unresolved.
- [ ] Compare overlap among the top results across several random seeds and reasonable parameter settings.
- [ ] Check sensitivity to feature choices, peer-group sizes, and the sample definition.
- [ ] Document cases where the statistical baseline and Isolation Forest disagree.
- [ ] Optionally compare Local Outlier Factor after the first two methods are understood.

Useful evidence includes ranking overlap, documented review findings, runtime, and examples of model limitations. A small manual review supports discussion of those reviewed cases; it does not establish population-wide performance.

If the project later scores new awards, separate training and evaluation data and construct features using only information available at the scoring time.

**Done when:** the report contains evidence about usefulness and stability, including examples the model handles poorly.

## 8. Finish the CS 513 deliverable

- [ ] Move repeated notebook steps into small reusable functions.
- [ ] Document a repeatable sequence from a saved source snapshot to the final outputs.
- [ ] Add focused checks for consequential behavior such as pagination, duplicate handling, and amount parsing.
- [ ] Write the report: question, data, methods, results, limitations, and next steps.
- [ ] Prepare a short demonstration of collection, charts, rankings, and source inspection.
- [ ] Update the README with implemented features, actual commands, figures, and measured results.

**Done when:** someone following the instructions can reproduce the analysis using the same documented input snapshot.

## Suggested six-week schedule

This is a proposed pace of roughly 4–6 focused hours per week; adjust it to the class deadline and rubric.

| Week | Focus | Deliverable |
| --- | --- | --- |
| 1 | Scope, repository, first collection | Proposal, data dictionary draft, 100–300 records |
| 2 | Collection method and cleaning | Documented study dataset and quality summary |
| 3 | Exploration | Notebook with 4–5 charts and observations |
| 4 | Statistical baseline and Isolation Forest | Reproducible ranked outputs |
| 5 | Review and sensitivity analysis | Comparison table and reviewed examples |
| 6 | Report and reproducibility | Final report, updated README, and demo |

## Portfolio upgrades after the class study

| Order | Upgrade | Completion check |
| --- | --- | --- |
| 1 | PostgreSQL storage | Re-running ingestion does not duplicate records; source snapshots remain traceable |
| 2 | FastAPI scoring and retrieval endpoints | Inputs are validated and output definitions are documented |
| 3 | Analyst dashboard | Users can filter awards, inspect comparisons, and open source records |
| 4 | Docker and continuous integration | The project runs from documented commands and key checks run automatically |
| 5 | Scheduled refresh and experiment tracking | Data and model versions can be traced to a specific run |

Add transaction history before attempting modification counts or historical recipient trends. Consider distributed processing only after measuring a workload that justifies it. Any later document retrieval or language-model feature should use source-grounded evidence and have its own evaluation.

## First session

1. Create `govspend-ai` and add these two Markdown files.
2. Write the one-page scope and confirm the class requirements.
3. Set up Python and a notebook.
4. Retrieve a small response and inspect five records.

**First milestone: a notebook that loads a small federal contract dataset and explains its columns.**
