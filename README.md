# BDNS — Blockchain-Based Domain Name System

> A proof-of-concept, blockchain-backed DNS platform built for the PUSL3190 Computing Project (BSc Honours Computer Security, University of Plymouth). BDNS replaces the centralised trust model of conventional DNS with a Proof-of-Authority blockchain ledger, ECDSA-based ownership verification, and structured attack simulation — wrapped in a full multi-user platform with accounts, subscription billing, and administration.

---

## Table of Contents

- [Overview](#overview)
- [Key Features](#key-features)
- [Architecture](#architecture)
- [Tech Stack](#tech-stack)
- [Project Structure](#project-structure)
- [Getting Started](#getting-started)
  - [Requirements](#requirements)
  - [Environment Variables](#environment-variables)
  - [Run with Docker Compose (recommended)](#run-with-docker-compose-recommended)
  - [Run Manually](#run-manually)
- [Accessing the Application](#accessing-the-application)
- [API Overview](#api-overview)
- [Security Simulations](#security-simulations)
- [Testing](#testing)
- [Known Limitations](#known-limitations)
- [Roadmap / Future Work](#roadmap--future-work)
- [License](#license)
- [Acknowledgements](#acknowledgements)

---

## Overview

Traditional DNS is centralised, unauthenticated by default, and vulnerable to spoofing and cache-poisoning attacks. DNSSEC only partially fixes this while keeping a centralised chain of trust. **BDNS** demonstrates an alternative: domain records are stored as transactions on a custom, permissioned blockchain, every mutation (register / update / transfer / freeze) requires a valid **ECDSA (NIST P-256)** signature from the owning key, and a **Proof-of-Authority (PoA)** consensus mechanism controls who may commit new blocks.

On top of that security core, BDNS is built out as a realistic multi-user product so the security model can be evaluated under real conditions rather than in isolation:

- Customer and administrator accounts with JWT-based authentication
- Tiered subscription plans billed through PayPal, with server-enforced domain quotas
- An administrative console for user management, domain moderation, auditing and support
- Live, WebSocket-driven propagation of ledger events to connected clients

The blockchain ledger (a JSON file) remains the single **authoritative source of truth** for domain ownership throughout. Everything else — Postgres, Redis, PayPal — supports or accelerates the platform around it.

---

## Key Features

### Core blockchain DNS
- Custom SHA-256-linked blockchain (`Block`, `Transaction`, `Ledger`)
- Proof-of-Authority consensus with deterministic, round-robin validator selection
- ECDSA (NIST P-256) signing and verification for every domain mutation
- Full, tamper-evident audit history per domain
- Redis-backed resolver cache with cache-first lookup and automatic invalidation on mutation
- Global public-DNS availability check (via `dnspython`) before registration
- Built-in **DNS spoofing** and **cache-poisoning** attack simulation endpoints

### Platform / product layer
- Email + password authentication (bcrypt-hashed credentials, JWT sessions)
- Role-based access control (`customer` / `admin`), enforced centrally via FastAPI dependencies
- Subscription plans (Individual / Small Business / Business / Enterprise) with server-defined pricing and domain quotas
- PayPal REST API integration (create-order / capture-order flow)
- Administrative console: user management, domain freeze/unfreeze, global audit trail, activity log, platform statistics, payments overview
- Customer support ticketing (create, reply, status tracking)
- WebSocket channel broadcasting live ledger updates to connected clients
- Supabase (PostgreSQL) mirror of users, domains, ledger blocks, audit logs, tickets and payments — for fast, indexed queries by the admin console

### Frontend
- Two static, multi-page portals — **Customer** and **Admin** — built with plain HTML/CSS/JS (no build step required)
- Shared client-side module (`shared.js` / `shared.css`) handling navigation, auth-token storage, API calls and WebSocket updates

---

## Architecture

```
 Customer Portal        Admin Portal
 (HTML/CSS/JS)          (HTML/CSS/JS)
        \                   /
         \                 /
          FastAPI API Layer  (/api/v1 : auth, domains, resolver, signing,
                               security, chain, admin, users, tickets,
                               payments, ws)
                 |
   ---------------------------------------------
   |            |               |               |
 Auth &      Domain          Resolver        (cross-cutting)
 Security    Service         Service         Signature / PayPal /
 (JWT+bcrypt) (register/     (cache-first     Support Ticket services
              update/        lookup)
              transfer/
              freeze)
                 |               |
          Blockchain Layer   WebSocket Manager
          (Ledger + PoA)     (live broadcast)
                 |               |
     -----------------------------------------------
     |                |                            |
 JSON Ledger File   Redis Cache            Supabase (PostgreSQL)
 (authoritative)    (resolver TTL)         users / domains mirror /
                                            ledger_blocks / audit_logs /
                                            tickets / payments
                                                     |
                                             PayPal REST API (external)
```

The blockchain ledger (JSON file) is the only authoritative store for domain ownership. Supabase is a **read-optimised mirror** used by the admin console and reporting endpoints; it is not consulted to determine domain ownership.

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | [FastAPI](https://fastapi.tiangolo.com/) + Pydantic (validation, OpenAPI docs) |
| Blockchain / consensus | Custom Python implementation (SHA-256 linking, Proof-of-Authority) |
| Cryptography | `ecdsa` (NIST P-256 / secp256r1) |
| Auth | `PyJWT` (JWT sessions) + `bcrypt` (password hashing) |
| Cache | Redis |
| Database | Supabase (managed PostgreSQL) |
| Payments | PayPal REST API (Orders v2, sandbox/live) |
| DNS lookups | `dnspython` (global availability checks) |
| Real-time | Native FastAPI/Starlette WebSockets |
| Frontend | Static HTML, CSS, vanilla JavaScript (no framework/build step) |
| Containerisation | Docker & Docker Compose |
| Testing | `pytest`, `httpx`, FastAPI `TestClient` |

---

## Project Structure

```
DNS-main/
├── backend/
│   ├── app/
│   │   ├── api/routes/       # admin, chain, domains, health, payments,
│   │   │                     # resolver, security, signing, tickets, users, ws
│   │   ├── blockchain/       # Block, Transaction, Ledger, PoA consensus
│   │   ├── cache/            # Redis cache client
│   │   ├── core/             # config, security (JWT/RBAC), plans, ws_manager
│   │   ├── crypto/           # ECDSA signature service
│   │   ├── models/           # Pydantic schemas
│   │   ├── resolver/         # resolver service, global DNS adapter
│   │   ├── services/         # domain_service, auth_service, paypal_service, ...
│   │   └── main.py
│   ├── data/                 # persisted ledger.json (Docker volume)
│   ├── tests/                # pytest unit + integration tests
│   ├── requirements.txt / pyproject.toml
│   └── Dockerfile
├── frontend/
│   ├── customer/              # customer portal pages
│   ├── admin/                 # admin portal pages
│   ├── assets/, shared.js, shared.css
│   └── serve_frontend.py      # lightweight static file server
├── docker-compose.yml
└── QUICK_START.md
```

---

## Getting Started

### Requirements

- Python 3.11+ (for a direct run) **or** Docker Desktop 4.x (for a containerised run)
- 4 GB RAM minimum (8 GB recommended), 2 GB free disk space
- Outbound internet access (required for the Supabase and PayPal integrations)
- A [Supabase](https://supabase.com) project (URL + service-role key)
- A [PayPal Developer](https://developer.paypal.com) sandbox app (client ID + secret)

### Environment Variables

Create `backend/.env` with the following (see `app/core/config.py`):

| Variable | Purpose |
|---|---|
| `LEDGER_STORAGE_PATH` | Path to the JSON blockchain ledger file (default `data/ledger.json`) |
| `AUTHORIZED_VALIDATORS` | Comma-separated list of PoA validator identifiers |
| `REDIS_URL` | Connection string for the resolver cache |
| `SUPABASE_URL` / `SUPABASE_SERVICE_ROLE_KEY` | Credentials for the Supabase-hosted PostgreSQL mirror |
| `JWT_SECRET` / `JWT_EXPIRES_HOURS` | Signing secret and expiry for issued authentication tokens |
| `ADMIN_REGISTRATION_CODE` | Shared secret required to self-register an administrator account |
| `PAYPAL_CLIENT_ID` / `PAYPAL_CLIENT_SECRET` / `PAYPAL_MODE` | PayPal REST API credentials and sandbox/live mode |

> **Note:** `PyJWT`, `bcrypt` and `supabase` are imported by the backend but are not fully pinned in `requirements.txt` (they *are* listed in `pyproject.toml`). If you install from `requirements.txt` directly, also run:
> `pip install pyjwt bcrypt supabase`

### Run with Docker Compose (recommended)

```bash
# 1. Make sure Docker Desktop is running
# 2. Create backend/.env with the variables above
# 3. From the project root:
docker-compose up --build
```

Wait for the `backend` and `redis` services to report healthy in the terminal output.

### Run Manually

```bash
cd backend
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS / Linux

pip install -r requirements.txt
pip install pyjwt bcrypt supabase   # see note above

uvicorn app.main:app --reload
```

In a second terminal, serve the frontend:

```bash
python frontend/serve_frontend.py
```

Windows users can alternatively double-click `RUN_PROJECT_WINDOWS.bat`.

---

## Accessing the Application

| Resource | URL |
|---|---|
| Customer Portal | http://localhost:5500/customer/index.html |
| Admin Portal | http://localhost:5500/admin/dashboard-admin.html |
| API Docs (Swagger UI) | http://localhost:8000/docs |
| Health Check | http://localhost:8000/api/v1/health |

**Demo walkthrough:** register a customer account → generate a keypair → register a domain → resolve it → view its audit history → run the spoofing/cache-poisoning simulations → purchase a plan via PayPal sandbox → open a support ticket → register an admin account (using `ADMIN_REGISTRATION_CODE`) → review the audit trail and freeze/unfreeze the demo domain.

---

## API Overview

All endpoints are versioned under `/api/v1`, except authentication which is served unprefixed at `/auth`.

| Router | Prefix | Responsibility |
|---|---|---|
| `auth` | `/auth` | Registration, login, JWT issuance |
| `domains` | `/api/v1/domains` | Register / update / transfer domains |
| `resolver` | `/api/v1/resolver` | Domain resolution + cache metrics |
| `signing` | `/api/v1/signing` | Keypair generation, message signing (dev convenience) |
| `security` | `/api/v1/security` | Spoofing & cache-poisoning simulations, security reports |
| `chain` | `/api/v1/chain` | Raw blockchain inspection |
| `admin` | `/api/v1/admin` | User management, domain moderation, audit trail, stats |
| `users` | `/api/v1/users` | Profile management |
| `tickets` | `/api/v1/tickets` | Support ticket workflow |
| `payments` | `/api/v1/payments` | PayPal order creation and capture |
| `ws` | `/api/v1/ws` | WebSocket channel for live chain updates |
| `health` | `/api/v1/health` | Liveness check |

Full interactive documentation is auto-generated by FastAPI at **`/docs`**.

HTTP status conventions: `201` created, `200` read/update, `401` missing/invalid auth, `403` forbidden (role/ownership), `404` not found, `409` conflict (duplicate registration).

---

## Security Simulations

Two endpoints exist specifically to demonstrate the blockchain ownership model under attack:

- **`POST /api/v1/security/simulate/spoofing`** — attempts to update a domain using an attacker-generated keypair. Rejected at the ownership-verification stage; the response confirms the record is unchanged.
- **`POST /api/v1/security/simulate/cache-poisoning`** — writes a malicious record directly into Redis, shows it being served, then shows the resolver falling back to the authoritative ledger record once the cache is invalidated.

---

## Testing

```bash
cd backend
pytest
```

Current coverage (`tests/`) includes the blockchain core, cryptography service, and the original domain/resolver/chain/signing/health API endpoints (`test_ledger.py`, `test_signature_service.py`, `test_chain_api.py`, `test_domains_api.py`, `test_resolver_api.py`, `test_signing_api.py`, `test_health.py`, `test_ui.py`).

> **Not yet covered by automated tests:** authentication, payments, admin, tickets and WebSocket modules. These have been verified manually against the running application. See [Known Limitations](#known-limitations).

---

## Known Limitations

- The JSON-file ledger does not scale to a large domain registry; an indexed database would be required in production.
- PoA consensus runs as a single-node authority — no multi-node voting, gossip, or Byzantine fault tolerance yet.
- The Supabase mirror write is **not transactional** with the blockchain commit; a failed mirror write does not roll back the ledger and can leave the two out of sync.
- The PayPal integration has only been exercised in **sandbox mode**; there is no webhook-based payment confirmation, refund, or dispute handling yet — the platform currently trusts the client-triggered capture-order call.
- Automated test coverage has not been extended to the auth, payments, admin, ticketing, or WebSocket modules.
- `requirements.txt` is missing `pyjwt`, `bcrypt`, and `supabase`, which are required at runtime (see [Environment Variables](#environment-variables)).

---

## Roadmap / Future Work

- Multi-node PoA with gossip-based block propagation and validator voting
- Migrate ledger persistence to an indexed backend (e.g. SQLite/Postgres) instead of a flat JSON file
- Webhook-based PayPal payment confirmation instead of client-triggered capture
- Reconciliation/outbox mechanism to keep the Supabase mirror consistent with the ledger
- Extend automated test coverage to auth, payments, admin, tickets and WebSocket modules
- Hardware-security-module-backed validator key management

---

## License

This project was developed for academic purposes as part of the PUSL3190 Computing Project at the University of Plymouth. No open-source license has been assigned; please contact the author before reuse.

---

## Acknowledgements

Built with [FastAPI](https://fastapi.tiangolo.com/), [Redis](https://redis.io/), [Docker](https://www.docker.com/), the [`ecdsa`](https://pypi.org/project/ecdsa/) library, [Supabase](https://supabase.com/), and the [PayPal Developer](https://developer.paypal.com/) platform. Supervised by Mr. Chamara Dissanayake.
