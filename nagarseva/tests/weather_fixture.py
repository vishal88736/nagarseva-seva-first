"""Synthetic browser fixture; never recorded as real weather or sent to a provider."""
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo


def weather_fixture(status="cached", pocket_id="NS-0001"):
    now = datetime.now(timezone.utc)
    today = now.astimezone(ZoneInfo("Asia/Kolkata")).date()
    return {"pocket_id": pocket_id, "provider": "Open-Meteo", "source_url": "https://open-meteo.com/en/docs", "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/", "terms_url": "https://open-meteo.com/en/terms", "synthetic": False,
            "location_synthetic": True, "timezone": "Asia/Kolkata", "coordinate_scope": "Synthetic browser fixture, never field evidence", "status": status,
            "fetched_at": (now - timedelta(hours=1) if status == "stale" else now).isoformat(), "cache_age_seconds": 3600 if status == "stale" else 0,
            "requested_coordinates": {"lat": 19.1, "lon": 72.9}, "grid_coordinates": {"lat": 19.08, "lon": 72.89},
            "days": [] if status == "unavailable" else [{"date": (today + timedelta(days=i)).isoformat(), "precipitation_mm": None if i == 1 else 123.4,
                     "precipitation_probability_pct": 99, "max_temperature_c": 35.5} for i in range(7)]}
