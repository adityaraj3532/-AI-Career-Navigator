"""create careers and assessment results

Revision ID: 003_create_careers_and_assessment_results
Revises: 002_create_assessment_tables
Create Date: 2026-10-23

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '003_create_careers_and_assessment_results'
down_revision: Union[str, None] = '002_create_assessment_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. careers table
    op.create_table(
        'careers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('cluster', sa.String(length=128), nullable=False),
        sa.Column('overview', sa.Text(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
        sa.Column('source_url', sa.String(length=512), nullable=False),
        sa.Column('dimension_weights', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('reviewer', sa.String(length=128), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_careers_code'), 'careers', ['code'], unique=True)
    op.create_index(op.f('ix_careers_title'), 'careers', ['title'], unique=False)
    op.create_index(op.f('ix_careers_cluster'), 'careers', ['cluster'], unique=False)
    op.create_index(op.f('ix_careers_status'), 'careers', ['status'], unique=False)

    # 2. assessment_results table
    op.create_table(
        'assessment_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('attempt_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assessment_attempts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assessment_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assessment_versions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('dimension_scores', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('holland_code', sa.String(length=8), nullable=False),
        sa.Column('holland_code_label', sa.String(length=128), nullable=False),
        sa.Column('traits', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('skills', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('recommended_streams', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('career_suggestions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('ai_explanation', sa.Text(), nullable=False),
        sa.Column('disclaimer_note', sa.String(length=256), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'version', name='uq_user_assessment_result_version'),
    )
    op.create_index(op.f('ix_assessment_results_user_id'), 'assessment_results', ['user_id'], unique=False)
    op.create_index(op.f('ix_assessment_results_attempt_id'), 'assessment_results', ['attempt_id'], unique=True)
    op.create_index(op.f('ix_assessment_results_version'), 'assessment_results', ['version'], unique=False)
    op.create_index(op.f('ix_assessment_results_holland_code'), 'assessment_results', ['holland_code'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_assessment_results_holland_code'), table_name='assessment_results')
    op.drop_index(op.f('ix_assessment_results_version'), table_name='assessment_results')
    op.drop_index(op.f('ix_assessment_results_attempt_id'), table_name='assessment_results')
    op.drop_index(op.f('ix_assessment_results_user_id'), table_name='assessment_results')
    op.drop_table('assessment_results')

    op.drop_index(op.f('ix_careers_status'), table_name='careers')
    op.drop_index(op.f('ix_careers_cluster'), table_name='careers')
    op.drop_index(op.f('ix_careers_title'), table_name='careers')
    op.drop_index(op.f('ix_careers_code'), table_name='careers')
    op.drop_table('careers')
