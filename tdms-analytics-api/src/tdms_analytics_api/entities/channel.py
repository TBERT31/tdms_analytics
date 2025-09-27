"""Channel entity."""
from uuid import UUID

from pydantic import BaseModel, Field


class Channel(BaseModel):
    """Channel entity."""
    
    channel_id: UUID = Field(..., description="Unique channel identifier")
    dataset_id: UUID = Field(..., description="Parent dataset identifier")
    group_name: str = Field(..., description="TDMS group name")
    channel_name: str = Field(..., description="TDMS channel name")
    unit: str = Field(default="", description="Measurement unit")
    has_time: bool = Field(..., description="Whether channel has time data")
    n_rows: int = Field(..., description="Number of data points")
    
    class Config:
        from_attributes = True