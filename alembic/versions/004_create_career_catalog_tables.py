"""create career catalog tables and extend careers

Revision ID: 004_create_career_catalog_tables
Revises: 003_create_careers_and_assessment_results
Create Date: 2026-10-23

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '004_create_career_catalog_tables'
down_revision: Union[str, None] = '003_create_careers_and_assessment_results'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Alter careers table: add aliases, description, day_in_life, salary_ranges, demand, required_skills, education_paths, last_verified_at
    op.add_column('careers', sa.Column('aliases', postgresql.ARRAY(sa.String(length=128)), server_default='{}', nullable=False))
    op.add_column('careers', sa.Column('description', sa.Text(), nullable=True))
    op.add_column('careers', sa.Column('day_in_life', sa.Text(), nullable=True))
    op.add_column('careers', sa.Column('salary_ranges', postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column('careers', sa.Column('demand', sa.String(length=32), server_default='moderate', nullable=False))
    op.create_index(op.f('ix_careers_demand'), 'careers', ['demand'], unique=False)
    op.add_column('careers', sa.Column('required_skills', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False))
    op.add_column('careers', sa.Column('education_paths', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False))
    op.add_column('careers', sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True))

    # 2. exams table
    op.create_table(
        'exams',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('conducting_body', sa.String(length=255), nullable=False),
        sa.Column('exam_level', sa.String(length=64), nullable=False),
        sa.Column('registration_url', sa.String(length=512), nullable=True),
        sa.Column('source_url', sa.String(length=512), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
        sa.Column('reviewer', sa.String(length=128), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_exams_code'), 'exams', ['code'], unique=True)
    op.create_index(op.f('ix_exams_name'), 'exams', ['name'], unique=False)
    op.create_index(op.f('ix_exams_status'), 'exams', ['status'], unique=False)

    # 3. colleges table
    op.create_table(
        'colleges',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('location', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('official_url', sa.String(length=512), nullable=False),
        sa.Column('fees', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('cutoffs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('nirf_rank', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source_url', sa.String(length=512), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
        sa.Column('reviewer', sa.String(length=128), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_colleges_name'), 'colleges', ['name'], unique=False)
    op.create_index(op.f('ix_colleges_status'), 'colleges', ['status'], unique=False)

    # 4. courses table
    op.create_table(
        'courses',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('degree_level', sa.String(length=64), nullable=False),
        sa.Column('duration', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('source_url', sa.String(length=512), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
        sa.Column('reviewer', sa.String(length=128), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_courses_code'), 'courses', ['code'], unique=True)
    op.create_index(op.f('ix_courses_title'), 'courses', ['title'], unique=False)
    op.create_index(op.f('ix_courses_status'), 'courses', ['status'], unique=False)

    # 5. certificates table
    op.create_table(
        'certificates',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('issuing_organization', sa.String(length=255), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('url', sa.String(length=512), nullable=True),
        sa.Column('source_url', sa.String(length=512), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
        sa.Column('reviewer', sa.String(length=128), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_certificates_code'), 'certificates', ['code'], unique=True)
    op.create_index(op.f('ix_certificates_name'), 'certificates', ['name'], unique=False)
    op.create_index(op.f('ix_certificates_status'), 'certificates', ['status'], unique=False)

    # 6. internships table
    op.create_table(
        'internships',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('code', sa.String(length=64), nullable=False),
        sa.Column('title', sa.String(length=255), nullable=False),
        sa.Column('domain', sa.String(length=128), nullable=False),
        sa.Column('stipend_range', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('duration_months', sa.Integer(), nullable=True),
        sa.Column('locations', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('source_url', sa.String(length=512), nullable=False),
        sa.Column('status', sa.String(length=32), server_default='draft', nullable=False),
        sa.Column('reviewer', sa.String(length=128), nullable=True),
        sa.Column('last_verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(op.f('ix_internships_code'), 'internships', ['code'], unique=True)
    op.create_index(op.f('ix_internships_title'), 'internships', ['title'], unique=False)
    op.create_index(op.f('ix_internships_domain'), 'internships', ['domain'], unique=False)
    op.create_index(op.f('ix_internships_status'), 'internships', ['status'], unique=False)

    # 7. Association Tables (composite PKs, ON DELETE CASCADE, indexed on both sides)
    op.create_table(
        'career_exams',
        sa.Column('career_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('careers.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('exam_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('exams.id', ondelete='CASCADE'), primary_key=True, nullable=False),
    )
    op.create_index(op.f('ix_career_exams_career_id'), 'career_exams', ['career_id'], unique=False)
    op.create_index(op.f('ix_career_exams_exam_id'), 'career_exams', ['exam_id'], unique=False)

    op.create_table(
        'career_colleges',
        sa.Column('career_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('careers.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('college_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('colleges.id', ondelete='CASCADE'), primary_key=True, nullable=False),
    )
    op.create_index(op.f('ix_career_colleges_career_id'), 'career_colleges', ['career_id'], unique=False)
    op.create_index(op.f('ix_career_colleges_college_id'), 'career_colleges', ['college_id'], unique=False)

    op.create_table(
        'career_courses',
        sa.Column('career_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('careers.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('course_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('courses.id', ondelete='CASCADE'), primary_key=True, nullable=False),
    )
    op.create_index(op.f('ix_career_courses_career_id'), 'career_courses', ['career_id'], unique=False)
    op.create_index(op.f('ix_career_courses_course_id'), 'career_courses', ['course_id'], unique=False)

    op.create_table(
        'career_certificates',
        sa.Column('career_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('careers.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('certificate_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('certificates.id', ondelete='CASCADE'), primary_key=True, nullable=False),
    )
    op.create_index(op.f('ix_career_certificates_career_id'), 'career_certificates', ['career_id'], unique=False)
    op.create_index(op.f('ix_career_certificates_certificate_id'), 'career_certificates', ['certificate_id'], unique=False)

    op.create_table(
        'career_internships',
        sa.Column('career_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('careers.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('internship_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('internships.id', ondelete='CASCADE'), primary_key=True, nullable=False),
    )
    op.create_index(op.f('ix_career_internships_career_id'), 'career_internships', ['career_id'], unique=False)
    op.create_index(op.f('ix_career_internships_internship_id'), 'career_internships', ['internship_id'], unique=False)

    op.create_table(
        'career_related',
        sa.Column('career_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('careers.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('related_career_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('careers.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.CheckConstraint('career_id != related_career_id', name='ck_career_not_self_related'),
    )
    op.create_index(op.f('ix_career_related_career_id'), 'career_related', ['career_id'], unique=False)
    op.create_index(op.f('ix_career_related_related_career_id'), 'career_related', ['related_career_id'], unique=False)

    op.create_table(
        'college_exams',
        sa.Column('college_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('colleges.id', ondelete='CASCADE'), primary_key=True, nullable=False),
        sa.Column('exam_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('exams.id', ondelete='CASCADE'), primary_key=True, nullable=False),
    )
    op.create_index(op.f('ix_college_exams_college_id'), 'college_exams', ['college_id'], unique=False)
    op.create_index(op.f('ix_college_exams_exam_id'), 'college_exams', ['exam_id'], unique=False)


def downgrade() -> None:
    # Drop association tables
    op.drop_table('college_exams')
    op.drop_table('career_related')
    op.drop_table('career_internships')
    op.drop_table('career_certificates')
    op.drop_table('career_courses')
    op.drop_table('career_colleges')
    op.drop_table('career_exams')

    # Drop entity tables
    op.drop_table('internships')
    op.drop_table('certificates')
    op.drop_table('courses')
    op.drop_table('colleges')
    op.drop_table('exams')

    # Revert columns from careers table
    op.drop_index(op.f('ix_careers_demand'), table_name='careers')
    op.drop_column('careers', 'last_verified_at')
    op.drop_column('careers', 'education_paths')
    op.drop_column('careers', 'required_skills')
    op.drop_column('careers', 'demand')
    op.drop_column('careers', 'salary_ranges')
    op.drop_column('careers', 'day_in_life')
    op.drop_column('careers', 'description')
    op.drop_column('careers', 'aliases')
