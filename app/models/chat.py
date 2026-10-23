import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.database import Base


class ChatConversation(Base):
    __tablename__ = "chat_conversations"
    __table_args__ = (
        Index("ix_chat_conversations_user_updated", "user_id", "updated_at"),
        CheckConstraint(
            "mode IN ('career', 'roadmap', 'skills', 'interview')",
            name="ck_chat_conversations_mode",
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
    mode: Mapped[str] = mapped_column(
        String(32),
        nullable=False,
    )  # career, roadmap, skills, interview
    career_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("careers.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    title: Mapped[str] = mapped_column(
        String(128),
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

    user = relationship("User", backref="chat_conversations")
    career = relationship("Career", lazy="selectin")
    messages = relationship(
        "ChatMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="ChatMessage.seq.asc()",
    )


class ChatMessage(Base):
    __tablename__ = "chat_messages"
    __table_args__ = (
        UniqueConstraint("conversation_id", "seq", name="uq_chat_messages_conversation_seq"),
        Index(
            "uq_chat_messages_client_msg",
            "conversation_id",
            "client_message_id",
            unique=True,
            postgresql_where=text("client_message_id IS NOT NULL"),
        ),
        Index("ix_chat_messages_conversation_created", "conversation_id", "created_at"),
        CheckConstraint(
            "role IN ('user', 'assistant')",
            name="ck_chat_messages_role",
        ),
        CheckConstraint(
            "ai_status IN ('ok', 'fallback', 'safety')",
            name="ck_chat_messages_ai_status",
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )
    conversation_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("chat_conversations.id", ondelete="CASCADE"),
        index=True,
        nullable=False,
    )
    seq: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    client_message_id: Mapped[Optional[str]] = mapped_column(
        String(64),
        nullable=True,
    )
    role: Mapped[str] = mapped_column(
        String(16),
        nullable=False,
    )  # user, assistant
    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    sources: Mapped[List[Dict[str, Any]]] = mapped_column(
        JSONB,
        default=list,
        nullable=False,
    )
    ai_status: Mapped[str] = mapped_column(
        String(16),
        default="ok",
        nullable=False,
    )  # ok, fallback, safety
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    conversation = relationship("ChatConversation", back_populates="messages")
