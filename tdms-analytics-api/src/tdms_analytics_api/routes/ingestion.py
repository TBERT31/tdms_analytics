"""Ingestion endpoints for TDMS files."""
from typing import Any, Dict

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from clickhouse_connect.driver import Client
from loguru import logger

from tdms_analytics.config import get_settings
from tdms_analytics.dependencies.database import get_db
from tdms_analytics.services.ingestion import IngestionService

router = APIRouter()


@router.post("/ingest")
async def ingest_tdms_file(
    file: UploadFile = File(...),
    db: Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Ingest TDMS file into ClickHouse.
    
    Analyse et ingère un fichier TDMS dans la base de données ClickHouse.
    Support des gros fichiers avec traitement par chunks.
    """
    settings = get_settings()
    
    # Validation du fichier
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided")
    
    if not file.filename.lower().endswith('.tdms'):
        raise HTTPException(
            status_code=400, 
            detail="Only TDMS files are supported"
        )
    
    # Vérification de la taille (approximative)
    if hasattr(file, 'size') and file.size and file.size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail=f"File too large. Maximum size: {settings.MAX_FILE_SIZE} bytes"
        )
    
    logger.info(f"Starting ingestion of file: {file.filename}")
    
    try:
        ingestion_service = IngestionService(db)
        result = await ingestion_service.ingest_tdms_file(file)
        
        logger.info(f"Successfully ingested {file.filename}")
        return result
        
    except Exception as e:
        logger.error(f"Failed to ingest {file.filename}: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Ingestion failed: {str(e)}"
        )


@router.get("/api/constraints")
async def get_api_constraints() -> Dict[str, Any]:
    """
    Get API constraints for frontend.
    
    Retourne les limites et contraintes de l'API pour le frontend.
    """
    settings = get_settings()
    
    return {
        "file_upload": {
            "max_file_size": settings.MAX_FILE_SIZE,
            "supported_formats": [".tdms"],
            "chunk_size": settings.UPLOAD_CHUNK_SIZE
        },
        "data_processing": {
            "default_points": settings.DEFAULT_POINTS,
            "max_points": settings.MAX_POINTS,
            "min_points": settings.MIN_POINTS,
            "default_limit": settings.DEFAULT_LIMIT,
            "max_limit": settings.MAX_LIMIT,
            "min_limit": settings.MIN_LIMIT
        },
        "downsampling": {
            "methods": ["lttb", "uniform", "clickhouse"],
            "default_method": "lttb",
            "lttbc_available": settings.ENABLE_LTTBC
        }
    }