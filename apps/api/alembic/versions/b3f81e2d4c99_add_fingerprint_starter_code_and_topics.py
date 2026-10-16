"""add_fingerprint_starter_code_and_topics

Revision ID: b3f81e2d4c99
Revises: a7c3b2e1d0f5
Create Date: 2026-10-16 15:00:00.000000

"""
from datetime import datetime, timezone
import hashlib
import re
from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b3f81e2d4c99'
down_revision: Union[str, Sequence[str], None] = 'a7c3b2e1d0f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def normalize_text(text: str) -> str:
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r"[^\w\s]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def compute_content_fingerprint(title: str, statement: str) -> str:
    norm_title = normalize_text(title)
    norm_statement = normalize_text(statement[:300] if statement else "")
    payload = f"{norm_title}::{norm_statement}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)

    # 1. Add content_fingerprint to problems
    prob_cols = {c['name'] for c in inspector.get_columns('problems')}
    if 'content_fingerprint' not in prob_cols:
        op.add_column('problems', sa.Column('content_fingerprint', sa.String(length=64), nullable=True))
        op.create_index('ix_problems_content_fingerprint', 'problems', ['content_fingerprint'], unique=False)

    # 2. Add starter_code and content_fingerprint to problem_versions
    pv_cols = {c['name'] for c in inspector.get_columns('problem_versions')}
    if 'starter_code' not in pv_cols:
        op.add_column('problem_versions', sa.Column('starter_code', sa.Text(), nullable=True))
    if 'content_fingerprint' not in pv_cols:
        op.add_column('problem_versions', sa.Column('content_fingerprint', sa.String(length=64), nullable=True))
        op.create_index('ix_problem_versions_content_fingerprint', 'problem_versions', ['content_fingerprint'], unique=False)

    # 3. Backfill fingerprints for existing problem_versions and problems
    pvs = bind.execute(sa.text("SELECT id, problem_id, title, statement_markdown FROM problem_versions")).fetchall()
    for pv_id, prob_id, title, statement in pvs:
        fp = compute_content_fingerprint(title or "", statement or "")
        bind.execute(
            sa.text("UPDATE problem_versions SET content_fingerprint = :fp WHERE id = :id"),
            {"fp": fp, "id": pv_id}
        )
        bind.execute(
            sa.text("UPDATE problems SET content_fingerprint = :fp WHERE id = :pid"),
            {"fp": fp, "pid": prob_id}
        )

    # 4. Seed new professional taxonomy topics if not present
    existing_slugs = {row[0] for row in bind.execute(sa.text("SELECT slug FROM problem_topics")).fetchall()}
    new_topics = [
        ("Heaps", "heaps"),
        ("Binary Search", "binary-search"),
        ("Greedy Algorithms", "greedy"),
        ("Backtracking", "backtracking"),
        ("Bit Manipulation", "bit-manipulation"),
        ("SQL", "sql"),
    ]

    now = datetime.now(timezone.utc)
    for name, slug in new_topics:
        if slug not in existing_slugs:
            bind.execute(
                sa.text("""
                    INSERT INTO problem_topics (id, name, slug, created_at, updated_at)
                    VALUES (:id, :name, :slug, :now, :now)
                """),
                {
                    "id": str(uuid.uuid4()),
                    "name": name,
                    "slug": slug,
                    "now": now,
                }
            )


def downgrade() -> None:
    # Downgrade logic if needed
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    prob_cols = {c['name'] for c in inspector.get_columns('problems')}
    if 'content_fingerprint' in prob_cols:
        op.drop_index('ix_problems_content_fingerprint', table_name='problems')
        op.drop_column('problems', 'content_fingerprint')

    pv_cols = {c['name'] for c in inspector.get_columns('problem_versions')}
    if 'content_fingerprint' in pv_cols:
        op.drop_index('ix_problem_versions_content_fingerprint', table_name='problem_versions')
        op.drop_column('problem_versions', 'content_fingerprint')
    if 'starter_code' in pv_cols:
        op.drop_column('problem_versions', 'starter_code')
