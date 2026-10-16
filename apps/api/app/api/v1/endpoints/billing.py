"""
Billing, Subscription Management, and Quota Enforcement Endpoints
Provides real database-backed plan discovery, subscription lifecycle management,
atomic quota queries, authorized invoice retrieval, and cryptographic webhook verification.
"""

import json
import logging
from typing import Annotated, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user
from app.billing.provider import payment_provider
from app.billing.service import BillingService
from app.core.authz import (
    ALL_ORG_ROLES,
    ROLE_BILLING_MANAGER,
    ROLE_ORG_ADMIN,
    verify_organization_access,
)
from app.db.session import get_db
from app.models.user import User
from app.schemas.billing import (
    CheckoutSessionCreateRequest,
    CheckoutSessionResponse,
    InvoiceResponse,
    PlanResponse,
    QuotaStatusResponse,
    SubscriptionCancelRequest,
    SubscriptionCancelResponse,
    SubscriptionResponse,
    WebhookResponse,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/billing", tags=["Billing & Subscriptions"])


@router.get("/plans", response_model=List[PlanResponse])
async def list_plans(
    db: Annotated[AsyncSession, Depends(get_db)],
    current_user: Annotated[User, Depends(get_current_user)],
):
    """
    List all active subscription plans and configurable quota limits.
    """
    return await BillingService.list_active_plans(db)


@router.get("/subscription", response_model=SubscriptionResponse)
async def get_subscription(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    organization_id: Optional[str] = Query(None, description="Optional organization ID for tenant billing"),
):
    """
    Retrieve current subscription status for user or organization.
    Tenant-scoped: Requires billing_manager or org_admin role when organization_id is provided.
    """
    if organization_id:
        await verify_organization_access(
            db,
            user_id=current_user.id,
            organization_id=organization_id,
            allowed_roles={ROLE_BILLING_MANAGER, ROLE_ORG_ADMIN},
        )
        subject_type = "organization"
        subject_id = organization_id
    else:
        subject_type = "user"
        subject_id = current_user.id

    return await BillingService.get_subscription_details(db, subject_type, subject_id)


@router.post("/checkout-session", response_model=CheckoutSessionResponse)
async def create_checkout_session(
    req: CheckoutSessionCreateRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Create a payment checkout session with a real provider (e.g., Stripe).
    Fails safely with HTTP 503 if provider credentials are not configured in environment.
    Never creates simulated or fake checkout sessions.
    """
    if req.organization_id:
        await verify_organization_access(
            db,
            user_id=current_user.id,
            organization_id=req.organization_id,
            allowed_roles={ROLE_BILLING_MANAGER, ROLE_ORG_ADMIN},
        )
        subject_type = "organization"
        subject_id = req.organization_id
    else:
        subject_type = "user"
        subject_id = current_user.id

    # Validate requested plan exists and is active
    plan = await BillingService.get_plan_by_name(db, req.plan_name)
    if not plan or plan.status != "active":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={"code": "PLAN_NOT_FOUND", "message": f"Plan '{req.plan_name}' is not an active billing plan."},
        )

    if plan.price_minor_units == 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "FREE_PLAN_CHECKOUT", "message": "Cannot initiate checkout session for a free plan."},
        )

    # Check provider configuration
    if not payment_provider.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail={
                "code": "PROVIDER_NOT_CONFIGURED",
                "message": (
                    "Payment provider integration is not configured on this environment. "
                    "STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET are required prerequisites for checkout."
                ),
            },
        )

    try:
        session = await payment_provider.create_checkout_session(
            customer_email=current_user.email,
            plan_name=plan.name,
            price_minor_units=plan.price_minor_units,
            currency=plan.currency,
            billing_subject_type=subject_type,
            billing_subject_id=subject_id,
            success_url=req.success_url or "http://localhost:5173/billing?status=success",
            cancel_url=req.cancel_url or "http://localhost:5173/billing?status=canceled",
        )
        return CheckoutSessionResponse(
            session_id=session["id"],
            checkout_url=session["url"],
            provider="stripe",
        )
    except Exception as exc:
        logger.error(f"Failed to create Stripe checkout session: {exc}")
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail={"code": "PROVIDER_ERROR", "message": f"Payment provider error: {str(exc)}"},
        )


@router.post("/cancel", response_model=SubscriptionCancelResponse)
async def cancel_subscription(
    req: SubscriptionCancelRequest,
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Request cancellation of an active paid subscription.
    Tenant-scoped: Requires billing_manager or org_admin role when organization_id is provided.
    """
    if req.organization_id:
        await verify_organization_access(
            db,
            user_id=current_user.id,
            organization_id=req.organization_id,
            allowed_roles={ROLE_BILLING_MANAGER, ROLE_ORG_ADMIN},
        )
        subject_type = "organization"
        subject_id = req.organization_id
    else:
        subject_type = "user"
        subject_id = current_user.id

    return await BillingService.cancel_subscription(
        db=db,
        billing_subject_type=subject_type,
        billing_subject_id=subject_id,
        at_period_end=req.at_period_end,
    )


@router.get("/invoices", response_model=List[InvoiceResponse])
async def list_invoices(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    organization_id: Optional[str] = Query(None, description="Optional organization ID for tenant billing"),
):
    """
    Retrieve authorized invoice history.
    Tenant-scoped: Enforces that non-authorized members cannot access organization billing records.
    """
    if organization_id:
        await verify_organization_access(
            db,
            user_id=current_user.id,
            organization_id=organization_id,
            allowed_roles={ROLE_BILLING_MANAGER, ROLE_ORG_ADMIN},
        )
        subject_type = "organization"
        subject_id = organization_id
    else:
        subject_type = "user"
        subject_id = current_user.id

    return await BillingService.list_invoices(db, subject_type, subject_id)


@router.get("/usage", response_model=QuotaStatusResponse)
async def get_usage_quota(
    current_user: Annotated[User, Depends(get_current_user)],
    db: Annotated[AsyncSession, Depends(get_db)],
    organization_id: Optional[str] = Query(None, description="Optional organization ID for tenant billing"),
):
    """
    View current-period usage counters, configured plan limits, and remaining quota.
    Tenant-scoped: Any active organization member may view current org usage.
    """
    if organization_id:
        await verify_organization_access(
            db,
            user_id=current_user.id,
            organization_id=organization_id,
            allowed_roles=ALL_ORG_ROLES,
        )
        subject_type = "organization"
        subject_id = organization_id
    else:
        subject_type = "user"
        subject_id = current_user.id

    return await BillingService.get_quota_status(db, subject_type, subject_id)


@router.post("/webhooks", response_model=WebhookResponse)
async def handle_stripe_webhook(
    request: Request,
    db: Annotated[AsyncSession, Depends(get_db)],
):
    """
    Receive and idempotently process verified Stripe webhook events.
    Verifies HMAC-SHA256 signature using constant-time comparison and 300s timestamp tolerance.
    Does not log raw webhook payloads containing sensitive data.
    """
    raw_payload = await request.body()
    signature_header = request.headers.get("stripe-signature") or request.headers.get("Stripe-Signature")

    if not signature_header:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MISSING_SIGNATURE", "message": "Missing Stripe-Signature header."},
        )

    # Verify cryptographic signature
    is_valid = payment_provider.verify_webhook_signature(raw_payload, signature_header)
    if not is_valid:
        logger.warning("Stripe webhook rejected: cryptographic signature verification failed.")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "INVALID_WEBHOOK_SIGNATURE", "message": "Webhook signature verification failed."},
        )

    try:
        event_dict = json.loads(raw_payload.decode("utf-8"))
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={"code": "MALFORMED_JSON", "message": f"Could not parse webhook payload: {exc}"},
        )

    result = await BillingService.process_stripe_webhook(db, event_dict, raw_payload)
    return WebhookResponse(**result)
