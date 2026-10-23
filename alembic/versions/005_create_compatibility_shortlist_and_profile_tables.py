"""create compatibility, shortlist, and profile tables

Revision ID: 005_create_compatibility_and_shortlist
Revises: 004_create_career_catalog_tables
Create Date: 2026-10-23

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '005_create_compatibility_and_shortlist'
down_revision: Union[str, None] = '004_create_career_catalog_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add catalog fields to careers: time_to_job_ready_months, entrance_difficulty
    op.add_column('careers', sa.Column('time_to_job_ready_months', sa.Integer(), nullable=True))
    op.add_column('careers', sa.Column('entrance_difficulty', sa.String(length=32), nullable=True))

    # 2. student_profiles table
    op.create_table(
        'student_profiles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=True),
        sa.Column('budget_level', sa.String(length=32), nullable=True),
        sa.Column('hours_available_per_week', sa.Integer(), nullable=True),
        sa.Column('subjects_of_interest', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('skills', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_student_profiles_user_id'), 'student_profiles', ['user_id'], unique=True)

    # 3. user_shortlists table
    op.create_table(
        'user_shortlists',
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('career_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('careers.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_user_shortlists_user_id'), 'user_shortlists', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_shortlists_career_id'), 'user_shortlists', ['career_id'], unique=False)

    # 4. user_career_compatibility_snapshots table (append-only)
    op.create_table(
        'user_career_compatibility_snapshots',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('career_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('careers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('overall_score', sa.Integer(), nullable=False),
        sa.Column('factor_breakdown', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('strengths', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('gaps', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('weights_version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('inputs_hash', sa.String(length=64), nullable=False),
        sa.Column('explanation_status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('ai_explanation', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_user_career_comp_latest', 'user_career_compatibility_snapshots', ['user_id', 'career_id', sa.text('created_at DESC')])
    op.create_index(op.f('ix_user_career_compatibility_snapshots_inputs_hash'), 'user_career_compatibility_snapshots', ['inputs_hash'], unique=False)
    op.create_index(op.f('ix_user_career_compatibility_snapshots_user_id'), 'user_career_compatibility_snapshots', ['user_id'], unique=False)
    op.create_index(op.f('ix_user_career_compatibility_snapshots_career_id'), 'user_career_compatibility_snapshots', ['career_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_career_compatibility_snapshots_career_id'), table_name='user_career_compatibility_snapshots')
    op.drop_index(op.f('ix_user_career_compatibility_snapshots_user_id'), table_name='user_career_compatibility_snapshots')
    op.drop_index(op.f('ix_user_career_compatibility_snapshots_inputs_hash'), table_name='user_career_compatibility_snapshots')
    op.drop_index('ix_user_career_comp_latest', table_name='user_career_compatibility_snapshots')
    op.drop_table('user_career_compatibility_snapshots')

    op.drop_index(op.f('ix_user_shortlists_career_id'), table_name='user_shortlists')
    op.drop_index(op.f('ix_user_shortlists_user_id'), table_name='user_shortlists')
    op.drop_table('user_shortlists')

    op.drop_index(op.f('ix_student_profiles_user_id'), table_name='student_profiles')
    op.drop_table('student_profiles')

    op.drop_column('careers', 'entrance_difficulty')
    op.drop_column('careers', 'time_to_job_ready_months')
