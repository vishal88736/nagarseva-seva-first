"""Validate authorised Kobo/ODK JSON exports; dry-run unless --apply is explicit."""
import argparse
import json
import os
import sys
from pathlib import Path
import httpx
from data_common import ROOT

sys.path.insert(0, str(ROOT / "nagarseva"))
from model.api.field_survey import FieldSurvey


def validate_records(rows):
    if not isinstance(rows, list) or len(rows) > 1000:
        raise ValueError("Expected a JSON list with at most 1000 survey records")
    records = [FieldSurvey.model_validate(r) for r in rows]
    identifiers = [r.survey_id for r in records]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError("Duplicate survey identifiers in input")
    return records


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("--api-base", default="http://127.0.0.1:8000")
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    if args.input.stat().st_size > 5_000_000:
        raise SystemExit("Survey input exceeds 5 MB")
    records = validate_records(json.loads(args.input.read_text()))
    if not args.apply:
        print(f"Validated {len(records)} records; dry run, no observations imported")
        return
    key = os.environ.get("NAGARSEVA_OFFICER_KEY")
    if not key:
        raise SystemExit("Set NAGARSEVA_OFFICER_KEY in the environment; never pass it in an argument")
    if not args.api_base.startswith("https://") and not args.api_base.startswith(("http://127.0.0.1:", "http://localhost:")):
        raise SystemExit("Use HTTPS for remote API imports")
    imported = duplicates = 0
    with httpx.Client(base_url=args.api_base, timeout=20, headers={"X-Officer-Key": key}) as client:
        # Validate all foreign keys before writing. Backend validates again transactionally.
        for record in records:
            client.get("/urban/data/settlements/" + record.settlement_id).raise_for_status()
        for record in records:
            response = client.post("/urban/data/surveys", json=record.model_dump(mode="json"))
            if response.status_code == 409:
                duplicates += 1
            else:
                response.raise_for_status(); imported += 1
    print(f"Imported {imported}; skipped {duplicates} already-present identifiers. Spot observations remain reported and unranked.")


if __name__ == "__main__":
    main()
