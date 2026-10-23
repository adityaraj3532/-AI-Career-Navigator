"""create recommendations and actions

Revision ID: 009_create_recommendations_and_actions
Revises: 008_create_roadmap_and_exam_cycle_tables
Create Date: 2026-10-23

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '009_create_recommendations_and_actions'
down_revision: Union[str, None] = '008_create_roadmap_and_exam_cycle_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add missing columns to courses table
    op.add_column('courses', sa.Column('cost_inr', sa.Integer(), nullable=True))
    op.add_column('courses', sa.Column('mode', sa.String(length=32), nullable=True))
    op.add_column('courses', sa.Column('location', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('courses', sa.Column('eligibility', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('courses', sa.Column('application_deadline', sa.DateTime(timezone=True), nullable=True))
    op.add_column('courses', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))

    # 2. Add missing columns to certificates table
    op.add_column('certificates', sa.Column('cost_inr', sa.Integer(), nullable=True))
    op.add_column('certificates', sa.Column('duration', sa.String(length=64), nullable=True))
    op.add_column('certificates', sa.Column('mode', sa.String(length=32), nullable=True))
    op.add_column('certificates', sa.Column('location', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('certificates', sa.Column('eligibility', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('certificates', sa.Column('application_deadline', sa.DateTime(timezone=True), nullable=True))
    op.add_column('certificates', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))

    # 3. Add missing columns to internships table
    op.add_column('internships', sa.Column('cost_inr', sa.Integer(), server_default='0', nullable=True))
    op.add_column('internships', sa.Column('duration', sa.String(length=64), nullable=True))
    op.add_column('internships', sa.Column('mode', sa.String(length=32), nullable=True))
    op.add_column('internships', sa.Column('location', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('internships', sa.Column('eligibility', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('internships', sa.Column('application_deadline', sa.DateTime(timezone=True), nullable=True))
    op.add_column('internships', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))

    # 4. Create recommendation_actions table
    op.create_table(
        'recommendation_actions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('item_type', sa.String(length=32), nullable=False),
        sa.Column('item_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('state', sa.String(length=32), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('user_id', 'item_type', 'item_id', name='uq_recommendation_actions_user_item'),
    )
    op.create_index(op.f('ix_recommendation_actions_user_id'), 'recommendation_actions', ['user_id'], unique=False)
    op.create_index(op.f('ix_recommendation_actions_item_id'), 'recommendation_actions', ['item_id'], unique=False)
    op.create_index('ix_recommendation_actions_user_state', 'recommendation_actions', ['user_id', 'state'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_recommendation_actions_user_state', table_name='recommendation_actions')
    op.drop_index(op.f('ix_recommendation_actions_item_id'), table_name='recommendation_actions')
    op.drop_index(op.f('ix_recommendation_actions_user_id'), table_name='recommendation_actions')
    op.drop_table('recommendation_actions')

    op.drop_column('internships', 'expires_at')
    op.drop_column('internships', 'application_deadline')
    op.drop_column('internships', 'eligibility')
    op.drop_column('internships', 'location')
    op.drop_column('internships', 'mode')
    op.drop_column('internships', 'duration')
    op.drop_column('internships', 'cost_inr')

    op.drop_column('certificates', 'expires_at')
    op.drop_column('certificates', 'application_deadline')
    op.drop_column('certificates', 'eligibility')
    op.drop_column('certificates', 'location')
    op.drop_column('certificates', 'mode')
    op.drop_column('certificates', 'duration')
    op.drop_column('certificates', 'cost_inr')

    op.drop_column('courses', 'expires_at')
    op.drop_column('courses', 'application_deadline')
    op.drop_column('courses', 'eligibility')
    op.drop_column('courses', 'location')
    op.drop_column('courses', 'mode')
    op.drop_column('courses', 'cost_inr')
