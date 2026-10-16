"""
Payment Provider Abstraction and Stripe Webhook Adapter
Implements official Stripe webhook signature verification, checkout session handling,
and idempotent event parsing.
"""

from abc import ABC, abstractmethod
from datetime import datetime, timezone
import hashlib
import hmac
import json
import logging
import time
from typing import Any, Dict, Optional, Tuple

import httpx

from app.core.config import settings

logger = logging.getLogger(__name__)


class BillingProviderError(Exception):
    """Base error for billing provider operations."""
    pass


class ProviderNotConfiguredError(BillingProviderError):
    """Raised when an operation is requested on an unconfigured payment provider."""
    pass


class InvalidWebhookSignatureError(BillingProviderError):
    """Raised when a webhook signature fails cryptographic verification."""
    pass


class BasePaymentProvider(ABC):
    """Abstract payment provider interface."""

    @abstractmethod
    def is_configured(self) -> bool:
        """Return True if real provider API credentials are configured."""
        pass

    @abstractmethod
    async def create_checkout_session(
        self,
        customer_email: str,
        plan_name: str,
        price_minor_units: int,
        currency: str,
        billing_subject_type: str,
        billing_subject_id: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        """Create a real checkout session on the provider."""
        pass

    @abstractmethod
    async def cancel_subscription(
        self,
        provider_subscription_id: str,
        at_period_end: bool = True,
    ) -> Dict[str, Any]:
        """Request subscription cancellation with provider."""
        pass

    @abstractmethod
    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature_header: str,
        secret: Optional[str] = None,
    ) -> bool:
        """Verify webhook signature according to provider's cryptographic specifications."""
        pass


class StripePaymentProvider(BasePaymentProvider):
    """
    Official Stripe implementation using direct REST API calls and HMAC-SHA256 signature verification.
    Requires STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET in environment for real payments.
    """

    def is_configured(self) -> bool:
        """True if Stripe API secret key is configured."""
        return bool(settings.STRIPE_SECRET_KEY and settings.STRIPE_SECRET_KEY.startswith("sk_"))

    def is_webhook_configured(self) -> bool:
        """True if Stripe webhook signing secret is configured."""
        return bool(settings.STRIPE_WEBHOOK_SECRET and settings.STRIPE_WEBHOOK_SECRET.startswith("whsec_"))

    async def create_checkout_session(
        self,
        customer_email: str,
        plan_name: str,
        price_minor_units: int,
        currency: str,
        billing_subject_type: str,
        billing_subject_id: str,
        success_url: str,
        cancel_url: str,
    ) -> Dict[str, Any]:
        """
        Creates a real Stripe Checkout Session via Stripe REST API.
        Never fakes session creation if unconfigured.
        """
        if not self.is_configured():
            raise ProviderNotConfiguredError(
                "Stripe payment provider is not configured. STRIPE_SECRET_KEY environment variable is required."
            )

        endpoint = "https://api.stripe.com/v1/checkout/sessions"
        headers = {
            "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "customer_email": customer_email,
            "mode": "subscription",
            "success_url": success_url,
            "cancel_url": cancel_url,
            "metadata[billing_subject_type]": billing_subject_type,
            "metadata[billing_subject_id]": billing_subject_id,
            "metadata[plan_name]": plan_name,
            "line_items[0][price_data][currency]": currency.lower(),
            "line_items[0][price_data][product_data][name]": f"Concept-Aware Evaluation - {plan_name}",
            "line_items[0][price_data][unit_amount]": str(price_minor_units),
            "line_items[0][price_data][recurring][interval]": "month",
            "line_items[0][quantity]": "1",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(endpoint, headers=headers, data=data)
            if resp.status_code != 200:
                logger.error(f"Stripe API error: {resp.status_code} - {resp.text}")
                raise BillingProviderError(f"Stripe checkout creation failed: {resp.text}")
            return resp.json()

    async def cancel_subscription(
        self,
        provider_subscription_id: str,
        at_period_end: bool = True,
    ) -> Dict[str, Any]:
        """Cancel subscription with Stripe."""
        if not self.is_configured():
            raise ProviderNotConfiguredError("Stripe payment provider is not configured.")

        endpoint = f"https://api.stripe.com/v1/subscriptions/{provider_subscription_id}"
        headers = {
            "Authorization": f"Bearer {settings.STRIPE_SECRET_KEY}",
            "Content-Type": "application/x-www-form-urlencoded",
        }
        data = {
            "cancel_at_period_end": "true" if at_period_end else "false",
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(endpoint, headers=headers, data=data)
            if resp.status_code != 200:
                raise BillingProviderError(f"Stripe subscription cancel failed: {resp.text}")
            return resp.json()

    def verify_webhook_signature(
        self,
        payload_bytes: bytes,
        signature_header: str,
        secret: Optional[str] = None,
    ) -> bool:
        """
        Validates Stripe webhook signature header using HMAC-SHA256 and constant-time comparison.
        Header format: t=1492774577,v1=5257a869e7ecebeda32affa62cd49231...
        Enforces a 300-second timestamp tolerance to defeat replay attacks.
        """
        signing_secret = secret or settings.STRIPE_WEBHOOK_SECRET
        if not signing_secret:
            logger.warning("Webhook received but STRIPE_WEBHOOK_SECRET is not configured.")
            return False

        if not signature_header:
            return False

        # Parse header items
        pairs = {}
        for item in signature_header.split(","):
            parts = item.strip().split("=", 1)
            if len(parts) == 2:
                key, val = parts[0].strip(), parts[1].strip()
                if key not in pairs:
                    pairs[key] = []
                pairs[key].append(val)

        if "t" not in pairs or "v1" not in pairs:
            return False

        try:
            timestamp = int(pairs["t"][0])
        except ValueError:
            return False

        # 300-second timestamp tolerance
        now = int(time.time())
        if abs(now - timestamp) > 300:
            logger.warning(f"Webhook timestamp {timestamp} outside acceptable tolerance window (now={now}).")
            return False

        # Compute expected HMAC signature
        signed_payload = f"{timestamp}.".encode("utf-8") + payload_bytes
        expected_sig = hmac.new(
            signing_secret.encode("utf-8"),
            signed_payload,
            hashlib.sha256,
        ).hexdigest()

        # Constant-time comparison against any matching v1 signatures
        for sig in pairs["v1"]:
            if hmac.compare_digest(expected_sig, sig):
                return True

        return False


# Singleton provider instance
payment_provider: BasePaymentProvider = StripePaymentProvider()
