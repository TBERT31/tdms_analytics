"""Channel repository for data access."""
from typing import Any, Dict, List, Optional
from uuid import UUID

from tdms_analytics_api.repos.base import BaseRepository


class ChannelRepository(BaseRepository):
    """Repository for channel operations."""
    
    async def find_by_id(self, channel_id: UUID) -> Optional[Dict[str, Any]]:
        """Find channel by ID."""
        result = self._execute_query("""
            SELECT 
                channel_id,
                dataset_id,
                group_name,
                channel_name,
                unit,
                has_time,
                n_rows
            FROM channels
            WHERE channel_id = %(channel_id)s
        """, {"channel_id": str(channel_id)})
        
        if result.result_set:
            row = result.result_set[0]
            return {
                "channel_id": row[0],
                "dataset_id": row[1],
                "group_name": row[2],
                "channel_name": row[3],
                "unit": row[4],
                "has_time": bool(row[5]),
                "n_rows": row[6]
            }
        return None
    
    async def find_all(self) -> List[Dict[str, Any]]:
        """Find all channels."""
        result = self._execute_query("""
            SELECT 
                channel_id,
                dataset_id,
                group_name,
                channel_name,
                unit,
                has_time,
                n_rows
            FROM channels
            ORDER BY group_name, channel_name
        """)
        
        return [
            {
                "channel_id": row[0],
                "dataset_id": row[1],
                "group_name": row[2],
                "channel_name": row[3],
                "unit": row[4],
                "has_time": bool(row[5]),
                "n_rows": row[6]
            }
            for row in result.result_set
        ]
    
    async def create(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new channel."""
        channel_data = {
            "channel_id": str(entity_data["channel_id"]),
            "dataset_id": str(entity_data["dataset_id"]),
            "group_name": entity_data["group_name"],
            "channel_name": entity_data["channel_name"],
            "unit": entity_data.get("unit", ""),
            "has_time": entity_data["has_time"],
            "n_rows": entity_data["n_rows"]
        }
        
        self._insert_data("channels", [channel_data])
        return channel_data
    
    async def update(self, channel_id: UUID, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing channel."""
        set_clauses = []
        params = {"channel_id": str(channel_id)}
        
        updatable_fields = ["group_name", "channel_name", "unit", "n_rows"]
        for field in updatable_fields:
            if field in entity_data:
                set_clauses.append(f"{field} = %({field})s")
                params[field] = entity_data[field]
        
        if not set_clauses:
            return await self.find_by_id(channel_id)
        
        update_query = f"""
            ALTER TABLE channels
            UPDATE {', '.join(set_clauses)}
            WHERE channel_id = %(channel_id)s
        """
        
        self._execute_command(update_query, params)
        return await self.find_by_id(channel_id)
    
    async def delete(self, channel_id: UUID) -> bool:
        """Delete channel."""
        try:
            self._execute_command("""
                DELETE FROM channels
                WHERE channel_id = %(channel_id)s
            """, {"channel_id": str(channel_id)})
            return True
        except Exception:
            return False
    
    async def find_by_dataset(self, dataset_id: UUID) -> List[Dict[str, Any]]:
        """Find all channels for a dataset."""
        result = self._execute_query("""
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
        
        return [
            {
                "channel_id": row[0],
                "dataset_id": row[1],
                "group_name": row[2],
                "channel_name": row[3],
                "unit": row[4],
                "has_time": bool(row[5]),
                "n_rows": row[6]
            }
            for row in result.result_set
        ]
    
    async def find_by_group(self, dataset_id: UUID, group_name: str) -> List[Dict[str, Any]]:
        """Find all channels in a specific group."""
        result = self._execute_query("""
            SELECT 
                channel_id,
                dataset_id,
                group_name,
                channel_name,
                unit,
                has_time,
                n_rows
            FROM channels
            WHERE dataset_id = %(dataset_id)s AND group_name = %(group_name)s
            ORDER BY channel_name
        """, {"dataset_id": str(dataset_id), "group_name": group_name})
        
        return [
            {
                "channel_id": row[0],
                "dataset_id": row[1],
                "group_name": row[2],
                "channel_name": row[3],
                "unit": row[4],
                "has_time": bool(row[5]),
                "n_rows": row[6]
            }
            for row in result.result_set
        ]
    
    async def get_time_range(self, channel_id: UUID) -> Optional[Dict[str, Any]]:
        """Get time range for a channel."""
        channel = await self.find_by_id(channel_id)
        if not channel:
            return None
        
        has_time = channel["has_time"]
        
        if has_time:
            # Query time-based data
            result = self._execute_query("""
                SELECT 
                    MIN(timestamp) as min_timestamp,
                    MAX(timestamp) as max_timestamp,
                    MIN(index) as min_index,
                    MAX(index) as max_index,
                    COUNT(*) as total_points
                FROM sensor_data_with_time
                WHERE channel_id = %(channel_id)s
            """, {"channel_id": str(channel_id)})
        else:
            # Query index-based data
            result = self._execute_query("""
                SELECT 
                    NULL as min_timestamp,
                    NULL as max_timestamp,
                    MIN(index) as min_index,
                    MAX(index) as max_index,
                    COUNT(*) as total_points
                FROM sensor_data
                WHERE channel_id = %(channel_id)s
            """, {"channel_id": str(channel_id)})
        
        if result.result_set:
            row = result.result_set[0]
            return {
                "channel_id": str(channel_id),
                "has_time": has_time,
                "min_timestamp": row[0],
                "max_timestamp": row[1],
                "min_index": row[2],
                "max_index": row[3],
                "total_points": row[4] or 0
            }
        
        return {
            "channel_id": str(channel_id),
            "has_time": has_time,
            "min_timestamp": None,
            "max_timestamp": None,
            "min_index": None,
            "max_index": None,
            "total_points": 0
        }
    
    async def delete_channel_data(self, channel_id: UUID) -> int:
        """Delete all data for a channel and return number of deleted rows."""
        channel = await self.find_by_id(channel_id)
        if not channel:
            return 0
        
        has_time = channel["has_time"]
        table_name = "sensor_data_with_time" if has_time else "sensor_data"
        
        # Count rows before deletion
        count_result = self._execute_query(f"""
            SELECT COUNT(*) FROM {table_name}
            WHERE channel_id = %(channel_id)s
        """, {"channel_id": str(channel_id)})
        
        deleted_count = count_result.result_set[0][0] if count_result.result_set else 0
        
        # Delete data
        self._execute_command(f"""
            DELETE FROM {table_name}
            WHERE channel_id = %(channel_id)s
        """, {"channel_id": str(channel_id)})
        
        return deleted_count
    
    async def get_groups_for_dataset(self, dataset_id: UUID) -> List[str]:
        """Get all unique group names for a dataset."""
        result = self._execute_query("""
            SELECT DISTINCT group_name
            FROM channels
            WHERE dataset_id = %(dataset_id)s
            ORDER BY group_name
        """, {"dataset_id": str(dataset_id)})
        
        return [row[0] for row in result.result_set]