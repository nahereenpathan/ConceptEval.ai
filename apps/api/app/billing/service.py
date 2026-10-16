"""
SaaS Billing, Subscription Management, and Quota Enforcement Service
Handles database-backed plan entitlements, atomic quota reservations,
concurrency protection, settlement, and idempotent webhook processing.
"""

from datetime import datetime, timedelta, timezone
import hashlib
import json
import logging
from typing import Any, Dict, List, Optional, Tuple
from fastapi import HTTPException, status
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.billing import (
    BillingEvent,
    Invoice,
    Plan,
    PlanLimit,
    Subscription,
    UsageCounter,
)
from app.models.organization import Organization
from app.models.user import User
from app.schemas.billing import (
    InvoiceResponse,
    PlanLimitResponse,
    PlanResponse,
    QuotaStatusResponse,
    SubscriptionCancelResponse,
    SubscriptionResponse,
    UsageMetricResponse,
)
from app.billing.provider import payment_provider

logger = logging.getLogger(__name__)

DEFAULT_FREE_PLAN_NAME = "student_free"


def get_current_utc_month_bounds() -> Tuple[datetime, datetime]:
    """Calculate the first and last instant of the current calendar month in UTC."""
    now = datetime.now(timezone.utc)
    start = datetime(now.year, now.month, 1, 0, 0, 0, tzinfo=timezone.utc)
    if now.month == 12:
        end = datetime(now.year + 1, 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    else:
        end = datetime(now.year, now.month + 1, 1, 0, 0, 0, tzinfo=timezone.utc)
    return start, end


class BillingService:
    """Core domain service for billing, subscriptions, and quota enforcement."""

    @staticmethod
    async def list_active_plans(db: AsyncSession) -> List[PlanResponse]:
        """Retrieve all active plans with their configured quota limits."""
        stmt = (
            select(Plan)
            .where(Plan.status == "active")
            .options(selectinload(Plan.limits))
            .order_by(Plan.price_minor_units.asc())
        )
        plans = (await db.execute(stmt)).scalars().all()

        results = []
        for p in plans:
            try:
                features = json.loads(p.features_json)
            except Exception:
                features = {}

            limits_dtos = [
                PlanLimitResponse(
                    limit_key=l.limit_key,
                    limit_value=l.limit_value,
                    period=l.period,
                )
                for l in p.limits
            ]
            results.append(
                PlanResponse(
                    id=p.id,
                    name=p.name,
                    status=p.status,
                    billing_interval=p.billing_interval,
                    price_minor_units=p.price_minor_units,
                    price_usd=p.price_minor_units / 100.0,
                    currency=p.currency,
                    features=features,
                    limits=limits_dtos,
                )
            )
        return results

    @staticmethod
    async def get_plan_by_name(db: AsyncSession, name: str) -> Optional[Plan]:
        """Fetch a plan and its limits by unique name."""
        stmt = (
            select(Plan)
            .where(Plan.name == name)
            .options(selectinload(Plan.limits))
        )
        return (await db.execute(stmt)).scalars().first()

    @staticmethod
    async def resolve_billing_subject_subscription(
        db: AsyncSession,
        billing_subject_type: str,
        billing_subject_id: str,
    ) -> Tuple[Optional[Subscription], Plan, datetime, datetime]:
        """
        Resolves the active subscription and applicable plan for a user or organization.
        If no paid subscription exists, returns the default student_free plan and current month bounds.
        """
        # Look for explicit subscription record
        stmt = (
            select(Subscription)
            .where(
                (Subscription.organization_id == billing_subject_id)
                if billing_subject_type == "organization"
                else (Subscription.user_id == billing_subject_id)
            )
            .options(selectinload(Subscription.plan).selectinload(Plan.limits))
            .order_by(Subscription.created_at.desc())
        )
        sub = (await db.execute(stmt)).scalars().first()

        now = datetime.now(timezone.utc)
        if sub and sub.status in ("active", "trialing"):
            return sub, sub.plan, sub.current_period_start, sub.current_period_end

        # Fallback to default free plan
        free_plan = await BillingService.get_plan_by_name(db, DEFAULT_FREE_PLAN_NAME)
        if not free_plan:
            # Fallback query if seeded differently
            stmt_any = select(Plan).options(selectinload(Plan.limits)).order_by(Plan.price_minor_units.asc())
            free_plan = (await db.execute(stmt_any)).scalars().first()
            if not free_plan:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail={"code": "NO_BILLING_PLANS", "message": "No billing plans configured in database."},
                )

        month_start, month_end = get_current_utc_month_bounds()
        return sub, free_plan, month_start, month_end

    @staticmethod
    async def reserve_submission_quota(
        db: AsyncSession,
        billing_subject_type: str,
        billing_subject_id: str,
    ) -> Dict[str, Any]:
        """
        Atomically checks and reserves 1 submission quota unit for the billing subject.
        Prevents race conditions using atomic database increments with upper-bound conditions.
        Raises HTTP 429 Too Many Requests if the monthly submission quota is exhausted.
        Raises HTTP 402 Payment Required if subscription is past_due or canceled.
        """
        sub, plan, period_start, period_end = await BillingService.resolve_billing_subject_subscription(
            db, billing_subject_type, billing_subject_id
        )

        # Check subscription status if an explicit record exists
        if sub and sub.status in ("past_due", "canceled", "unpaid"):
            now = datetime.now(timezone.utc)
            if sub.current_period_end < now:
                raise HTTPException(
                    status_code=status.HTTP_402_PAYMENT_REQUIRED,
                    detail={
                        "code": "SUBSCRIPTION_INACTIVE",
                        "message": f"Subscription status is {sub.status}. Please renew your plan to continue evaluating code.",
                        "status": sub.status,
                    },
                )

        # Find submissions_per_month limit
        limit_val = 50  # conservative default if limit record missing
        for lim in plan.limits:
            if lim.limit_key == "submissions_per_month":
                limit_val = lim.limit_value
                break

        # Ensure usage counter row exists for current monthly period
        stmt_counter = select(UsageCounter).where(
            UsageCounter.billing_subject_type == billing_subject_type,
            UsageCounter.billing_subject_id == billing_subject_id,
            UsageCounter.metric_key == "submissions",
            UsageCounter.period_start == period_start,
        )
        counter = (await db.execute(stmt_counter)).scalar_one_or_none()

        if not counter:
            counter = UsageCounter(
                billing_subject_type=billing_subject_type,
                billing_subject_id=billing_subject_id,
                metric_key="submissions",
                period_start=period_start,
                period_end=period_end,
                used_quantity=0,
            )
            db.add(counter)
            await db.flush()

        # Quota check
        if counter.used_quantity >= limit_val:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "QUOTA_EXCEEDED",
                    "message": f"Monthly submission quota of {limit_val} has been reached for this billing period.",
                    "limit": limit_val,
                    "used": counter.used_quantity,
                    "period_end": period_end.isoformat(),
                },
            )

        # Atomic reservation increment with concurrency lock condition
        stmt_atomic = (
            update(UsageCounter)
            .where(
                UsageCounter.id == counter.id,
                UsageCounter.used_quantity < limit_val,
            )
            .values(
                used_quantity=UsageCounter.used_quantity + 1,
                updated_at=datetime.now(timezone.utc),
            )
        )
        result = await db.execute(stmt_atomic)
        if result.rowcount == 0:
            # Another concurrent request grabbed the last remaining quota
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "QUOTA_EXCEEDED",
                    "message": f"Monthly submission quota of {limit_val} has been reached.",
                    "limit": limit_val,
                    "used": limit_val,
                },
            )

        await db.flush()
        return {
            "reserved": True,
            "billing_subject_type": billing_subject_type,
            "billing_subject_id": billing_subject_id,
            "metric": "submissions",
            "period_start": period_start,
        }

    @staticmethod
    async def release_submission_quota(
        db: AsyncSession,
        billing_subject_type: str,
        billing_subject_id: str,
        count: int = 1,
    ) -> None:
        """
        Releases reserved quota when an evaluation cannot be dispatched or encounters
        immediate infrastructure failure before sandboxed execution.
        """
        try:
            _, _, period_start, _ = await BillingService.resolve_billing_subject_subscription(
                db, billing_subject_type, billing_subject_id
            )
            stmt = (
                update(UsageCounter)
                .where(
                    UsageCounter.billing_subject_type == billing_subject_type,
                    UsageCounter.billing_subject_id == billing_subject_id,
                    UsageCounter.metric_key == "submissions",
                    UsageCounter.period_start == period_start,
                    UsageCounter.used_quantity >= count,
                )
                .values(
                    used_quantity=UsageCounter.used_quantity - count,
                    updated_at=datetime.now(timezone.utc),
                )
            )
            await db.execute(stmt)
            await db.flush()
        except Exception as exc:
            logger.error(f"Failed to release quota reservation for {billing_subject_id}: {exc}")

    @staticmethod
    async def record_execution_seconds(
        db: AsyncSession,
        billing_subject_type: str,
        billing_subject_id: str,
        duration_seconds: float,
    ) -> None:
        """Records actual sandboxed execution duration into the current billing period counter."""
        if duration_seconds <= 0:
            return

        try:
            _, _, period_start, period_end = await BillingService.resolve_billing_subject_subscription(
                db, billing_subject_type, billing_subject_id
            )
            stmt_counter = select(UsageCounter).where(
                UsageCounter.billing_subject_type == billing_subject_type,
                UsageCounter.billing_subject_id == billing_subject_id,
                UsageCounter.metric_key == "execution_seconds",
                UsageCounter.period_start == period_start,
            )
            counter = (await db.execute(stmt_counter)).scalar_one_or_none()

            seconds_int = int(round(duration_seconds))
            if not counter:
                counter = UsageCounter(
                    billing_subject_type=billing_subject_type,
                    billing_subject_id=billing_subject_id,
                    metric_key="execution_seconds",
                    period_start=period_start,
                    period_end=period_end,
                    used_quantity=seconds_int,
                )
                db.add(counter)
            else:
                counter.used_quantity += seconds_int
                counter.updated_at = datetime.now(timezone.utc)

            await db.flush()
        except Exception as exc:
            logger.error(f"Failed to record execution seconds for {billing_subject_id}: {exc}")

    @staticmethod
    async def get_quota_status(
        db: AsyncSession,
        billing_subject_type: str,
        billing_subject_id: str,
    ) -> QuotaStatusResponse:
        """Retrieve quota status, limits, and current usage for caller or organization."""
        sub, plan, period_start, period_end = await BillingService.resolve_billing_subject_subscription(
            db, billing_subject_type, billing_subject_id
        )

        # Fetch usage counters for current period
        stmt_counters = select(UsageCounter).where(
            UsageCounter.billing_subject_type == billing_subject_type,
            UsageCounter.billing_subject_id == billing_subject_id,
            UsageCounter.period_start == period_start,
        )
        counters = (await db.execute(stmt_counters)).scalars().all()
        usage_map = {c.metric_key: c.used_quantity for c in counters}

        quota_metrics = []
        can_submit = True

        for lim in plan.limits:
            metric_lookup = "submissions" if lim.limit_key == "submissions_per_month" else (
                "execution_seconds" if lim.limit_key == "execution_seconds_per_month" else lim.limit_key
            )
            used = usage_map.get(metric_lookup, 0)
            remaining = max(0, lim.limit_value - used)
            if lim.limit_key == "submissions_per_month" and remaining <= 0:
                can_submit = False

            quota_metrics.append(
                UsageMetricResponse(
                    metric_key=lim.limit_key,
                    used=used,
                    limit=lim.limit_value,
                    remaining=remaining,
                    period=lim.period,
                )
            )

        status_str = sub.status if sub else "active"
        if sub and sub.status in ("past_due", "canceled", "unpaid") and sub.current_period_end < datetime.now(timezone.utc):
            can_submit = False

        return QuotaStatusResponse(
            billing_subject_type=billing_subject_type,
            billing_subject_id=billing_subject_id,
            plan_name=plan.name,
            subscription_status=status_str,
            current_period_start=period_start,
            current_period_end=period_end,
            quotas=quota_metrics,
            can_submit=can_submit,
        )

    @staticmethod
    async def process_stripe_webhook(
        db: AsyncSession,
        event_dict: Dict[str, Any],
        raw_payload: bytes,
    ) -> Dict[str, Any]:
        """
        Idempotently processes verified Stripe webhook events.
        Records BillingEvent audit log and updates Subscription and Invoice records.
        """
        event_id = event_dict.get("id")
        event_type = event_dict.get("type")
        if not event_id or not event_type:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "INVALID_WEBHOOK_PAYLOAD", "message": "Missing event id or type."},
            )

        payload_hash = hashlib.sha256(raw_payload).hexdigest()

        # Idempotency check: verify if already processed
        stmt_audit = select(BillingEvent).where(
            BillingEvent.provider == "stripe",
            BillingEvent.provider_event_id == event_id,
        )
        existing_event = (await db.execute(stmt_audit)).scalar_one_or_none()
        if existing_event:
            logger.info(f"Duplicate webhook {event_id} ({event_type}) received; skipping side-effects.")
            return {
                "received": True,
                "event_id": event_id,
                "event_type": event_type,
                "status": "duplicate_ignored",
            }

        # Record billing event
        audit = BillingEvent(
            provider="stripe",
            provider_event_id=event_id,
            event_type=event_type,
            payload_hash=payload_hash,
            processing_status="processed",
            processed_at=datetime.now(timezone.utc),
        )
        db.add(audit)

        data_obj = event_dict.get("data", {}).get("object", {})

        # Handle specific webhook event types
        if event_type == "checkout.session.completed":
            await BillingService._handle_checkout_completed(db, data_obj)
        elif event_type in ("customer.subscription.updated", "customer.subscription.created"):
            await BillingService._handle_subscription_updated(db, data_obj)
        elif event_type == "customer.subscription.deleted":
            await BillingService._handle_subscription_deleted(db, data_obj)
        elif event_type == "invoice.payment_succeeded":
            await BillingService._handle_invoice_succeeded(db, data_obj)
        elif event_type == "invoice.payment_failed":
            await BillingService._handle_invoice_failed(db, data_obj)

        await db.commit()
        return {
            "received": True,
            "event_id": event_id,
            "event_type": event_type,
            "status": "processed",
        }

    @staticmethod
    async def _handle_checkout_completed(db: AsyncSession, session_obj: Dict[str, Any]) -> None:
        """Handle checkout.session.completed from Stripe."""
        meta = session_obj.get("metadata", {})
        subject_type = meta.get("billing_subject_type")
        subject_id = meta.get("billing_subject_id")
        plan_name = meta.get("plan_name")
        customer_id = session_obj.get("customer") or "cust_unknown"
        provider_sub_id = session_obj.get("subscription")

        if not subject_type or not subject_id or not plan_name:
            logger.warning(f"Checkout completed without billing metadata: {session_obj.get('id')}")
            return

        plan = await BillingService.get_plan_by_name(db, plan_name)
        if not plan:
            return

        now = datetime.now(timezone.utc)
        period_end = now + timedelta(days=30)

        # Check existing subscription
        stmt = select(Subscription).where(
            (Subscription.organization_id == subject_id)
            if subject_type == "organization"
            else (Subscription.user_id == subject_id)
        )
        sub = (await db.execute(stmt)).scalar_one_or_none()

        if sub:
            sub.plan_id = plan.id
            sub.provider = "stripe"
            sub.provider_customer_id = customer_id
            sub.provider_subscription_id = provider_sub_id
            sub.status = "active"
            sub.current_period_start = now
            sub.current_period_end = period_end
            sub.cancel_at_period_end = False
        else:
            sub = Subscription(
                organization_id=subject_id if subject_type == "organization" else None,
                user_id=subject_id if subject_type == "user" else None,
                plan_id=plan.id,
                provider="stripe",
                provider_customer_id=customer_id,
                provider_subscription_id=provider_sub_id,
                status="active",
                current_period_start=now,
                current_period_end=period_end,
                cancel_at_period_end=False,
            )
            db.add(sub)
        await db.flush()

    @staticmethod
    async def _handle_subscription_updated(db: AsyncSession, sub_obj: Dict[str, Any]) -> None:
        """Reconcile subscription updates."""
        provider_sub_id = sub_obj.get("id")
        if not provider_sub_id:
            return

        stmt = select(Subscription).where(Subscription.provider_subscription_id == provider_sub_id)
        sub = (await db.execute(stmt)).scalar_one_or_none()
        if not sub:
            return

        status_str = sub_obj.get("status", "active")
        sub.status = status_str
        sub.cancel_at_period_end = bool(sub_obj.get("cancel_at_period_end", False))

        start_ts = sub_obj.get("current_period_start")
        end_ts = sub_obj.get("current_period_end")
        if start_ts:
            sub.current_period_start = datetime.fromtimestamp(start_ts, tz=timezone.utc)
        if end_ts:
            sub.current_period_end = datetime.fromtimestamp(end_ts, tz=timezone.utc)
        await db.flush()

    @staticmethod
    async def _handle_subscription_deleted(db: AsyncSession, sub_obj: Dict[str, Any]) -> None:
        """Mark subscription as canceled."""
        provider_sub_id = sub_obj.get("id")
        if not provider_sub_id:
            return

        stmt = select(Subscription).where(Subscription.provider_subscription_id == provider_sub_id)
        sub = (await db.execute(stmt)).scalar_one_or_none()
        if sub:
            sub.status = "canceled"
            await db.flush()

    @staticmethod
    async def _handle_invoice_succeeded(db: AsyncSession, inv_obj: Dict[str, Any]) -> None:
        """Record paid invoice and activate subscription."""
        inv_id = inv_obj.get("id")
        provider_sub_id = inv_obj.get("subscription")
        if not inv_id or not provider_sub_id:
            return

        stmt = select(Subscription).where(Subscription.provider_subscription_id == provider_sub_id)
        sub = (await db.execute(stmt)).scalar_one_or_none()
        if not sub:
            return

        sub.status = "active"

        # Check existing invoice
        stmt_inv = select(Invoice).where(Invoice.provider_invoice_id == inv_id)
        invoice = (await db.execute(stmt_inv)).scalar_one_or_none()

        now = datetime.now(timezone.utc)
        amount = inv_obj.get("amount_paid", 0)
        currency = (inv_obj.get("currency") or "USD").upper()

        if invoice:
            invoice.status = "paid"
            invoice.paid_at = now
        else:
            invoice = Invoice(
                subscription_id=sub.id,
                provider_invoice_id=inv_id,
                amount_minor_units=amount,
                currency=currency,
                status="paid",
                issued_at=now,
                paid_at=now,
            )
            db.add(invoice)
        await db.flush()

    @staticmethod
    async def _handle_invoice_failed(db: AsyncSession, inv_obj: Dict[str, Any]) -> None:
        """Handle payment failure on renewal invoice."""
        inv_id = inv_obj.get("id")
        provider_sub_id = inv_obj.get("subscription")
        if not inv_id or not provider_sub_id:
            return

        stmt = select(Subscription).where(Subscription.provider_subscription_id == provider_sub_id)
        sub = (await db.execute(stmt)).scalar_one_or_none()
        if not sub:
            return

        sub.status = "past_due"

        now = datetime.now(timezone.utc)
        amount = inv_obj.get("amount_due", 0)
        currency = (inv_obj.get("currency") or "USD").upper()

        invoice = Invoice(
            subscription_id=sub.id,
            provider_invoice_id=inv_id,
            amount_minor_units=amount,
            currency=currency,
            status="open",
            issued_at=now,
            paid_at=None,
        )
        db.add(invoice)
        await db.flush()

    @staticmethod
    async def get_subscription_details(
        db: AsyncSession,
        billing_subject_type: str,
        billing_subject_id: str,
    ) -> SubscriptionResponse:
        """Fetch subscription details, or synthetic default free subscription if none active."""
        sub, plan, period_start, period_end = await BillingService.resolve_billing_subject_subscription(
            db, billing_subject_type, billing_subject_id
        )
        if sub:
            return SubscriptionResponse(
                id=sub.id,
                plan_name=plan.name,
                plan_display_name=plan.name.replace("_", " ").title(),
                status=sub.status,
                billing_subject_type=billing_subject_type,
                billing_subject_id=billing_subject_id,
                provider=sub.provider,
                provider_subscription_id=sub.provider_subscription_id,
                current_period_start=sub.current_period_start,
                current_period_end=sub.current_period_end,
                cancel_at_period_end=sub.cancel_at_period_end,
                is_active=(sub.status in ("active", "trialing")),
            )

        # Free tier virtual subscription
        return SubscriptionResponse(
            id=f"sub_free_{billing_subject_id}",
            plan_name=plan.name,
            plan_display_name="Student Free Plan",
            status="active",
            billing_subject_type=billing_subject_type,
            billing_subject_id=billing_subject_id,
            provider="platform",
            provider_subscription_id=None,
            current_period_start=period_start,
            current_period_end=period_end,
            cancel_at_period_end=False,
            is_active=True,
        )

    @staticmethod
    async def cancel_subscription(
        db: AsyncSession,
        billing_subject_type: str,
        billing_subject_id: str,
        at_period_end: bool = True,
    ) -> SubscriptionCancelResponse:
        """Request subscription cancellation, with real provider cancellation if configured."""
        stmt = (
            select(Subscription)
            .where(
                (Subscription.organization_id == billing_subject_id)
                if billing_subject_type == "organization"
                else (Subscription.user_id == billing_subject_id)
            )
            .order_by(Subscription.created_at.desc())
        )
        sub = (await db.execute(stmt)).scalars().first()
        if not sub or sub.status == "canceled":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail={"code": "NO_ACTIVE_SUBSCRIPTION", "message": "No active paid subscription found to cancel."},
            )

        # If connected to a real provider subscription, cancel with provider if configured
        if sub.provider_subscription_id and payment_provider.is_configured():
            try:
                await payment_provider.cancel_subscription(
                    sub.provider_subscription_id,
                    at_period_end=at_period_end,
                )
            except Exception as exc:
                logger.error(f"Provider cancellation failed for {sub.provider_subscription_id}: {exc}")

        if at_period_end:
            sub.cancel_at_period_end = True
            msg = f"Subscription will cancel at the end of the current billing period ({sub.current_period_end.isoformat()})."
        else:
            sub.status = "canceled"
            sub.cancel_at_period_end = False
            msg = "Subscription canceled immediately."

        await db.commit()
        return SubscriptionCancelResponse(
            subscription_id=sub.id,
            status=sub.status,
            cancel_at_period_end=sub.cancel_at_period_end,
            message=msg,
        )

    @staticmethod
    async def list_invoices(
        db: AsyncSession,
        billing_subject_type: str,
        billing_subject_id: str,
    ) -> List[InvoiceResponse]:
        """Fetch all billing invoices for the subject."""
        stmt = (
            select(Invoice)
            .join(Subscription, Invoice.subscription_id == Subscription.id)
            .where(
                (Subscription.organization_id == billing_subject_id)
                if billing_subject_type == "organization"
                else (Subscription.user_id == billing_subject_id)
            )
            .order_by(Invoice.issued_at.desc())
        )
        invoices = (await db.execute(stmt)).scalars().all()
        return [
            InvoiceResponse(
                id=inv.id,
                provider_invoice_id=inv.provider_invoice_id,
                amount_minor_units=inv.amount_minor_units,
                amount_usd=inv.amount_minor_units / 100.0,
                currency=inv.currency,
                status=inv.status,
                issued_at=inv.issued_at,
                paid_at=inv.paid_at,
            )
            for inv in invoices
        ]
