"""
SaaS Billing, Subscriptions, and Usage Enforcement Models
"""

from datetime import datetime, timezone
from typing import Optional
from sqlalchemy import BigInteger, Boolean, DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class Plan(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """SaaS subscription plan definition."""
    __tablename__ = "plans"

    name: Mapped[str] = mapped_column(String(64), unique=True, nullable=False)  # free, student_pro, institution
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)
    billing_interval: Mapped[str] = mapped_column(String(32), default="month", nullable=False)  # month, year
    price_minor_units: Mapped[int] = mapped_column(Integer, default=0, nullable=False)  # e.g. 1900 for $19.00
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    features_json: Mapped[str] = mapped_column(Text, default="{}", nullable=False)

    limits = relationship("PlanLimit", back_populates="plan", cascade="all, delete-orphan")
    subscriptions = relationship("Subscription", back_populates="plan")


class PlanLimit(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Quota policy limit for a plan (e.g. submissions_per_month, classroom_seats)."""
    __tablename__ = "plan_limits"

    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("plans.id", ondelete="CASCADE"), index=True, nullable=False)
    limit_key: Mapped[str] = mapped_column(String(64), nullable=False)  # submissions_per_month, execution_minutes, seats
    limit_value: Mapped[int] = mapped_column(Integer, nullable=False)
    period: Mapped[str] = mapped_column(String(32), default="month", nullable=False)  # month, day, lifetime

    plan = relationship("Plan", back_populates="limits")

    __table_args__ = (
        UniqueConstraint("plan_id", "limit_key", name="uq_plan_limit_key"),
    )


class Subscription(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Customer subscription mapping an organization or individual user to a plan."""
    __tablename__ = "subscriptions"

    organization_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("organizations.id", ondelete="SET NULL"), index=True, nullable=True)
    user_id: Mapped[Optional[str]] = mapped_column(String(36), ForeignKey("users.id", ondelete="SET NULL"), index=True, nullable=True)
    plan_id: Mapped[str] = mapped_column(String(36), ForeignKey("plans.id"), index=True, nullable=False)
    provider: Mapped[str] = mapped_column(String(32), default="stripe", nullable=False)
    provider_customer_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    provider_subscription_id: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    status: Mapped[str] = mapped_column(String(32), default="active", nullable=False)  # active, past_due, cancelled, trialing
    current_period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    current_period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    cancel_at_period_end: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    plan = relationship("Plan", back_populates="subscriptions")
    invoices = relationship("Invoice", back_populates="subscription", cascade="all, delete-orphan")


class BillingEvent(Base, UUIDPrimaryKeyMixin):
    """Idempotent audit record of verified webhooks received from payment providers."""
    __tablename__ = "billing_events"

    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_event_id: Mapped[str] = mapped_column(String(128), index=True, nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    processing_status: Mapped[str] = mapped_column(String(32), default="received", nullable=False)  # received, processed, failed, ignored
    received_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), nullable=False)
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        UniqueConstraint("provider", "provider_event_id", name="uq_billing_provider_event"),
    )


class UsageCounter(Base, UUIDPrimaryKeyMixin):
    """Aggregated usage metrics for quota calculation and quota enforcement."""
    __tablename__ = "usage_counters"

    billing_subject_type: Mapped[str] = mapped_column(String(32), nullable=False)  # user, organization
    billing_subject_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    metric_key: Mapped[str] = mapped_column(String(64), index=True, nullable=False)  # submissions, execution_seconds
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    used_quantity: Mapped[int] = mapped_column(BigInteger, default=0, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc), nullable=False)

    __table_args__ = (
        UniqueConstraint("billing_subject_type", "billing_subject_id", "metric_key", "period_start", name="uq_usage_counter_subject_metric_period"),
    )


class Invoice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Locally reconciled record of provider-issued invoices."""
    __tablename__ = "invoices"

    subscription_id: Mapped[str] = mapped_column(String(36), ForeignKey("subscriptions.id", ondelete="CASCADE"), index=True, nullable=False)
    provider_invoice_id: Mapped[str] = mapped_column(String(128), unique=True, index=True, nullable=False)
    amount_minor_units: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), default="USD", nullable=False)
    status: Mapped[str] = mapped_column(String(32), nullable=False)  # paid, open, void, uncollectible
    issued_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    subscription = relationship("Subscription", back_populates="invoices")
