"""
Configuration module for Redisify.

This module provides a singleton configuration manager for Redis connections
and other global settings used throughout the Redisify library.
"""

from typing import Optional
from redis.asyncio import Redis, ConnectionPool


class RedisifyConfig:
    """
    Singleton configuration manager for Redisify.
    
    This class manages the global Redis connection and other configuration
    settings. It ensures that only one Redis connection is maintained
    throughout the application lifecycle.
    """

    _instance = None
    _redis: Optional[Redis] = None
    _connection_pool: Optional[ConnectionPool] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # No need to reinitialize if already done
        pass

    @classmethod
    def connect_to_redis(cls, host: str = "localhost", port: int = 6379, db: int = 0, password: Optional[str] = None, decode_responses: bool = True, max_connections: int = 10, **kwargs) -> None:
        """
        Configure the global Redis connection.
        
        Args:
            host: Redis server hostname
            port: Redis server port
            db: Redis database number
            password: Redis password (if required)
            decode_responses: Whether to decode responses to strings
            max_connections: Maximum number of connections in the pool
            **kwargs: Additional Redis connection parameters
        """
        # Create connection pool
        cls._connection_pool = ConnectionPool(host=host, port=port, db=db, password=password, decode_responses=decode_responses, max_connections=max_connections, **kwargs)

        # Create Redis client
        cls._redis = Redis(connection_pool=cls._connection_pool)

    @classmethod
    def connect_to_redis_url(cls, url: str, **kwargs) -> None:
        """
        Configure the global Redis connection using a URL.
        
        Args:
            url: Redis connection URL (e.g., redis://localhost:6379/0)
            **kwargs: Additional Redis connection parameters
        """
        cls._connection_pool = ConnectionPool.from_url(url, **kwargs)
        cls._redis = Redis(connection_pool=cls._connection_pool)

    @classmethod
    def connect_to_redis_client(cls, redis_client: Redis) -> None:
        """
        Configure the global Redis connection using an existing Redis client.
        
        Args:
            redis_client: Existing Redis client instance
        """
        cls._redis = redis_client

    @classmethod
    def get_redis(cls) -> Redis:
        """
        Get the global Redis client.
        
        Returns:
            Redis client instance
            
        Raises:
            RuntimeError: If Redis connection has not been configured
        """
        if cls._redis is None:
            raise RuntimeError("Redis connection not configured. Call connect_to_redis() first.")
        return cls._redis

    @classmethod
    def is_configured(cls) -> bool:
        """
        Check if Redis connection has been configured.
        
        Returns:
            True if Redis is configured, False otherwise
        """
        return cls._redis is not None

    @classmethod
    def reset(cls) -> None:
        """
        Reset the configuration, clearing all Redis connections.
        
        This is useful for testing or when you need to reconfigure
        the Redis connection.
        """
        cls._redis = None
        cls._connection_pool = None


# Global instance
config = RedisifyConfig()


# Convenience functions
def connect_to_redis(*args, **kwargs):
    """Connect to Redis with the given parameters."""
    config.connect_to_redis(*args, **kwargs)


def connect_to_redis_url(url: str, **kwargs):
    """Connect to Redis using a URL."""
    config.connect_to_redis_url(url, **kwargs)


def connect_to_redis_client(redis_client):
    """Connect to Redis using an existing Redis client."""
    config.connect_to_redis_client(redis_client)


def get_redis():
    """Get the global Redis client."""
    return config.get_redis()


def is_configured():
    """Check if Redis is configured."""
    return config.is_configured()


def reset():
    """Reset the Redis configuration."""
    config.reset()
