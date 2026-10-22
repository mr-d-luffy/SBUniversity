import asyncio
import json
import time
from typing import Any, Dict, List, Optional, Tuple
import redis.asyncio as aioredis
from app.core.config import settings
from app.core.logging import logger

redis_client: Optional[aioredis.Redis] = None
REDIS_CHANNEL_LB_UPDATES = "lb:updates"


class InMemoryRedisFallback:
    """In-memory fallback for local dev or testing when Redis is not running."""
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._expiry: Dict[str, float] = {}
        self._zsets: Dict[str, Dict[str, float]] = {}
        self._subscribers: Dict[str, List[asyncio.Queue]] = {}

    async def hit_rate_limit(self, key: str, window_seconds: int) -> int:
        now = time.monotonic()
        if self._expiry.get(key, 0) <= now:
            self._store.pop(key, None)
            self._store[key] = 1
            self._expiry[key] = now + window_seconds
        else:
            self._store[key] = int(self._store.get(key, 0)) + 1
        return int(self._store[key])

    async def get(self, key: str) -> Optional[str]:
        return self._store.get(key)

    async def set(self, key: str, value: str, ex: Optional[int] = None) -> bool:
        self._store[key] = value
        return True

    async def delete(self, *keys: str) -> int:
        count = 0
        for k in keys:
            if k in self._store:
                del self._store[k]
                count += 1
            if k in self._zsets:
                del self._zsets[k]
                count += 1
        return count

    async def zadd(self, key: str, mapping: Dict[str, float]) -> int:
        if key not in self._zsets:
            self._zsets[key] = {}
        added = 0
        for member, score in mapping.items():
            if member not in self._zsets[key]:
                added += 1
            self._zsets[key][member] = float(score)
        return added

    async def zrem(self, key: str, *members: str) -> int:
        if key not in self._zsets:
            return 0
        removed = 0
        for m in members:
            if m in self._zsets[key]:
                del self._zsets[key][m]
                removed += 1
        return removed

    async def zrevrange(self, key: str, start: int, stop: int, withscores: bool = False):
        if key not in self._zsets:
            return []
        sorted_items = sorted(self._zsets[key].items(), key=lambda x: x[1], reverse=True)
        slice_items = sorted_items[start : stop + 1 if stop != -1 else None]
        if withscores:
            return slice_items
        return [item[0] for item in slice_items]

    async def zrevrank(self, key: str, member: str) -> Optional[int]:
        if key not in self._zsets or member not in self._zsets[key]:
            return None
        sorted_items = sorted(self._zsets[key].items(), key=lambda x: x[1], reverse=True)
        for rank, (m, _) in enumerate(sorted_items):
            if m == member:
                return rank
        return None

    async def zscore(self, key: str, member: str) -> Optional[float]:
        return self._zsets.get(key, {}).get(member)

    async def publish(self, channel: str, message: str) -> int:
        queues = self._subscribers.get(channel, [])
        for q in queues:
            await q.put(message)
        return len(queues)

    def pubsub(self):
        class PubSub:
            def __init__(self, fallback: "InMemoryRedisFallback"):
                self.fallback = fallback
                self.channels: List[str] = []
                self.queue = asyncio.Queue()

            async def subscribe(self, *channels: str):
                for ch in channels:
                    self.channels.append(ch)
                    if ch not in self.fallback._subscribers:
                        self.fallback._subscribers[ch] = []
                    self.fallback._subscribers[ch].append(self.queue)

            async def unsubscribe(self, *channels: str):
                for ch in channels:
                    if ch in self.fallback._subscribers and self.queue in self.fallback._subscribers[ch]:
                        self.fallback._subscribers[ch].remove(self.queue)

            async def listen(self):
                while True:
                    data = await self.queue.get()
                    yield {"type": "message", "data": data}

            async def close(self):
                await self.unsubscribe(*self.channels)

        return PubSub(self)

    async def ping(self) -> bool:
        return True

    async def close(self):
        pass


_in_memory_fallback = InMemoryRedisFallback()


async def get_redis_client():
    global redis_client
    if redis_client is not None:
        return redis_client

    try:
        client = aioredis.from_url(
            settings.REDIS_URL,
            encoding="utf-8",
            decode_responses=True,
            socket_connect_timeout=2.0,
            socket_timeout=2.0,
        )
        await client.ping()
        logger.info("Connected to Redis at %s", settings.REDIS_URL)
        redis_client = client
        return redis_client
    except Exception as e:
        logger.warning("Redis connection failed (%s); using in-memory fallback for local operation.", e)
        redis_client = _in_memory_fallback
        return redis_client


async def close_redis_client():
    global redis_client
    if redis_client is not None:
        try:
            await redis_client.close()
        except Exception:
            pass
        redis_client = None
