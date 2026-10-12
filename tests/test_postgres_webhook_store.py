"""Optional integration tests for shared Postgres webhook claims.

Set WEBHOOK_TEST_DATABASE_URL to run these against a disposable Postgres database.
"""
from __future__ import annotations

import os
import uuid
from concurrent.futures import ThreadPoolExecutor

import pytest

DATABASE_URL = os.environ.get("WEBHOOK_TEST_DATABASE_URL")
OWNER_ID = os.environ.get("WEBHOOK_TEST_OWNER_ID")
pytestmark = pytest.mark.skipif(
    not DATABASE_URL or not OWNER_ID,
    reason="WEBHOOK_TEST_DATABASE_URL and WEBHOOK_TEST_OWNER_ID are required",
)


def test_independent_stores_atomically_claim_one_shared_event():
    pytest.importorskip("psycopg")
    from backend.stores.postgres_webhook_store import PostgresWebhookStore

    store_a = PostgresWebhookStore(DATABASE_URL)
    store_b = PostgresWebhookStore(DATABASE_URL)
    event_id = f"cross-instance-{uuid.uuid4().hex}"
    args = {
        "event_id": event_id,
        "payload_hash": "stable-payload-hash",
        "uid": OWNER_ID,
        "session_id": "cross-instance-session",
        "payload": {"transcript": "test"},
    }
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(lambda pair: pair[0].record_incoming_event(**args)[0],
                                     [(store_a,), (store_b,)]))
        assert sorted(outcomes) == [False, True]
    finally:
        store_a.clear_event(f"{args['uid']}:{event_id}")
