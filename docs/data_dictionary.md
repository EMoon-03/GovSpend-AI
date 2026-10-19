# Data Dictionary (draft)

**Status:** draft from the API contract. Definitions marked _verify_ still need checking against real records and the [USAspending data dictionary](https://www.usaspending.gov/data-dictionary) before the study relies on them.

**Source:** `POST /api/v2/search/spending_by_award/` ([contract](https://github.com/fedspendingtransparency/usaspending-api/blob/master/usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md)), produced by `src/govspend/collect.py` and flattened by `src/govspend/flatten.py`.

**Unit:** one prime contract award (award types A–D), as of the snapshot's retrieval time.

| Column | API field | Type | Meaning | Missing / notes |
| --- | --- | --- | --- | --- |
| `internal_id` | `internal_id` | int | Database row ID used by the API | Not stable across releases — don't join on it |
| `generated_internal_id` | `generated_internal_id` | str | Stable award key, e.g. `CONT_AWD_…` | Primary key; duplicates dropped on this |
| `award_id` | `Award ID` | str | Human-readable PIID | Not guaranteed unique across agencies |
| `recipient_name` | `Recipient Name` | str | Recipient legal name | Name variants exist; prefer UEI for grouping |
| `recipient_uei` | `Recipient UEI` | str | Unique Entity ID (SAM.gov) | May be missing on older awards — _verify rate_ |
| `award_amount` | `Award Amount` | float, USD | _Verify:_ believed to be total obligated amount across the award's life at snapshot time — **not** FY2025 spending | Kept as NaN if unparseable; zero/negative inspected separately |
| `total_outlays` | `Total Outlays` | float, USD | Amount actually paid out | Often missing — _verify rate_ |
| `awarding_agency` | `Awarding Agency` | str | Top-tier awarding agency | Candidate peer dimension |
| `awarding_sub_agency` | `Awarding Sub Agency` | str | Sub-tier awarding agency | |
| `contract_award_type` | `Contract Award Type` | str | BPA call / purchase order / delivery order / definitive contract | |
| `start_date` | `Start Date` | date | _Verify:_ period of performance start | NaT if unparseable |
| `end_date` | `End Date` | date | _Verify:_ current period of performance end | |
| `base_obligation_date` | `Base Obligation Date` | date | Date of the base (first) obligation | |
| `last_modified_date` | `Last Modified Date` | date | Last update to the award record | Shows snapshot staleness |
| `naics_code` / `naics_description` | `NAICS` | str | Industry code and label | Split from a `{code, description}` object |
| `psc_code` / `psc_description` | `PSC` | str | Product/service code and label | Same split |
| `description` | `Description` | str | Free-text award description | Not used as a model feature yet |

## Filter semantics to confirm

- **Time period:** no `date_type` is sent, so FY2025 (2024-10-01 – 2025-09-30) selects awards with **transaction activity** in that window — an award started in 2019 with a 2025 modification is included.
- **NAICS `5415`:** a prefix — covers 541511 (custom programming), 541512 (systems design), 541513 (facilities management), 541519 (other computer services).
