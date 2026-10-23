"""create adaptive test tables

Revision ID: 006_create_adaptive_test_tables
Revises: 005_create_compatibility_and_shortlist
Create Date: 2026-10-23

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '006_create_adaptive_test_tables'
down_revision: Union[str, None] = '005_create_compatibility_and_shortlist'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. test_question_banks
    op.create_table(
        'test_question_banks',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('topic', sa.String(length=64), nullable=False),
        sa.Column('subtopic', sa.String(length=64), nullable=True),
        sa.Column('language', sa.String(length=32), nullable=True),
        sa.Column('difficulty', sa.Integer(), nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('options', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('correct_option_id', sa.String(length=32), nullable=False),
        sa.Column('explanation', sa.Text(), nullable=False),
        sa.Column('source_note', sa.String(length=256), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
        sa.Column('reviewer', sa.String(length=128), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('career_cluster', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_test_question_banks_type'), 'test_question_banks', ['type'], unique=False)
    op.create_index(op.f('ix_test_question_banks_topic'), 'test_question_banks', ['topic'], unique=False)
    op.create_index(op.f('ix_test_question_banks_language'), 'test_question_banks', ['language'], unique=False)
    op.create_index(op.f('ix_test_question_banks_difficulty'), 'test_question_banks', ['difficulty'], unique=False)
    op.create_index(op.f('ix_test_question_banks_status'), 'test_question_banks', ['status'], unique=False)
    op.create_index(op.f('ix_test_question_banks_career_cluster'), 'test_question_banks', ['career_cluster'], unique=False)

    # 2. test_attempts
    op.create_table(
        'test_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('career_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('careers.id', ondelete='CASCADE'), nullable=False),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('topic', sa.String(length=64), nullable=False),
        sa.Column('language', sa.String(length=32), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='in_progress', nullable=False),
        sa.Column('current_difficulty', sa.Integer(), server_default='2', nullable=False),
        sa.Column('target_questions', sa.Integer(), server_default='6', nullable=False),
        sa.Column('time_limit_seconds', sa.Integer(), server_default='1200', nullable=False),
        sa.Column('demonstrated_level', sa.String(length=32), nullable=True),
        sa.Column('confidence', sa.String(length=32), nullable=True),
        sa.Column('score_percentage', sa.Integer(), nullable=True),
        sa.Column('total_correct', sa.Integer(), nullable=True),
        sa.Column('total_answered', sa.Integer(), server_default='0', nullable=False),
        sa.Column('disclaimer_note', sa.String(length=256), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(op.f('ix_test_attempts_user_id'), 'test_attempts', ['user_id'], unique=False)
    op.create_index(op.f('ix_test_attempts_career_id'), 'test_attempts', ['career_id'], unique=False)
    op.create_index(op.f('ix_test_attempts_topic'), 'test_attempts', ['topic'], unique=False)
    op.create_index(op.f('ix_test_attempts_status'), 'test_attempts', ['status'], unique=False)
    op.create_index('ix_test_attempts_user_topic_status', 'test_attempts', ['user_id', 'topic', 'status'], unique=False)

    # 3. test_attempt_answers
    op.create_table(
        'test_attempt_answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('attempt_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('test_attempts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('test_question_banks.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_order', sa.Integer(), nullable=False),
        sa.Column('difficulty_at_question', sa.Integer(), nullable=False),
        sa.Column('selected_option_id', sa.String(length=32), nullable=False),
        sa.Column('is_correct', sa.Boolean(), nullable=False),
        sa.Column('time_taken_seconds', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('attempt_id', 'question_id', name='uq_attempt_question_answer'),
    )
    op.create_index(op.f('ix_test_attempt_answers_attempt_id'), 'test_attempt_answers', ['attempt_id'], unique=False)
    op.create_index(op.f('ix_test_attempt_answers_question_id'), 'test_attempt_answers', ['question_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_test_attempt_answers_question_id'), table_name='test_attempt_answers')
    op.drop_index(op.f('ix_test_attempt_answers_attempt_id'), table_name='test_attempt_answers')
    op.drop_table('test_attempt_answers')

    op.drop_index('ix_test_attempts_user_topic_status', table_name='test_attempts')
    op.drop_index(op.f('ix_test_attempts_status'), table_name='test_attempts')
    op.drop_index(op.f('ix_test_attempts_topic'), table_name='test_attempts')
    op.drop_index(op.f('ix_test_attempts_career_id'), table_name='test_attempts')
    op.drop_index(op.f('ix_test_attempts_user_id'), table_name='test_attempts')
    op.drop_table('test_attempts')

    op.drop_index(op.f('ix_test_question_banks_career_cluster'), table_name='test_question_banks')
    op.drop_index(op.f('ix_test_question_banks_status'), table_name='test_question_banks')
    op.drop_index(op.f('ix_test_question_banks_difficulty'), table_name='test_question_banks')
    op.drop_index(op.f('ix_test_question_banks_language'), table_name='test_question_banks')
    op.drop_index(op.f('ix_test_question_banks_topic'), table_name='test_question_banks')
    op.drop_index(op.f('ix_test_question_banks_type'), table_name='test_question_banks')
    op.drop_table('test_question_banks')
