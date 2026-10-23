import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Table,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


# Association Tables with composite primary keys, ON DELETE CASCADE, and indexes on both sides
career_exams = Table(
    "career_exams",
    Base.metadata,
    Column("career_id", UUID(as_uuid=True), ForeignKey("careers.id", ondelete="CASCADE"), primary_key=True, index=True),
    Column("exam_id", UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), primary_key=True, index=True),
)

career_colleges = Table(
    "career_colleges",
    Base.metadata,
    Column("career_id", UUID(as_uuid=True), ForeignKey("careers.id", ondelete="CASCADE"), primary_key=True, index=True),
    Column("college_id", UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), primary_key=True, index=True),
)

career_courses = Table(
    "career_courses",
    Base.metadata,
    Column("career_id", UUID(as_uuid=True), ForeignKey("careers.id", ondelete="CASCADE"), primary_key=True, index=True),
    Column("course_id", UUID(as_uuid=True), ForeignKey("courses.id", ondelete="CASCADE"), primary_key=True, index=True),
)

career_certificates = Table(
    "career_certificates",
    Base.metadata,
    Column("career_id", UUID(as_uuid=True), ForeignKey("careers.id", ondelete="CASCADE"), primary_key=True, index=True),
    Column("certificate_id", UUID(as_uuid=True), ForeignKey("certificates.id", ondelete="CASCADE"), primary_key=True, index=True),
)

career_internships = Table(
    "career_internships",
    Base.metadata,
    Column("career_id", UUID(as_uuid=True), ForeignKey("careers.id", ondelete="CASCADE"), primary_key=True, index=True),
    Column("internship_id", UUID(as_uuid=True), ForeignKey("internships.id", ondelete="CASCADE"), primary_key=True, index=True),
)

career_related = Table(
    "career_related",
    Base.metadata,
    Column("career_id", UUID(as_uuid=True), ForeignKey("careers.id", ondelete="CASCADE"), primary_key=True, index=True),
    Column("related_career_id", UUID(as_uuid=True), ForeignKey("careers.id", ondelete="CASCADE"), primary_key=True, index=True),
    CheckConstraint("career_id != related_career_id", name="ck_career_not_self_related"),
)

college_exams = Table(
    "college_exams",
    Base.metadata,
    Column("college_id", UUID(as_uuid=True), ForeignKey("colleges.id", ondelete="CASCADE"), primary_key=True, index=True),
    Column("exam_id", UUID(as_uuid=True), ForeignKey("exams.id", ondelete="CASCADE"), primary_key=True, index=True),
)


class Career(Base):
    __tablename__ = "careers"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    cluster: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    aliases: Mapped[List[str]] = mapped_column(
        ARRAY(String(128)),
        default=list,
        nullable=False,
    )
    overview: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    day_in_life: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    # Formatted as: {"currency": "INR", "is_approximate": True, "as_of_year": 2026, "source_url": "...", "entry": {"min": int, "max": int}, "mid": ..., "senior": ...}
    salary_ranges: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    demand: Mapped[str] = mapped_column(
        String(32),
        default="moderate",
        index=True,
        nullable=False,
    )
    time_to_job_ready_months: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    entrance_difficulty: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    # List of {"name": str, "level": "beginner"|"intermediate"|"advanced"|"expert"}
    required_skills: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    # List of stages: [{"stage": str, "stream": Optional[str], "degree": Optional[str], "description": str}]
    education_paths: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="draft",
        index=True,
        nullable=False,
    )
    source_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    # RIASEC scale: {"R": int, "I": int, "A": int, "S": int, "E": int, "C": int} (0-100)
    dimension_weights: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    reviewer: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    # Eagerly loaded relationships via secondary association tables
    exams: Mapped[List["Exam"]] = relationship(
        "Exam",
        secondary=career_exams,
        back_populates="careers",
        lazy="selectin",
    )
    colleges: Mapped[List["College"]] = relationship(
        "College",
        secondary=career_colleges,
        back_populates="careers",
        lazy="selectin",
    )
    courses: Mapped[List["Course"]] = relationship(
        "Course",
        secondary=career_courses,
        back_populates="careers",
        lazy="selectin",
    )
    certificates: Mapped[List["Certificate"]] = relationship(
        "Certificate",
        secondary=career_certificates,
        back_populates="careers",
        lazy="selectin",
    )
    internships: Mapped[List["Internship"]] = relationship(
        "Internship",
        secondary=career_internships,
        back_populates="careers",
        lazy="selectin",
    )
    related_careers: Mapped[List["Career"]] = relationship(
        "Career",
        secondary=career_related,
        primaryjoin="Career.id == career_related.c.career_id",
        secondaryjoin="Career.id == career_related.c.related_career_id",
        lazy="selectin",
    )


