"""create chat_conversations and chat_messages tables

Revision ID: 015_create_ai_chat
Revises: 014_create_planner_tasks
Create Date: 2026-10-24

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '015_create_ai_chat'
down_revision: Union[str, None] = '014_create_planner_tasks'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. chat_conversations
    op.create_table(
        'chat_conversations',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('mode', sa.String(length=32), nullable=False),
        sa.Column('career_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('careers.id', ondelete='SET NULL'), nullable=True),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("mode IN ('career', 'roadmap', 'skills', 'interview')", name='ck_chat_conversations_mode'),
    )
    op.create_index('ix_chat_conversations_user_id', 'chat_conversations', ['user_id'])
    op.create_index('ix_chat_conversations_career_id', 'chat_conversations', ['career_id'])
    op.create_index('ix_chat_conversations_user_updated', 'chat_conversations', ['user_id', 'updated_at'])

    # 2. chat_messages
    op.create_table(
        'chat_messages',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('conversation_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('chat_conversations.id', ondelete='CASCADE'), nullable=False),
        sa.Column('seq', sa.Integer(), nullable=False),
        sa.Column('client_message_id', sa.String(length=64), nullable=True),
        sa.Column('role', sa.String(length=16), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('sources', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('ai_status', sa.String(length=16), server_default='ok', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('conversation_id', 'seq', name='uq_chat_messages_conversation_seq'),
        sa.CheckConstraint("role IN ('user', 'assistant')", name='ck_chat_messages_role'),
        sa.CheckConstraint("ai_status IN ('ok', 'fallback', 'safety')", name='ck_chat_messages_ai_status'),
    )
    op.create_index('ix_chat_messages_conversation_id', 'chat_messages', ['conversation_id'])
    op.create_index('ix_chat_messages_conversation_created', 'chat_messages', ['conversation_id', 'created_at'])
    op.create_index(
        'uq_chat_messages_client_msg',
        'chat_messages',
        ['conversation_id', 'client_message_id'],
        unique=True,
        postgresql_where=sa.text("client_message_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index('uq_chat_messages_client_msg', table_name='chat_messages')
    op.drop_index('ix_chat_messages_conversation_created', table_name='chat_messages')
    op.drop_index('ix_chat_messages_conversation_id', table_name='chat_messages')
    op.drop_table('chat_messages')

    op.drop_index('ix_chat_conversations_user_updated', table_name='chat_conversations')
    op.drop_index('ix_chat_conversations_career_id', table_name='chat_conversations')
    op.drop_index('ix_chat_conversations_user_id', table_name='chat_conversations')
    op.drop_table('chat_conversations')
