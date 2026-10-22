import asyncio
import json
import re
import time
from typing import Any, Dict, Optional
import httpx
import jwt
from jwt.algorithms import RSAAlgorithm
from app.core.config import settings
from app.core.logging import logger
from app.core.redis import get_redis_client

JWKS_CACHE_KEY = "jwks:clerk"
JWKS_CACHE_TTL = 3600  # 1 hour
JWKS_REDIS_TIMEOUT = 1.5
_jwks_memory_cache: Optional[Dict[str, Any]] = None
_jwks_memory_expires_at = 0.0


class SecurityError(Exception):
    def __init__(self, message: str, code: str = "UNAUTHORIZED"):
        self.message = message
        self.code = code
        super().__init__(message)


async def get_clerk_jwks(force_refresh: bool = False) -> Dict[str, Any]:
    """Load Clerk signing keys, using Redis as an optional cache."""
    global _jwks_memory_cache, _jwks_memory_expires_at

    redis = await get_redis_client()
    if not force_refresh:
        try:
            cached = await asyncio.wait_for(
                redis.get(JWKS_CACHE_KEY), timeout=JWKS_REDIS_TIMEOUT
            )
            if cached:
                try:
                    jwks = json.loads(cached)
                    _jwks_memory_cache = jwks
                    _jwks_memory_expires_at = time.monotonic() + JWKS_CACHE_TTL
                    return jwks
                except (TypeError, json.JSONDecodeError):
                    logger.warning("Ignoring malformed Clerk JWKS cache entry")
        except Exception as exc:
            logger.warning("Redis JWKS cache read failed; fetching keys from Clerk: %s", exc)

        if _jwks_memory_cache and time.monotonic() < _jwks_memory_expires_at:
            return _jwks_memory_cache

    jwks_url = settings.CLERK_JWKS_URL or "https://api.clerk.com/v1/jwks"
    headers = {}
    if settings.CLERK_SECRET_KEY:
        headers["Authorization"] = f"Bearer {settings.CLERK_SECRET_KEY}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(jwks_url, headers=headers)
            if resp.status_code == 200:
                jwks_data = resp.json()
                _jwks_memory_cache = jwks_data
                _jwks_memory_expires_at = time.monotonic() + JWKS_CACHE_TTL
                try:
                    await asyncio.wait_for(
                        redis.set(
                            JWKS_CACHE_KEY,
                            json.dumps(jwks_data),
                            ex=JWKS_CACHE_TTL,
                        ),
                        timeout=JWKS_REDIS_TIMEOUT,
                    )
                except Exception as exc:
                    logger.warning("Could not cache Clerk JWKS in Redis: %s", exc)
                return jwks_data
            else:
                logger.error("Failed to fetch JWKS from Clerk: status %d", resp.status_code)
    except Exception as e:
        logger.error("Exception fetching JWKS: %s", e)

    if _jwks_memory_cache and time.monotonic() < _jwks_memory_expires_at:
        return _jwks_memory_cache
    return {"keys": []}


async def verify_clerk_token(token: str) -> Dict[str, Any]:
    """
    Verifies a Clerk JWT.
    Returns the decoded token claims if valid, raises SecurityError otherwise.
    """
    if not token:
        raise SecurityError("Missing authorization token")

    # Support dev token bypass for testing/mocking only outside production.
    if (
        settings.ALLOW_DEV_AUTH_BYPASS
        and not settings.is_production
        and token.startswith("dev-token-")
    ):
        # Format: dev-token-{role}-{clerk_id}
        match = re.fullmatch(r"dev-token-(student|teacher|admin)-([A-Za-z0-9_-]{1,128})", token)
        if not match:
            raise SecurityError("Invalid development token", code="INVALID_TOKEN")
        role, clerk_id = match.groups()
        return {
            "sub": clerk_id,
            "role": role,
            "public_metadata": {"role": role},
            "email": f"{role}@sbuniversity.edu",
            "name": f"Dev {role.capitalize()}",
        }

    try:
        unverified_header = jwt.get_unverified_header(token)
    except jwt.InvalidTokenError:
        raise SecurityError("Invalid token header", code="INVALID_TOKEN")

    if unverified_header.get("alg") != "RS256":
        raise SecurityError("Unsupported token signing algorithm", code="INVALID_TOKEN")

    kid = unverified_header.get("kid")
    if not kid:
        raise SecurityError("Token missing key ID (kid)")

    jwks = await get_clerk_jwks()
    keys = jwks.get("keys", [])
    matching_key = next((k for k in keys if k.get("kid") == kid), None)

    if not matching_key:
        # Try refreshing JWKS once
        jwks = await get_clerk_jwks(force_refresh=True)
        keys = jwks.get("keys", [])
        matching_key = next((k for k in keys if k.get("kid") == kid), None)

    if not matching_key:
        raise SecurityError("Unable to verify token signature: public key not found")

    public_key = RSAAlgorithm.from_jwk(json.dumps(matching_key))

    decode_kwargs: Dict[str, Any] = {
        "algorithms": ["RS256"],
        "options": {
            "verify_exp": True,
            "verify_iat": True,
            "require": ["exp", "iat", "sub"],
        },
    }
    if settings.CLERK_ISSUER:
        decode_kwargs["issuer"] = settings.CLERK_ISSUER
    elif settings.is_production:
        raise SecurityError("Token issuer validation is not configured")
    if settings.CLERK_AUDIENCE:
        decode_kwargs["audience"] = settings.CLERK_AUDIENCE

    try:
        payload = jwt.decode(token, public_key, **decode_kwargs)
        return payload
    except jwt.ExpiredSignatureError:
        raise SecurityError("Token has expired", code="TOKEN_EXPIRED")
    except jwt.InvalidTokenError:
        raise SecurityError("Invalid token", code="INVALID_TOKEN")
