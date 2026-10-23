import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class AssessmentVersion(Base):
    __tablename__ = "assessment_versions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    version_number: Mapped[int] = mapped_column(
        Integer,
        unique=True,
        index=True,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(String(128), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    questions: Mapped[List["AssessmentQuestion"]] = relationship(
        "AssessmentQuestion",
        back_populates="assessment_version",
        cascade="all, delete-orphan",
        order_by="AssessmentQuestion.question_order",
    )
    attempts: Mapped[List["AssessmentAttempt"]] = relationship(
        "AssessmentAttempt",
        back_populates="assessment_version",
    )


class AssessmentQuestion(Base):
    __tablename__ = "assessment_questions"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    assessment_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_versions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question_order: Mapped[int] = mapped_column(Integer, nullable=False, index=True)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    dimension: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    reverse_scored: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    assessment_version: Mapped["AssessmentVersion"] = relationship(
        "AssessmentVersion",
        back_populates="questions",
    )
    answers: Mapped[List["AssessmentAnswer"]] = relationship(
        "AssessmentAnswer",
        back_populates="question",
        cascade="all, delete-orphan",
    )


class AssessmentAttempt(Base):
    __tablename__ = "assessment_attempts"

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
    assessment_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_versions.id", ondelete="RESTRICT"),
        index=True,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="draft",
        index=True,
        nullable=False,
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    submitted_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    assessment_version: Mapped["AssessmentVersion"] = relationship(
        "AssessmentVersion",
        back_populates="attempts",
    )
    answers: Mapped[List["AssessmentAnswer"]] = relationship(
        "AssessmentAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
    )
    result: Mapped[Optional["AssessmentResult"]] = relationship(
        "AssessmentResult",
        back_populates="attempt",
        uselist=False,
    )


class AssessmentAnswer(Base):
    __tablename__ = "assessment_answers"
    __table_args__ = (
        UniqueConstraint("attempt_id", "question_id", name="uq_attempt_question_answer"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_attempts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_questions.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    value: Mapped[int] = mapped_column(Integer, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    attempt: Mapped["AssessmentAttempt"] = relationship(
        "AssessmentAttempt",
        back_populates="answers",
    )
    question: Mapped["AssessmentQuestion"] = relationship(
        "AssessmentQuestion",
        back_populates="answers",
    )


class AssessmentResult(Base):
    __tablename__ = "assessment_results"
    __table_args__ = (
        UniqueConstraint("user_id", "version", name="uq_user_assessment_result_version"),
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
    attempt_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_attempts.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    assessment_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("assessment_versions.id", ondelete="RESTRICT"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
        index=True,
    )
    # JSONB normalized dimension scores: {"R": 40.0, "I": 95.0, "A": 85.0, "S": 60.0, "E": 50.0, "C": 70.0}
    dimension_scores: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    holland_code: Mapped[str] = mapped_column(
        String(8),
        nullable=False,
        index=True,
    )
    holland_code_label: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    traits: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
    )
    skills: Mapped[List[str]] = mapped_column(
        JSONB,
        nullable=False,
    )
    recommended_streams: Mapped[Optional[List[str]]] = mapped_column(
        JSONB,
        nullable=True,
    )
    # List of code-ranked careers with AI-synthesized personal reasons:
    # [{"career_id": "...", "career_title": "...", "similarity_score": 0.95, "reason": "..."}]
    career_suggestions: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
    )
    ai_explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    disclaimer_note: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
        default="These results provide career navigation guidance and vocational exploration insights; they are not a psychological evaluation or clinical diagnosis.",
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    attempt: Mapped["AssessmentAttempt"] = relationship(
        "AssessmentAttempt",
        back_populates="result",
    )
