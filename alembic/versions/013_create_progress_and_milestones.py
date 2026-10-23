"""create progress and milestones tables

Revision ID: 013_create_progress_and_milestones
Revises: 012_create_mock_interviews
Create Date: 2026-10-24

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '013_create_progress_and_milestones'
down_revision: Union[str, None] = '012_create_mock_interviews'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add timezone column to student_profiles
    op.add_column(
        'student_profiles',
        sa.Column('timezone', sa.String(length=64), server_default='Asia/Kolkata', nullable=False)
    )

    # 2. activity_events table
    op.create_table(
        'activity_events',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('source_type', sa.String(length=64), nullable=False),
        sa.Column('source_id', sa.String(length=128), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('local_date', sa.Date(), nullable=False),
        sa.Column('tz', sa.String(length=64), server_default='Asia/Kolkata', nullable=False),
        sa.UniqueConstraint('source_type', 'source_id', name='uq_activity_events_source'),
    )
    op.create_index('ix_activity_events_user_id', 'activity_events', ['user_id'])
    op.create_index('ix_activity_events_local_date', 'activity_events', ['local_date'])
    op.create_index('ix_activity_events_user_local_date', 'activity_events', ['user_id', 'local_date'])

    # 3. milestone_rules table
    op.create_table(
        'milestone_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('key', sa.String(length=64), nullable=False, unique=True),
        sa.Column('rule_type', sa.String(length=64), nullable=False),
        sa.Column('params', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_milestone_rules_key', 'milestone_rules', ['key'])

    # 4. user_milestones table
    op.create_table(
        'user_milestones',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('rule_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('milestone_rules.id', ondelete='CASCADE'), nullable=False),
        sa.Column('awarded_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.UniqueConstraint('user_id', 'rule_id', name='uq_user_milestones_user_rule'),
    )
    op.create_index('ix_user_milestones_user_id', 'user_milestones', ['user_id'])

    # 5. weekly_goals table
    op.create_table(
        'weekly_goals',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('week_start', sa.Date(), nullable=False),
        sa.Column('goal_type', sa.String(length=32), nullable=False),
        sa.Column('target', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('user_id', 'week_start', 'goal_type', name='uq_weekly_goals_user_week_type'),
    )
    op.create_index('ix_weekly_goals_user_id', 'weekly_goals', ['user_id'])
    op.create_index('ix_weekly_goals_week_start', 'weekly_goals', ['week_start'])


def downgrade() -> None:
    op.drop_table('weekly_goals')
    op.drop_table('user_milestones')
    op.drop_table('milestone_rules')
    op.drop_table('activity_events')
    op.drop_column('student_profiles', 'timezone')
