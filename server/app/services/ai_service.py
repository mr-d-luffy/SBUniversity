import json
import uuid
from typing import AsyncGenerator, List, Optional
from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.core.logging import logger
from app.db.models.chat import ChatMessage, ChatRole, ChatSession
from app.db.models.user import User, UserRole
from app.repositories.chat_repository import ChatRepository
from app.repositories.exam_repository import ExamRepository
from app.services.ranking_service import RankingService

SYSTEM_PROMPT_TEMPLATE = """You are Aarsh Intelligence, the academic AI assistant of SiliconBrains University.
You are professional, encouraging, knowledgeable, and helpful to university students, teachers, and staff.

Guidelines:
1. Help students with study concepts, exam preparation strategies, course questions, platform navigation (e.g. how to download results or certificates), and understanding their academic progress.
2. Under NO circumstances provide answers to active, live exam questions or facilitate academic dishonesty.
3. Keep answers concise, well-structured, clear, and pedagogically sound.
4. You have access to the user's academic context provided below.

User Academic Context:
- Name: {user_name}
- Role: {user_role}
- Current Task Points: {points}
- Current Rank: {rank}
"""


class AIService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.chat_repo = ChatRepository(db)
        self.exam_repo = ExamRepository(db)
        self.ranking_service = RankingService(db)

    async def get_or_create_session(self, user_id: uuid.UUID, session_id: Optional[uuid.UUID] = None) -> ChatSession:
        if session_id:
            sess = await self.chat_repo.get_session(session_id)
            if sess and sess.user_id == user_id:
                return sess

        new_sess = ChatSession(user_id=user_id, title="New Conversation")
        return await self.chat_repo.create_session(new_sess)

    async def chat_stream(
        self,
        user: User,
        message: str,
        session_id: Optional[uuid.UUID] = None,
    ) -> AsyncGenerator[str, None]:
        # 1. Anti-cheat guardrail: Check if student has an active in-progress exam attempt!
        if user.role == UserRole.STUDENT:
            active_attempt = await self.exam_repo.get_active_attempt_for_student(user.id)
            if active_attempt:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail={
                        "error": {
                            "code": "EXAM_IN_PROGRESS",
                            "message": "Aarsh Intelligence is unavailable while you have an active exam in progress.",
                            "details": {"attempt_id": str(active_attempt.id)},
                        }
                    },
                )

        # 2. Get/create session
        session = await self.get_or_create_session(user.id, session_id)

        # Save user message
        await self.chat_repo.add_message(session.id, ChatRole.USER, message)

        # 3. Assemble academic context
        rank_info = await self.ranking_service.get_student_rank(user.id)
        system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
            user_name=user.full_name,
            user_role=user.role.value,
            points=rank_info.points,
            rank=f"#{rank_info.rank}" if rank_info.rank else "Unranked",
        )

        full_reply_chunks: List[str] = []

        # 4. Stream response using Gemini or simulated fallback
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY != "your-gemini-api-key":
            try:
                from google import genai
                client = genai.Client(api_key=settings.GEMINI_API_KEY)
                
                # Fetch recent history for session
                history_msgs = []
                for m in session.messages[-8:]:
                    role = "user" if m.role == ChatRole.USER else "model"
                    history_msgs.append({"role": role, "parts": [{"text": m.content}]})

                prompt_contents = [{"role": "user", "parts": [{"text": f"System context:\n{system_prompt}\n\nUser message: {message}"}]}]
                
                response_stream = client.models.generate_content_stream(
                    model=settings.GEMINI_MODEL,
                    contents=prompt_contents,
                )

                for chunk in response_stream:
                    text_part = chunk.text or ""
                    if text_part:
                        full_reply_chunks.append(text_part)
                        yield f"data: {json.dumps({'token': text_part, 'session_id': str(session.id)})}\n\n"

            except Exception as e:
                logger.error("Gemini API call failed: %s", e)
                fallback_msg = f"Hello {user.full_name}, I am Aarsh Intelligence. I'm currently operating in offline mode. For support regarding your courses or exams, please reach out to academic services."
                full_reply_chunks.append(fallback_msg)
                yield f"data: {json.dumps({'token': fallback_msg, 'session_id': str(session.id)})}\n\n"
        else:
            # Informative academic fallback response
            fallback_msg = (
                f"Hello {user.full_name}! I am Aarsh Intelligence, your academic study assistant at SiliconBrains University. "
                f"You currently have {rank_info.points} Task Points. How can I assist with your studies or exam preparation today?"
            )
            for word in fallback_msg.split(" "):
                token = word + " "
                full_reply_chunks.append(token)
                yield f"data: {json.dumps({'token': token, 'session_id': str(session.id)})}\n\n"

        complete_text = "".join(full_reply_chunks).strip()
        await self.chat_repo.add_message(session.id, ChatRole.MODEL, complete_text)

        # Set title if new session
        if not session.title or session.title == "New Conversation":
            session.title = message[:40] + ("..." if len(message) > 40 else "")
            await self.db.commit()

        yield f"data: {json.dumps({'done': True, 'session_id': str(session.id)})}\n\n"
