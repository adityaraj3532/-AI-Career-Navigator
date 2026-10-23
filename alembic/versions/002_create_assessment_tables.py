"""create assessment tables

Revision ID: 002_create_assessment_tables
Revises: 001_initial_auth
Create Date: 2026-10-23

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '002_create_assessment_tables'
down_revision: Union[str, None] = '001_initial_auth'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. assessment_versions
    op.create_table(
        'assessment_versions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('version_number', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_assessment_versions_version_number'), 'assessment_versions', ['version_number'], unique=True)

    # 2. assessment_questions
    op.create_table(
        'assessment_questions',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('assessment_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assessment_versions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_order', sa.Integer(), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('dimension', sa.String(length=64), nullable=False),
        sa.Column('reverse_scored', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_assessment_questions_assessment_version_id'), 'assessment_questions', ['assessment_version_id'], unique=False)
    op.create_index(op.f('ix_assessment_questions_question_order'), 'assessment_questions', ['question_order'], unique=False)
    op.create_index(op.f('ix_assessment_questions_dimension'), 'assessment_questions', ['dimension'], unique=False)

    # 3. assessment_attempts
    op.create_table(
        'assessment_attempts',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
        sa.Column('assessment_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assessment_versions.id', ondelete='RESTRICT'), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('submitted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_assessment_attempts_user_id'), 'assessment_attempts', ['user_id'], unique=False)
    op.create_index(op.f('ix_assessment_attempts_assessment_version_id'), 'assessment_attempts', ['assessment_version_id'], unique=False)
    op.create_index(op.f('ix_assessment_attempts_status'), 'assessment_attempts', ['status'], unique=False)

    # 4. assessment_answers
    op.create_table(
        'assessment_answers',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('attempt_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assessment_attempts.id', ondelete='CASCADE'), nullable=False),
        sa.Column('question_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('assessment_questions.id', ondelete='CASCADE'), nullable=False),
        sa.Column('value', sa.Integer(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint('attempt_id', 'question_id', name='uq_attempt_question_answer'),
    )
    op.create_index(op.f('ix_assessment_answers_attempt_id'), 'assessment_answers', ['attempt_id'], unique=False)
    op.create_index(op.f('ix_assessment_answers_question_id'), 'assessment_answers', ['question_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_assessment_answers_question_id'), table_name='assessment_answers')
    op.drop_index(op.f('ix_assessment_answers_attempt_id'), table_name='assessment_answers')
    op.drop_table('assessment_answers')

    op.drop_index(op.f('ix_assessment_attempts_status'), table_name='assessment_attempts')
    op.drop_index(op.f('ix_assessment_attempts_assessment_version_id'), table_name='assessment_attempts')
    op.drop_index(op.f('ix_assessment_attempts_user_id'), table_name='assessment_attempts')
    op.drop_table('assessment_attempts')

    op.drop_index(op.f('ix_assessment_questions_dimension'), table_name='assessment_questions')
    op.drop_index(op.f('ix_assessment_questions_question_order'), table_name='assessment_questions')
    op.drop_index(op.f('ix_assessment_questions_assessment_version_id'), table_name='assessment_questions')
    op.drop_table('assessment_questions')

    op.drop_index(op.f('ix_assessment_versions_version_number'), table_name='assessment_versions')
    op.drop_table('assessment_versions')
