from datetime import datetime, timedelta, timezone
from model.src.service_records import service_record


def test_unknown_and_stale_measurements_are_excluded_from_index():
    row = {"pocket_id": "p", "water_hours_per_day": None}
    assert service_record(row, [])["assurance_index"] is None
    now = datetime.now(timezone.utc)
    old = {"service": "water", "value": 8, "verification": "field_verified", "observed_at": (now - timedelta(days=31)).isoformat(), "created_at": now.isoformat(), "source_label": "Inspection log", "synthetic": False}
    record = service_record(row, [old], now)
    assert record["services"]["water"]["status"] == "stale"
    assert record["assurance_index"] is None
    assert record["field_verified_services"] == 0
