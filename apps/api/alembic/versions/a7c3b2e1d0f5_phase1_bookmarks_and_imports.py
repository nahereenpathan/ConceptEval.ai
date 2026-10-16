"""phase1_bookmarks_and_imports

Revision ID: a7c3b2e1d0f5
Revises: f91c7a8b3d21
Create Date: 2026-10-16 13:00:00.000000

"""
from datetime import datetime, timezone
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a7c3b2e1d0f5'
down_revision: Union[str, Sequence[str], None] = 'f91c7a8b3d21'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Create problem_bookmarks, content_import_audits, and seed standard problem topics."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # 1. Create problem_bookmarks table
    if 'problem_bookmarks' not in existing_tables:
        op.create_table(
            'problem_bookmarks',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('user_id', sa.String(length=36), nullable=False),
            sa.Column('problem_id', sa.String(length=36), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['problem_id'], ['problems.id'], ondelete='CASCADE'),
            sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
            sa.PrimaryKeyConstraint('id'),
            sa.UniqueConstraint('user_id', 'problem_id', name='uq_user_problem_bookmark')
        )
        op.create_index('ix_problem_bookmarks_problem_id', 'problem_bookmarks', ['problem_id'], unique=False)
        op.create_index('ix_problem_bookmarks_user_id', 'problem_bookmarks', ['user_id'], unique=False)

    # 2. Create content_import_audits table
    if 'content_import_audits' not in existing_tables:
        op.create_table(
            'content_import_audits',
            sa.Column('id', sa.String(length=36), nullable=False),
            sa.Column('imported_by_user_id', sa.String(length=36), nullable=False),
            sa.Column('source_name', sa.String(length=255), nullable=False),
            sa.Column('license_type', sa.String(length=64), nullable=False),
            sa.Column('provenance_url', sa.String(length=512), nullable=True),
            sa.Column('format', sa.String(length=32), nullable=False),
            sa.Column('total_processed', sa.Integer(), nullable=False),
            sa.Column('imported_count', sa.Integer(), nullable=False),
            sa.Column('skipped_duplicates', sa.Integer(), nullable=False),
            sa.Column('errors_json', sa.Text(), nullable=True),
            sa.Column('import_metadata_json', sa.Text(), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
            sa.ForeignKeyConstraint(['imported_by_user_id'], ['users.id']),
            sa.PrimaryKeyConstraint('id')
        )
        op.create_index('ix_content_import_audits_imported_by_user_id', 'content_import_audits', ['imported_by_user_id'], unique=False)

    # 3. Seed standard topic taxonomy (avoid duplicates)
    bind = op.get_bind()
    existing_slugs = {row[0] for row in bind.execute(sa.text("SELECT slug FROM problem_topics")).fetchall()}

    standard_topics = [
        ("Arrays", "arrays"),
        ("Strings", "strings"),
        ("Hashing & Maps", "hashing"),
        ("Sorting", "sorting"),
        ("Searching", "searching"),
        ("Recursion", "recursion"),
        ("Loops & Iteration", "loops"),
        ("Functions", "functions"),
        ("Linked Lists", "linked-lists"),
        ("Stacks", "stacks"),
        ("Queues", "queues"),
        ("Trees", "trees"),
        ("Graphs", "graphs"),
        ("Dynamic Programming", "dynamic-programming"),
        ("OOP & Classes", "oop"),
        ("Math", "math"),
    ]

    topics_table = sa.table(
        'problem_topics',
        sa.column('id', sa.String),
        sa.column('name', sa.String),
        sa.column('slug', sa.String),
        sa.column('created_at', sa.DateTime),
        sa.column('updated_at', sa.DateTime),
    )

    now = datetime.now(timezone.utc)
    seed_topic_rows = []
    for name, slug in standard_topics:
        if slug not in existing_slugs:
            seed_topic_rows.append({
                'id': str(uuid.uuid4()),
                'name': name,
                'slug': slug,
                'created_at': now,
                'updated_at': now,
            })

    if seed_topic_rows:
        op.bulk_insert(topics_table, seed_topic_rows)

    # 4. Associate existing problem versions with their respective topics
    assignments_table = sa.table(
        'problem_topic_assignments',
        sa.column('id', sa.String),
        sa.column('problem_version_id', sa.String),
        sa.column('topic_id', sa.String),
    )

    all_topics = {row[0]: row[1] for row in bind.execute(sa.text("SELECT slug, id FROM problem_topics")).fetchall()}
    existing_assignments = {
        (row[0], row[1])
        for row in bind.execute(sa.text("SELECT problem_version_id, topic_id FROM problem_topic_assignments")).fetchall()
    }

    topic_assignments = []
    if 'loops' in all_topics:
        pair = ('87a50837-40af-4d7d-b4c2-5e5ca8c8bb2a', all_topics['loops'])
        if pair not in existing_assignments:
            topic_assignments.append({
                'id': str(uuid.uuid4()),
                'problem_version_id': pair[0],
                'topic_id': pair[1],
            })

    if 'recursion' in all_topics:
        pair = ('dce7e7bc-c459-403c-8319-fd21c68d309e', all_topics['recursion'])
        if pair not in existing_assignments:
            topic_assignments.append({
                'id': str(uuid.uuid4()),
                'problem_version_id': pair[0],
                'topic_id': pair[1],
            })

    if topic_assignments:
        op.bulk_insert(assignments_table, topic_assignments)


def downgrade() -> None:
    """Revert bookmarks and imports tables."""
    op.drop_table('content_import_audits')
    op.drop_table('problem_bookmarks')
