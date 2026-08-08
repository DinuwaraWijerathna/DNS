# BDNS Final Prototype - Quick Start

## Run on Windows
1. Open this folder in VS Code.
2. Open Terminal.
3. Run:

```powershell
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Or double-click/run:

```text
RUN_PROJECT_WINDOWS.bat
```

## Open
- Dashboard: http://localhost:8000/dashboard
- API Docs: http://localhost:8000/docs
- Health: http://localhost:8000/api/v1/health

## Demo Flow
1. Open dashboard.
2. Click Generate Keypair.
3. Register `example.bd` with IP `203.0.113.10`.
4. Resolve `example.bd`.
5. Update the IP to `203.0.113.20`.
6. Load Audit History.
7. Run Spoofing Test.
8. Run Cache Test.
9. Open API Docs for endpoint-level testing.

## Main Final Features
- FastAPI backend
- Static dashboard UI
- Blockchain ledger storage
- ECDSA signing helper
- Domain registration/update/transfer
- Resolver with cache and metrics
- Domain audit history
- Security simulation endpoints
- Swagger API documentation
- Automated tests
