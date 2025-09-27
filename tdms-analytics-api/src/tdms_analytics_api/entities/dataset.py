"""Dataset entity."""
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, Field


class Dataset(BaseModel):
    """Dataset entity."""
    
    dataset_id: UUID = Field(..., description="Unique dataset identifier")
    filename: str = Field(..., description="Original filename")
    created_at: datetime = Field(..., description="Creation timestamp")
    total_points: int = Field(..., description="Total number of data points")
    
    class Config:
        from_attributes = True