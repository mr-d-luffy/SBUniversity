from pathlib import Path
from pathlib import PurePosixPath
from typing import Optional
from app.core.config import settings
from app.core.logging import logger

try:
    from supabase import Client, create_client
    supabase_client: Optional[Client] = None
    if settings.SUPABASE_URL and settings.SUPABASE_SERVICE_KEY:
        supabase_client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
except Exception as e:
    supabase_client = None
    logger.warning("Supabase client init failed or skipped: %s", e)

LOCAL_STORAGE_DIR = Path("storage_local")
LOCAL_STORAGE_DIR.mkdir(parents=True, exist_ok=True)


def _validate_storage_key(path: str) -> None:
    key = PurePosixPath(path)
    if not path or "\\" in path or key.is_absolute() or ".." in key.parts:
        raise ValueError("Invalid storage path")


def _local_storage_path(path: str) -> Path:
    root = LOCAL_STORAGE_DIR.resolve()
    candidate = Path(path)
    resolved = candidate.resolve() if candidate.is_absolute() else (root / candidate).resolve()
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise ValueError("Storage path escapes the local storage directory") from exc
    return resolved


class StorageService:
    @staticmethod
    async def upload_file(path: str, content: bytes, content_type: str = "application/pdf") -> str:
        """Uploads to Supabase Storage, with a development-only local fallback."""
        _validate_storage_key(path)
        if supabase_client:
            try:
                bucket = settings.SUPABASE_STORAGE_BUCKET
                res = supabase_client.storage.from_(bucket).upload(
                    path=path,
                    file=content,
                    file_options={"content-type": content_type, "upsert": "true"},
                )
                logger.info("Uploaded %s to Supabase Storage", path)
                return path
            except Exception as e:
                logger.error("Failed uploading to Supabase Storage: %s", e)
                if settings.is_production:
                    raise RuntimeError("Could not upload stored file") from e

        if settings.is_production:
            raise RuntimeError("Supabase Storage is required in production")

        local_path = _local_storage_path(path)
        local_path.parent.mkdir(parents=True, exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(content)
        return str(local_path.resolve())

    @staticmethod
    async def download_file(path: str) -> Optional[bytes]:
        """Downloads from Supabase Storage, with a development-only local fallback."""
        local_path = _local_storage_path(path)
        if supabase_client and not Path(path).is_absolute():
            _validate_storage_key(path)
            try:
                bucket = settings.SUPABASE_STORAGE_BUCKET
                res = supabase_client.storage.from_(bucket).download(path)
                return res
            except Exception as e:
                logger.error("Failed downloading from Supabase Storage: %s", e)
                if settings.is_production:
                    raise RuntimeError("Could not download stored file") from e

        if settings.is_production:
            raise RuntimeError("Supabase Storage is required in production")
        if local_path.exists():
            with open(local_path, "rb") as f:
                return f.read()

        return None

    @staticmethod
    async def delete_file(path: str) -> None:
        """Deletes a stored object from Supabase Storage or local disk."""
        if supabase_client and not Path(path).is_absolute():
            _validate_storage_key(path)
            try:
                bucket = settings.SUPABASE_STORAGE_BUCKET
                supabase_client.storage.from_(bucket).remove([path])
                return
            except Exception as e:
                logger.error("Failed deleting %s from Supabase Storage: %s", path, e)
                raise RuntimeError("Could not delete stored file") from e

        if settings.is_production:
            raise RuntimeError("Supabase Storage is required in production")
        local_path = _local_storage_path(path)
        try:
            local_path.unlink(missing_ok=True)
        except OSError as e:
            logger.error("Failed deleting local stored file %s: %s", local_path, e)
            raise RuntimeError("Could not delete stored file") from e
