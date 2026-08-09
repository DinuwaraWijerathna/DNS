from contextlib import asynccontextmanager
from pathlib import Path
import asyncio

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from app.api.routes.admin import router as admin_router
from app.api.routes.chain import router as chain_router
from app.api.routes.domains import router as domains_router
from app.api.auth import router as auth_router
from app.api.routes.health import router as health_router
from app.api.routes.resolver import router as resolver_router
from app.api.routes.signing import router as signing_router
from app.api.routes.security import router as security_router
from app.api.routes.payments import router as payments_router
from app.api.routes.tickets import router as tickets_router
from app.api.routes.users import router as users_router
from app.api.routes.ws import router as ws_router
from app.blockchain.consensus_poa import PoAConsensus
from app.blockchain.ledger import Ledger
from app.cache.redis_client import RedisCacheClient
from app.core.config import get_settings
from app.core.ws_manager import set_main_loop
from app.crypto.signature_service import SignatureService
from app.resolver.dns_adapter import DnsAdapter
from app.resolver.resolver_service import ResolverService
from app.services.domain_service import DomainService

settings = get_settings()
PROJECT_ROOT = Path(__file__).resolve().parents[2]
FRONTEND_DIR = PROJECT_ROOT / "frontend"


def init_ledger(app: FastAPI) -> None:
    consensus = PoAConsensus(settings.authorized_validators_list)
    ledger = Ledger(consensus=consensus, storage_path=settings.ledger_storage_path)
    ledger.initialize()
    if not ledger.is_chain_valid():
        raise RuntimeError("Ledger integrity check failed during startup.")
    cache_client = RedisCacheClient(
        redis_url=settings.redis_url,
        default_ttl_seconds=settings.resolver_cache_ttl_seconds,
    )
    domain_service = DomainService(
        ledger=ledger,
        signature_service=SignatureService(),
        cache_client=cache_client,
    )
    resolver_service = ResolverService(
        domain_service=domain_service,
        cache_client=cache_client,
        dns_adapter=DnsAdapter(),
        cache_ttl_seconds=settings.resolver_cache_ttl_seconds,
        metrics_log_size=settings.resolver_metrics_log_size,
    )
    app.state.ledger = ledger
    app.state.domain_service = domain_service
    app.state.resolver_service = resolver_service


@asynccontextmanager
async def lifespan(app: FastAPI):
    set_main_loop(asyncio.get_running_loop())
    init_ledger(app)
    yield


app = FastAPI(title=settings.app_name, lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(chain_router, prefix=settings.api_prefix)
app.include_router(domains_router, prefix=settings.api_prefix)
app.include_router(resolver_router, prefix=settings.api_prefix)
app.include_router(signing_router, prefix=settings.api_prefix)
app.include_router(security_router, prefix=settings.api_prefix)
app.include_router(payments_router, prefix=settings.api_prefix)
app.include_router(admin_router, prefix=settings.api_prefix)
app.include_router(users_router, prefix=settings.api_prefix)
app.include_router(tickets_router, prefix=settings.api_prefix)
app.include_router(ws_router, prefix=settings.api_prefix)
app.include_router(auth_router)
app.mount("/ui/assets", StaticFiles(directory=FRONTEND_DIR / "assets"), name="ui-assets")


@app.get("/")
def root() -> dict[str, str]:
    return {"message": "BDNS backend running"}


@app.get("/dashboard")
def dashboard() -> FileResponse:
    return FileResponse(FRONTEND_DIR / "index.html")
