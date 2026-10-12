# OMIMIND multi-user release test matrix

This matrix describes the release gate for the public multi-user deployment. Local automated coverage is listed separately from checks that need configured staging services or a browser.

## Authentication and identity

| Scenario | Expected result | Coverage |
| --- | --- | --- |
| Supabase email/password login and session refresh | Verified access token maps to the Supabase `sub`; browser only receives the publishable key | Staging verification |
| Expired or forged session | Request is rejected | `tests/test_auth_session.py` |
| Missing application credentials | Protected route returns 401 | `tests/test_security_hardening.py` |
| Query-string credentials | Request returns 401 | `tests/test_security_hardening.py` |
| Caller-supplied `uid` in query or body | Does not select an identity | `tests/test_auth_session.py`, `tests/test_security_hardening.py` |
| Unsupported deployment mode | Startup validation fails | `tests/test_security_hardening.py` |

## Webhooks

| Scenario | Expected result | Coverage |
| --- | --- | --- |
| Valid shared-secret request with fresh timestamp | Event is claimed and processed | `tests/test_webhook_persistence.py`, `tests/test_api_endpoints.py` |
| Signed request | HMAC covers timestamp and exact raw body | `tests/test_webhook_persistence.py` |
| Missing, malformed, expired, or future timestamp | Request is rejected | `tests/test_security_hardening.py`, `tests/test_webhook_persistence.py` |
| Missing credentials, including Omi mobile endpoints | Request is rejected | `tests/test_security_hardening.py` |
| Invalid signature or changed signed body/timestamp | Request is rejected | `tests/test_webhook_persistence.py` |
| Completed event replay | Duplicate is not processed twice | `tests/test_webhook_persistence.py` |
| Same event ID with changed payload | Request is rejected with conflict | `tests/test_webhook_persistence.py` |
| Failed event or stale processing lease | Retry is allowed and attempt count increments | `tests/test_webhook_persistence.py` |
| App restart or two instances sharing Postgres | Completed event is recognized; only one concurrent claim succeeds | `tests/test_webhook_persistence.py`; Postgres integration in `tests/test_postgres_webhook_store.py` |
| Missing production Postgres URL | Startup fails with a configuration error | `tests/test_security_hardening.py` |
| Retention | Completed/failed records expire after 72 hours during inbox activity | `tests/test_webhook_persistence.py` |

## Memory, pipeline, and product experience

| Scenario | Expected result | Coverage |
| --- | --- | --- |
| Memory reads, search, and deletion | Operations use the one configured identity; caller identity values do not widen scope | `tests/test_api_endpoints.py`, `tests/test_security_hardening.py` |
| Sample meeting and custom transcript | Pipeline produces a dossier and indexes the expected utterances | `tests/test_api_endpoints.py`, pipeline tests |
| Lyzr success and unavailable provider | Result identifies cloud reasoning or deterministic fallback | `tests/test_lyzr_client.py`, `tests/test_live_lyzr_manager.py` |
| Qdrant unavailable | User receives a clear processing failure or fallback where supported | `tests/test_memory_agent.py`, staging check |
| SSE disconnect and retry | No false completion is shown; reconnect behavior is documented and verified in staging | Staging check |
| Demo telemetry and architecture illustration | Static values are labeled illustrative; no live wearable state is implied | Manual browser review |
| Follow-up actions | Email, Jira, and calendar outputs remain drafts until user action | Manual browser review |
| First-run meeting workflow | Evaluator can choose a sample, process it, and review evidence and outputs | Manual browser review |

## Staging-only release gate

Before deployment, run the webhook integration test against the configured shared Postgres service (`WEBHOOK_TEST_DATABASE_URL`), then exercise one valid webhook and one duplicate against two separate application instances. Verify the same payload after a process restart, and confirm production startup fails when `WEBHOOK_DATABASE_URL` is removed. Review the first-run workflow and simulated-data labels in a browser with the production-like configuration.
