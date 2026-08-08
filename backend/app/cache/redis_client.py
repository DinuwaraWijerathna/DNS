from __future__ import annotations

import json
from datetime import UTC, datetime, timedelta
from typing import Any

try:
    import redis
    from redis.exceptions import RedisError
except ModuleNotFoundError:  # Redis is optional; the app falls back to in-memory cache.
    redis = None

    class RedisError(Exception):
        pass


class RedisCacheClient:
    def __init__(self, redis_url: str, default_ttl_seconds: int = 60) -> None:
        self.default_ttl_seconds = default_ttl_seconds
        self._fallback_store: dict[str, tuple[datetime, Any]] = {}
        self._redis_client: redis.Redis | None = None
        if redis is not None:
            try:
                self._redis_client = redis.Redis.from_url(redis_url, decode_responses=True)
                self._redis_client.ping()
            except RedisError:
                self._redis_client = None

    @staticmethod
    def domain_cache_key(domain: str) -> str:
        return f"resolver:{domain.strip().lower()}"

    def get_json(self, key: str) -> dict[str, Any] | None:
        if self._redis_client is not None:
            try:
                value = self._redis_client.get(key)
                return json.loads(value) if value else None
            except (RedisError, json.JSONDecodeError):
                return self._get_fallback(key)
        return self._get_fallback(key)

    def set_json(self, key: str, value: dict[str, Any], ttl_seconds: int | None = None) -> None:
        ttl = ttl_seconds or self.default_ttl_seconds
        if self._redis_client is not None:
            try:
                self._redis_client.setex(key, ttl, json.dumps(value))
                return
            except RedisError:
                pass
        self._set_fallback(key, value, ttl)

    def delete(self, key: str) -> None:
        if self._redis_client is not None:
            try:
                self._redis_client.delete(key)
            except RedisError:
                pass
        self._fallback_store.pop(key, None)

    def invalidate_domain(self, domain: str) -> None:
        self.delete(self.domain_cache_key(domain))

    def _get_fallback(self, key: str) -> dict[str, Any] | None:
        cached = self._fallback_store.get(key)
        if not cached:
            return None
        expires_at, value = cached
        if datetime.now(UTC) >= expires_at:
            self._fallback_store.pop(key, None)
            return None
        return value

    def _set_fallback(self, key: str, value: dict[str, Any], ttl_seconds: int) -> None:
        expires_at = datetime.now(UTC) + timedelta(seconds=ttl_seconds)
        self._fallback_store[key] = (expires_at, value)
