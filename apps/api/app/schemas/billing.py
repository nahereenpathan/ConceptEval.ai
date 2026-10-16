"""
Billing, Subscription, and Usage Quota Schemas
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class PlanLimitResponse(BaseModel):
    limit_key: str
    limit_value: int
    period: str


class PlanResponse(BaseModel):
    id: str
    name: str
    status: str
    billing_interval: str
    price_minor_units: int
    price_usd: float
    currency: str
    features: Dict[str, Any]
    limits: List[PlanLimitResponse] = []


class SubscriptionResponse(BaseModel):
    id: str
    plan_name: str
    plan_display_name: str
    status: str  # active, trialing, past_due, canceled
    billing_subject_type: str  # user, organization
    billing_subject_id: str
    provider: str
    provider_subscription_id: Optional[str] = None
    current_period_start: datetime
    current_period_end: datetime
    cancel_at_period_end: bool
    is_active: bool


class CheckoutSessionCreateRequest(BaseModel):
    plan_name: str
    organization_id: Optional[str] = None
    success_url: Optional[str] = None
    cancel_url: Optional[str] = None


class CheckoutSessionResponse(BaseModel):
    session_id: str
    checkout_url: str
    provider: str


class SubscriptionCancelRequest(BaseModel):
    organization_id: Optional[str] = None
    at_period_end: bool = True


class SubscriptionCancelResponse(BaseModel):
    subscription_id: str
    status: str
    cancel_at_period_end: bool
    message: str


class InvoiceResponse(BaseModel):
    id: str
    provider_invoice_id: str
    amount_minor_units: int
    amount_usd: float
    currency: str
    status: str
    issued_at: datetime
    paid_at: Optional[datetime] = None


class UsageMetricResponse(BaseModel):
    metric_key: str
    used: int
    limit: int
    remaining: int
    period: str


class QuotaStatusResponse(BaseModel):
    billing_subject_type: str
    billing_subject_id: str
    plan_name: str
    subscription_status: str
    current_period_start: datetime
    current_period_end: datetime
    quotas: List[UsageMetricResponse] = []
    can_submit: bool


class WebhookResponse(BaseModel):
    received: bool
    event_id: str
    event_type: str
    status: str
