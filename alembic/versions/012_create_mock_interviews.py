"""create mock interview tables

Revision ID: 012_create_mock_interviews
Revises: 011_create_user_portfolios
Create Date: 2026-10-24

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '012_create_mock_interviews'
down_revision: Union[str, None] = '011_create_user_portfolios'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. interview_questions
    op.create_table(
        'interview_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('career_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('careers.id', ondelete='CASCADE'), nullable=True),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('level', sa.String(length=32), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('key_points', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('sample_answer', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
        sa.Column('source_note', sa.Text(), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_verified_by', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_interview_questions_lookup', 'interview_questions', ['career_id', 'type', 'level', 'status'], unique=False)
    op.create_index('ix_interview_questions_status', 'interview_questions', ['status'], unique=False)

    # 2. interview_sessions
    op.create_table(
        'interview_sessions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('career_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('careers.id', ondelete='CASCADE'), nullable=True),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('level', sa.String(length=32), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='in_progress', nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_interview_sessions_user_status', 'interview_sessions', ['user_id', 'status'], unique=False)
    op.create_index('ix_interview_sessions_user_id', 'interview_sessions', ['user_id'], unique=False)

    # 3. session_questions
    op.create_table(
        'session_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_questions.id', ondelete='SET NULL'), nullable=True),
        sa.Column('parent_session_question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('session_questions.id', ondelete='CASCADE'), nullable=True),
        sa.Column('order', sa.Integer(), server_default='1', nullable=False),
        sa.Column('question_text', sa.Text(), nullable=False),
        sa.Column('key_points', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('is_follow_up', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_session_questions_session_id', 'session_questions', ['session_id'], unique=False)
    op.create_index('ix_session_questions_parent_id', 'session_questions', ['parent_session_question_id'], unique=False)

    # 4. interview_answers
    op.create_table(
        'interview_answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('session_questions.id', ondelete='CASCADE'), unique=True, nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('answer_text', sa.String(length=2000), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_interview_answers_user_id', 'interview_answers', ['user_id'], unique=False)

    # 5. interview_results
    op.create_table(
        'interview_results',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('session_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('interview_sessions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('session_question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('session_questions.id', ondelete='CASCADE'), nullable=True),
        sa.Column('rubric_version', sa.String(length=32), nullable=False),
        sa.Column('coverage_score', sa.Integer(), nullable=False),
        sa.Column('depth_score', sa.Integer(), nullable=False),
        sa.Column('structure_score', sa.Integer(), nullable=False),
        sa.Column('overall_score', sa.Integer(), nullable=False),
        sa.Column('covered_points', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('scoring_method', sa.String(length=32), nullable=False),
        sa.Column('confidence', sa.String(length=32), server_default='medium', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index('ix_interview_results_session', 'interview_results', ['session_id'], unique=False)
    op.create_index('ix_interview_results_question', 'interview_results', ['session_question_id'], unique=False)


def downgrade() -> None:
    op.drop_table('interview_results')
    op.drop_table('interview_answers')
    op.drop_table('session_questions')
    op.drop_table('interview_sessions')
    op.drop_table('interview_questions')
