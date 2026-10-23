"""create planner_tasks table

Revision ID: 014_create_planner_tasks
Revises: 013_create_progress_and_milestones
Create Date: 2026-10-24

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '014_create_planner_tasks'
down_revision: Union[str, None] = '013_create_progress_and_milestones'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'planner_tasks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('roadmap_item_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('roadmap_items.id', ondelete='CASCADE'), nullable=True),
        sa.Column('task_type', sa.String(length=32), nullable=False, server_default='user_custom'),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('notes', sa.String(length=1000), nullable=True),
        sa.Column('estimated_minutes', sa.Integer(), nullable=False),
        sa.Column('scheduled_date', sa.Date(), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('priority', sa.String(length=16), server_default='medium', nullable=False),
        sa.Column('user_rescheduled', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "((task_type = 'roadmap_item' AND roadmap_item_id IS NOT NULL) OR (task_type <> 'roadmap_item' AND roadmap_item_id IS NULL))",
            name='ck_planner_tasks_type_roadmap_item',
        ),
        sa.CheckConstraint(
            'estimated_minutes > 0 AND estimated_minutes <= 1440',
            name='ck_planner_tasks_estimated_minutes',
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'cancelled')",
            name='ck_planner_tasks_status',
        ),
        sa.CheckConstraint(
            "priority IN ('low', 'medium', 'high')",
            name='ck_planner_tasks_priority',
        ),
    )

    op.create_index('ix_planner_tasks_user_id', 'planner_tasks', ['user_id'])
    op.create_index('ix_planner_tasks_roadmap_item_id', 'planner_tasks', ['roadmap_item_id'])
    op.create_index('ix_planner_tasks_scheduled_date', 'planner_tasks', ['scheduled_date'])
    op.create_index('ix_planner_tasks_user_scheduled_date', 'planner_tasks', ['user_id', 'scheduled_date'])
    op.create_index('ix_planner_tasks_status', 'planner_tasks', ['status'])

    # Partial unique index: A roadmap item cannot have more than one non-cancelled task per user
    op.create_index(
        'uq_planner_tasks_user_roadmap_item_active',
        'planner_tasks',
        ['user_id', 'roadmap_item_id'],
        unique=True,
        postgresql_where=sa.text("status <> 'cancelled' AND roadmap_item_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index('uq_planner_tasks_user_roadmap_item_active', table_name='planner_tasks')
    op.drop_index('ix_planner_tasks_status', table_name='planner_tasks')
    op.drop_index('ix_planner_tasks_user_scheduled_date', table_name='planner_tasks')
    op.drop_index('ix_planner_tasks_scheduled_date', table_name='planner_tasks')
    op.drop_index('ix_planner_tasks_roadmap_item_id', table_name='planner_tasks')
    op.drop_index('ix_planner_tasks_user_id', table_name='planner_tasks')
    op.drop_table('planner_tasks')
