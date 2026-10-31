import json
import time
from io import BytesIO

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi import HTTPException
from httpx import AsyncClient
from starlette.datastructures import UploadFile
from starlette.requests import Request
from starlette.responses import Response

from app.core import security
from app.core.config import settings
from app.core.rate_limit import RateLimiter
from app.core.redis import InMemoryRedisFallback
from app.core.security import SecurityError, verify_clerk_token
from app.core.uploads import read_audio_upload, read_image_upload
from app.main import should_record_request_telemetry
from app.services.storage_service import _local_storage_path


@pytest.mark.parametrize(
    "path",
    [
        "/api/v1/community-chat/conversations",
        "/api/v1/community-chat/conversations/abc-123/messages",
        "/api/v1/community-chat/conversations/abc-123/devices",
        "/api/v1/community-chat/conversations/abc-123/keys",
        "/api/v1/whiteboard/courses/course-123/session",
        "/api/v1/whiteboard/sessions/session-123/messages",
    ],
)
def test_high_frequency_polling_is_not_written_to_request_telemetry(path: str):
    assert not should_record_request_telemetry("GET", path)


def test_non_polling_gets_remain_in_request_telemetry():
    assert should_record_request_telemetry("GET", "/api/v1/community-chat/students")
    assert should_record_request_telemetry("GET", "/api/v1/whiteboard/courses")
    assert not should_record_request_telemetry("POST", "/api/v1/community-chat/conversations")


@pytest.mark.asyncio
async def test_development_bypass_accepts_only_valid_role_and_subject(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "DEBUG", True)
    monkeypatch.setattr(settings, "ALLOW_DEV_AUTH_BYPASS", True)

    claims = await verify_clerk_token("dev-token-admin-user_123")
    assert claims["sub"] == "user_123"
    assert claims["role"] == "admin"
    with pytest.raises(SecurityError):
        await verify_clerk_token("dev-token-admin")


@pytest.mark.asyncio
async def test_development_bypass_cannot_be_used_in_production(monkeypatch):
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "DEBUG", True)
    monkeypatch.setattr(settings, "ALLOW_DEV_AUTH_BYPASS", True)

    with pytest.raises(SecurityError):
        await verify_clerk_token("dev-token-admin-user_123")


@pytest.mark.asyncio
async def test_jwt_requires_signature_and_issuer_audience_time_claims(monkeypatch):
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public_jwk = json.loads(jwt.algorithms.RSAAlgorithm.to_jwk(private_key.public_key()))
    public_jwk["kid"] = "unit-test-key"
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "ALLOW_DEV_AUTH_BYPASS", False)
    monkeypatch.setattr(settings, "CLERK_ISSUER", "https://clerk.example")
    monkeypatch.setattr(settings, "CLERK_AUDIENCE", "sbu-api")

    async def get_test_jwks(force_refresh=False):
        return {"keys": [public_jwk]}

    monkeypatch.setattr(security, "get_clerk_jwks", get_test_jwks)
    claims = {
        "sub": "clerk-user",
        "iss": "https://clerk.example",
        "aud": "sbu-api",
        "iat": int(time.time()),
        "exp": int(time.time()) + 60,
    }
    token = jwt.encode(
        claims, private_key, algorithm="RS256", headers={"kid": "unit-test-key"}
    )
    assert (await verify_clerk_token(token))["sub"] == "clerk-user"

    missing_iat = {key: value for key, value in claims.items() if key != "iat"}
    invalid_token = jwt.encode(
        missing_iat, private_key, algorithm="RS256", headers={"kid": "unit-test-key"}
    )
    with pytest.raises(SecurityError):
        await verify_clerk_token(invalid_token)


@pytest.mark.asyncio
async def test_authentication_token_is_not_accepted_in_url(client: AsyncClient):
    response = await client.get("/me?token=dev-token-student-u_student1")
    assert response.status_code == 401
    assert response.headers["x-request-id"]
    assert response.headers["x-content-type-options"] == "nosniff"


@pytest.mark.asyncio
async def test_audio_upload_checks_content_signature():
    valid = UploadFile(
        file=BytesIO(b"\x1a\x45\xdf\xa3webm-data"),
        filename="recording.webm",
        headers={"content-type": "audio/webm"},
    )
    content, media_type, extension = await read_audio_upload(valid, 1024)
    assert content.startswith(b"\x1a\x45\xdf\xa3")
    assert (media_type, extension) == ("audio/webm", "webm")

    spoofed = UploadFile(
        file=BytesIO(b"not audio"),
        filename="recording.webm",
        headers={"content-type": "audio/webm"},
    )
    with pytest.raises(HTTPException) as error:
        await read_audio_upload(spoofed, 1024)
    assert getattr(error.value, "status_code", None) == 415


@pytest.mark.asyncio
async def test_profile_image_upload_checks_size_and_signature():
    upload = UploadFile(
        file=BytesIO(b"\xff\xd8\xffjpeg-data"),
        filename="../../profile.jpg",
        headers={"content-type": "image/jpeg"},
    )
    content, media_type, extension = await read_image_upload(upload, 1024)
    assert content.startswith(b"\xff\xd8\xff")
    assert (media_type, extension) == ("image/jpeg", "jpg")


def test_local_storage_rejects_traversal():
    with pytest.raises(ValueError):
        _local_storage_path("../outside.txt")


@pytest.mark.asyncio
async def test_rate_limiter_counts_user_and_client_ip(monkeypatch):
    fallback = InMemoryRedisFallback()

    async def get_test_redis():
        return fallback

    monkeypatch.setattr("app.core.rate_limit.get_redis_client", get_test_redis)
    monkeypatch.setattr(settings, "APP_ENV", "development")
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "http",
            "path": "/api/v1/test",
            "raw_path": b"/api/v1/test",
            "query_string": b"",
            "headers": [],
            "client": ("192.0.2.1", 1234),
            "server": ("test", 80),
        }
    )
    user = type("TestUser", (), {"clerk_user_id": "user-1", "id": "user-1"})()
    limiter = RateLimiter(requests_limit=1, window_seconds=60)
    await limiter(request, Response(), user)
    with pytest.raises(HTTPException) as error:
        await limiter(request, Response(), user)
    assert error.value.status_code == 429


@pytest.mark.asyncio
async def test_rate_limiter_fails_closed_in_production(monkeypatch):
    async def unavailable_redis():
        return InMemoryRedisFallback()

    monkeypatch.setattr("app.core.rate_limit.get_redis_client", unavailable_redis)
    monkeypatch.setattr(settings, "APP_ENV", "production")
    monkeypatch.setattr(settings, "RATE_LIMIT_ENABLED", True)
    request = Request(
        {
            "type": "http",
            "http_version": "1.1",
            "method": "POST",
            "scheme": "https",
            "path": "/api/v1/test",
            "raw_path": b"/api/v1/test",
            "query_string": b"",
            "headers": [],
            "client": ("192.0.2.1", 1234),
            "server": ("test", 443),
        }
    )
    user = type("TestUser", (), {"clerk_user_id": "user-1", "id": "user-1"})()
    with pytest.raises(HTTPException) as error:
        await RateLimiter(10, 60)(request, Response(), user)
    assert error.value.status_code == 503
