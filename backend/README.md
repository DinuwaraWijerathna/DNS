# BDNS Backend

FastAPI backend for the Blockchain-Backed DNS MVP.

## Run locally

Start the project with a single command (from the repository root):

`./backend/.venv/bin/uvicorn app.main:app --reload --app-dir ./backend`

Then open:
- API: `http://127.0.0.1:8000`
- Dashboard: `http://127.0.0.1:8000/dashboard`

## Test

- `pytest`

## Phase 2 Domain APIs

- `POST /api/v1/domains/register`
- `PUT /api/v1/domains/{domain}/ip`
- `POST /api/v1/domains/{domain}/transfer`
- `GET /api/v1/domains/{domain}`
- `GET /api/v1/domains/{domain}/history`

Signatures are ECDSA (NIST256p) over canonical JSON:
`{"tx_type":"...","domain":"...","payload":{...}}`

## Phase 3 Resolver APIs

- `GET /api/v1/resolver/{domain}`
- `GET /api/v1/resolver/metrics/summary`
- `GET /api/v1/resolver/logs/recent?limit=50`

Resolver uses Redis caching (with in-memory fallback if Redis is unavailable),
TTL-based cache entries, and exposes query latency/cache-hit metrics.

## Phase 4 Management UI

- Route: `GET /dashboard`
- Static assets: `/ui/assets/*`
- Includes:
  - register/update/transfer flows
  - resolve + lookup + audit views
  - resolver metrics cards and query logs access
  - built-in signing helper for demo key generation + auto-sign

## Signing Helper APIs

- `POST /api/v1/crypto/keypair`
- `POST /api/v1/crypto/sign`
