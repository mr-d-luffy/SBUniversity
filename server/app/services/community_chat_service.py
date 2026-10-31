import base64
import uuid
from datetime import datetime, timezone
from typing import List, Optional

from cryptography.exceptions import UnsupportedAlgorithm
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException

from app.db.models.chat import (
    CommunityChatDevice,
    CommunityConversation,
    CommunityConversationKeyEnvelope,
    CommunityConversationKind,
)
from app.db.models.user import User, UserRole, UserStatus
from app.repositories.community_chat_repository import (
    COMMUNITY_CHAT_LIFETIME,
    CommunityChatRepository,
)
from app.schemas.chat import (
    CommunityChatDeviceResponse,
    CommunityConversationResponse,
    CommunityKeyEnvelopeCreate,
    CommunityKeyEnvelopeResponse,
    CommunityMessageResponse,
    CommunityStudentOption,
)
from app.services.storage_service import StorageService


class CommunityChatService:
    def __init__(self, repository: CommunityChatRepository):
        self.repo = repository

    async def cleanup_expired(self) -> int:
        return await self.repo.delete_expired()

    async def get_or_create_student_room(self, user: User) -> CommunityConversation:
        if user.role not in {UserRole.STUDENT, UserRole.TEACHER}:
            raise HTTPException(status_code=403, detail="This chat action is not allowed")
        await self.cleanup_expired()
        return await self.repo.get_or_create_student_room()

    async def list_conversations(
        self, user: User
    ) -> List[CommunityConversationResponse]:
        await self.cleanup_expired()
        if user.role == UserRole.STUDENT:
            room = await self.repo.get_or_create_student_room()
            conversations = await self.repo.list_for_student(user.id)
            if room.id not in {conversation.id for conversation in conversations}:
                conversations.append(room)
        elif user.role in {UserRole.ADMIN, UserRole.TEACHER}:
            kind = (
                CommunityConversationKind.ADMIN_SUPPORT
                if user.role == UserRole.ADMIN
                else CommunityConversationKind.TEACHER_SUPPORT
            )
            conversations = await self.repo.list_for_staff(
                kind,
                user.id,
                include_student_room=user.role == UserRole.TEACHER,
                include_owned_admin_support=user.role == UserRole.TEACHER,
            )
            if user.role == UserRole.TEACHER:
                room = await self.repo.get_or_create_student_room()
                if room.id not in {conversation.id for conversation in conversations}:
                    conversations.append(room)
        else:
            raise HTTPException(status_code=403, detail="Community chat is unavailable")

        messages = await self.repo.list_last_messages(conversations)
        user_ids: set[uuid.UUID] = set()
        for conversation in conversations:
            if conversation.kind == CommunityConversationKind.PEER_DIRECT:
                user_ids.add(
                    conversation.peer_two_id
                    if conversation.peer_one_id == user.id
                    else conversation.peer_one_id
                )
            elif conversation.kind in {
                CommunityConversationKind.ADMIN_SUPPORT,
                CommunityConversationKind.TEACHER_SUPPORT,
            }:
                user_ids.add(conversation.requester_student_id)
        users = await self.repo.get_users(user_ids)

        return [
            self._conversation_response(conversation, user, messages, users)
            for conversation in conversations
        ]

    async def list_students(
        self, current_user: User, search: str = ""
    ) -> List[CommunityStudentOption]:
        if (
            current_user.role != UserRole.STUDENT
            or current_user.status != UserStatus.ACTIVE
        ):
            raise HTTPException(status_code=403, detail="This chat action is not allowed")
        await self.cleanup_expired()
        students = await self.repo.list_active_students(current_user.id, search)
        return [
            CommunityStudentOption(
                id=student.id,
                full_name=student.full_name,
                avatar_url=student.avatar_url,
            )
            for student in students
        ]

    async def register_device(
        self, user: User, device_id: uuid.UUID, public_key: str
    ) -> CommunityChatDeviceResponse:
        if user.status != UserStatus.ACTIVE:
            raise HTTPException(status_code=403, detail="This chat action is not allowed")
        try:
            parsed_key = serialization.load_der_public_key(
                base64.b64decode(public_key, validate=True)
            )
        except (ValueError, TypeError, UnsupportedAlgorithm) as error:
            raise HTTPException(status_code=422, detail="Invalid chat device public key") from error
        if not isinstance(parsed_key, rsa.RSAPublicKey) or parsed_key.key_size != 3072:
            raise HTTPException(status_code=422, detail="Chat device keys must be RSA-3072")
        existing = await self.repo.get_device(device_id)
        if existing:
            if existing.user_id != user.id or existing.public_key != public_key:
                raise HTTPException(status_code=409, detail="This chat device is already registered")
            return CommunityChatDeviceResponse(
                device_id=existing.device_id,
                user_id=existing.user_id,
                public_key=existing.public_key,
            )
        device = CommunityChatDevice(
            device_id=device_id,
            user_id=user.id,
            public_key=public_key,
        )
        await self.repo.save_device(device)
        return CommunityChatDeviceResponse(
            device_id=device.device_id,
            user_id=device.user_id,
            public_key=device.public_key,
        )

    async def list_conversation_devices(
        self, user: User, conversation_id: uuid.UUID
    ) -> list[CommunityChatDeviceResponse]:
        conversation = await self._get_accessible_conversation(user, conversation_id)
        if conversation.kind == CommunityConversationKind.STUDENT_ROOM:
            participant_ids = await self.repo.list_active_user_ids(
                {UserRole.STUDENT, UserRole.TEACHER}
            )
        elif conversation.kind == CommunityConversationKind.PEER_DIRECT:
            participant_ids = {conversation.peer_one_id, conversation.peer_two_id}
        elif conversation.kind == CommunityConversationKind.ADMIN_SUPPORT:
            participant_ids = await self.repo.list_active_user_ids(
                {UserRole.ADMIN}, {conversation.requester_student_id}
            )
        else:
            participant_ids = await self.repo.list_active_user_ids(
                {UserRole.TEACHER}, {conversation.requester_student_id}
            )
        devices = await self.repo.list_devices_for_users(participant_ids)
        return [
            CommunityChatDeviceResponse(
                device_id=device.device_id,
                user_id=device.user_id,
                public_key=device.public_key,
            )
            for device in devices
        ]

    async def list_key_envelopes(
        self, user: User, conversation_id: uuid.UUID
    ) -> list[CommunityKeyEnvelopeResponse]:
        await self._get_accessible_conversation(user, conversation_id)
        envelopes = await self.repo.list_key_envelopes(conversation_id)
        return [
            CommunityKeyEnvelopeResponse(
                key_id=envelope.key_id,
                device_id=envelope.device_id,
                wrapped_key=envelope.wrapped_key,
                created_at=envelope.created_at,
            )
            for envelope in envelopes
        ]

    async def save_key_envelopes(
        self,
        user: User,
        conversation_id: uuid.UUID,
        sender_device_id: uuid.UUID,
        envelopes: list[CommunityKeyEnvelopeCreate],
    ) -> None:
        await self._get_accessible_conversation(user, conversation_id)
        sender_device = await self.repo.get_device(sender_device_id)
        if not sender_device or sender_device.user_id != user.id:
            raise HTTPException(status_code=404, detail="Chat device not found")
        directory = await self.list_conversation_devices(user, conversation_id)
        allowed_device_ids = {device.device_id for device in directory}
        if any(envelope.device_id not in allowed_device_ids for envelope in envelopes):
            raise HTTPException(status_code=403, detail="A key recipient is not in this chat")
        for item in envelopes:
            existing = await self.repo.get_key_envelope(
                conversation_id, item.key_id, item.device_id
            )
            if existing:
                continue
            await self.repo.save_key_envelope(
                CommunityConversationKeyEnvelope(
                    conversation_id=conversation_id,
                    key_id=item.key_id,
                    device_id=item.device_id,
                    wrapped_key=item.wrapped_key,
                )
            )

    async def start_peer_direct(
        self, current_user: User, other_student_id: uuid.UUID
    ) -> CommunityConversationResponse:
        if current_user.role not in {UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN} or current_user.status != UserStatus.ACTIVE:
            raise HTTPException(status_code=403, detail="This chat action is not allowed")
        await self.cleanup_expired()
        if other_student_id == current_user.id:
            raise HTTPException(status_code=400, detail="You cannot start a chat with yourself")
        other = await self.repo.get_users({other_student_id})
        other_student = other.get(other_student_id)
        if (
            other_student is None
            or other_student.role != UserRole.STUDENT
            or other_student.status != UserStatus.ACTIVE
        ):
            raise HTTPException(status_code=404, detail="Student not found")

        first, second = sorted((current_user.id, other_student_id), key=lambda value: value.int)
        conversation = await self.repo.find_peer_direct(first, second)
        if conversation is None:
            now = datetime.now(timezone.utc)
            conversation = await self.repo.save_conversation(
                CommunityConversation(
                    kind=CommunityConversationKind.PEER_DIRECT,
                    created_by=current_user.id,
                    peer_one_id=first,
                    peer_two_id=second,
                    expires_at=now + COMMUNITY_CHAT_LIFETIME,
                )
            )
        return self._conversation_response(
            conversation, current_user, {}, {other_student.id: other_student}
        )

    async def start_staff_support(
        self, current_user: User, staff_role: UserRole
    ) -> CommunityConversationResponse:
        if current_user.status != UserStatus.ACTIVE or not (
            current_user.role == UserRole.STUDENT
            or (current_user.role == UserRole.TEACHER and staff_role == UserRole.ADMIN)
        ):
            raise HTTPException(status_code=403, detail="This chat action is not allowed")
        if staff_role not in {UserRole.ADMIN, UserRole.TEACHER}:
            raise HTTPException(status_code=422, detail="Choose admin or teacher support")
        await self.cleanup_expired()
        kind = (
            CommunityConversationKind.ADMIN_SUPPORT
            if staff_role == UserRole.ADMIN
            else CommunityConversationKind.TEACHER_SUPPORT
        )
        conversation = await self.repo.find_support(current_user.id, kind)
        if conversation is None:
            now = datetime.now(timezone.utc)
            conversation = await self.repo.save_conversation(
                CommunityConversation(
                    kind=kind,
                    created_by=current_user.id,
                    requester_student_id=current_user.id,
                    expires_at=now + COMMUNITY_CHAT_LIFETIME,
                )
            )
        title = "Admin Support" if staff_role == UserRole.ADMIN else "Teacher Support"
        return CommunityConversationResponse(
            id=conversation.id,
            kind=conversation.kind,
            title=title,
            other_user_role=staff_role,
            expires_at=conversation.expires_at,
        )

    async def list_messages(
        self, user: User, conversation_id: uuid.UUID
    ) -> List[CommunityMessageResponse]:
        await self.cleanup_expired()
        conversation = await self._get_accessible_conversation(user, conversation_id)
        rows = await self.repo.list_messages(conversation.id)
        return [
            CommunityMessageResponse(
                id=message.id,
                conversation_id=message.conversation_id,
                sender_id=message.sender_id,
                sender_name=message.sender.full_name,
                sender_role=message.sender.role,
                sender_avatar_url=message.sender.avatar_url,
                is_mine=message.sender_id == user.id,
                content=message.content,
                audio_url=(
                    f"/community-chat/messages/{message.id}/audio"
                    if message.audio_path
                    else None
                ),
                audio_mime_type=message.audio_mime_type,
                audio_size_bytes=message.audio_size_bytes,
                created_at=message.created_at,
            )
            for message in rows
        ]

    async def send_message(
        self, user: User, conversation_id: uuid.UUID, content: str
    ) -> CommunityMessageResponse:
        await self.cleanup_expired()
        conversation = await self._get_accessible_conversation(user, conversation_id)
        normalized = content.strip()
        if not normalized:
            raise HTTPException(status_code=422, detail="Message cannot be empty")
        message = await self.repo.add_message(conversation, user.id, normalized)
        return CommunityMessageResponse(
            id=message.id,
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            sender_name=message.sender.full_name,
            sender_role=message.sender.role,
            sender_avatar_url=message.sender.avatar_url,
            is_mine=message.sender_id == user.id,
            content=message.content,
            audio_url=None,
            audio_mime_type=None,
            audio_size_bytes=None,
            created_at=message.created_at,
        )

    async def send_audio(
        self,
        user: User,
        conversation_id: uuid.UUID,
        contents: bytes,
        media_type: str,
        extension: str,
    ) -> CommunityMessageResponse:
        await self.cleanup_expired()
        conversation = await self._get_accessible_conversation(user, conversation_id)
        if not contents:
            raise HTTPException(status_code=400, detail="Audio recording is empty")
        message_id = uuid.uuid4()
        storage_path = (
            f"community-chat/{conversation.id}/{message_id}.{extension}"
        )
        saved_path = await StorageService.upload_file(
            storage_path, contents, "application/octet-stream"
        )
        try:
            message = await self.repo.add_message(
                conversation,
                user.id,
                "Voice message",
                audio_path=saved_path,
                audio_mime_type=media_type,
                audio_size_bytes=len(contents),
            )
        except Exception:
            await StorageService.delete_file(saved_path)
            raise
        return CommunityMessageResponse(
            id=message.id,
            conversation_id=message.conversation_id,
            sender_id=message.sender_id,
            sender_name=message.sender.full_name,
            sender_role=message.sender.role,
            sender_avatar_url=message.sender.avatar_url,
            is_mine=True,
            content=message.content,
            audio_url=f"/community-chat/messages/{message.id}/audio",
            audio_mime_type=message.audio_mime_type,
            audio_size_bytes=message.audio_size_bytes,
            created_at=message.created_at,
        )

    async def get_audio(
        self, user: User, message_id: uuid.UUID
    ) -> tuple[bytes, str]:
        await self.cleanup_expired()
        message = await self.repo.get_message(message_id)
        if (
            message is None
            or not message.audio_path
            or not self._can_access(user, message.conversation)
        ):
            raise HTTPException(status_code=404, detail="Voice message not found")
        contents = await StorageService.download_file(message.audio_path)
        if contents is None:
            raise HTTPException(status_code=404, detail="Voice message audio not found")
        return contents, message.audio_mime_type or "application/octet-stream"

    async def _get_accessible_conversation(
        self, user: User, conversation_id: uuid.UUID
    ) -> CommunityConversation:
        conversation = await self.repo.get_accessible_conversation(conversation_id)
        if not conversation or not self._can_access(user, conversation):
            raise HTTPException(status_code=404, detail="Chat conversation not found")
        return conversation

    @staticmethod
    def _can_access(user: User, conversation: CommunityConversation) -> bool:
        if user.status != UserStatus.ACTIVE:
            return False
        if conversation.kind == CommunityConversationKind.STUDENT_ROOM:
            return user.role in {UserRole.STUDENT, UserRole.TEACHER}
        if conversation.kind == CommunityConversationKind.PEER_DIRECT:
            return user.role in {UserRole.STUDENT, UserRole.TEACHER, UserRole.ADMIN} and user.id in {
                conversation.peer_one_id,
                conversation.peer_two_id,
            }
        if conversation.kind == CommunityConversationKind.ADMIN_SUPPORT:
            return (
                user.role == UserRole.ADMIN
                or (
                    user.role in {UserRole.STUDENT, UserRole.TEACHER}
                    and user.id == conversation.requester_student_id
                )
            )
        if conversation.kind == CommunityConversationKind.TEACHER_SUPPORT:
            return (
                user.role == UserRole.TEACHER
                or (
                    user.role == UserRole.STUDENT
                    and user.id == conversation.requester_student_id
                )
            )
        return False

    @staticmethod
    def _conversation_response(
        conversation: CommunityConversation,
        current_user: User,
        last_messages: dict,
        users: dict,
    ) -> CommunityConversationResponse:
        other_user_id: Optional[uuid.UUID] = None
        other_user_role: Optional[UserRole] = None
        if conversation.kind == CommunityConversationKind.STUDENT_ROOM:
            title = "Student Community"
        elif conversation.kind == CommunityConversationKind.PEER_DIRECT:
            other_user_id = (
                conversation.peer_two_id
                if conversation.peer_one_id == current_user.id
                else conversation.peer_one_id
            )
            title = users[other_user_id].full_name if other_user_id in users else "Student"
            other_user_role = UserRole.STUDENT
        elif conversation.kind == CommunityConversationKind.ADMIN_SUPPORT:
            requester = users.get(conversation.requester_student_id)
            is_requester = current_user.id == conversation.requester_student_id
            title = (
                "Admin Support"
                if is_requester
                else requester.full_name if requester else "User"
            )
            other_user_role = UserRole.ADMIN
            if not is_requester:
                other_user_id = conversation.requester_student_id
        else:
            requester = users.get(conversation.requester_student_id)
            title = (
                "Teacher Support"
                if current_user.role == UserRole.STUDENT
                else requester.full_name if requester else "Student"
            )
            other_user_role = UserRole.TEACHER
            if current_user.role != UserRole.STUDENT:
                other_user_id = conversation.requester_student_id

        last_message = last_messages.get(conversation.id)
        return CommunityConversationResponse(
            id=conversation.id,
            kind=conversation.kind,
            title=title,
            other_user_id=other_user_id,
            other_user_role=other_user_role,
            last_message=last_message.content if last_message else None,
            last_message_at=last_message.created_at if last_message else None,
            expires_at=conversation.expires_at,
            is_shared_room=conversation.kind == CommunityConversationKind.STUDENT_ROOM,
        )