class Exam(Base):
    __tablename__ = "exams"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    conducting_body: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    exam_level: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    registration_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    source_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="draft",
        index=True,
        nullable=False,
    )
    reviewer: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    careers: Mapped[List["Career"]] = relationship(
        "Career",
        secondary=career_exams,
        back_populates="exams",
        lazy="selectin",
    )
    colleges: Mapped[List["College"]] = relationship(
        "College",
        secondary=college_exams,
        back_populates="exams",
        lazy="selectin",
    )


class College(Base):
    __tablename__ = "colleges"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )
    # {"city": str, "state": str, "country": "India"}
    location: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    official_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    # fees, cutoffs, nirf_rank stay null until verified, and when set they need a year
    fees: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    cutoffs: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    nirf_rank: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    source_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="draft",
        index=True,
        nullable=False,
    )
    reviewer: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    careers: Mapped[List["Career"]] = relationship(
        "Career",
        secondary=career_colleges,
        back_populates="colleges",
        lazy="selectin",
    )
    exams: Mapped[List["Exam"]] = relationship(
        "Exam",
        secondary=college_exams,
        back_populates="colleges",
        lazy="selectin",
    )


class Course(Base):
    __tablename__ = "courses"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )
    degree_level: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    duration: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    cost_inr: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    mode: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )  # "online" | "offline" | "hybrid"
    location: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )  # null for online
    eligibility: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    application_deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    source_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="draft",
        index=True,
        nullable=False,
    )
    reviewer: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    careers: Mapped[List["Career"]] = relationship(
        "Career",
        secondary=career_courses,
        back_populates="courses",
        lazy="selectin",
    )


class Certificate(Base):
    __tablename__ = "certificates"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )
    issuing_organization: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    cost_inr: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    duration: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    mode: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )  # "online" | "offline" | "hybrid"
    location: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )  # null for online
    eligibility: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    application_deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    source_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="draft",
        index=True,
        nullable=False,
    )
    reviewer: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    careers: Mapped[List["Career"]] = relationship(
        "Career",
        secondary=career_certificates,
        back_populates="certificates",
        lazy="selectin",
    )


class Internship(Base):
    __tablename__ = "internships"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    code: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        index=True,
        nullable=False,
    )
    domain: Mapped[str] = mapped_column(
        String(128),
        index=True,
        nullable=False,
    )
    stipend_range: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    duration_months: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    duration: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    locations: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    description: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    cost_inr: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    mode: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )  # "online" | "offline" | "hybrid"
    location: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )  # null for online
    eligibility: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    application_deadline: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    expires_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    source_url: Mapped[str] = mapped_column(
        String(512),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="draft",
        index=True,
        nullable=False,
    )
    reviewer: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    careers: Mapped[List["Career"]] = relationship(
        "Career",
        secondary=career_internships,
        back_populates="internships",
        lazy="selectin",
    )


class UserShortlist(Base):
    __tablename__ = "user_shortlists"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    career_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("careers.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    career: Mapped["Career"] = relationship("Career", lazy="selectin")


class UserCareerCompatibilitySnapshot(Base):
    __tablename__ = "user_career_compatibility_snapshots"
    __table_args__ = (
        Index("ix_user_career_comp_latest", "user_id", "career_id", text("created_at DESC")),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    career_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("careers.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    overall_score: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    factor_breakdown: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    strengths: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    gaps: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    weights_version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    inputs_hash: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    explanation_status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
    )
    ai_explanation: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    career: Mapped["Career"] = relationship("Career", lazy="selectin")
