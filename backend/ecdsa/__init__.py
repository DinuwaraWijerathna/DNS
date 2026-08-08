from __future__ import annotations

from dataclasses import dataclass

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec
from cryptography.hazmat.primitives.asymmetric.utils import decode_dss_signature, encode_dss_signature


class BadSignatureError(Exception):
    pass


class MalformedPointError(Exception):
    pass


@dataclass(frozen=True)
class _Curve:
    name: str = "NIST256p"
    key_size_bytes: int = 32

    def to_crypto_curve(self) -> ec.EllipticCurve:
        return ec.SECP256R1()


NIST256p = _Curve()


class VerifyingKey:
    def __init__(self, public_key, curve: _Curve = NIST256p) -> None:
        self._public_key = public_key
        self.curve = curve

    @classmethod
    def from_string(cls, data: bytes, curve: _Curve = NIST256p) -> "VerifyingKey":
        if len(data) != curve.key_size_bytes * 2:
            raise MalformedPointError("Invalid public key length.")
        encoded = b"\x04" + data
        try:
            public_key = ec.EllipticCurvePublicKey.from_encoded_point(curve.to_crypto_curve(), encoded)
        except ValueError as exc:
            raise MalformedPointError("Invalid public key point.") from exc
        return cls(public_key, curve)

    def to_string(self) -> bytes:
        raw = self._public_key.public_bytes(
            encoding=serialization.Encoding.X962,
            format=serialization.PublicFormat.UncompressedPoint,
        )
        return raw[1:]

    def verify(self, signature: bytes, data: bytes) -> bool:
        try:
            if len(signature) == self.curve.key_size_bytes * 2:
                r = int.from_bytes(signature[: self.curve.key_size_bytes], "big")
                s = int.from_bytes(signature[self.curve.key_size_bytes :], "big")
                der_signature = encode_dss_signature(r, s)
            else:
                der_signature = signature
            self._public_key.verify(der_signature, data, ec.ECDSA(hashes.SHA256()))
            return True
        except InvalidSignature as exc:
            raise BadSignatureError("Invalid signature.") from exc
        except ValueError as exc:
            raise BadSignatureError("Invalid signature format.") from exc


class SigningKey:
    def __init__(self, private_key, curve: _Curve = NIST256p) -> None:
        self._private_key = private_key
        self.curve = curve
        self.verifying_key = VerifyingKey(private_key.public_key(), curve)

    @classmethod
    def generate(cls, curve: _Curve = NIST256p) -> "SigningKey":
        return cls(ec.generate_private_key(curve.to_crypto_curve()), curve)

    @classmethod
    def from_string(cls, data: bytes, curve: _Curve = NIST256p) -> "SigningKey":
        if len(data) != curve.key_size_bytes:
            raise MalformedPointError("Invalid private key length.")
        value = int.from_bytes(data, "big")
        if value <= 0:
            raise MalformedPointError("Invalid private key value.")
        try:
            private_key = ec.derive_private_key(value, curve.to_crypto_curve())
        except ValueError as exc:
            raise MalformedPointError("Invalid private key value.") from exc
        return cls(private_key, curve)

    def to_string(self) -> bytes:
        value = self._private_key.private_numbers().private_value
        return value.to_bytes(self.curve.key_size_bytes, "big")

    def sign(self, data: bytes) -> bytes:
        der_signature = self._private_key.sign(data, ec.ECDSA(hashes.SHA256()))
        r, s = decode_dss_signature(der_signature)
        return r.to_bytes(self.curve.key_size_bytes, "big") + s.to_bytes(self.curve.key_size_bytes, "big")
