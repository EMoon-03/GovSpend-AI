"""Collect prime contract awards from the USAspending spending_by_award endpoint.

Every run writes to its own snapshot folder under data/raw/<run_id>/:
  page_001.json, page_002.json, ...   original API responses, untouched
  collection_notes.json               request body, limits, timestamps, stop reason

Usage (from the repo root):
  python -m govspend.collect --max-records 200
  python -m govspend.collect --max-records 200 --sort "Start Date" --order asc

API contract:
  https://github.com/fedspendingtransparency/usaspending-api/blob/master/
  usaspending_api/api_contracts/contracts/v2/search/spending_by_award.md
"""

from __future__ import annotations

import argparse
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import requests

API_URL = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
PAGE_LIMIT_MAX = 100  # the endpoint rejects larger page sizes

# Contract award types: A = BPA call, B = purchase order,
# C = delivery order, D = definitive contract.
CONTRACT_TYPE_CODES = ["A", "B", "C", "D"]

FIELDS = [
    "Award ID",
    "generated_internal_id",
    "Recipient Name",
    "Recipient UEI",
    "Award Amount",
    "Total Outlays",
    "Awarding Agency",
    "Awarding Sub Agency",
    "Contract Award Type",
    "Start Date",
    "End Date",
    "Base Obligation Date",
    "Last Modified Date",
    "NAICS",
    "PSC",
    "Description",
]

# FY2025 = Oct 1, 2024 through Sep 30, 2025.
DEFAULT_START = "2024-10-01"
DEFAULT_END = "2025-09-30"
DEFAULT_NAICS = ["5415"]

REPO_ROOT = Path(__file__).resolve().parents[2]
RAW_DIR = REPO_ROOT / "data" / "raw"


def build_request_body(
    *,
    page: int,
    limit: int,
    start_date: str = DEFAULT_START,
    end_date: str = DEFAULT_END,
    naics: list[str] | None = None,
    sort: str = "Award Amount",
    order: str = "desc",
) -> dict[str, Any]:
    """Build one spending_by_award request body.

    Note: with no date_type, time_period matches awards that had *activity*
    (transactions) in the window — not awards that started in it. Record this
    in the collection notes; see PLAN.md section 1.
    """
    if not 1 <= limit <= PAGE_LIMIT_MAX:
        raise ValueError(f"limit must be between 1 and {PAGE_LIMIT_MAX}")
    if sort not in FIELDS:
        raise ValueError(f"sort field {sort!r} must be one of the requested fields")
    return {
        "subawards": False,
        "page": page,
        "limit": limit,
        "sort": sort,
        "order": order,
        "filters": {
            "award_type_codes": CONTRACT_TYPE_CODES,
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            "naics_codes": {"require": list(naics if naics is not None else DEFAULT_NAICS)},
        },
        "fields": FIELDS,
    }


def post_with_retry(
    session: requests.Session,
    body: dict[str, Any],
    *,
    retries: int = 3,
    backoff: float = 2.0,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """POST a request, retrying on timeouts, 429s and 5xx errors."""
    for attempt in range(1, retries + 1):
        try:
            resp = session.post(API_URL, json=body, timeout=timeout)
        except (requests.Timeout, requests.ConnectionError):
            if attempt == retries:
                raise
        else:
            if resp.status_code == 200:
                return resp.json()
            retryable = resp.status_code == 429 or resp.status_code >= 500
            if not retryable or attempt == retries:
                raise RuntimeError(
                    f"USAspending returned HTTP {resp.status_code}: {resp.text[:500]}"
                )
        time.sleep(backoff * attempt)
    raise RuntimeError("unreachable")  # pragma: no cover


def collect(
    max_records: int,
    *,
    session: requests.Session | None = None,
    out_root: Path = RAW_DIR,
    start_date: str = DEFAULT_START,
    end_date: str = DEFAULT_END,
    naics: list[str] | None = None,
    sort: str = "Award Amount",
    order: str = "desc",
    pause: float = 0.5,
) -> Path:
    """Page through results until max_records or the last page; return the run folder."""
    session = session or requests.Session()
    started = datetime.now(timezone.utc)
    run_id = started.strftime("%Y%m%dT%H%M%SZ")
    run_dir = out_root / run_id
    run_dir.mkdir(parents=True, exist_ok=False)

    page = 1
    collected = 0
    pages: list[dict[str, Any]] = []
    stop_reason = ""

    while collected < max_records:
        limit = min(PAGE_LIMIT_MAX, max_records - collected)
        body = build_request_body(
            page=page, limit=limit, start_date=start_date, end_date=end_date,
            naics=naics, sort=sort, order=order,
        )
        data = post_with_retry(session, body)
        results = data.get("results", [])
        meta = data.get("page_metadata", {}) or {}

        page_file = run_dir / f"page_{page:03d}.json"
        page_file.write_text(json.dumps(data, indent=2))
        pages.append({"page": page, "limit": limit, "n_results": len(results),
                      "has_next": meta.get("hasNext"), "file": page_file.name,
                      "messages": data.get("messages", [])})
        collected += len(results)

        if not results:
            stop_reason = "empty page"
            break
        if not meta.get("hasNext"):
            stop_reason = "last page reached (hasNext = false)"
            break
        page += 1
        time.sleep(pause)
    else:
        stop_reason = f"record cap reached ({max_records})"

    notes = {
        "run_id": run_id,
        "source_url": API_URL,
        "retrieved_at_utc_start": started.isoformat(),
        "retrieved_at_utc_end": datetime.now(timezone.utc).isoformat(),
        "record_cap": max_records,
        "records_collected": collected,
        "stop_reason": stop_reason,
        "sort": sort,
        "order": order,
        "time_period_semantics": (
            "No date_type sent: the API matches awards with transaction activity "
            "in the window, not awards that started in it."
        ),
        "sampling_caveat": (
            "A capped list sorted by Award Amount over-represents large awards. "
            "This is a development sample, not a study cohort."
            if sort == "Award Amount" else ""
        ),
        "example_request_body": build_request_body(
            page=1, limit=min(PAGE_LIMIT_MAX, max_records), start_date=start_date,
            end_date=end_date, naics=naics, sort=sort, order=order,
        ),
        "pages": pages,
    }
    (run_dir / "collection_notes.json").write_text(json.dumps(notes, indent=2))
    return run_dir


def main(argv: list[str] | None = None) -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--max-records", type=int, default=200)
    p.add_argument("--start-date", default=DEFAULT_START)
    p.add_argument("--end-date", default=DEFAULT_END)
    p.add_argument("--naics", nargs="+", default=DEFAULT_NAICS,
                   help="NAICS codes or prefixes to require (default: 5415)")
    p.add_argument("--sort", default="Award Amount", choices=FIELDS)
    p.add_argument("--order", default="desc", choices=["asc", "desc"])
    args = p.parse_args(argv)

    run_dir = collect(
        args.max_records, start_date=args.start_date, end_date=args.end_date,
        naics=args.naics, sort=args.sort, order=args.order,
    )
    notes = json.loads((run_dir / "collection_notes.json").read_text())
    print(f"Saved {notes['records_collected']} records to {run_dir}")
    print(f"Stop reason: {notes['stop_reason']}")


if __name__ == "__main__":
    main()
