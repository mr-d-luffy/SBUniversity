import json
from fastapi import APIRouter, Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession
from svix.webhooks import Webhook, WebhookVerificationError
from app.core.config import settings
from app.core.logging import logger
from app.db.models.user import StudentProfile, User, UserRole, UserStatus
from app.db.session import get_db
from app.repositories.user_repository import UserRepository

router = APIRouter(prefix="/webhooks", tags=["Webhooks"])


@router.post("/clerk")
async def clerk_webhook(
    request: Request,
    svix_id: str = Header(None, alias="svix-id"),
    svix_timestamp: str = Header(None, alias="svix-timestamp"),
    svix_signature: str = Header(None, alias="svix-signature"),
    db: AsyncSession = Depends(get_db),
):
    body = await request.body()

    # Verify Svix webhook signature if secret is configured
    if settings.CLERK_WEBHOOK_SECRET:
        if not svix_id or not svix_timestamp or not svix_signature:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing Svix signature headers")
        headers = {
            "svix-id": svix_id,
            "svix-timestamp": svix_timestamp,
            "svix-signature": svix_signature,
        }
        wh = Webhook(settings.CLERK_WEBHOOK_SECRET)
        try:
            payload = wh.verify(body, headers)
        except WebhookVerificationError as e:
            logger.error("Clerk webhook verification failed: %s", e)
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid signature")
    else:
        try:
            payload = json.loads(body)
        except (json.JSONDecodeError, UnicodeDecodeError) as e:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Webhook body must contain valid JSON",
            ) from e

    if not isinstance(payload, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload must be a JSON object",
        )

    event_type = payload.get("type")
    data = payload.get("data", {})
    if not isinstance(event_type, str) or not isinstance(data, dict):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Webhook payload must include a string type and object data",
        )

    user_repo = UserRepository(db)

    logger.info("Received Clerk webhook event: %s", event_type)

    if event_type == "user.created":
        clerk_id = data.get("id")
        email_addresses = data.get("email_addresses", [])
        email = email_addresses[0].get("email_address") if email_addresses else f"{clerk_id}@sbuniversity.edu"
        first_name = data.get("first_name") or ""
        last_name = data.get("last_name") or ""
        full_name = f"{first_name} {last_name}".strip() or "SiliconBrains University Student"
        avatar_url = data.get("image_url")
        role_str = data.get("public_metadata", {}).get("role", "student")

        try:
            role = UserRole(role_str)
        except ValueError:
            role = UserRole.STUDENT

        existing = await user_repo.get_by_clerk_id(clerk_id)
        if not existing:
            user = User(
                clerk_user_id=clerk_id,
                email=email,
                full_name=full_name,
                avatar_url=avatar_url,
                role=role,
                status=UserStatus.ACTIVE,
            )
            # Create default student profile if student
            if role == UserRole.STUDENT:
                student_code = await user_repo.next_student_code(2026)
                user.student_profile = StudentProfile(student_code=student_code, qr_token=str(clerk_id))

            await user_repo.create(user)
            logger.info("Created user %s (%s)", user.id, email)

    elif event_type == "user.updated":
        clerk_id = data.get("id")
        user = await user_repo.get_by_clerk_id(clerk_id)
        if user:
            public_metadata = data.get("public_metadata")
            role_str = (
                public_metadata.get("role")
                if isinstance(public_metadata, dict)
                else None
            )
            if role_str:
                try:
                    user.role = UserRole(role_str)
                except ValueError:
                    logger.warning("Ignoring unknown Clerk role value in user.updated event")
            first_name = data.get("first_name") or ""
            last_name = data.get("last_name") or ""
            full_name = f"{first_name} {last_name}".strip()
            if full_name:
                user.full_name = full_name
            if data.get("image_url"):
                user.avatar_url = data.get("image_url")
            await user_repo.update(user)

    elif event_type == "user.deleted":
        clerk_id = data.get("id")
        user = await user_repo.get_by_clerk_id(clerk_id)
        if user:
            user.status = UserStatus.DELETED
            await user_repo.update(user)

    return {"received": True}
