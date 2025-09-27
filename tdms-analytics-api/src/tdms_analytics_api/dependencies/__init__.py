"""Dependencies for TDMS Analytics API."""

from .database import get_clickhouse_client, get_db

__all__ = ["get_clickhouse_client", "get_db"]