from __future__ import annotations

import httpx

from app.core.config import get_settings

settings = get_settings()

PAYPAL_BASE_URLS = {
    "sandbox": "https://api-m.sandbox.paypal.com",
    "live": "https://api-m.paypal.com",
}

# Server-side source of truth for plan pricing.
# The frontend only ever sends a plan *name* - never a raw amount -
# so a tampered client request can never change what gets charged.
PLAN_PRICES: dict[str, dict[str, str]] = {
    "individual": {"amount": "9.00", "currency": "USD"},
    "smallbusiness": {"amount": "29.00", "currency": "USD"},
    "business": {"amount": "99.00", "currency": "USD"},
}


class PayPalError(Exception):
    pass


class PayPalService:
    def __init__(self) -> None:
        if not settings.paypal_client_id or not settings.paypal_client_secret:
            raise PayPalError("PayPal credentials are not configured.")
        self.base_url = PAYPAL_BASE_URLS.get(settings.paypal_mode, PAYPAL_BASE_URLS["sandbox"])

    async def _get_access_token(self) -> str:
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v1/oauth2/token",
                data={"grant_type": "client_credentials"},
                auth=(settings.paypal_client_id, settings.paypal_client_secret),
                headers={"Accept": "application/json"},
            )
        if response.status_code != 200:
            raise PayPalError(f"Failed to authenticate with PayPal: {response.text}")
        return response.json()["access_token"]

    async def create_order(self, plan: str) -> dict:
        plan_info = PLAN_PRICES.get(plan)
        if not plan_info:
            raise PayPalError(f"Unknown plan: {plan}")

        token = await self._get_access_token()

        payload = {
            "intent": "CAPTURE",
            "purchase_units": [
                {
                    "reference_id": plan,
                    "amount": {
                        "currency_code": plan_info["currency"],
                        "value": plan_info["amount"],
                    },
                }
            ],
        }

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v2/checkout/orders",
                json=payload,
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
            )

        if response.status_code not in (200, 201):
            raise PayPalError(f"Failed to create PayPal order: {response.text}")

        return response.json()

    async def capture_order(self, order_id: str) -> dict:
        token = await self._get_access_token()

        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/v2/checkout/orders/{order_id}/capture",
                headers={
                    "Content-Type": "application/json",
                    "Authorization": f"Bearer {token}",
                },
            )

        if response.status_code not in (200, 201):
            raise PayPalError(f"Failed to capture PayPal order: {response.text}")

        return response.json()
