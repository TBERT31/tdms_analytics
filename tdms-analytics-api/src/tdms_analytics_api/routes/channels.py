"""Channel management endpoints."""
from typing import List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from clickhouse_connect.driver import Client
from loguru import logger

from tdms_analytics_api.dependencies.database import get_db
from tdms_analytics_api.entities.channel import Channel
from tdms_analytics_api.entities.time_range import TimeRange
from tdms_analytics_api.services.channel import ChannelService

router = APIRouter()


@router.get("/datasets/{dataset_id}/channels", response_model=List[Channel])
async def list_channels(
    dataset_id: UUID,
    db: Client = Depends(get_db)
) -> List[Channel]:
    """
    List all channels for a dataset.
    
    Retourne tous les canaux d'un dataset donné.
    """
    try:
        channel_service = ChannelService(db)
        return await channel_service.list_channels(dataset_id)
    except ValueError as e:
        logger.warning(f"Dataset not found: {dataset_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to list channels for dataset {dataset_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve channels")


@router.get("/channels/{channel_id}/time_range", response_model=TimeRange)
async def get_channel_time_range(
    channel_id: UUID,
    db: Client = Depends(get_db)
) -> TimeRange:
    """
    Get time range information for a channel.
    
    Retourne les informations de plage temporelle d'un canal.
    """
    try:
        channel_service = ChannelService(db)
        return await channel_service.get_channel_time_range(channel_id)
    except ValueError as e:
        logger.warning(f"Channel not found: {channel_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get time range for channel {channel_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve time range")