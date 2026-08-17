from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any
import uuid
from app.services.global_dns_service import domain_exists_globally
from app.blockchain.ledger import Ledger
from app.blockchain.transaction import Transaction
from app.crypto.signature_service import SignatureService
from app.core.supabase_client import supabase
from app.core.ws_manager import broadcast_chain_update

class DomainError(Exception):
    pass


class DomainAlreadyExistsError(DomainError):
    pass


class DomainNotFoundError(DomainError):
    pass


class DomainOwnershipError(DomainError):
    pass


class DomainSignatureError(DomainError):
    pass


class DomainFrozenError(DomainError):
    pass


class DomainAlreadyFrozenError(DomainError):
    pass


class DomainAlreadyActiveError(DomainError):
    pass


@dataclass(slots=True)
class DomainMutationResult:
    tx_id: str
    block_hash: str
    chain_height: int


class DomainService:
    def __init__(
        self,
        ledger: Ledger,
        signature_service: SignatureService,
        cache_client: Any | None = None,
    ) -> None:
        self.ledger = ledger
        self.signature_service = signature_service
        self.cache_client = cache_client

    def register_domain(
        self,
        domain: str,
        ip: str,
        owner_public_key: str,
        signature: str,
    ) -> DomainMutationResult:
        normalized_domain = domain.strip().lower()
        state, _ = self._build_indexes()
        if normalized_domain in state:
            raise DomainAlreadyExistsError("Domain already exists.")
        
        if domain_exists_globally(normalized_domain):
            raise DomainAlreadyExistsError(
        "Domain already exists in global DNS."
    )

        payload = {"ip": ip}
        self._verify_signature(
            tx_type="register",
            domain=normalized_domain,
            payload=payload,
            owner_public_key=owner_public_key,
            signature=signature,
        )

        tx = Transaction(
            tx_type="register",
            domain=normalized_domain,
            payload=payload,
            owner_public_key=owner_public_key,
            signature=signature,
        )
        return self._commit_transaction(tx)

    def allocate_ip(self, domain: str) -> tuple[str, str]:
        """Allocate a unique IP from the BDNS private pool (10.x.x.x) based on the domain hash.
        Returns (allocated_ip, allocation_id).
        """
        import hashlib
        normalized_domain = domain.strip().lower()

        # Collect all IPs already registered on the blockchain
        state, _ = self._build_indexes()
        used_ips: set[str] = set()
        for record in state.values():
            ip = record.get("ip", "")
            if ip.startswith("10."):
                used_ips.add(ip)

        # Generate a stable IP by hashing the domain name.
        # If there's a collision, we salt the domain and try again.
        for salt_counter in range(100):
            salt = f"-{salt_counter}" if salt_counter > 0 else ""
            input_str = normalized_domain + salt
            h = hashlib.sha256(input_str.encode("utf-8")).digest()
            
            # Map hash bytes to a 10.x.y.z range (excluding network/broadcast addresses)
            second = 10 + (h[0] % 240)  # 10.10.y.z to 10.250.y.z
            third = 1 + (h[1] % 254)
            fourth = 1 + (h[2] % 254)
            
            candidate = f"10.{second}.{third}.{fourth}"
            if candidate not in used_ips:
                allocation_id = str(uuid.uuid4()).replace("-", "")[:16].upper()
                return candidate, allocation_id

        raise RuntimeError("IP address allocation collision threshold reached.")

    def update_domain(
        self,
        domain: str,
        ip: str,
        owner_public_key: str,
        signature: str,
    ) -> DomainMutationResult:
        normalized_domain = domain.strip().lower()
        state, _ = self._build_indexes()
        current = state.get(normalized_domain)
        if not current:
            raise DomainNotFoundError("Domain not found.")
        if current.get("status") == "frozen":
            raise DomainFrozenError(
                "This domain has been frozen by an administrator and cannot be updated."
            )
        if current["owner_public_key"] != owner_public_key:
            raise DomainOwnershipError("Only the current owner can update this domain.")

        payload = {"ip": ip}
        self._verify_signature(
            tx_type="update",
            domain=normalized_domain,
            payload=payload,
            owner_public_key=owner_public_key,
            signature=signature,
        )

        tx = Transaction(
            tx_type="update",
            domain=normalized_domain,
            payload=payload,
            owner_public_key=owner_public_key,
            signature=signature,
        )
        return self._commit_transaction(tx)

    def transfer_domain(
        self,
        domain: str,
        owner_public_key: str,
        new_owner_public_key: str,
        signature: str,
    ) -> DomainMutationResult:
        normalized_domain = domain.strip().lower()
        state, _ = self._build_indexes()
        current = state.get(normalized_domain)
        if not current:
            raise DomainNotFoundError("Domain not found.")
        if current.get("status") == "frozen":
            raise DomainFrozenError(
                "This domain has been frozen by an administrator and cannot be transferred."
            )
        if current["owner_public_key"] != owner_public_key:
            raise DomainOwnershipError("Only the current owner can transfer this domain.")

        payload = {"new_owner_public_key": new_owner_public_key}
        self._verify_signature(
            tx_type="transfer",
            domain=normalized_domain,
            payload=payload,
            owner_public_key=owner_public_key,
            signature=signature,
        )

        tx = Transaction(
            tx_type="transfer",
            domain=normalized_domain,
            payload=payload,
            owner_public_key=owner_public_key,
            signature=signature,
        )
        return self._commit_transaction(tx)

    def list_domains(self) -> list[dict[str, Any]]:
        state, _ = self._build_indexes()
        return sorted(state.values(), key=lambda item: item["domain"])

    def get_domain(self, domain: str) -> dict[str, Any]:
        normalized_domain = domain.strip().lower()
        state, _ = self._build_indexes()
        current = state.get(normalized_domain)
        if not current:
            raise DomainNotFoundError("Domain not found.")
        return current

    def get_domain_history(self, domain: str) -> list[dict[str, Any]]:
        normalized_domain = domain.strip().lower()
        _, audit = self._build_indexes()
        return audit.get(normalized_domain, [])

    def freeze_domain(
        self,
        domain: str,
        admin_user_id: str,
        reason: str | None = None,
    ) -> DomainMutationResult:
        """Admin-only action: freeze a domain on-chain. No owner signature is
        required since this is an administrative security action, not an
        owner-authorised mutation."""
        normalized_domain = domain.strip().lower()
        state, _ = self._build_indexes()
        current = state.get(normalized_domain)
        if not current:
            raise DomainNotFoundError("Domain not found.")
        if current.get("status") == "frozen":
            raise DomainAlreadyFrozenError("Domain is already frozen.")

        tx = Transaction(
            tx_type="admin_freeze",
            domain=normalized_domain,
            payload={
                "reason": reason or "No reason provided.",
                "admin_user_id": admin_user_id,
            },
            owner_public_key=current["owner_public_key"],
            signature="ADMIN_ACTION_NO_SIGNATURE_REQUIRED",
        )
        return self._commit_transaction(tx)

    def unfreeze_domain(
        self,
        domain: str,
        admin_user_id: str,
        reason: str | None = None,
    ) -> DomainMutationResult:
        """Admin-only action: lift a freeze placed on a domain."""
        normalized_domain = domain.strip().lower()
        state, _ = self._build_indexes()
        current = state.get(normalized_domain)
        if not current:
            raise DomainNotFoundError("Domain not found.")
        if current.get("status") != "frozen":
            raise DomainAlreadyActiveError("Domain is not currently frozen.")

        tx = Transaction(
            tx_type="admin_unfreeze",
            domain=normalized_domain,
            payload={
                "reason": reason or "No reason provided.",
                "admin_user_id": admin_user_id,
            },
            owner_public_key=current["owner_public_key"],
            signature="ADMIN_ACTION_NO_SIGNATURE_REQUIRED",
        )
        return self._commit_transaction(tx)

    def get_global_audit_trail(self, limit: int = 200) -> list[dict[str, Any]]:
        """Full cross-domain audit trail reconstructed straight from the
        blockchain ledger (every committed transaction of every type),
        newest first. This backs the admin Global Audit Trail page."""
        events: list[dict[str, Any]] = []
        for block in self.ledger.chain:
            for tx in block.transactions:
                if tx.tx_type == "genesis":
                    continue
                events.append({
                    "tx_id": tx.tx_id,
                    "tx_type": tx.tx_type,
                    "domain": tx.domain,
                    "payload": tx.payload,
                    "owner_public_key": tx.owner_public_key,
                    "timestamp": tx.timestamp,
                    "block_index": block.index,
                    "block_hash": block.hash,
                    "validator": block.validator,
                })
        events.sort(key=lambda event: event["timestamp"], reverse=True)
        return events[:limit]

    def _commit_transaction(self, tx: Transaction) -> DomainMutationResult:
        self.ledger.add_transaction(tx)
        block = self.ledger.commit_pending_transactions()

        if tx.tx_type == "register":
            supabase.table("domains").insert({
                "domain_name": tx.domain,
                "ip_address": tx.payload["ip"],
                "owner_public_key": tx.owner_public_key,
                "status": "active"
            }).execute()

        elif tx.tx_type == "update":
            supabase.table("domains").update({
                "ip_address": tx.payload["ip"],
                "updated_at": datetime.utcnow().isoformat()
            }).eq("domain_name", tx.domain).execute()

        elif tx.tx_type == "transfer":
            supabase.table("domains").update({
                "owner_public_key": tx.payload["new_owner_public_key"],
                "status": "transferred",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("domain_name", tx.domain).execute()

        elif tx.tx_type == "admin_freeze":
            supabase.table("domains").update({
                "status": "frozen",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("domain_name", tx.domain).execute()

        elif tx.tx_type == "admin_unfreeze":
            supabase.table("domains").update({
                "status": "active",
                "updated_at": datetime.utcnow().isoformat()
            }).eq("domain_name", tx.domain).execute()

        supabase.table("ledger_blocks").insert({
            "block_index": int(block.index),
            "block_hash": str(block.hash),
            "previous_hash": str(getattr(block, "previous_hash", "")),
            "transaction_type": tx.tx_type,
            "transaction_data": {
                "tx_id": tx.tx_id,
                "domain": tx.domain,
                "payload": tx.payload,
                "owner_public_key": tx.owner_public_key,
                "signature": tx.signature,
                "timestamp": tx.timestamp
            },
            "validator": str(getattr(block, "validator", "validator-1"))
        }).execute()

        supabase.table("audit_logs").insert({
            "action_type": tx.tx_type.upper(),
            "details": {
                "domain": tx.domain,
                "tx_id": tx.tx_id,
                "block_hash": block.hash,
                "chain_height": self.ledger.get_chain_height()
            }
        }).execute()

        if self.cache_client is not None:
            self.cache_client.invalidate_domain(tx.domain)

        # Push a live update to any connected dashboards (Blockchain Ledger, My
        # Domains, admin overview, ...) so they refresh instantly instead of
        # waiting on a polling interval.
        broadcast_chain_update({
            "tx_type": tx.tx_type,
            "domain": tx.domain,
            "tx_id": tx.tx_id,
            "block_hash": block.hash,
            "block_index": block.index,
            "chain_height": self.ledger.get_chain_height(),
            "validator": getattr(block, "validator", "validator-1"),
        })

        return DomainMutationResult(
            tx_id=tx.tx_id,
            block_hash=block.hash,
            chain_height=self.ledger.get_chain_height(),
        )

    def _verify_signature(
        self,
        *,
        tx_type: str,
        domain: str,
        payload: dict[str, Any],
        owner_public_key: str,
        signature: str,
    ) -> None:
        is_valid = self.signature_service.verify_signature(
            tx_type=tx_type,
            domain=domain,
            payload=payload,
            owner_public_key=owner_public_key,
            signature=signature,
        )
        if not is_valid:
            raise DomainSignatureError("Invalid transaction signature.")

    def _build_indexes(self) -> tuple[dict[str, dict[str, Any]], dict[str, list[dict[str, Any]]]]:
        latest_state: dict[str, dict[str, Any]] = {}
        audit_log: dict[str, list[dict[str, Any]]] = {}

        RELEVANT_TYPES = {"register", "update", "transfer", "admin_freeze", "admin_unfreeze"}

        for block in self.ledger.chain:
            for tx in block.transactions:
                if tx.tx_type not in RELEVANT_TYPES:
                    continue

                domain = tx.domain
                audit_event = {
                    "tx_id": tx.tx_id,
                    "tx_type": tx.tx_type,
                    "domain": tx.domain,
                    "payload": tx.payload,
                    "owner_public_key": tx.owner_public_key,
                    "signature": tx.signature,
                    "timestamp": tx.timestamp,
                    "block_index": block.index,
                    "block_hash": block.hash,
                    "validator": block.validator,
                    "committed_at": datetime.fromisoformat(block.timestamp),
                }
                audit_log.setdefault(domain, []).append(audit_event)

                if tx.tx_type == "register":
                    latest_state[domain] = {
                        "domain": domain,
                        "ip": tx.payload["ip"],
                        "owner_public_key": tx.owner_public_key,
                        "updated_at": tx.timestamp,
                        "status": "active",
                    }
                elif tx.tx_type == "update" and domain in latest_state:
                    latest_state[domain]["ip"] = tx.payload["ip"]
                    latest_state[domain]["updated_at"] = tx.timestamp
                elif tx.tx_type == "transfer" and domain in latest_state:
                    latest_state[domain]["owner_public_key"] = tx.payload["new_owner_public_key"]
                    latest_state[domain]["updated_at"] = tx.timestamp
                elif tx.tx_type == "admin_freeze" and domain in latest_state:
                    latest_state[domain]["status"] = "frozen"
                    latest_state[domain]["updated_at"] = tx.timestamp
                elif tx.tx_type == "admin_unfreeze" and domain in latest_state:
                    latest_state[domain]["status"] = "active"
                    latest_state[domain]["updated_at"] = tx.timestamp

        return latest_state, audit_log
