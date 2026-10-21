import enum
import uuid
from datetime import datetime
from typing import List, Optional
from sqlalchemy import (
    CheckConstraint,
    DateTime,
    Enum,
    ForeignKey,
    String,
    Text,
    UniqueConstraint,
    Uuid,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class ChatRole(str, enum.Enum):
    USER = "user"
    MODEL = "model"


class CommunityConversationKind(str, enum.Enum):
    STUDENT_ROOM = "student_room"
    PEER_DIRECT = "peer_direct"
    ADMIN_SUPPORT = "admin_support"
    TEACHER_SUPPORT = "teacher_support"


class ChatSession(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "chat_sessions"

    user_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    title: Mapped[Optional[str]] = mapped_column(String, nullable=True)

    user: Mapped["User"] = relationship("User", back_populates="chat_sessions")
    messages: Mapped[List["ChatMessage"]] = relationship("ChatMessage", back_populates="session", cascade="all, delete-orphan", order_by="ChatMessage.created_at")


class ChatMessage(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "chat_messages"

    session_id: Mapped[uuid.UUID] = mapped_column(Uuid, ForeignKey("chat_sessions.id", ondelete="CASCADE"), nullable=False, index=True)
    role: Mapped[ChatRole] = mapped_column(
        Enum(ChatRole, name="chat_role", values_callable=lambda obj: [e.value for e in obj]),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)

    session: Mapped["ChatSession"] = relationship("ChatSession", back_populates="messages")


class CommunityConversation(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    __tablename__ = "community_conversations"
    __table_args__ = (
        UniqueConstraint("room_key", name="uq_community_conversation_room_key"),
        UniqueConstraint(
            "peer_one_id",
            "peer_two_id",
            name="uq_community_conversation_peer_pair",
        ),
        UniqueConstraint(
            "requester_student_id",
            "kind",
            name="uq_community_conversation_student_support_kind",
        ),
        CheckConstraint(
            "(kind = 'student_room' AND room_key IS NOT NULL "
            "AND peer_one_id IS NULL AND peer_two_id IS NULL "
            "AND requester_student_id IS NULL) OR "
            "(kind = 'peer_direct' AND room_key IS NULL "
            "AND peer_one_id IS NOT NULL AND peer_two_id IS NOT NULL "
            "AND peer_one_id < peer_two_id AND requester_student_id IS NULL) OR "
            "(kind IN ('admin_support', 'teacher_support') "
            "AND room_key IS NULL AND peer_one_id IS NULL AND peer_two_id IS NULL "
            "AND requester_student_id IS NOT NULL)",
            name="ck_community_conversation_target",
        ),
    )

    kind: Mapped[CommunityConversationKind] = mapped_column(
        Enum(
            CommunityConversationKind,
            name="community_conversation_kind",
            values_callable=lambda obj: [entry.value for entry in obj],
        ),
        nullable=False,
        index=True,
    )
    created_by: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="SET NULL"), nullable=True
    )
    room_key: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    peer_one_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    peer_two_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    requester_student_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=True
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, index=True
    )

    messages: Mapped[List["CommunityMessage"]] = relationship(
        "CommunityMessage",
        back_populates="conversation",
        cascade="all, delete-orphan",
        order_by="CommunityMessage.created_at",
    )


class CommunityMessage(Base, UUIDPrimaryKeyMixin):
    __tablename__ = "community_messages"
    __table_args__ = (
        CheckConstraint(
            "length(content) > 0 AND length(content) <= 4000",
            name="ck_community_message_content_length",
        ),
        CheckConstraint(
            "audio_size_bytes IS NULL OR "
            "(audio_size_bytes > 0 AND audio_size_bytes <= 26214400)",
            name="ck_community_message_audio_size",
        ),
    )

    conversation_id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        ForeignKey("community_conversations.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    sender_id: Mapped[uuid.UUID] = mapped_column(
        Uuid, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    audio_path: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    audio_mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    audio_size_bytes: Mapped[Optional[int]] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False, index=True
    )

    conversation: Mapped["CommunityConversation"] = relationship(
        "CommunityConversation", back_populates="messages"
    )
    sender: Mapped["User"] = relationship("User", foreign_keys=[sender_id])
