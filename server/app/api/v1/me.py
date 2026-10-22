import mimetypes
import uuid
from fastapi import APIRouter, Depends, File, UploadFile
from fastapi import HTTPException, status
from fastapi.responses import Response
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_current_user
from app.core.uploads import read_image_upload
from app.db.models.user import User
from app.db.session import get_db
from app.schemas.user import UserResponse, UserUpdate
from app.services.storage_service import StorageService
from app.services.user_service import UserService

router = APIRouter(prefix="/me", tags=["Me"])
MAX_PROFILE_PHOTO_BYTES = 5 * 1024 * 1024


@router.get("/photo")
async def get_profile_photo(current_user: User = Depends(get_current_user)):
    photo_path = current_user.avatar_url
    if not photo_path:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile photo not found")

    contents = await StorageService.download_file(photo_path)
    if contents is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Profile photo not found")

    media_type = mimetypes.guess_type(photo_path)[0] or "application/octet-stream"
    if not media_type.startswith("image/"):
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Profile file is not an image")

    return Response(
        content=contents,
        media_type=media_type,
        headers={
            "Cache-Control": "private, no-store",
            "X-Content-Type-Options": "nosniff",
            "Content-Disposition": "inline",
        },
    )


@router.get("", response_model=UserResponse)
async def get_my_profile(current_user: User = Depends(get_current_user)):
    return current_user


@router.patch("", response_model=UserResponse)
async def update_my_profile(
    data: UserUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service = UserService(db)
    return await service.update_profile(current_user, data)


@router.post("/photo", response_model=UserResponse)
async def upload_profile_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    contents, media_type, extension = await read_image_upload(
        file, MAX_PROFILE_PHOTO_BYTES
    )
    filename = f"avatars/{current_user.id}/{uuid.uuid4()}.{extension}"

    photo_path = await StorageService.upload_file(filename, contents, media_type)

    service = UserService(db)
    current_user.avatar_url = photo_path
    if current_user.student_profile:
        current_user.student_profile.photo_path = photo_path

    return await service.update_profile(current_user, UserUpdate(avatar_url=photo_path))
