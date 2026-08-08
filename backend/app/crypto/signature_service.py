from __future__ import annotations

import hashlib
import json
from typing import Any

from ecdsa import BadSignatureError, NIST256p, VerifyingKey


class SignatureService:
    @staticmethod
    def build_signing_message(tx_type: str, domain: str, payload: dict[str, Any]) -> str:
        body = {"tx_type": tx_type, "domain": domain, "payload": payload}
        return json.dumps(body, sort_keys=True, separators=(",", ":"))

    def verify_signature(
        self,
        *,
        tx_type: str,
        domain: str,
        payload: dict[str, Any],
        owner_public_key: str,
        signature: str,
    ) -> bool:
        message = self.build_signing_message(tx_type, domain, payload).encode("utf-8")
        try:
            key_bytes = bytes.fromhex(owner_public_key)
            sig_bytes = bytes.fromhex(signature)
            verifying_key = VerifyingKey.from_string(key_bytes, curve=NIST256p, hashfunc=hashlib.sha256)
            return verifying_key.verify(sig_bytes, message)
        except (ValueError, BadSignatureError):
            return False