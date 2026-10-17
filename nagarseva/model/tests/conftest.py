"""Isolate local operational records while exercising real API routes."""
import pytest
from model.api import main
from model.api.store import RecordStore


@pytest.fixture(scope="session", autouse=True)
def planning_data():
    main._load()


@pytest.fixture
def api_store(tmp_path, monkeypatch):
    store = RecordStore(tmp_path / "test.sqlite3")
    monkeypatch.setattr(main, "STORE", store)
    monkeypatch.delenv("NAGARSEVA_OFFICER_KEY", raising=False)
    monkeypatch.setenv("NAGARSEVA_MODE", "demo")
    return store
