import json
from typing import Any
import redis.asyncio as redis
from redis.exceptions import RedisError
from .config import get_settings

settings = get_settings()
client = redis.from_url(settings.redis_url, decode_responses=True)


async def cache_get_json(key: str) -> Any | None:
    try:
        raw = await client.get(key)
        return json.loads(raw) if raw else None
    except RedisError:
        return None


async def cache_set_json(key: str, value: Any, ttl: int = 3600) -> None:
    try:
        await client.set(key, json.dumps(value, ensure_ascii=False, default=str), ex=ttl)
    except RedisError:
        pass


async def cache_delete(key: str) -> None:
    try:
        await client.delete(key)
    except RedisError:
        pass


async def close_cache() -> None:
    try:
        await client.aclose()
    except RedisError:
        pass
