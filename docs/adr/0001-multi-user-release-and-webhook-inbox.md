# ADR 0001: Multi-user release model and durable webhook inbox

## Status

Accepted for the public OMIMIND release.

## Decision

OMIMIND is a multi-user application. Supabase Auth email/password sessions are
the only production identity source. Every request derives `owner_id` from the
verified Supabase `sub` claim; caller-supplied `uid` values are ignored or
rejected. `DEPLOYMENT_MODE=multi_user` is required.

Supabase Postgres is the durable application database and webhook inbox.
Qdrant stores transcript vectors with the authenticated owner ID in every
payload and every query applies an owner filter. SQLite remains a local
development adapter only. Vercel `/tmp` is never used for webhook data.

The Omi account is linked to a Supabase account through a one-time pairing
flow. Connection tokens are hashed at rest, scoped to one owner, and can be
rotated or revoked. Webhooks require a configured signature/secret and a fresh
timestamp. Event IDs, payload hashes, leases, retries, and retention are
handled by shared durable storage.

The meeting pipeline exposes the configured Lyzr roles (memory recall, meeting
analyst, action extractor, manager, and follow-up planner) as persisted events
and SSE updates. Provider failures remain visible and deterministic output is
labelled as fallback. Lyzr credentials and agent IDs are deployment secrets;
they are never accepted in the browser.

## Consequences

- Anonymous visitors can understand the product and sample workflow.
- Authenticated users receive isolated meetings, memories, actions, Omi
  connections, and agent traces.
- Account deletion removes the user's Postgres rows, webhook records, Omi
  mappings, run history, and Qdrant points.
- Public deployments fail startup when Supabase, Postgres, Qdrant, Lyzr, or
  Omi signing configuration is missing.
- Full enterprise account features such as SSO and organization billing remain
  future work; the current release still has real per-user isolation.
