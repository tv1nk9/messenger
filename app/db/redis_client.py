import redis.asyncio as aioredis

from app.core.configs import settings

def build_redis_client() -> aioredis.Redis:
    return aioredis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        max_connections=settings.redis_max_connections,
        socket_timeout=settings.redis_socket_timeout,
        socket_connect_timeout=settings.redis_connect_timeout,
        health_check_interval=settings.redis_health_check_interval,
        retry_on_timeout=True,
    )