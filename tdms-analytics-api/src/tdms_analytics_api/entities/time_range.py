"""Time range entity."""
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TimeRange(BaseModel):
    """Time range information for a channel."""
    
    channel_id: UUID = Field(..., description="Channel identifier")
    has_time: bool = Field(..., description="Whether channel has time data")
    min_timestamp: Optional[float] = Field(None, description="Minimum timestamp (Unix)")
    max_timestamp: Optional[float] = Field(None, description="Maximum timestamp (Unix)")
    min_iso: Optional[str] = Field(None, description="Minimum timestamp (ISO)")
    max_iso: Optional[str] = Field(None, description="Maximum timestamp (ISO)")
    min_index: Optional[int] = Field(None, description="Minimum index")
    max_index: Optional[int] = Field(None, description="Maximum index")
    total_points: int = Field(default=0, description="Total number of points")
    
    class Config:
        from_attributes = True