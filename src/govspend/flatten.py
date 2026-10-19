"""Turn a raw snapshot folder into one flat, typed table.

Usage (from the repo root):
  python -m govspend.flatten                 # newest snapshot in data/raw/
  python -m govspend.flatten data/raw/<run_id>

Writes data/processed/awards_<run_id>.csv.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"
PROCESSED_DIR = REPO_ROOT / "data" / "processed"

# API field name -> snake_case column
COLUMN_MAP = {
    "internal_id": "internal_id",
    "generated_internal_id": "generated_internal_id",
    "Award ID": "award_id",
    "Recipient Name": "recipient_name",
    "Recipient UEI": "recipient_uei",
    "Award Amount": "award_amount",
    "Total Outlays": "total_outlays",
    "Awarding Agency": "awarding_agency",
    "Awarding Sub Agency": "awarding_sub_agency",
    "Contract Award Type": "contract_award_type",
    "Start Date": "start_date",
    "End Date": "end_date",
    "Base Obligation Date": "base_obligation_date",
    "Last Modified Date": "last_modified_date",
    "Description": "description",
}
DATE_COLS = ["start_date", "end_date", "base_obligation_date", "last_modified_date"]
AMOUNT_COLS = ["award_amount", "total_outlays"]


def split_code(value: Any) -> tuple[str | None, str | None]:
    """NAICS/PSC come back as {"code", "description"} or as a plain string."""
    if value is None:
        return None, None
    if isinstance(value, dict):
        return value.get("code"), value.get("description")
    return str(value), None


def latest_run(raw_dir: Path = RAW_DIR) -> Path:
    runs = sorted(d for d in raw_dir.iterdir() if (d / "collection_notes.json").exists())
    if not runs:
        raise FileNotFoundError(f"No snapshots in {raw_dir}. Run `python -m govspend.collect` first.")
    return runs[-1]


def load_records(run_dir: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for page_file in sorted(run_dir.glob("page_*.json")):
        records.extend(json.loads(page_file.read_text()).get("results", []))
    return records


def flatten(records: list[dict[str, Any]]) -> pd.DataFrame:
    """Flatten raw results; parse amounts/dates; drop exact duplicate awards."""
    rows = []
    for rec in records:
        row = {col: rec.get(api) for api, col in COLUMN_MAP.items()}
        row["naics_code"], row["naics_description"] = split_code(rec.get("NAICS"))
        row["psc_code"], row["psc_description"] = split_code(rec.get("PSC"))
        rows.append(row)

    df = pd.DataFrame(rows, columns=list(COLUMN_MAP.values()) + [
        "naics_code", "naics_description", "psc_code", "psc_description"])

    for col in AMOUNT_COLS:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    for col in DATE_COLS:
        df[col] = pd.to_datetime(df[col], errors="coerce")

    # Paging a sort that changes between requests can repeat an award across pages.
    # generated_internal_id is the stable source identifier.
    before = len(df)
    df = df.drop_duplicates(subset="generated_internal_id", keep="first").reset_index(drop=True)
    df.attrs["duplicates_dropped"] = before - len(df)
    return df


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("run_dir", nargs="?", type=Path, help="snapshot folder (default: newest)")
    args = p.parse_args(argv)

    run_dir = args.run_dir or latest_run()
    df = flatten(load_records(run_dir))
    PROCESSED_DIR.mkdir(parents=True, exist_ok=True)
    out = PROCESSED_DIR / f"awards_{run_dir.name}.csv"
    df.to_csv(out, index=False)
    print(f"{len(df)} awards -> {out} ({df.attrs['duplicates_dropped']} duplicates dropped)")


if __name__ == "__main__":
    main()
