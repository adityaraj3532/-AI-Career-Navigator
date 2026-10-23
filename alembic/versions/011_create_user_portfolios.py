"""create user portfolios table

Revision ID: 011_create_user_portfolios
Revises: 010_create_password_reset_tokens
Create Date: 2026-10-24

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '011_create_user_portfolios'
down_revision: Union[str, None] = '010_create_password_reset_tokens'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'user_portfolios',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('slug', sa.String(length=64), nullable=False),
        sa.Column('is_public', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('headline', sa.String(length=160), nullable=True),
        sa.Column('about', sa.Text(), nullable=True),
        sa.Column('visibility', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('featured_item_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('custom_projects', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('custom_certificates', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('competitions', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('achievements', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_user_portfolios_user_id'), 'user_portfolios', ['user_id'], unique=True)
    op.create_index(op.f('ix_user_portfolios_slug'), 'user_portfolios', ['slug'], unique=True)
    op.create_index(op.f('ix_user_portfolios_is_public'), 'user_portfolios', ['is_public'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_user_portfolios_is_public'), table_name='user_portfolios')
    op.drop_index(op.f('ix_user_portfolios_slug'), table_name='user_portfolios')
    op.drop_index(op.f('ix_user_portfolios_user_id'), table_name='user_portfolios')
    op.drop_table('user_portfolios')
