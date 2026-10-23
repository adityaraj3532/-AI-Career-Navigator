import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


def default_visibility() -> Dict[str, bool]:
    return {
        "about": False,
        "skills": False,
        "projects": False,
        "certificates": False,
        "competitions": False,
        "achievements": False,
    }


class UserPortfolio(Base):
    __tablename__ = "user_portfolios"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        unique=True,
        index=True,
        nullable=False,
    )
    slug: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        index=True,
        nullable=False,
    )
    is_public: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        index=True,
    )
    headline: Mapped[Optional[str]] = mapped_column(
        String(160),
        nullable=True,
    )
    about: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    visibility: Mapped[Dict[str, bool]] = mapped_column(
        JSONB,
        default=default_visibility,
        nullable=False,
    )
    featured_item_ids: Mapped[List[str]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    custom_projects: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    custom_certificates: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    competitions: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    achievements: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
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

    user = relationship("User", backref="user_portfolio", uselist=False)
