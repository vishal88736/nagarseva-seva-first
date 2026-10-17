"""Contract, persistence and outage tests for external forecasts; no live requests."""
import asyncio
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo

import httpx
import pytest

from model.api import main
from model.api.store import RecordStore
from model.src.public_context import ForecastService, normalize_forecast


def provider_response(now):
    today = now.astimezone(ZoneInfo("Asia/Kolkata")).date()
    return {"latitude": 19.1, "longitude": 72.9, "daily_units": {"precipitation_sum": "mm", "precipitation_probability_max": "%", "temperature_2m_max": "°C"},
            "daily": {"time": [(today + timedelta(days=i)).isoformat() for i in range(7)], "precipitation_sum": [None, 0, 10, 20, 0, 2, 4], "precipitation_probability_max": [None, 0, 30, 70, 0, 10, 20], "temperature_2m_max": [None, 30, 32, 35, 29, 28, 30]}}


def test_forecast_cache_persists_and_sends_only_area_coordinates(tmp_path, monkeypatch):
    service, store = ForecastService(), RecordStore(tmp_path / "weather.sqlite3")
    now = datetime(2026, 10, 11, 8, tzinfo=timezone.utc)
    calls = []
    async def fetch(lat, lon):
        calls.append((lat, lon))
        return provider_response(now)
    monkeypatch.setattr(service, "fetch", fetch)
    async def exercise():
        live = await service.get(19.076, 72.8777, store, now=now)
        assert live["status"] == "live" and live["synthetic"] is False
        assert live["days"][0]["precipitation_mm"] is None
        assert live["licence"] == "CC BY 4.0" and live["fetched_at"] == now.isoformat()
        # A fresh service/store instance must retain the cache across API restarts.
        restarted = ForecastService()
        async def forbidden(*args):
            raise AssertionError("A valid cache must avoid another network request")
        monkeypatch.setattr(restarted, "fetch", forbidden)
        cached = await restarted.get(19.081, 72.87, RecordStore(store.path), now=now + timedelta(minutes=15))
        assert cached["status"] == "cached" and cached["cache_age_seconds"] == 900
        assert calls == [(19.1, 72.9)]
    asyncio.run(exercise())


def test_forecast_outage_staleness_backoff_and_disabled(tmp_path, monkeypatch):
    service, store = ForecastService(), RecordStore(tmp_path / "weather.sqlite3")
    now = datetime(2026, 10, 11, 8, tzinfo=timezone.utc)
    calls = []
    async def fetch(*args):
        calls.append(args)
        if len(calls) > 1:
            raise httpx.ConnectError("Provider offline")
        return provider_response(now)
    monkeypatch.setattr(service, "fetch", fetch)
    async def exercise():
        await service.get(19.08, 72.88, store, now=now)
        stale = await service.get(19.08, 72.88, store, now=now + timedelta(hours=1))
        assert stale["status"] == "stale" and stale["fetched_at"] == now.isoformat()
        await service.get(19.08, 72.88, store, now=now + timedelta(hours=1, seconds=10))
        assert len(calls) == 2  # Failed provider refreshes are backed off.
        outdated = await service.get(19.08, 72.88, store, now=now + timedelta(hours=25))
        assert outdated["status"] == "unavailable" and outdated["days"] == []
        disabled = await service.get(19.08, 72.88, store, enabled=False, now=now)
        assert disabled["status"] == "disabled" and len(calls) == 3
    asyncio.run(exercise())


@pytest.mark.parametrize("problem", ["unit", "length", "date", "range", "nan"])
def test_provider_contract_rejects_invalid_data(problem):
    now = datetime(2026, 10, 11, 8, tzinfo=timezone.utc)
    data = provider_response(now)
    if problem == "unit": data["daily_units"]["temperature_2m_max"] = "°F"
    if problem == "length": data["daily"]["precipitation_sum"] = [0]
    if problem == "date": data["daily"]["time"][0] = "2020-01-01"
    if problem == "range": data["daily"]["precipitation_probability_max"][0] = 101
    if problem == "nan": data["daily"]["precipitation_sum"][0] = float("nan")
    with pytest.raises(ValueError): normalize_forecast(data, now)


def test_source_and_weather_api_do_not_create_field_evidence(api_store, monkeypatch):
    async def fetch(lat, lon):
        return provider_response(datetime.now(timezone.utc))
    monkeypatch.setattr(main.FORECAST, "fetch", fetch)
    async def exercise():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=main.app), base_url="http://test") as client:
            catalog = (await client.get("/sources")).json()
            census = next(source for source in catalog["sources"] if source["id"] == "census")
            assert census["reuse"] == "permission_required" and census["integration"] == "dataset_reference"
            before = (await client.get("/pilot/evidence")).json()["metrics"]
            weather = (await client.get("/context/NS-0001/weather")).json()
            assert weather["status"] == "live" and weather["location_synthetic"] is True
            assert weather["days"] and not weather["synthetic"]
            assert (await client.get("/context/missing/weather")).status_code == 404
            monkeypatch.setenv("NAGARSEVA_WEATHER_ENABLED", "0")
            assert (await client.get("/context/NS-0001/weather")).json()["status"] == "disabled"
            assert (await client.get("/pilot/evidence")).json()["metrics"] == before
            assert api_store.observations() == []
    asyncio.run(exercise())
