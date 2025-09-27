"""Channel service using repository pattern."""
from typing import List
from uuid import UUID

from clickhouse_connect.driver import Client
from loguru import logger

from tdms_analytics_api.entities.channel import Channel
from tdms_analytics_api.entities.time_range import TimeRange
from tdms_analytics_api.repos.channel import ChannelRepository
from tdms_analytics_api.repos.dataset import DatasetRepository
from tdms_analytics_api.exceptions.channel import ChannelNotFoundError
from tdms_analytics_api.exceptions.dataset import DatasetNotFoundError
from tdms_analytics_api.utils.time_utils import timestamp_to_iso


class ChannelService:
    """Service for channel operations using repository pattern."""
    
    def __init__(self, db_client: Client):
        self.channel_repo = ChannelRepository(db_client)
        self.dataset_repo = DatasetRepository(db_client)
    
    async def list_channels(self, dataset_id: UUID) -> List[Channel]:
        """List all channels for a dataset."""
        try:
            # Check if dataset exists
            dataset = await self.dataset_repo.find_by_id(dataset_id)
            if not dataset:
                raise DatasetNotFoundError(str(dataset_id))
            
            # Get channels
            channels_data = await self.channel_repo.find_by_dataset(dataset_id)
            return [Channel(**data) for data in channels_data]
            
        except DatasetNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to list channels for dataset {dataset_id}: {e}")
            raise
    
    async def get_channel_time_range(self, channel_id: UUID) -> TimeRange:
        """Get time range information for a channel."""
        try:
            # Get time range data
            time_range_data = await self.channel_repo.get_time_range(channel_id)
            if not time_range_data:
                raise ChannelNotFoundError(str(channel_id))
            
            # Convert timestamps to ISO format if present
            if time_range_data.get("min_timestamp"):
                time_range_data["min_iso"] = timestamp_to_iso(time_range_data["min_timestamp"])
            if time_range_data.get("max_timestamp"):
                time_range_data["max_iso"] = timestamp_to_iso(time_range_data["max_timestamp"])
            
            return TimeRange(**time_range_data)
            
        except ChannelNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get time range for channel {channel_id}: {e}")
            raise