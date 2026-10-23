"""create skill tracker tables

Revision ID: 007_create_skill_tracker_tables
Revises: 006_create_adaptive_test_tables
Create Date: 2026-10-23

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '007_create_skill_tracker_tables'
down_revision: Union[str, None] = '006_create_adaptive_test_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. skills catalog table
    op.create_table(
        'skills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('aliases', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('category', sa.String(length=64), server_default='General', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_skills_slug'), 'skills', ['slug'], unique=True)

    # 2. skill_evidence append-only table
    op.create_table(
        'skill_evidence',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('source_type', sa.String(length=32), nullable=False),
        sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('score', sa.Integer(), nullable=True),
        sa.Column('level_signal', sa.String(length=32), nullable=True),
        sa.Column('subtopic_scores', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('summary', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('source_type', 'source_id', name='uq_skill_evidence_source'),
    )
    op.create_index(op.f('ix_skill_evidence_user_id'), 'skill_evidence', ['user_id'], unique=False)
    op.create_index(op.f('ix_skill_evidence_skill_id'), 'skill_evidence', ['skill_id'], unique=False)
    op.create_index('ix_skill_evidence_user_skill', 'skill_evidence', ['user_id', 'skill_id'], unique=False)

    # 3. user_skills aggregated state table
    op.create_table(
        'user_skills',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('current_level', sa.String(length=32), server_default='beginner', nullable=False),
        sa.Column('confidence', sa.String(length=32), server_default='low', nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'skill_id', name='uq_user_skill'),
    )
    op.create_index(op.f('ix_user_skills_user_id'), 'user_skills', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_skills_skill_id'), 'user_skills', ['skill_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_skills_skill_id'), table_name='user_skills')
    op.drop_index(op.f('ix_user_skills_user_id'), table_name='user_skills')
    op.drop_table('user_skills')

    op.drop_index('ix_skill_evidence_user_skill', table_name='skill_evidence')
    op.drop_index(op.f('ix_skill_evidence_skill_id'), table_name='skill_evidence')
    op.drop_index(op.f('ix_skill_evidence_user_id'), table_name='skill_evidence')
    op.drop_table('skill_evidence')

    op.drop_index(op.f('ix_skills_slug'), table_name='skills')
    op.drop_table('skills')
