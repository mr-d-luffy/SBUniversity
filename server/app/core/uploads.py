from typing import Callable

from fastapi import HTTPException, UploadFile


AUDIO_TYPES = {
    "audio/webm": ("webm", lambda content: content.startswith(b"\x1a\x45\xdf\xa3")),
    "audio/ogg": ("ogg", lambda content: content.startswith(b"OggS")),
    "audio/mp4": ("m4a", lambda content: len(content) >= 8 and content[4:8] == b"ftyp"),
    "audio/mpeg": (
        "mp3",
        lambda content: content.startswith(b"ID3")
        or (len(content) >= 2 and content[0] == 0xFF and content[1] & 0xE0 == 0xE0),
    ),
    "audio/wav": (
        "wav",
        lambda content: len(content) >= 12
        and content.startswith(b"RIFF")
        and content[8:12] == b"WAVE",
    ),
    "audio/x-wav": (
        "wav",
        lambda content: len(content) >= 12
        and content.startswith(b"RIFF")
        and content[8:12] == b"WAVE",
    ),
    "audio/aac": (
        "aac",
        lambda content: len(content) >= 2
        and content[0] == 0xFF
        and content[1] & 0xF6 == 0xF0,
    ),
}

IMAGE_TYPES = {
    "image/jpeg": ("jpg", lambda content: content.startswith(b"\xff\xd8\xff")),
    "image/png": ("png", lambda content: content.startswith(b"\x89PNG\r\n\x1a\n")),
    "image/webp": (
        "webp",
        lambda content: len(content) >= 12
        and content.startswith(b"RIFF")
        and content[8:12] == b"WEBP",
    ),
}


async def read_validated_upload(
    upload: UploadFile,
    allowed_types: dict[str, tuple[str, Callable[[bytes], bool]]],
    max_bytes: int,
    file_kind: str,
) -> tuple[bytes, str, str]:
    media_type = (upload.content_type or "").split(";", maxsplit=1)[0].strip().lower()
    descriptor = allowed_types.get(media_type)
    if descriptor is None:
        await upload.close()
        raise HTTPException(status_code=415, detail=f"Unsupported {file_kind} format.")

    contents = await upload.read(max_bytes + 1)
    await upload.close()
    if not contents:
        raise HTTPException(status_code=400, detail=f"{file_kind.capitalize()} is empty.")
    if len(contents) > max_bytes:
        raise HTTPException(status_code=413, detail=f"{file_kind.capitalize()} exceeds the size limit.")

    extension, signature_check = descriptor
    if not signature_check(contents):
        raise HTTPException(status_code=415, detail=f"File contents are not a valid {file_kind} format.")
    return contents, media_type, extension


async def read_audio_upload(upload: UploadFile, max_bytes: int) -> tuple[bytes, str, str]:
    return await read_validated_upload(upload, AUDIO_TYPES, max_bytes, "audio")


async def read_image_upload(upload: UploadFile, max_bytes: int) -> tuple[bytes, str, str]:
    return await read_validated_upload(upload, IMAGE_TYPES, max_bytes, "image")
