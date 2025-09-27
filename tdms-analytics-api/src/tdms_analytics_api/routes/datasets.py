"""Dataset management endpoints."""
from typing import Any, Dict, List
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from clickhouse_connect.driver import Client
from loguru import logger

from tdms_analytics_api.dependencies.database import get_db
from tdms_analytics_api.entities.dataset import Dataset
from tdms_analytics_api.services.dataset import DatasetService

router = APIRouter()


@router.get("/datasets", response_model=List[Dataset])
async def list_datasets(db: Client = Depends(get_db)) -> List[Dataset]:
    """
    List all datasets.
    
    Retourne la liste de tous les datasets disponibles.
    """
    try:
        dataset_service = DatasetService(db)
        return await dataset_service.list_datasets()
    except Exception as e:
        logger.error(f"Failed to list datasets: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve datasets")


@router.get("/dataset_meta")
async def get_dataset_meta(
    dataset_id: UUID,
    db: Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Get dataset metadata including channels information.
    
    Retourne les métadonnées complètes d'un dataset avec ses canaux.
    """
    try:
        dataset_service = DatasetService(db)
        return await dataset_service.get_dataset_meta(dataset_id)
    except ValueError as e:
        logger.warning(f"Dataset not found: {dataset_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to get dataset meta for {dataset_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to retrieve dataset metadata")


@router.delete("/datasets/{dataset_id}")
async def delete_dataset(
    dataset_id: UUID,
    db: Client = Depends(get_db)
) -> Dict[str, Any]:
    """
    Delete a dataset and all associated data.
    
    Supprime complètement un dataset et toutes ses données associées.
    """
    try:
        dataset_service = DatasetService(db)
        result = await dataset_service.delete_dataset(dataset_id)
        
        logger.info(f"Successfully deleted dataset {dataset_id}")
        return result
        
    except ValueError as e:
        logger.warning(f"Dataset not found for deletion: {dataset_id}")
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"Failed to delete dataset {dataset_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to delete dataset")