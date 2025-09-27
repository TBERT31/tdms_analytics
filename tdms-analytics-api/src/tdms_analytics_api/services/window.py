"""Window service for data retrieval with downsampling using repository pattern."""
from datetime import datetime
from typing import Any, Dict, Optional
from uuid import UUID

import pandas as pd
from clickhouse_connect.driver import Client
from loguru import logger

from tdms_analytics_api.config import get_settings
from tdms_analytics_api.repos.channel import ChannelRepository
from tdms_analytics_api.utils.lttb import smart_downsample_production
from tdms_analytics_api.utils.time_utils import parse_iso_to_timestamp
from tdms_analytics_api.exceptions.channel import ChannelNotFoundError


class WindowService:
    """Service for windowed data retrieval using repository pattern."""
    
    def __init__(self, db_client: Client):
        self.db = db_client
        self.settings = get_settings()
        self.channel_repo = ChannelRepository(db_client)
    
    async def get_window(
        self,
        channel_id: UUID,
        start: Optional[str] = None,
        end: Optional[str] = None,
        start_sec: Optional[float] = None,
        end_sec: Optional[float] = None,
        relative: bool = False,
        points: int = 2000,
        method: str = "lttb"
    ) -> Dict[str, Any]:
        """Get windowed sensor data with downsampling."""
        try:
            # Get channel info using repository
            channel_data = await self.channel_repo.find_by_id(channel_id)
            if not channel_data:
                raise ChannelNotFoundError(str(channel_id))
            
            has_time = channel_data["has_time"]
            
            # Build query based on channel type and parameters
            if has_time:
                data = await self._get_time_based_window(
                    channel_id, start, end, start_sec, end_sec, relative
                )
            else:
                data = await self._get_index_based_window(
                    channel_id, start_sec, end_sec
                )
            
            # Convert to DataFrame for downsampling
            if len(data) == 0:
                return {
                    "channel_id": str(channel_id),
                    "has_time": has_time,
                    "data": [],
                    "total_points": 0,
                    "downsampled_points": 0,
                    "method": method
                }
            
            df = pd.DataFrame(data)
            
            # Apply downsampling if needed
            if len(df) > points:
                df = smart_downsample_production(df, points, method, prefer_speed=self.settings.ENABLE_LTTBC)
                logger.info(f"Downsampled from {len(data)} to {len(df)} points using {method}")
            
            # Convert back to list format
            result_data = df.to_dict('records')
            
            return {
                "channel_id": str(channel_id),
                "has_time": has_time,
                "data": result_data,
                "total_points": len(data),
                "downsampled_points": len(result_data),
                "method": method,
                "relative": relative
            }
            
        except ChannelNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get window for channel {channel_id}: {e}")
            raise
    
    async def get_window_filtered(
        self,
        channel_id: UUID,
        start_timestamp: Optional[float] = None,
        end_timestamp: Optional[float] = None,
        cursor: Optional[float] = None,
        limit: int = 50000,
        points: int = 2000,
        method: str = "lttb"
    ) -> Dict[str, Any]:
        """Get filtered and paginated sensor data window."""
        try:
            # Get channel info using repository
            channel_data = await self.channel_repo.find_by_id(channel_id)
            if not channel_data:
                raise ChannelNotFoundError(str(channel_id))
            
            has_time = channel_data["has_time"]
            
            if not has_time:
                raise ValueError("Filtered window only supports time-based channels")
            
            # Build filtered query with pagination
            data, next_cursor = await self._get_filtered_time_data(
                channel_id, start_timestamp, end_timestamp, cursor, limit
            )
            
            if len(data) == 0:
                return {
                    "channel_id": str(channel_id),
                    "data": [],
                    "total_points": 0,
                    "downsampled_points": 0,
                    "has_more": False,
                    "next_cursor": None,
                    "method": method
                }
            
            # Convert to DataFrame for downsampling
            df = pd.DataFrame(data)
            
            # Apply downsampling if needed
            original_count = len(df)
            if len(df) > points:
                df = smart_downsample_production(df, points, method, prefer_speed=self.settings.ENABLE_LTTBC)
                logger.info(f"Downsampled from {original_count} to {len(df)} points using {method}")
            
            # Convert back to list format
            result_data = df.to_dict('records')
            
            return {
                "channel_id": str(channel_id),
                "data": result_data,
                "total_points": original_count,
                "downsampled_points": len(result_data),
                "has_more": next_cursor is not None,
                "next_cursor": next_cursor,
                "method": method,
                "limit": limit
            }
            
        except ChannelNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get filtered window for channel {channel_id}: {e}")
            raise
    
    # Méthodes privées restent avec accès direct DB pour performance des requêtes de données
    async def _get_time_based_window(
        self,
        channel_id: UUID,
        start: Optional[str],
        end: Optional[str],
        start_sec: Optional[float],
        end_sec: Optional[float],
        relative: bool
    ) -> list:
        """Get data for time-based channels."""
        
        where_conditions = ["channel_id = %(channel_id)s"]
        params = {"channel_id": str(channel_id)}
        
        # Handle time filtering
        if start or start_sec is not None:
            if start:
                start_ts = parse_iso_to_timestamp(start)
                where_conditions.append("timestamp >= %(start_ts)s")
                params["start_ts"] = start_ts
            elif start_sec is not None:
                # Get base timestamp and add seconds
                base_result = self.db.query("""
                    SELECT MIN(timestamp) FROM sensor_data_with_time
                    WHERE channel_id = %(channel_id)s
                """, {"channel_id": str(channel_id)})
                
                if base_result.result_set and base_result.result_set[0][0]:
                    base_ts = base_result.result_set[0][0]
                    start_ts = base_ts + start_sec
                    where_conditions.append("timestamp >= %(start_ts)s")
                    params["start_ts"] = start_ts
        
        if end or end_sec is not None:
            if end:
                end_ts = parse_iso_to_timestamp(end)
                where_conditions.append("timestamp <= %(end_ts)s")
                params["end_ts"] = end_ts
            elif end_sec is not None:
                # Get base timestamp and add seconds
                base_result = self.db.query("""
                    SELECT MIN(timestamp) FROM sensor_data_with_time
                    WHERE channel_id = %(channel_id)s
                """, {"channel_id": str(channel_id)})
                
                if base_result.result_set and base_result.result_set[0][0]:
                    base_ts = base_result.result_set[0][0]
                    end_ts = base_ts + end_sec
                    where_conditions.append("timestamp <= %(end_ts)s")
                    params["end_ts"] = end_ts
        
        where_clause = " AND ".join(where_conditions)
        
        # Build time column based on relative flag
        if relative:
            time_column = """(timestamp - (
                SELECT MIN(timestamp) FROM sensor_data_with_time 
                WHERE channel_id = %(channel_id)s
            )) as time"""
        else:
            time_column = "timestamp as time"
        
        query = f"""
            SELECT {time_column}, value
            FROM sensor_data_with_time
            WHERE {where_clause}
            ORDER BY timestamp
        """
        
        result = self.db.query(query, params)
        
        return [
            {"time": row[0], "value": row[1]}
            for row in result.result_set
        ]
    
    async def _get_index_based_window(
        self,
        channel_id: UUID,
        start_sec: Optional[float],
        end_sec: Optional[float]
    ) -> list:
        """Get data for index-based channels."""
        
        where_conditions = ["channel_id = %(channel_id)s"]
        params = {"channel_id": str(channel_id)}
        
        # For index-based, treat start_sec/end_sec as index values
        if start_sec is not None:
            where_conditions.append("index >= %(start_idx)s")
            params["start_idx"] = int(start_sec)
        
        if end_sec is not None:
            where_conditions.append("index <= %(end_idx)s")
            params["end_idx"] = int(end_sec)
        
        where_clause = " AND ".join(where_conditions)
        
        query = f"""
            SELECT index as time, value
            FROM sensor_data
            WHERE {where_clause}
            ORDER BY index
        """
        
        result = self.db.query(query, params)
        
        return [
            {"time": row[0], "value": row[1]}
            for row in result.result_set
        ]
    
    async def _get_filtered_time_data(
        self,
        channel_id: UUID,
        start_timestamp: Optional[float],
        end_timestamp: Optional[float],
        cursor: Optional[float],
        limit: int
    ) -> tuple:
        """Get filtered time data with pagination."""
        
        where_conditions = ["channel_id = %(channel_id)s"]
        params = {"channel_id": str(channel_id)}
        
        if start_timestamp is not None:
            where_conditions.append("timestamp >= %(start_ts)s")
            params["start_ts"] = start_timestamp
        
        if end_timestamp is not None:
            where_conditions.append("timestamp <= %(end_ts)s")
            params["end_ts"] = end_timestamp
        
        if cursor is not None:
            where_conditions.append("timestamp > %(cursor)s")
            params["cursor"] = cursor
        
        where_clause = " AND ".join(where_conditions)
        
        # Fetch one extra to detect if there's more data
        query = f"""
            SELECT timestamp as time, value
            FROM sensor_data_with_time
            WHERE {where_clause}
            ORDER BY timestamp
            LIMIT {limit + 1}
        """
        
        result = self.db.query(query, params)
        
        data = [
            {"time": row[0], "value": row[1]}
            for row in result.result_set
        ]
        
        # Check if there's more data
        has_more = len(data) > limit
        if has_more:
            data = data[:-1]  # Remove the extra record
            next_cursor = data[-1]["time"] if data else None
        else:
            next_cursor = None
        
        return data, next_cursor