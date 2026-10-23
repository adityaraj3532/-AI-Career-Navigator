import uuid
from datetime import date, datetime, timezone
from typing import Optional
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    text,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class PlannerTask(Base):
    __tablename__ = "planner_tasks"
    __table_args__ = (
        # Partial unique index: A roadmap item cannot have more than one non-cancelled task per user
        Index(
            "uq_planner_tasks_user_roadmap_item_active",
            "user_id",
            "roadmap_item_id",
            unique=True,
            postgresql_where=text("status <> 'cancelled' AND roadmap_item_id IS NOT NULL"),
        ),
        Index("ix_planner_tasks_user_scheduled_date", "user_id", "scheduled_date"),
        Index("ix_planner_tasks_status", "status"),
        # CHECK: task_type is 'roadmap_item' iff roadmap_item_id is NOT NULL
        CheckConstraint(
            "((task_type = 'roadmap_item' AND roadmap_item_id IS NOT NULL) OR (task_type <> 'roadmap_item' AND roadmap_item_id IS NULL))",
            name="ck_planner_tasks_type_roadmap_item",
        ),
        CheckConstraint(
            "estimated_minutes > 0 AND estimated_minutes <= 1440",
            name="ck_planner_tasks_estimated_minutes",
        ),
        CheckConstraint(
            "status IN ('pending', 'in_progress', 'completed', 'cancelled')",
            name="ck_planner_tasks_status",
        ),
        CheckConstraint(
            "priority IN ('low', 'medium', 'high')",
            name="ck_planner_tasks_priority",
        ),
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
    roadmap_item_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roadmap_items.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    task_type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
        default="user_custom",
    )  # roadmap_item, user_custom, ai_suggestion
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        String(1000),
        nullable=True,
    )
    estimated_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    scheduled_date: Mapped[date] = mapped_column(
        Date,
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="pending",
        nullable=False,
    )  # pending, in_progress, completed, cancelled
    priority: Mapped[str] = mapped_column(
        String(16),
        default="medium",
        nullable=False,
    )  # low, medium, high
    user_rescheduled: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
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

    user = relationship("User", backref="planner_tasks")
    roadmap_item = relationship("RoadmapItem", backref="planner_tasks")
