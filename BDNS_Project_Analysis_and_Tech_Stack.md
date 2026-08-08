# Blockchain-Backed Secure DNS (BDNS)  
## Project Analysis and Recommended Tech Stack

## 1) Project Overview

Based on the three documents (`Proposal`, `PID`, and `Interim Report`), the project is a **Blockchain-Backed Secure DNS (BDNS)** prototype.

The core idea is to replace centralized trust points in traditional DNS with a decentralized, tamper-resistant blockchain ledger for domain records.

Traditional DNS depends on centralized authorities (registrars, authoritative servers, root hierarchy). This creates single points of failure and allows attacks such as:

- DNS spoofing  
- Cache poisoning  
- Man-in-the-middle (MitM) redirection  
- Domain hijacking

BDNS aims to improve:

- **Integrity**: DNS records cannot be silently modified  
- **Transparency**: all updates are auditable and traceable  
- **Ownership verification**: only key owners can update records  
- **Resilience**: decentralized nodes reduce dependency on one authority

---

## 2) What the System Must Do (from requirements)

### Functional requirements

- Register new domains and store them on blockchain
- Update domain records through signed transactions
- Verify domain ownership using cryptographic signatures
- Resolve domain name to IP from blockchain data
- Provide a web interface for management (register/update/view)
- Keep logs/audit trail of registrations, updates, and resolution activity

### Non-functional requirements

- Security against spoofing, poisoning, tampering
- Low latency resolution (target appears as <100 ms in one section and <50 ms in another)
- Reliability/availability in distributed node conditions
- Basic scalability (e.g., around 1,000 domains in prototype benchmarks)
- Usability (clear and manageable interface)

---

## 3) Scope Clarification

The documents clearly position this as an **academic proof-of-concept**, not production internet DNS.

In scope:

- Custom blockchain layer
- Resolver module
- Web-based domain management
- Attack simulation and performance/security evaluation

Out of scope:

- Full global DNS root integration
- Production-scale traffic optimization
- Real-world TLD governance and policy integration

---

## 4) Recommended Best Tech Stack

This stack is the best fit for your project goals, timeline, and academic prototype constraints.

### Core backend

- **Language**: `Python 3.11+`
- **API Framework**: `FastAPI` (or Flask if your current code already uses it)
- **Validation/Serialization**: `Pydantic` (if FastAPI)

### Blockchain and cryptography

- **Hashing**: Python `hashlib` (SHA-256)
- **Digital signatures**: `cryptography` library (ECDSA)
- **Data integrity proofs**: Merkle tree implementation (custom/simple module)
- **Consensus for prototype**: simplified **Proof-of-Authority (PoA)**

### DNS resolver and DNS protocol layer

- **DNS server library**: `dnslib`
- **DNS query tooling/tests**: `dnspython`

### Storage and performance

- **Primary prototype chain storage**: JSON or local block files
- **Optional indexed state DB**: `PostgreSQL` (or `SQLite` for local-only simplicity)
- **Cache layer**: `Redis` for faster repeated lookups

### Frontend

- **Recommended**: `React + Vite`
- **Alternative for speed**: server-rendered templates (if you want quicker completion)

### Networking and node communication

- Start with **REST over HTTP** for node sync and transaction propagation
- Consider `WebSocket` only if you need near real-time node event broadcasting

### Observability and testing

- **Unit/integration tests**: `pytest`
- **Performance/load tests**: `k6` or `Locust`
- **Metrics**: `Prometheus`
- **Dashboards**: `Grafana`
- **Logging**: structured logs using Python logging (JSON output preferred)

### Deployment and reproducibility

- **Containerization**: `Docker` + `Docker Compose`
- Multi-container local lab for 5-10 blockchain nodes + resolver + web app + cache + metrics

---

## 5) Why This Stack Is Best for BDNS

- Aligns directly with your documents (Python, web interface, cryptography, PoA prototype).
- Lightweight and realistic for academic deadlines.
- Easy to demonstrate measurable success criteria (latency, integrity, spoofing resistance, uptime).
- Avoids complexity/cost of public smart-contract chains (gas fees, congestion, chain dependencies).
- Supports a clean architecture where each module can be evaluated independently.

---

## 6) Suggested High-Level Architecture

1. User submits registration/update via Web UI  
2. Backend verifies request + signature  
3. Transaction broadcast to PoA validator nodes  
4. Block committed to distributed ledger  
5. Resolver queries latest verified state (cache first, then chain/index)  
6. Resolver returns verified IP response  
7. Metrics/logging pipeline captures latency, failures, and security events

---

## 7) Key Risks and Mitigation

- **Latency overhead from blockchain checks**  
  - Mitigation: resolver cache (`Redis`), indexed latest-state store

- **Crypto implementation mistakes**  
  - Mitigation: use established libraries, avoid custom cryptography

- **Node sync inconsistency in prototype network**  
  - Mitigation: deterministic block validation rules + health checks

- **Scope creep**  
  - Mitigation: focus on 3 modules (blockchain, resolver, web), avoid production features

---

## 8) Final Recommendation

Use a **Python-first modular prototype**:

- FastAPI/Flask + custom PoA blockchain + ECDSA signatures + DNS resolver (`dnslib`) + Redis cache + Dockerized multi-node environment.

This gives the strongest balance of:

- security demonstration quality,
- implementation feasibility,
- measurable results for your final evaluation.

---

## 9) Next Steps (Execution Plan)

1. Freeze evaluation targets (resolve the `<50 ms` vs `<100 ms` latency inconsistency).  
2. Implement blockchain core (blocks, tx, signatures, PoA validator).  
3. Implement resolver path with cache-first lookup.  
4. Build web management UI + auth and signed transaction flow.  
5. Run attack simulations (spoofing, poisoning, tampering attempts).  
6. Collect metrics/logs and produce final benchmark report and demo.

