"""Channel service for managing channels."""
from datetime import datetime
from typing import List
from uuid import UUID

from clickhouse_connect.driver import Client
from loguru import logger

from tdms_analytics.entities.channel import Channel
from tdms_analytics.entities.time_range import TimeRange


class ChannelService:
    """Service for channel operations."""
    
    def __init__(self, db_client: Client):
        self.db = db_client
    
    async def list_channels(self, dataset_id: UUID) -> List[Channel]:
        """
        List all channels for a dataset.
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            List of channels
        """
        try:
            # First check if dataset exists
            dataset_check = self.db.query("""
                SELECT COUNT(*) FROM datasets
                WHERE dataset_id = %(dataset_id)s
            """, {"dataset_id": str(dataset_id)})
            
            if not dataset_check.result_set or dataset_check.result_set[0][0] == 0:
                raise ValueError(f"Dataset {dataset_id} not found")
            
            # Get channels
            result = self.db.query("""
                SELECT 
                    channel_id,
                    dataset_id,
                    group_name,
                    channel_name,
                    unit,
                    has_time,
                    n_rows
                FROM channels
                WHERE dataset_id = %(dataset_id)s
                ORDER BY group_name, channel_name
            """, {"dataset_id": str(dataset_id)})
            
            channels = []
            for row in result.result_set:
                channel = Channel(
                    channel_id=row[0],
                    dataset_id=row[1],
                    group_name=row[2],
                    channel_name=row[3],
                    unit=row[4] or "",
                    has_time=bool(row[5]),
                    n_rows=row[6]
                )
                channels.append(channel)
            
            logger.info(f"Retrieved {len(channels)} channels for dataset {dataset_id}")
            return channels
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to list channels for dataset {dataset_id}: {e}")
            raise
    
    async def get_channel_time_range(self, channel_id: UUID) -> TimeRange:
        """
        Get time range information for a channel.
        
        Args:
            channel_id: Channel identifier
            
        Returns:
            Time range information
        """
        try:
            # Get channel info
            channel_result = self.db.query("""
                SELECT channel_id, has_time, n_rows
                FROM channels
                WHERE channel_id = %(channel_id)s
            """, {"channel_id": str(channel_id)})
            
            if not channel_result.result_set:
                raise ValueError(f"Channel {channel_id} not found")
            
            channel_row = channel_result.result_set[0]
            has_time = bool(channel_row[1])
            n_rows = channel_row[2]
            
            time_range = TimeRange(
                channel_id=channel_id,
                has_time=has_time,
                total_points=n_rows
            )
            
            if has_time:
                # Get time range from sensor_data_with_time
                time_result = self.db.query("""
                    SELECT 
                        MIN(timestamp) as min_timestamp,
                        MAX(timestamp) as max_timestamp,
                        MIN(index) as min_index,
                        MAX(index) as max_index,
                        COUNT(*) as total_points
                    FROM sensor_data_with_time
                    WHERE channel_id = %(channel_id)s
                """, {"channel_id": str(channel_id)})
                
                if time_result.result_set and time_result.result_set[0][0] is not None:
                    row = time_result.result_set[0]
                    min_ts = row[0]
                    max_ts = row[1]
                    
                    time_range.min_timestamp = float(min_ts) if min_ts is not None else None
                    time_range.max_timestamp = float(max_ts) if max_ts is not None else None
                    time_range.min_index = row[2]
                    time_range.max_index = row[3]
                    time_range.total_points = row[4]
                    
                    # Convert to ISO format
                    if min_ts is not None:
                        time_range.min_iso = datetime.fromtimestamp(min_ts).isoformat()
                    if max_ts is not None:
                        time_range.max_iso = datetime.fromtimestamp(max_ts).isoformat()
            else:
                # Get index range from sensor_data
                index_result = self.db.query("""
                    SELECT 
                        MIN(index) as min_index,
                        MAX(index) as max_index,
                        COUNT(*) as total_points
                    FROM sensor_data
                    WHERE channel_id = %(channel_id)s
                """, {"channel_id": str(channel_id)})
                
                if index_result.result_set:
                    row = index_result.result_set[0]
                    time_range.min_index = row[0]
                    time_range.max_index = row[1]
                    time_range.total_points = row[2]
            
            logger.info(f"Retrieved time range for channel {channel_id}")
            return time_range
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to get time range for channel {channel_id}: {e}")
            raise