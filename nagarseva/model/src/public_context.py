"""Public weather context. No resident data, alerts or field measurements are inferred."""
from __future__ import annotations

import asyncio
from datetime import date, datetime, timedelta, timezone
import math
from zoneinfo import ZoneInfo

import httpx


DAILY = {"precipitation_sum": ("mm", "precipitation_mm", 0, 2000),
         "precipitation_probability_max": ("%", "precipitation_probability_pct", 0, 100),
         "temperature_2m_max": ("°C", "max_temperature_c", -90, 70)}
SOURCE = {"provider": "Open-Meteo", "source_url": "https://open-meteo.com/en/docs",
          "licence": "CC BY 4.0", "licence_url": "https://creativecommons.org/licenses/by/4.0/",
          "terms_url": "https://open-meteo.com/en/terms", "synthetic": False,
          "timezone": "Asia/Kolkata", "coordinate_scope": "Area coordinates rounded to 0.1 degrees; no household coordinates are sent."}


def normalize_forecast(payload: dict, now: datetime) -> dict:
    """Reject changed units/malformed responses instead of presenting false measurements."""
    today = now.astimezone(ZoneInfo("Asia/Kolkata")).date()
    daily, units = payload["daily"], payload["daily_units"]
    times = daily["time"]
    if len(times) != 7 or len(set(times)) != 7:
        raise ValueError("Expected seven distinct forecast days")
    dates = [date.fromisoformat(value) for value in times]
    if dates != [today + timedelta(days=i) for i in range(7)]:
        raise ValueError("Forecast does not cover the current seven days")
    days = [{"date": value} for value in times]
    for field, (unit, output, minimum, maximum) in DAILY.items():
        if units.get(field) != unit or len(daily[field]) != len(times):
            raise ValueError("Unexpected weather units or array lengths")
        for day, value in zip(days, daily[field]):
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not minimum <= value <= maximum):
                raise ValueError("Invalid weather value")
            day[output] = value
    lat, lon = payload["latitude"], payload["longitude"]
    if not all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v) for v in [lat, lon]) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("Invalid forecast grid coordinates")
    return {"days": days, "grid_coordinates": {"lat": lat, "lon": lon}, "fetched_at": now.isoformat()}


class ForecastService:
    def __init__(self):
        self._lock: asyncio.Lock | None = None
        self._loop = None

    async def fetch(self, lat: float, lon: float) -> dict:
        async with httpx.AsyncClient(timeout=6, follow_redirects=False, headers={"User-Agent": "NagarSeva/0.3 educational housing planning demo"}) as client:
            response = await client.get("https://api.open-meteo.com/v1/forecast", params={
                "latitude": lat, "longitude": lon, "daily": ",".join(DAILY), "timezone": "Asia/Kolkata", "forecast_days": 7})
            response.raise_for_status()
            return response.json()

    async def get(self, lat: float, lon: float, store, enabled: bool = True, now: datetime | None = None) -> dict:
        if not enabled:
            return {**SOURCE, "status": "disabled", "days": [], "fetched_at": None, "cache_age_seconds": None}
        # A coarse grid shares one result across nearby pockets and avoids disclosing exact locations.
        lat, lon = round(lat, 1), round(lon, 1)
        key = f"weather:v1:{lat:.1f}:{lon:.1f}"
        loop = asyncio.get_running_loop()
        if self._loop is not loop:
            self._lock, self._loop = asyncio.Lock(), loop
        async with self._lock:
            clock = now or datetime.now(timezone.utc)
            cached = store.cached_public_data(key) or {}
            saved = cached.get("forecast")
            age = (clock - datetime.fromisoformat(saved["fetched_at"])).total_seconds() if saved else None
            attempted = cached.get("attempted_at")
            since_attempt = (clock - datetime.fromisoformat(attempted)).total_seconds() if attempted else None
            status = "cached"
            if age is None or age >= 1800 or age < 0:
                if since_attempt is None or since_attempt >= 60 or since_attempt < 0:
                    try:
                        saved = normalize_forecast(await self.fetch(lat, lon), clock)
                        age, status = 0, "live"
                        store.cache_public_data(key, {"forecast": saved, "attempted_at": clock.isoformat()})
                    except (httpx.HTTPError, ValueError, TypeError, KeyError):
                        store.cache_public_data(key, {"forecast": saved, "attempted_at": clock.isoformat()})
                        status = "stale"
                else:
                    status = "stale"
            if not saved or age is None or age < 0 or age > 86400:
                return {**SOURCE, "status": "unavailable", "days": [], "fetched_at": None, "cache_age_seconds": None,
                        "requested_coordinates": {"lat": lat, "lon": lon}}
            today = clock.astimezone(ZoneInfo("Asia/Kolkata")).date().isoformat()
            return {**SOURCE, **saved, "days": [day for day in saved["days"] if day["date"] >= today], "status": status,
                    "requested_coordinates": {"lat": lat, "lon": lon}, "cache_age_seconds": round(age)}
