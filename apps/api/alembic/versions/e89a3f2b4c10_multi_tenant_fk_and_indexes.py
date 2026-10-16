"""multi_tenant_fk_and_indexes

Revision ID: e89a3f2b4c10
Revises: 4ffec925a11f
Create Date: 2026-10-16 11:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'e89a3f2b4c10'
down_revision: Union[str, Sequence[str], None] = '4ffec925a11f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Add foreign key constraints and composite indexes for multi-tenant isolation."""
    with op.batch_alter_table('problems', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_problems_owner_organization_id',
            'organizations',
            ['owner_organization_id'],
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_index(
            'ix_problems_owner_org_status',
            ['owner_organization_id', 'status'],
            unique=False
        )

    with op.batch_alter_table('submissions', schema=None) as batch_op:
        batch_op.create_foreign_key(
            'fk_submissions_organization_id',
            'organizations',
            ['organization_id'],
            ['id'],
            ondelete='SET NULL'
        )
        batch_op.create_index(
            'ix_submissions_org_user',
            ['organization_id', 'user_id'],
            unique=False
        )


def downgrade() -> None:
    """Revert foreign key constraints and composite indexes."""
    with op.batch_alter_table('submissions', schema=None) as batch_op:
        batch_op.drop_index('ix_submissions_org_user')
        batch_op.drop_constraint('fk_submissions_organization_id', type_='foreignkey')

    with op.batch_alter_table('problems', schema=None) as batch_op:
        batch_op.drop_index('ix_problems_owner_org_status')
        batch_op.drop_constraint('fk_problems_owner_organization_id', type_='foreignkey')
