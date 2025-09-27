"""Health check endpoints."""
from typing import Dict, Any

from fastapi import APIRouter, Depends
from clickhouse_connect.driver import Client

from tdms_analytics.dependencies.database import get_db

router = APIRouter()


@router.get("/health")
async def health_check(db: Client = Depends(get_db)) -> Dict[str, Any]:
    """
    Health check endpoint.
    
    Vérifie la santé de l'API et la connectivité à ClickHouse.
    """
    try:
        # Test ClickHouse connection
        result = db.query("SELECT 1 as health_check")
        clickhouse_status = "healthy" if result.result_set else "unhealthy"
        
        return {
            "status": "healthy",
            "service": "TDMS Analytics API",
            "version": "0.1.0",
            "clickhouse": clickhouse_status,
            "database": db.database
        }
    except Exception as e:
        return {
            "status": "unhealthy",
            "service": "TDMS Analytics API", 
            "version": "0.1.0",
            "clickhouse": "unhealthy",
            "error": str(e)
        }