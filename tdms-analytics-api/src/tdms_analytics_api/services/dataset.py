"""Dataset service for managing datasets."""
from typing import Any, Dict, List
from uuid import UUID

from clickhouse_connect.driver import Client
from loguru import logger

from tdms_analytics.entities.dataset import Dataset
from tdms_analytics.entities.channel import Channel


class DatasetService:
    """Service for dataset operations."""
    
    def __init__(self, db_client: Client):
        self.db = db_client
    
    async def list_datasets(self) -> List[Dataset]:
        """
        List all datasets.
        
        Returns:
            List of all datasets
        """
        try:
            result = self.db.query("""
                SELECT 
                    dataset_id,
                    filename,
                    created_at,
                    total_points
                FROM datasets
                ORDER BY created_at DESC
            """)
            
            datasets = []
            for row in result.result_set:
                dataset = Dataset(
                    dataset_id=row[0],
                    filename=row[1],
                    created_at=row[2],
                    total_points=row[3]
                )
                datasets.append(dataset)
            
            logger.info(f"Retrieved {len(datasets)} datasets")
            return datasets
            
        except Exception as e:
            logger.error(f"Failed to list datasets: {e}")
            raise
    
    async def get_dataset_meta(self, dataset_id: UUID) -> Dict[str, Any]:
        """
        Get dataset metadata with channels.
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            Dataset metadata with channels information
        """
        try:
            # Get dataset info
            dataset_result = self.db.query("""
                SELECT 
                    dataset_id,
                    filename,
                    created_at,
                    total_points
                FROM datasets
                WHERE dataset_id = %(dataset_id)s
            """, {"dataset_id": str(dataset_id)})
            
            if not dataset_result.result_set:
                raise ValueError(f"Dataset {dataset_id} not found")
            
            dataset_row = dataset_result.result_set[0]
            dataset_info = {
                "dataset_id": dataset_row[0],
                "filename": dataset_row[1],
                "created_at": dataset_row[2].isoformat() if dataset_row[2] else None,
                "total_points": dataset_row[3]
            }
            
            # Get channels info
            channels_result = self.db.query("""
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
            for row in channels_result.result_set:
                channel = {
                    "channel_id": row[0],
                    "dataset_id": row[1],
                    "group_name": row[2],
                    "channel_name": row[3],
                    "unit": row[4],
                    "has_time": bool(row[5]),
                    "n_rows": row[6]
                }
                channels.append(channel)
            
            # Group channels by group_name for better organization
            groups = {}
            for channel in channels:
                group_name = channel["group_name"]
                if group_name not in groups:
                    groups[group_name] = {
                        "group_name": group_name,
                        "channels": []
                    }
                groups[group_name]["channels"].append(channel)
            
            return {
                "dataset": dataset_info,
                "channels": channels,
                "groups": list(groups.values()),
                "total_channels": len(channels)
            }
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to get dataset meta for {dataset_id}: {e}")
            raise
    
    async def delete_dataset(self, dataset_id: UUID) -> Dict[str, Any]:
        """
        Delete a dataset and all associated data.
        
        Args:
            dataset_id: Dataset identifier
            
        Returns:
            Deletion result
        """
        try:
            # Check if dataset exists
            dataset_result = self.db.query("""
                SELECT dataset_id, filename
                FROM datasets
                WHERE dataset_id = %(dataset_id)s
            """, {"dataset_id": str(dataset_id)})
            
            if not dataset_result.result_set:
                raise ValueError(f"Dataset {dataset_id} not found")
            
            filename = dataset_result.result_set[0][1]
            
            # Get channels to delete their data
            channels_result = self.db.query("""
                SELECT channel_id, has_time
                FROM channels
                WHERE dataset_id = %(dataset_id)s
            """, {"dataset_id": str(dataset_id)})
            
            channels_deleted = 0
            data_points_deleted = 0
            
            # Delete sensor data for each channel
            for row in channels_result.result_set:
                channel_id = row[0]
                has_time = bool(row[1])
                
                table_name = "sensor_data_with_time" if has_time else "sensor_data"
                
                # Count points before deletion
                count_result = self.db.query(f"""
                    SELECT COUNT(*) FROM {table_name}
                    WHERE channel_id = %(channel_id)s
                """, {"channel_id": channel_id})
                
                points_count = count_result.result_set[0][0] if count_result.result_set else 0
                data_points_deleted += points_count
                
                # Delete data
                self.db.command(f"""
                    DELETE FROM {table_name}
                    WHERE channel_id = %(channel_id)s
                """, {"channel_id": channel_id})
                
                channels_deleted += 1
            
            # Delete channels
            self.db.command("""
                DELETE FROM channels
                WHERE dataset_id = %(dataset_id)s
            """, {"dataset_id": str(dataset_id)})
            
            # Delete dataset
            self.db.command("""
                DELETE FROM datasets
                WHERE dataset_id = %(dataset_id)s
            """, {"dataset_id": str(dataset_id)})
            
            logger.info(f"Deleted dataset {dataset_id} ({filename}): {channels_deleted} channels, {data_points_deleted} data points")
            
            return {
                "status": "success",
                "dataset_id": str(dataset_id),
                "filename": filename,
                "channels_deleted": channels_deleted,
                "data_points_deleted": data_points_deleted
            }
            
        except ValueError:
            raise
        except Exception as e:
            logger.error(f"Failed to delete dataset {dataset_id}: {e}")
            raise