"""seed_subscription_plans

Revision ID: f91c7a8b3d21
Revises: e89a3f2b4c10
Create Date: 2026-10-16 12:00:00.000000

"""
from datetime import datetime, timezone
import json
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f91c7a8b3d21'
down_revision: Union[str, Sequence[str], None] = 'e89a3f2b4c10'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add billing indexes and seed default subscription plans."""
    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.create_index(
            'ix_subscriptions_user_status',
            ['user_id', 'status'],
            unique=False
        )
        batch_op.create_index(
            'ix_subscriptions_org_status',
            ['organization_id', 'status'],
            unique=False
        )

    with op.batch_alter_table('usage_counters', schema=None) as batch_op:
        batch_op.create_index(
            'ix_usage_counters_subject',
            ['billing_subject_type', 'billing_subject_id'],
            unique=False
        )

    # Seed Default Plans and Limits
    plans_table = sa.table(
        'plans',
        sa.column('id', sa.String(36)),
        sa.column('name', sa.String(64)),
        sa.column('status', sa.String(32)),
        sa.column('billing_interval', sa.String(32)),
        sa.column('price_minor_units', sa.Integer()),
        sa.column('currency', sa.String(3)),
        sa.column('features_json', sa.Text()),
        sa.column('created_at', sa.DateTime(timezone=True)),
        sa.column('updated_at', sa.DateTime(timezone=True)),
    )

    plan_limits_table = sa.table(
        'plan_limits',
        sa.column('id', sa.String(36)),
        sa.column('plan_id', sa.String(36)),
        sa.column('limit_key', sa.String(64)),
        sa.column('limit_value', sa.Integer()),
        sa.column('period', sa.String(32)),
        sa.column('created_at', sa.DateTime(timezone=True)),
        sa.column('updated_at', sa.DateTime(timezone=True)),
    )

    now = datetime.now(timezone.utc)
    free_plan_id = "plan_student_free_default"
    pro_plan_id = "plan_student_pro_default"
    institution_plan_id = "plan_institution_standard_default"

    plans_data = [
        {
            "id": free_plan_id,
            "name": "student_free",
            "status": "active",
            "billing_interval": "month",
            "price_minor_units": 0,
            "currency": "USD",
            "features_json": json.dumps({
                "display_title": "Student Free Tier",
                "ast_evaluation": True,
                "public_problems": True,
                "priority_queue": False,
                "cohort_analytics": False,
            }),
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": pro_plan_id,
            "name": "student_pro",
            "status": "active",
            "billing_interval": "month",
            "price_minor_units": 1200,  # $12.00 / month
            "currency": "USD",
            "features_json": json.dumps({
                "display_title": "Student Pro Tier",
                "ast_evaluation": True,
                "public_problems": True,
                "priority_queue": True,
                "advanced_hints": True,
                "cohort_analytics": False,
            }),
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": institution_plan_id,
            "name": "institution_standard",
            "status": "active",
            "billing_interval": "month",
            "price_minor_units": 19900,  # $199.00 / month
            "currency": "USD",
            "features_json": json.dumps({
                "display_title": "Institution Standard Tier",
                "ast_evaluation": True,
                "public_problems": True,
                "priority_queue": True,
                "classrooms_unlimited": True,
                "cohort_analytics": True,
                "faculty_review": True,
            }),
            "created_at": now,
            "updated_at": now,
        },
    ]

    limits_data = [
        # Student Free limits
        {
            "id": "limit_free_submissions",
            "plan_id": free_plan_id,
            "limit_key": "submissions_per_month",
            "limit_value": 50,
            "period": "month",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "limit_free_execution_seconds",
            "plan_id": free_plan_id,
            "limit_key": "execution_seconds_per_month",
            "limit_value": 300,
            "period": "month",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "limit_free_seats",
            "plan_id": free_plan_id,
            "limit_key": "seats",
            "limit_value": 1,
            "period": "month",
            "created_at": now,
            "updated_at": now,
        },
        # Student Pro limits
        {
            "id": "limit_pro_submissions",
            "plan_id": pro_plan_id,
            "limit_key": "submissions_per_month",
            "limit_value": 1000,
            "period": "month",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "limit_pro_execution_seconds",
            "plan_id": pro_plan_id,
            "limit_key": "execution_seconds_per_month",
            "limit_value": 7200,
            "period": "month",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "limit_pro_seats",
            "plan_id": pro_plan_id,
            "limit_key": "seats",
            "limit_value": 1,
            "period": "month",
            "created_at": now,
            "updated_at": now,
        },
        # Institution Standard limits
        {
            "id": "limit_inst_submissions",
            "plan_id": institution_plan_id,
            "limit_key": "submissions_per_month",
            "limit_value": 25000,
            "period": "month",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "limit_inst_execution_seconds",
            "plan_id": institution_plan_id,
            "limit_key": "execution_seconds_per_month",
            "limit_value": 180000,
            "period": "month",
            "created_at": now,
            "updated_at": now,
        },
        {
            "id": "limit_inst_seats",
            "plan_id": institution_plan_id,
            "limit_key": "seats",
            "limit_value": 100,
            "period": "month",
            "created_at": now,
            "updated_at": now,
        },
    ]

    op.bulk_insert(plans_table, plans_data)
    op.bulk_insert(plan_limits_table, limits_data)


def downgrade() -> None:
    """Revert billing indexes and seeded plans."""
    op.execute("DELETE FROM plan_limits WHERE plan_id IN ('plan_student_free_default', 'plan_student_pro_default', 'plan_institution_standard_default')")
    op.execute("DELETE FROM plans WHERE id IN ('plan_student_free_default', 'plan_student_pro_default', 'plan_institution_standard_default')")

    with op.batch_alter_table('usage_counters', schema=None) as batch_op:
        batch_op.drop_index('ix_usage_counters_subject')

    with op.batch_alter_table('subscriptions', schema=None) as batch_op:
        batch_op.drop_index('ix_subscriptions_org_status')
        batch_op.drop_index('ix_subscriptions_user_status')
