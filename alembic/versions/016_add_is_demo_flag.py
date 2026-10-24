"""add is_demo boolean flag to users, skill_evidence, activity_events, user_portfolios, roadmaps

Revision ID: 016_add_is_demo_flag
Revises: 015_create_ai_chat
Create Date: 2026-10-24

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '016_add_is_demo_flag'
down_revision: Union[str, None] = '015_create_ai_chat'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.create_index(op.f('ix_users_is_demo'), 'users', ['is_demo'], unique=False)

    op.add_column('skill_evidence', sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('activity_events', sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('user_portfolios', sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.text('false')))
    op.add_column('roadmaps', sa.Column('is_demo', sa.Boolean(), nullable=False, server_default=sa.text('false')))


def downgrade() -> None:
    op.drop_column('roadmaps', 'is_demo')
    op.drop_column('user_portfolios', 'is_demo')
    op.drop_column('activity_events', 'is_demo')
    op.drop_column('skill_evidence', 'is_demo')
    op.drop_index(op.f('ix_users_is_demo'), table_name='users')
    op.drop_column('users', 'is_demo')
