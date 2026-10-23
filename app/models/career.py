import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import DateTime, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


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
    overview: Mapped[str] = mapped_column(
        Text,
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
    # Documented scale: Dict[str, int] with RIASEC keys ("R", "I", "A", "S", "E", "C")
    # normalized on a 0-100 scale representing archetype dimension affinity.
    dimension_weights: Mapped[Dict[str, Any]] = mapped_column(
        JSONB,
        nullable=False,
    )
    reviewer: Mapped[Optional[str]] = mapped_column(
        String(128),
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
