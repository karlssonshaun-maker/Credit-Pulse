import os

os.environ.setdefault("ENV", "test")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("DATABASE_URL", "postgresql+asyncpg://creditpulse:creditpulse_dev_only@localhost:5432/creditpulse_test")
os.environ.setdefault("SYNC_DATABASE_URL", "postgresql+psycopg2://creditpulse:creditpulse_dev_only@localhost:5432/creditpulse_test")


import pytest


@pytest.fixture
def fake_redis(monkeypatch):
    store = {}

    async def fake_get(key):
        val = store.get(key)
        if val is None:
            return None
        import json
        try:
            return json.loads(val)
        except Exception:
            return val

    async def fake_set(key, value, ttl):
        import json
        store[key] = json.dumps(value, default=str)

    monkeypatch.setattr("creditpulse.integrations.base.cache_get", fake_get)
    monkeypatch.setattr("creditpulse.integrations.base.cache_set", fake_set)
    return store
