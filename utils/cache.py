"""
Redis caching module
Handles caching of stats, trends, and frequently accessed data
"""
import json
import redis
from typing import Any, Optional
from loguru import logger
import os
from dotenv import load_dotenv

load_dotenv()


class RedisCache:
    """Redis cache wrapper with automatic serialization"""

    def __init__(self):
        """Initialize Redis connection"""
        try:
            self.redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.client = redis.from_url(
                self.redis_url,
                decode_responses=True,
                socket_connect_timeout=5
            )
            # Test connection
            self.client.ping()
            logger.info(f"✅ Redis connected: {self.redis_url}")
            self.enabled = True
        except Exception as e:
            logger.warning(f"⚠️ Redis not available: {e}. Caching disabled.")
            self.client = None
            self.enabled = False

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache

        Args:
            key: Cache key

        Returns:
            Cached value or None
        """
        if not self.enabled:
            return None

        try:
            value = self.client.get(key)
            if value:
                return json.loads(value)
            return None
        except Exception as e:
            logger.error(f"❌ Cache GET error for key '{key}': {e}")
            return None

    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache

        Args:
            key: Cache key
            value: Value to cache (will be JSON serialized)
            ttl: Time to live in seconds (optional)
        """
        if not self.enabled:
            return

        try:
            serialized = json.dumps(value, default=str)
            if ttl:
                self.client.setex(key, ttl, serialized)
            else:
                self.client.set(key, serialized)
            logger.debug(f"📦 Cached: {key} (TTL: {ttl}s)")
        except Exception as e:
            logger.error(f"❌ Cache SET error for key '{key}': {e}")

    def delete(self, key: str):
        """Delete key from cache"""
        if not self.enabled:
            return

        try:
            self.client.delete(key)
            logger.debug(f"🗑️ Deleted from cache: {key}")
        except Exception as e:
            logger.error(f"❌ Cache DELETE error for key '{key}': {e}")

    def clear_pattern(self, pattern: str):
        """
        Delete all keys matching pattern

        Args:
            pattern: Pattern with wildcards (e.g., "jobs:*")
        """
        if not self.enabled:
            return

        try:
            keys = self.client.keys(pattern)
            if keys:
                self.client.delete(*keys)
                logger.info(f"🗑️ Cleared {len(keys)} keys matching '{pattern}'")
        except Exception as e:
            logger.error(f"❌ Cache CLEAR error for pattern '{pattern}': {e}")

    def flush_all(self):
        """Clear entire cache (use with caution!)"""
        if not self.enabled:
            return

        try:
            self.client.flushdb()
            logger.warning("🗑️ Flushed entire cache")
        except Exception as e:
            logger.error(f"❌ Cache FLUSH error: {e}")

    def get_stats(self) -> dict:
        """Get cache statistics"""
        if not self.enabled:
            return {"status": "disabled"}

        try:
            info = self.client.info()
            return {
                "status": "active",
                "used_memory": info.get("used_memory_human"),
                "connected_clients": info.get("connected_clients"),
                "total_keys": self.client.dbsize(),
                "hits": info.get("keyspace_hits", 0),
                "misses": info.get("keyspace_misses", 0),
            }
        except Exception as e:
            logger.error(f"❌ Error getting cache stats: {e}")
            return {"status": "error", "error": str(e)}


# Global cache instance
_cache_instance: Optional[RedisCache] = None


def get_cache() -> RedisCache:
    """Get or create global cache instance"""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = RedisCache()
    return _cache_instance


# Cache key helpers
class CacheKeys:
    """Standard cache key prefixes with versioning"""
    VERSION = "v2"  # Increment this when cache structure changes
    STATS = "stats"
    TRENDS = "trends"
    SKILLS = "skills"
    JOBS = "jobs"
    CATEGORIES = "categories"

    @staticmethod
    def stats_key(filter_type: str = "all") -> str:
        """Generate stats cache key (versioned)"""
        return f"{CacheKeys.VERSION}:{CacheKeys.STATS}:{filter_type}"

    @staticmethod
    def trends_key(time_window: int = 30) -> str:
        """Generate trends cache key (versioned)"""
        return f"{CacheKeys.VERSION}:{CacheKeys.TRENDS}:{time_window}d"

    @staticmethod
    def skills_key(limit: int = 50) -> str:
        """Generate skills cache key (versioned)"""
        return f"{CacheKeys.VERSION}:{CacheKeys.SKILLS}:top{limit}"

    @staticmethod
    def job_key(job_id: str) -> str:
        """Generate job cache key (versioned)"""
        return f"{CacheKeys.VERSION}:{CacheKeys.JOBS}:{job_id}"

    @staticmethod
    def invalidate_all_versioned(cache: 'RedisCache') -> int:
        """
        Invalidate all cache keys for current version

        Returns:
            Number of keys deleted
        """
        pattern = f"{CacheKeys.VERSION}:*"
        keys = cache.client.keys(pattern)
        if keys:
            return cache.client.delete(*keys)
        return 0


if __name__ == "__main__":
    # Test cache
    cache = get_cache()

    # Test set/get
    cache.set("test:key", {"foo": "bar"}, ttl=60)
    print("Cached:", cache.get("test:key"))

    # Test stats
    print("Stats:", cache.get_stats())
