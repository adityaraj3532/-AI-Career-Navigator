"""create roadmap and exam cycle tables

Revision ID: 008_create_roadmap_and_exam_cycle_tables
Revises: 007_create_skill_tracker_tables
Create Date: 2026-10-23

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '008_create_roadmap_and_exam_cycle_tables'
down_revision: Union[str, None] = '007_create_skill_tracker_tables'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. exam_cycles table
    op.create_table(
        'exam_cycles',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('exam_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('year', sa.Integer(), nullable=False),
        sa.Column('registration_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('registration_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('exam_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_url', sa.String(length=512), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
        sa.Column('reviewer', sa.String(length=128), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['exam_id'], ['exams.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('exam_id', 'year', name='uq_exam_cycle_year'),
    )
    op.create_index(op.f('ix_exam_cycles_exam_id'), 'exam_cycles', ['exam_id'], unique=False)

    # 2. roadmap_templates table
    op.create_table(
        'roadmap_templates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('career_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('version', sa.Integer(), server_default='1', nullable=False),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
        sa.Column('reviewer', sa.String(length=128), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['career_id'], ['careers.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('career_id', 'version', name='uq_roadmap_template_career_version'),
    )
    op.create_index('ix_roadmap_templates_career_id', 'roadmap_templates', ['career_id'], unique=False)

    # 3. template_phases table
    op.create_table(
        'template_phases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('phase_order', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['roadmap_templates.id'], ondelete='CASCADE'),
        sa.UniqueConstraint('template_id', 'phase_order', name='uq_template_phase_order'),
    )
    op.create_index(op.f('ix_template_phases_template_id'), 'template_phases', ['template_id'], unique=False)

    # 4. template_items table
    op.create_table(
        'template_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('phase_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('item_code', sa.String(length=64), nullable=True),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('source_url', sa.String(length=512), nullable=True),
        sa.Column('estimated_minutes', sa.Integer(), server_default='60', nullable=False),
        sa.Column('difficulty', sa.Integer(), server_default='1', nullable=False),
        sa.Column('topic', sa.String(length=64), nullable=False),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('prerequisites', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('optional', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
        sa.Column('reviewer', sa.String(length=128), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sequence_order', sa.Integer(), server_default='0', nullable=False),
        sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['template_id'], ['roadmap_templates.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['phase_id'], ['template_phases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_template_items_template_id', 'template_items', ['template_id'], unique=False)
    op.create_index('ix_template_items_phase_id', 'template_items', ['phase_id'], unique=False)
    op.create_index('ix_template_items_item_code', 'template_items', ['item_code'], unique=False)
    op.create_index(op.f('ix_template_items_skill_id'), 'template_items', ['skill_id'], unique=False)

    # 5. roadmaps (user copies)
    op.create_table(
        'roadmaps',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('career_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('template_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('template_version', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('timezone', sa.String(length=64), server_default='UTC', nullable=False),
        sa.Column('hours_per_week', sa.Integer(), server_default='15', nullable=False),
        sa.Column('start_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('target_completion_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['career_id'], ['careers.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['template_id'], ['roadmap_templates.id'], ondelete='SET NULL'),
    )
    op.create_index(op.f('ix_roadmaps_user_id'), 'roadmaps', ['user_id'], unique=False)
    op.create_index(op.f('ix_roadmaps_career_id'), 'roadmaps', ['career_id'], unique=False)
    op.create_index('ix_roadmaps_user_career', 'roadmaps', ['user_id', 'career_id'], unique=False)
    op.create_index('ix_roadmaps_user_status', 'roadmaps', ['user_id', 'status'], unique=False)

    # 6. roadmap_phases
    op.create_table(
        'roadmap_phases',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('roadmap_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('name', sa.String(length=128), nullable=False),
        sa.Column('phase_order', sa.Integer(), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['roadmap_id'], ['roadmaps.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_roadmap_phases_roadmap_id', 'roadmap_phases', ['roadmap_id'], unique=False)

    # 7. roadmap_items
    op.create_table(
        'roadmap_items',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('roadmap_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('phase_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('item_code', sa.String(length=64), nullable=True),
        sa.Column('type', sa.String(length=32), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('source_url', sa.String(length=512), nullable=True),
        sa.Column('estimated_minutes', sa.Integer(), nullable=False),
        sa.Column('difficulty', sa.Integer(), server_default='1', nullable=False),
        sa.Column('topic', sa.String(length=64), nullable=False),
        sa.Column('skill_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('prerequisites', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('optional', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='todo', nullable=False),
        sa.Column('scheduled_week', sa.Integer(), nullable=True),
        sa.Column('scheduled_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('order_index', sa.Integer(), server_default='0', nullable=False),
        sa.Column('extra_data', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['roadmap_id'], ['roadmaps.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['phase_id'], ['roadmap_phases.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['skill_id'], ['skills.id'], ondelete='SET NULL'),
    )
    op.create_index('ix_roadmap_items_roadmap_id', 'roadmap_items', ['roadmap_id'], unique=False)
    op.create_index('ix_roadmap_items_status', 'roadmap_items', ['status'], unique=False)
    op.create_index('ix_roadmap_items_scheduled_week', 'roadmap_items', ['scheduled_week'], unique=False)
    op.create_index(op.f('ix_roadmap_items_skill_id'), 'roadmap_items', ['skill_id'], unique=False)

    # 8. replan_history
    op.create_table(
        'replan_history',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('roadmap_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('reason', sa.String(length=255), nullable=False),
        sa.Column('summary', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['roadmap_id'], ['roadmaps.id'], ondelete='CASCADE'),
    )
    op.create_index('ix_replan_history_roadmap_id', 'replan_history', ['roadmap_id'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_replan_history_roadmap_id', table_name='replan_history')
    op.drop_table('replan_history')

    op.drop_index(op.f('ix_roadmap_items_skill_id'), table_name='roadmap_items')
    op.drop_index('ix_roadmap_items_scheduled_week', table_name='roadmap_items')
    op.drop_index('ix_roadmap_items_status', table_name='roadmap_items')
    op.drop_index('ix_roadmap_items_roadmap_id', table_name='roadmap_items')
    op.drop_table('roadmap_items')

    op.drop_index('ix_roadmap_phases_roadmap_id', table_name='roadmap_phases')
    op.drop_table('roadmap_phases')

    op.drop_index('ix_roadmaps_user_status', table_name='roadmaps')
    op.drop_index('ix_roadmaps_user_career', table_name='roadmaps')
    op.drop_index(op.f('ix_roadmaps_career_id'), table_name='roadmaps')
    op.drop_index(op.f('ix_roadmaps_user_id'), table_name='roadmaps')
    op.drop_table('roadmaps')

    op.drop_index(op.f('ix_template_items_skill_id'), table_name='template_items')
    op.drop_index('ix_template_items_item_code', table_name='template_items')
    op.drop_index('ix_template_items_phase_id', table_name='template_items')
    op.drop_index('ix_template_items_template_id', table_name='template_items')
    op.drop_table('template_items')

    op.drop_index(op.f('ix_template_phases_template_id'), table_name='template_phases')
    op.drop_table('template_phases')

    op.drop_index('ix_roadmap_templates_career_id', table_name='roadmap_templates')
    op.drop_table('roadmap_templates')

    op.drop_index(op.f('ix_exam_cycles_exam_id'), table_name='exam_cycles')
    op.drop_table('exam_cycles')
