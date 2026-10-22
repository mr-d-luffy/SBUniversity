from fastapi import Depends, HTTPException, Request, Response, status
from app.core.config import settings
from app.core.deps import get_current_user
from app.core.logging import logger
from app.core.redis import InMemoryRedisFallback, get_redis_client
from app.db.models.user import User


class RateLimiter:
    def __init__(self, requests_limit: int, window_seconds: int, key_prefix: str = "rl"):
        self.limit = requests_limit
        self.window = window_seconds
        self.key_prefix = key_prefix

    async def __call__(
        self,
        request: Request,
        response: Response,
        current_user: User = Depends(get_current_user),
    ):
        if not settings.RATE_LIMIT_ENABLED:
            return True

        try:
            redis = await get_redis_client()
            current_counts = []
            if isinstance(redis, InMemoryRedisFallback):
                if settings.is_production:
                    raise RuntimeError("Redis is unavailable for production rate limiting")
                identifiers = [f"user:{current_user.clerk_user_id}"]
                if request.client:
                    identifiers.append(f"ip:{request.client.host}")
                for identifier in set(identifiers):
                    key = f"{self.key_prefix}:{request.url.path}:{identifier}"
                    current_counts.append(await redis.hit_rate_limit(key, self.window))
            else:
                script = """
                local count = redis.call('INCR', KEYS[1])
                if count == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
                return count
                """
                identifiers = [f"user:{current_user.clerk_user_id}"]
                if request.client:
                    identifiers.append(f"ip:{request.client.host}")
                for identifier in set(identifiers):
                    key = f"{self.key_prefix}:{request.url.path}:{identifier}"
                    current_counts.append(await redis.eval(script, 1, key, self.window))

            if any(count > self.limit for count in current_counts):
                response.headers["Retry-After"] = str(self.window)
                logger.warning(
                    "Rate limit exceeded actor_id=%s client=%s path=%s",
                    current_user.id,
                    request.client.host if request.client else "unknown",
                    request.url.path,
                )
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail={
                        "error": {
                            "code": "RATE_LIMIT_EXCEEDED",
                            "message": "Too many requests. Please try again later.",
                            "details": None,
                        }
                    },
                )
        except HTTPException:
            raise
        except Exception as exc:
            logger.error("Rate limiting unavailable for %s: %s", request.url.path, exc)
            if settings.is_production:
                raise HTTPException(
                    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                    detail={
                        "error": {
                            "code": "RATE_LIMITER_UNAVAILABLE",
                            "message": "Service temporarily unavailable.",
                            "details": None,
                        }
                    },
                ) from exc
            return True

        return True
