"""Dataset service using repository pattern."""
from typing import Any, Dict, List
from uuid import UUID

from clickhouse_connect.driver import Client
from loguru import logger

from tdms_analytics_api.entities.dataset import Dataset
from tdms_analytics_api.repos.dataset import DatasetRepository
from tdms_analytics_api.repos.channel import ChannelRepository
from tdms_analytics_api.exceptions.dataset import DatasetNotFoundError


class DatasetService:
    """Service for dataset operations using repository pattern."""
    
    def __init__(self, db_client: Client):
        self.dataset_repo = DatasetRepository(db_client)
        self.channel_repo = ChannelRepository(db_client)
    
    async def list_datasets(self) -> List[Dataset]:
        """List all datasets."""
        try:
            dataset_data = await self.dataset_repo.find_all()
            return [Dataset(**data) for data in dataset_data]
        except Exception as e:
            logger.error(f"Failed to list datasets: {e}")
            raise
    
    async def get_dataset_meta(self, dataset_id: UUID) -> Dict[str, Any]:
        """Get dataset metadata with channels."""
        try:
            # Get dataset info
            dataset_data = await self.dataset_repo.find_by_id(dataset_id)
            if not dataset_data:
                raise DatasetNotFoundError(str(dataset_id))
            
            # Get channels for this dataset
            channels_data = await self.channel_repo.find_by_dataset(dataset_id)
            
            # Group channels by group_name
            groups = {}
            for channel in channels_data:
                group_name = channel["group_name"]
                if group_name not in groups:
                    groups[group_name] = {
                        "group_name": group_name,
                        "channels": []
                    }
                groups[group_name]["channels"].append(channel)
            
            return {
                "dataset": dataset_data,
                "channels": channels_data,
                "groups": list(groups.values()),
                "total_channels": len(channels_data)
            }
            
        except DatasetNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to get dataset meta for {dataset_id}: {e}")
            raise
    
    async def delete_dataset(self, dataset_id: UUID) -> Dict[str, Any]:
        """Delete a dataset and all associated data."""
        try:
            # Check if dataset exists
            dataset_data = await self.dataset_repo.find_by_id(dataset_id)
            if not dataset_data:
                raise DatasetNotFoundError(str(dataset_id))
            
            filename = dataset_data["filename"]
            
            # Get channels to delete their data
            channels_data = await self.channel_repo.find_by_dataset(dataset_id)
            
            channels_deleted = 0
            data_points_deleted = 0
            
            # Delete sensor data for each channel
            for channel in channels_data:
                channel_id = UUID(channel["channel_id"])
                points_deleted = await self.channel_repo.delete_channel_data(channel_id)
                data_points_deleted += points_deleted
                channels_deleted += 1
            
            # Delete channels
            for channel in channels_data:
                channel_id = UUID(channel["channel_id"])
                await self.channel_repo.delete(channel_id)
            
            # Delete dataset
            await self.dataset_repo.delete(dataset_id)
            
            logger.info(f"Deleted dataset {dataset_id} ({filename}): {channels_deleted} channels, {data_points_deleted} data points")
            
            return {
                "status": "success",
                "dataset_id": str(dataset_id),
                "filename": filename,
                "channels_deleted": channels_deleted,
                "data_points_deleted": data_points_deleted
            }
            
        except DatasetNotFoundError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete dataset {dataset_id}: {e}")
            raise
