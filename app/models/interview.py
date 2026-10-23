import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class InterviewQuestion(Base):
    __tablename__ = "interview_questions"
    __table_args__ = (
        Index("ix_interview_questions_lookup", "career_id", "type", "level", "status"),
        Index("ix_interview_questions_status", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    career_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("careers.id", ondelete="CASCADE"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # "technical" | "hr"
    level: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # "beginner" | "intermediate" | "advanced"
    text: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    sample_answer: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(
        String(32), default="draft", nullable=False
    )  # "draft" | "verified"
    source_note: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    last_verified_by: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    career = relationship("Career", lazy="selectin")


class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    __table_args__ = (
        Index("ix_interview_sessions_user_status", "user_id", "status"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    career_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("careers.id", ondelete="CASCADE"),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(String(32), nullable=False)  # "technical" | "hr"
    level: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # "beginner" | "intermediate" | "advanced"
    status: Mapped[str] = mapped_column(
        String(32), default="in_progress", nullable=False
    )  # "in_progress" | "completed" | "expired" | "abandoned"
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    user = relationship("User", lazy="selectin")
    career = relationship("Career", lazy="selectin")
    session_questions = relationship(
        "SessionQuestion",
        back_populates="session",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="SessionQuestion.order",
    )


class SessionQuestion(Base):
    __tablename__ = "session_questions"
    __table_args__ = (
        Index("ix_session_questions_session_id", "session_id"),
        Index("ix_session_questions_parent_id", "parent_session_question_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    question_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_questions.id", ondelete="SET NULL"),
        nullable=True,
    )
    parent_session_question_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("session_questions.id", ondelete="CASCADE"),
        nullable=True,
    )
    order: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    key_points: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    is_follow_up: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    session = relationship("InterviewSession", back_populates="session_questions")
    answer = relationship(
        "InterviewAnswer",
        back_populates="session_question",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    results = relationship(
        "InterviewResult",
        back_populates="session_question",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class InterviewAnswer(Base):
    __tablename__ = "interview_answers"
    __table_args__ = (
        Index("ix_interview_answers_user", "user_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("session_questions.id", ondelete="CASCADE"),
        unique=True,
        nullable=False,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )
    answer_text: Mapped[str] = mapped_column(String(2000), nullable=False)
    submitted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    session_question = relationship("SessionQuestion", back_populates="answer")


class InterviewResult(Base):
    __tablename__ = "interview_results"
    __table_args__ = (
        Index("ix_interview_results_session", "session_id"),
        Index("ix_interview_results_question", "session_question_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4
    )
    session_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("interview_sessions.id", ondelete="CASCADE"),
        nullable=False,
    )
    session_question_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("session_questions.id", ondelete="CASCADE"),
        nullable=True,
    )
    rubric_version: Mapped[str] = mapped_column(String(32), nullable=False)
    coverage_score: Mapped[int] = mapped_column(Integer, nullable=False)
    depth_score: Mapped[int] = mapped_column(Integer, nullable=False)
    structure_score: Mapped[int] = mapped_column(Integer, nullable=False)
    overall_score: Mapped[int] = mapped_column(Integer, nullable=False)
    covered_points: Mapped[List[str]] = mapped_column(
        JSONB, default=list, nullable=False
    )
    scoring_method: Mapped[str] = mapped_column(
        String(32), nullable=False
    )  # "ai" | "fallback"
    confidence: Mapped[str] = mapped_column(
        String(32), default="medium", nullable=False
    )  # "high" | "medium" | "low"
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    session_question = relationship("SessionQuestion", back_populates="results")
