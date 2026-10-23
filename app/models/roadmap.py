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
    from app.models.skill import Skill


# ==============================================================================
# TEMPLATES (AUTHORING / SEED CATALOG)
# ==============================================================================

class RoadmapTemplate(Base):
    __tablename__ = "roadmap_templates"
    __table_args__ = (
        UniqueConstraint("career_id", "version", name="uq_roadmap_template_career_version"),
        Index("ix_roadmap_templates_career_id", "career_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    career_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("careers.id", ondelete="CASCADE"),
        nullable=False,
    )
    version: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="draft",
        nullable=False,
    )  # "draft" | "verified"
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

    career: Mapped["Career"] = relationship("Career", lazy="selectin")
    phases: Mapped[List["TemplatePhase"]] = relationship(
        "TemplatePhase",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplatePhase.phase_order",
        lazy="selectin",
    )
    items: Mapped[List["TemplateItem"]] = relationship(
        "TemplateItem",
        back_populates="template",
        cascade="all, delete-orphan",
        order_by="TemplateItem.sequence_order",
        lazy="selectin",
    )


class TemplatePhase(Base):
    __tablename__ = "template_phases"
    __table_args__ = (
        UniqueConstraint("template_id", "phase_order", name="uq_template_phase_order"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roadmap_templates.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    phase_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    template: Mapped["RoadmapTemplate"] = relationship("RoadmapTemplate", back_populates="phases")


class TemplateItem(Base):
    __tablename__ = "template_items"
    __table_args__ = (
        Index("ix_template_items_template_id", "template_id"),
        Index("ix_template_items_phase_id", "phase_id"),
        Index("ix_template_items_item_code", "item_code"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    template_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roadmap_templates.id", ondelete="CASCADE"),
        nullable=False,
    )
    phase_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("template_phases.id", ondelete="CASCADE"),
        nullable=True,
    )
    item_code: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )  # video, problem, project, certificate, exam, internship_task, outreach
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    estimated_minutes: Mapped[int] = mapped_column(
        Integer,
        default=60,
        nullable=False,
    )
    difficulty: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )  # 1 to 3
    topic: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    skill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prerequisites: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    optional: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="draft",
        nullable=False,
    )  # "draft" | "verified"
    reviewer: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
    )
    last_verified_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    sequence_order: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    extra_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    template: Mapped["RoadmapTemplate"] = relationship("RoadmapTemplate", back_populates="items")
    skill: Mapped[Optional["Skill"]] = relationship("Skill", lazy="selectin")


# ==============================================================================
# USER ROADMAPS (INDEPENDENT COPIES)
# ==============================================================================

class Roadmap(Base):
    __tablename__ = "roadmaps"
    __table_args__ = (
        Index("ix_roadmaps_user_career", "user_id", "career_id"),
        Index("ix_roadmaps_user_status", "user_id", "status"),
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
    template_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roadmap_templates.id", ondelete="SET NULL"),
        nullable=True,
    )
    template_version: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="active",
        nullable=False,
    )  # "active" | "completed" | "archived"
    timezone: Mapped[str] = mapped_column(
        String(64),
        default="UTC",
        nullable=False,
    )
    hours_per_week: Mapped[int] = mapped_column(
        Integer,
        default=15,
        nullable=False,
    )
    start_date: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    target_completion_date: Mapped[Optional[datetime]] = mapped_column(
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

    career: Mapped["Career"] = relationship("Career", lazy="selectin")
    phases: Mapped[List["RoadmapPhase"]] = relationship(
        "RoadmapPhase",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="RoadmapPhase.phase_order",
        lazy="selectin",
    )
    items: Mapped[List["RoadmapItem"]] = relationship(
        "RoadmapItem",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="RoadmapItem.order_index",
        lazy="selectin",
    )
    replan_history: Mapped[List["ReplanHistory"]] = relationship(
        "ReplanHistory",
        back_populates="roadmap",
        cascade="all, delete-orphan",
        order_by="ReplanHistory.created_at.desc()",
        lazy="selectin",
    )


class RoadmapPhase(Base):
    __tablename__ = "roadmap_phases"
    __table_args__ = (
        Index("ix_roadmap_phases_roadmap_id", "roadmap_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roadmaps.id", ondelete="CASCADE"),
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
    )
    phase_order: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    roadmap: Mapped["Roadmap"] = relationship("Roadmap", back_populates="phases")


class RoadmapItem(Base):
    __tablename__ = "roadmap_items"
    __table_args__ = (
        Index("ix_roadmap_items_roadmap_id", "roadmap_id"),
        Index("ix_roadmap_items_status", "status"),
        Index("ix_roadmap_items_scheduled_week", "scheduled_week"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roadmaps.id", ondelete="CASCADE"),
        nullable=False,
    )
    phase_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roadmap_phases.id", ondelete="CASCADE"),
        nullable=True,
    )
    item_code: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    type: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )
    title: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    source_url: Mapped[Optional[str]] = mapped_column(
        String(512),
        nullable=True,
    )
    estimated_minutes: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    difficulty: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    topic: Mapped[str] = mapped_column(
        String(64),
        nullable=False,
    )
    skill_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("skills.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    prerequisites: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    optional: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(32),
        default="todo",
        nullable=False,
    )  # "todo" | "in_progress" | "done" | "skipped"
    scheduled_week: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    scheduled_date: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    order_index: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    extra_data: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
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

    roadmap: Mapped["Roadmap"] = relationship("Roadmap", back_populates="items")
    skill: Mapped[Optional["Skill"]] = relationship("Skill", lazy="selectin")


class ReplanHistory(Base):
    __tablename__ = "replan_history"
    __table_args__ = (
        Index("ix_replan_history_roadmap_id", "roadmap_id"),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    roadmap_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("roadmaps.id", ondelete="CASCADE"),
        nullable=False,
    )
    reason: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    summary: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        default=dict,
        nullable=False,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    roadmap: Mapped["Roadmap"] = relationship("Roadmap", back_populates="replan_history")
