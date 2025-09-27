"""Data windowing endpoints with downsampling."""
from typing import Any, Dict, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from clickhouse_connect.driver import Client
from loguru import logger

from tdms_analytics_api.config import get_settings
from tdms_analytics_api.dependencies.database import get_db
from tdms_analytics_api.enums.downsampling import DownsamplingMethod
from tdms_analytics_api.services.window import WindowService

router = APIRouter()


@router.get("/window")
async def get_window(
    channel_id: UUID = Query(..., description="UUID du canal"),
    start: Optional[str] = Query(None, description="ISO date si has_time"),
    end: Optional[str] = Query(None, description="ISO date si has_time"),
    start_sec: Optional[float] = Query(None, description="fenêtre relative en secondes"),
    end_sec: Optional[float] = Query(None, description="fenêtre relative en secondes"),
    relative: bool = Query(False, description="temps en secondes depuis le début"),
    points: int = Query(2000, ge=10, le=20000),
    method: DownsamplingMethod = Query(DownsamplingMethod.LTTB, description="lttb|uniform|clickhouse - LTTB par défaut"),
    db: Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get windowed sensor data with downsampling.
    
    Endpoint principal pour récupérer des données de capteurs avec fenêtrage
    et downsampling optimisé.
    """
    try:
        window_service = WindowService(db)
        
        result = await window_service.get_window(
            channel_id=channel_id,
            start=start,
            end=end,
            start_sec=start_sec,
            end_sec=end_sec,
            relative=relative,
            points=points,
            method=method.value
        )
        
        logger.info(f"Retrieved window for channel {channel_id}: {len(result.get('data', []))} points")
        return result
        
    except ValueError as e:
        logger.warning(f"Invalid window request for channel {channel_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get window for channel {channel_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve window data")


@router.get("/get_window_filtered")
async def get_window_filtered(
    channel_id: UUID = Query(..., description="UUID du canal"),
    start_timestamp: Optional[float] = Query(None, description="Timestamp Unix de début"),
    end_timestamp: Optional[float] = Query(None, description="Timestamp Unix de fin"),
    cursor: Optional[float] = Query(None, description="Curseur temporel pour pagination"),
    limit: int = Query(50000, ge=10000, le=200000),
    points: int = Query(2000, ge=10, le=20000),
    method: DownsamplingMethod = Query(DownsamplingMethod.LTTB, description="lttb|uniform|clickhouse - LTTB par défaut"),
    db: Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get filtered and paginated sensor data window.
    
    Endpoint avancé pour la pagination et le filtrage des données avec
    support de curseur pour naviguer dans de gros volumes.
    """
    try:
        window_service = WindowService(db)
        
        result = await window_service.get_window_filtered(
            channel_id=channel_id,
            start_timestamp=start_timestamp,
            end_timestamp=end_timestamp,
            cursor=cursor,
            limit=limit,
            points=points,
            method=method.value
        )
        
        logger.info(f"Retrieved filtered window for channel {channel_id}: {len(result.get('data', []))} points")
        return result
        
    except ValueError as e:
        logger.warning(f"Invalid filtered window request for channel {channel_id}: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get filtered window for channel {channel_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve filtered window data")