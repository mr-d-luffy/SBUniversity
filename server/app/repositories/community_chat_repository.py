import uuid
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from sqlalchemy import delete, func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models.chat import (
    CommunityChatDevice,
    CommunityConversation,
    CommunityConversationKeyEnvelope,
    CommunityConversationKind,
    CommunityMessage,
)
from app.db.models.user import User, UserRole, UserStatus

COMMUNITY_CHAT_LIFETIME = timedelta(hours=10)


class CommunityChatRepository:
    ROOM_KEY = "student-community-room"

    def __init__(self, db: AsyncSession):
        self.db = db

    async def delete_expired(self, now: Optional[datetime] = None) -> int:
        cutoff = now or datetime.now(timezone.utc)
        expired_ids = list(
            (
                await self.db.execute(
                    select(CommunityConversation.id).where(
                        CommunityConversation.expires_at <= cutoff
                    )
                )
            )
            .scalars()
            .all()
        )
        if expired_ids:
            await self.db.execute(
                delete(CommunityMessage).where(
                    CommunityMessage.conversation_id.in_(expired_ids)
                )
            )
            await self.db.execute(
                delete(CommunityConversation)
                .where(CommunityConversation.id.in_(expired_ids))
                .execution_options(synchronize_session=False)
            )
            await self.db.commit()
        return len(expired_ids)

    async def get_or_create_student_room(self) -> CommunityConversation:
        stmt = select(CommunityConversation).where(
            CommunityConversation.room_key == self.ROOM_KEY
        )
        conversation = (await self.db.execute(stmt)).scalar_one_or_none()
        if conversation:
            return conversation

        now = datetime.now(timezone.utc)
        conversation = CommunityConversation(
            kind=CommunityConversationKind.STUDENT_ROOM,
            room_key=self.ROOM_KEY,
            expires_at=now + COMMUNITY_CHAT_LIFETIME,
        )
        self.db.add(conversation)
        try:
            await self.db.commit()
            await self.db.refresh(conversation)
            return conversation
        except IntegrityError:
            await self.db.rollback()
            existing = (await self.db.execute(stmt)).scalar_one_or_none()
            if existing is None:
                raise
            return existing

    async def find_peer_direct(
        self, peer_one_id: uuid.UUID, peer_two_id: uuid.UUID
    ) -> Optional[CommunityConversation]:
        stmt = select(CommunityConversation).where(
            CommunityConversation.kind == CommunityConversationKind.PEER_DIRECT,
            CommunityConversation.peer_one_id == peer_one_id,
            CommunityConversation.peer_two_id == peer_two_id,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def find_support(
        self, student_id: uuid.UUID, kind: CommunityConversationKind
    ) -> Optional[CommunityConversation]:
        stmt = select(CommunityConversation).where(
            CommunityConversation.requester_student_id == student_id,
            CommunityConversation.kind == kind,
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def save_conversation(
        self, conversation: CommunityConversation
    ) -> CommunityConversation:
        self.db.add(conversation)
        try:
            await self.db.commit()
            await self.db.refresh(conversation)
            return conversation
        except IntegrityError:
            await self.db.rollback()
            if conversation.kind == CommunityConversationKind.PEER_DIRECT:
                existing = await self.find_peer_direct(
                    conversation.peer_one_id, conversation.peer_two_id
                )
            else:
                existing = await self.find_support(
                    conversation.requester_student_id, conversation.kind
                )
            if existing is None:
                raise
            return existing

    async def list_for_student(self, student_id: uuid.UUID) -> List[CommunityConversation]:
        stmt = (
            select(CommunityConversation)
            .where(
                (CommunityConversation.room_key == self.ROOM_KEY)
                | (
                    (CommunityConversation.kind == CommunityConversationKind.PEER_DIRECT)
                    & (
                        (CommunityConversation.peer_one_id == student_id)
                        | (CommunityConversation.peer_two_id == student_id)
                    )
                )
                | (CommunityConversation.requester_student_id == student_id)
            )
            .order_by(CommunityConversation.updated_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_for_staff(
        self,
        kind: CommunityConversationKind,
        staff_id: uuid.UUID,
        include_student_room: bool = False,
        include_owned_admin_support: bool = False,
    ) -> List[CommunityConversation]:
        conversation_filter = (CommunityConversation.kind == kind) | (
            (CommunityConversation.kind == CommunityConversationKind.PEER_DIRECT)
            & (
                (CommunityConversation.peer_one_id == staff_id)
                | (CommunityConversation.peer_two_id == staff_id)
            )
        )
        if include_student_room:
            conversation_filter = conversation_filter | (
                CommunityConversation.room_key == self.ROOM_KEY
            )
        if include_owned_admin_support:
            conversation_filter = conversation_filter | (
                (CommunityConversation.kind == CommunityConversationKind.ADMIN_SUPPORT)
                & (CommunityConversation.requester_student_id == staff_id)
            )
        stmt = (
            select(CommunityConversation)
            .where(conversation_filter)
            .order_by(CommunityConversation.updated_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_last_messages(
        self, conversations: List[CommunityConversation]
    ) -> dict[uuid.UUID, CommunityMessage]:
        if not conversations:
            return {}
        latest_time = (
            select(
                CommunityMessage.conversation_id.label("conversation_id"),
                func.max(CommunityMessage.created_at).label("created_at"),
            )
            .where(
                CommunityMessage.conversation_id.in_(
                    [conversation.id for conversation in conversations]
                )
            )
            .group_by(CommunityMessage.conversation_id)
            .subquery()
        )
        stmt = (
            select(CommunityMessage)
            .join(
                latest_time,
                (CommunityMessage.conversation_id == latest_time.c.conversation_id)
                & (CommunityMessage.created_at == latest_time.c.created_at),
            )
        )
        messages = (await self.db.execute(stmt)).scalars().all()
        return {message.conversation_id: message for message in messages}

    async def get_users(self, user_ids: set[uuid.UUID]) -> dict[uuid.UUID, User]:
        if not user_ids:
            return {}
        users = (
            await self.db.execute(select(User).where(User.id.in_(user_ids)))
        ).scalars().all()
        return {user.id: user for user in users}

    async def get_device(self, device_id: uuid.UUID) -> Optional[CommunityChatDevice]:
        return await self.db.get(CommunityChatDevice, device_id)

    async def save_device(self, device: CommunityChatDevice) -> None:
        self.db.add(device)
        await self.db.commit()

    async def list_devices_for_users(
        self, user_ids: set[uuid.UUID]
    ) -> List[CommunityChatDevice]:
        if not user_ids:
            return []
        stmt = (
            select(CommunityChatDevice)
            .join(User, CommunityChatDevice.user_id == User.id)
            .where(
                CommunityChatDevice.user_id.in_(user_ids),
                User.status == UserStatus.ACTIVE,
            )
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def list_active_user_ids(
        self, roles: set[UserRole], include: Optional[set[uuid.UUID]] = None
    ) -> set[uuid.UUID]:
        stmt = select(User.id).where(
            User.status == UserStatus.ACTIVE,
            User.role.in_(roles),
        )
        ids = set((await self.db.execute(stmt)).scalars().all())
        return ids | (include or set())

    async def list_key_envelopes(
        self, conversation_id: uuid.UUID
    ) -> list[CommunityConversationKeyEnvelope]:
        stmt = (
            select(CommunityConversationKeyEnvelope)
            .where(
                CommunityConversationKeyEnvelope.conversation_id == conversation_id,
            )
            .order_by(CommunityConversationKeyEnvelope.created_at.desc())
        )
        return list((await self.db.execute(stmt)).scalars().all())

    async def get_key_envelope(
        self, conversation_id: uuid.UUID, key_id: uuid.UUID, device_id: uuid.UUID
    ) -> Optional[CommunityConversationKeyEnvelope]:
        return await self.db.get(
            CommunityConversationKeyEnvelope, (conversation_id, key_id, device_id)
        )

    async def save_key_envelope(
        self, envelope: CommunityConversationKeyEnvelope
    ) -> None:
        self.db.add(envelope)
        try:
            await self.db.commit()
        except IntegrityError:
            await self.db.rollback()
            existing = await self.get_key_envelope(
                envelope.conversation_id, envelope.key_id, envelope.device_id
            )
            if existing is None:
                raise

    async def get_accessible_conversation(
        self, conversation_id: uuid.UUID
    ) -> Optional[CommunityConversation]:
        stmt = select(CommunityConversation).where(
            CommunityConversation.id == conversation_id
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def list_messages(
        self, conversation_id: uuid.UUID, limit: int = 100
    ) -> List[CommunityMessage]:
        stmt = (
            select(CommunityMessage)
            .options(selectinload(CommunityMessage.sender))
            .where(CommunityMessage.conversation_id == conversation_id)
            .order_by(CommunityMessage.created_at.desc(), CommunityMessage.id.desc())
            .limit(limit)
        )
        return list(reversed((await self.db.execute(stmt)).scalars().all()))

    async def get_message(self, message_id: uuid.UUID) -> Optional[CommunityMessage]:
        stmt = (
            select(CommunityMessage)
            .options(selectinload(CommunityMessage.conversation))
            .where(CommunityMessage.id == message_id)
        )
        return (await self.db.execute(stmt)).scalar_one_or_none()

    async def add_message(
        self,
        conversation: CommunityConversation,
        sender_id: uuid.UUID,
        content: str,
        audio_path: Optional[str] = None,
        audio_mime_type: Optional[str] = None,
        audio_size_bytes: Optional[int] = None,
    ) -> CommunityMessage:
        now = datetime.now(timezone.utc)
        message = CommunityMessage(
            conversation_id=conversation.id,
            sender_id=sender_id,
            content=content,
            audio_path=audio_path,
            audio_mime_type=audio_mime_type,
            audio_size_bytes=audio_size_bytes,
            created_at=now,
        )
        conversation.updated_at = now
        conversation.expires_at = now + COMMUNITY_CHAT_LIFETIME
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)
        stmt = (
            select(CommunityMessage)
            .options(selectinload(CommunityMessage.sender))
            .where(CommunityMessage.id == message.id)
        )
        return (await self.db.execute(stmt)).scalar_one()

    async def list_active_students(
        self, current_user_id: uuid.UUID, search: str = ""
    ) -> List[User]:
        stmt = (
            select(User)
            .where(
                User.id != current_user_id,
                User.role == UserRole.STUDENT,
                User.status == UserStatus.ACTIVE,
            )
            .order_by(User.full_name.asc())
        )
        if search.strip():
            stmt = stmt.where(User.full_name.ilike(f"%{search.strip()}%"))
        return list((await self.db.execute(stmt)).scalars().all())
