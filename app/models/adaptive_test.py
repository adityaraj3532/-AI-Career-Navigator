import uuid
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base

if TYPE_CHECKING:
    from app.models.career import Career


class TestQuestionBank(Base):
    __tablename__ = "test_question_banks"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    type: Mapped[str] = mapped_column(
        String(32),
        index=True,
        nullable=False,
    )  # "skill" | "aptitude"
    topic: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    subtopic: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    language: Mapped[Optional[str]] = mapped_column(
        String(32),
        index=True,
        nullable=True,
    )  # e.g. "python", "cpp", "java", or None
    difficulty: Mapped[int] = mapped_column(
        Integer,
        index=True,
        nullable=False,
    )  # 1 (beginner), 2 (intermediate), 3 (advanced)
    question_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    # [{"id": "opt_a", "text": "..."}, {"id": "opt_b", "text": "..."}]
    options: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        nullable=False,
    )
    correct_option_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )  # Secret: never sent before answer!
    explanation: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    source_note: Mapped[str] = mapped_column(
        String(256),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="draft",
        index=True,
        nullable=False,
    )  # "draft" | "verified"
    reviewer: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    career_cluster: Mapped[Optional[str]] = mapped_column(
        String(64),
        index=True,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class TestAttempt(Base):
    __tablename__ = "test_attempts"
    __table_args__ = (
        Index("ix_test_attempts_user_topic_status", "user_id", "topic", "status"),
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
    type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )  # "skill" | "aptitude"
    topic: Mapped[str] = mapped_column(
        String(64),
        index=True,
        nullable=False,
    )
    language: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="in_progress",
        index=True,
        nullable=False,
    )  # "in_progress" | "finished" | "expired"
    current_difficulty: Mapped[int] = mapped_column(
        Integer,
        default=2,
        nullable=False,
    )
    target_questions: Mapped[int] = mapped_column(
        Integer,
        default=6,
        nullable=False,
    )
    time_limit_seconds: Mapped[int] = mapped_column(
        Integer,
        default=1200,
        nullable=False,
    )
    demonstrated_level: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )  # "beginner" | "intermediate" | "advanced"
    confidence: Mapped[Optional[str]] = mapped_column(
        String(32),
        nullable=True,
    )  # "low" | "medium" | "high"
    score_percentage: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    total_correct: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    total_answered: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    disclaimer_note: Mapped[Optional[str]] = mapped_column(
        String(256),
        nullable=True,
        default="This level is a preliminary estimate from a short adaptive diagnostic test.",
    )
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    finished_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    career: Mapped["Career"] = relationship("Career", lazy="selectin")
    answers: Mapped[List["TestAttemptAnswer"]] = relationship(
        "TestAttemptAnswer",
        back_populates="attempt",
        cascade="all, delete-orphan",
        order_by="TestAttemptAnswer.question_order",
        lazy="selectin",
    )


class TestAttemptAnswer(Base):
    __tablename__ = "test_attempt_answers"
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
        ForeignKey("test_attempts.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("test_question_banks.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    question_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    difficulty_at_question: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    selected_option_id: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    is_correct: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
    )
    time_taken_seconds: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    attempt: Mapped["TestAttempt"] = relationship("TestAttempt", back_populates="answers")
    question: Mapped["TestQuestionBank"] = relationship("TestQuestionBank", lazy="selectin")
