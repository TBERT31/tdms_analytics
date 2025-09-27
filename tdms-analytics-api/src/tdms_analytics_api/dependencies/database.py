"""Database dependencies and connection management."""
from functools import lru_cache
from typing import Generator

import clickhouse_connect
from clickhouse_connect.driver import Client
from loguru import logger

from tdms_analytics_api.config import get_settings


@lru_cache
def get_clickhouse_client() -> Client:
    """Get ClickHouse client instance."""
    settings = get_settings()
    
    try:
        client = clickhouse_connect.get_client(
            host=settings.CLICKHOUSE_HOST,
            port=settings.CLICKHOUSE_PORT,
            username=settings.CLICKHOUSE_USERNAME,
            password=settings.CLICKHOUSE_PASSWORD,
            database=settings.CLICKHOUSE_DATABASE,
            secure=settings.CLICKHOUSE_SECURE,
        )
        
        # Test connection
        client.ping()
        logger.info("ClickHouse client initialized successfully")
        return client
        
    except Exception as e:
        logger.error(f"Failed to initialize ClickHouse client: {e}")
        raise


def get_db() -> Generator[Client, None, None]:
    """Dependency to get database client."""
    client = get_clickhouse_client()
    try:
        yield client
    finally:
        # ClickHouse client doesn't need explicit closing
        pass