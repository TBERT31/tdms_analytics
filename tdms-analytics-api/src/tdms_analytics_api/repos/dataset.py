"""Dataset repository for data access."""
from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import UUID

from tdms_analytics.repos.base import BaseRepository


class DatasetRepository(BaseRepository):
    """Repository for dataset operations."""
    
    async def find_by_id(self, dataset_id: UUID) -> Optional[Dict[str, Any]]:
        """Find dataset by ID."""
        result = self._execute_query("""
            SELECT 
                dataset_id,
                filename,
                created_at,
                total_points
            FROM datasets
            WHERE dataset_id = %(dataset_id)s
        """, {"dataset_id": str(dataset_id)})
        
        if result.result_set:
            row = result.result_set[0]
            return {
                "dataset_id": row[0],
                "filename": row[1],
                "created_at": row[2],
                "total_points": row[3]
            }
        return None
    
    async def find_all(self) -> List[Dict[str, Any]]:
        """Find all datasets."""
        result = self._execute_query("""
            SELECT 
                dataset_id,
                filename,
                created_at,
                total_points
            FROM datasets
            ORDER BY created_at DESC
        """)
        
        return [
            {
                "dataset_id": row[0],
                "filename": row[1],
                "created_at": row[2],
                "total_points": row[3]
            }
            for row in result.result_set
        ]
    
    async def create(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new dataset."""
        dataset_data = {
            "dataset_id": str(entity_data["dataset_id"]),
            "filename": entity_data["filename"],
            "created_at": entity_data.get("created_at", datetime.utcnow()),
            "total_points": entity_data["total_points"]
        }
        
        self._insert_data("datasets", [dataset_data])
        return dataset_data
    
    async def update(self, dataset_id: UUID, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing dataset."""
        # Build update query dynamically based on provided fields
        set_clauses = []
        params = {"dataset_id": str(dataset_id)}
        
        updatable_fields = ["filename", "total_points"]
        for field in updatable_fields:
            if field in entity_data:
                set_clauses.append(f"{field} = %({field})s")
                params[field] = entity_data[field]
        
        if not set_clauses:
            # No fields to update
            return await self.find_by_id(dataset_id)
        
        update_query = f"""
            ALTER TABLE datasets
            UPDATE {', '.join(set_clauses)}
            WHERE dataset_id = %(dataset_id)s
        """
        
        self._execute_command(update_query, params)
        return await self.find_by_id(dataset_id)
    
    async def delete(self, dataset_id: UUID) -> bool:
        """Delete dataset."""
        try:
            self._execute_command("""
                DELETE FROM datasets
                WHERE dataset_id = %(dataset_id)s
            """, {"dataset_id": str(dataset_id)})
            return True
        except Exception:
            return False
    
    async def get_channel_count(self, dataset_id: UUID) -> int:
        """Get number of channels for a dataset."""
        result = self._execute_query("""
            SELECT COUNT(*) as channel_count
            FROM channels
            WHERE dataset_id = %(dataset_id)s
        """, {"dataset_id": str(dataset_id)})
        
        return result.result_set[0][0] if result.result_set else 0
    
    async def get_total_data_points(self, dataset_id: UUID) -> int:
        """Get total data points across all channels for a dataset."""
        result = self._execute_query("""
            SELECT SUM(n_rows) as total_points
            FROM channels
            WHERE dataset_id = %(dataset_id)s
        """, {"dataset_id": str(dataset_id)})
        
        return result.result_set[0][0] or 0 if result.result_set else 0
    
    async def find_by_filename(self, filename: str) -> List[Dict[str, Any]]:
        """Find datasets by filename (partial match)."""
        result = self._execute_query("""
            SELECT 
                dataset_id,
                filename,
                created_at,
                total_points
            FROM datasets
            WHERE filename LIKE %(pattern)s
            ORDER BY created_at DESC
        """, {"pattern": f"%{filename}%"})
        
        return [
            {
                "dataset_id": row[0],
                "filename": row[1],
                "created_at": row[2],
                "total_points": row[3]
            }
            for row in result.result_set
        ]