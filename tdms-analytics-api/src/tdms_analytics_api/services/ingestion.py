"""Ingestion service using repository pattern."""
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import aiofiles
from clickhouse_connect.driver import Client
from fastapi import UploadFile
from loguru import logger

from tdms_analytics.config import get_settings
from tdms_analytics.services.tdms_parser import TDMSParser
from tdms_analytics.repos.dataset import DatasetRepository
from tdms_analytics.repos.channel import ChannelRepository
from tdms_analytics.utils.time_utils import parse_tdms_timestamp


class IngestionService:
    """Service for ingesting TDMS files using repository pattern."""
    
    def __init__(self, db_client: Client):
        self.db = db_client
        self.settings = get_settings()
        self.parser = TDMSParser()
        self.dataset_repo = DatasetRepository(db_client)
        self.channel_repo = ChannelRepository(db_client)
    
    async def ingest_tdms_file(self, file: UploadFile) -> Dict[str, Any]:
        """Ingest a TDMS file into ClickHouse."""
        with tempfile.NamedTemporaryFile(suffix='.tdms', delete=False) as tmp_file:
            tmp_path = Path(tmp_file.name)
            
            try:
                # Write uploaded file to temporary location
                await self._write_upload_to_file(file, tmp_path)
                
                # Parse TDMS file
                logger.info(f"Parsing TDMS file: {file.filename}")
                parsed_data = self.parser.parse_file(tmp_path)
                
                # Create dataset using repository
                dataset_id = uuid.uuid4()
                total_points = sum(
                    len(ch_data["data"]) 
                    for group_data in parsed_data["groups"].values()
                    for ch_data in group_data["channels"].values()
                )
                
                dataset_info = await self.dataset_repo.create({
                    "dataset_id": dataset_id,
                    "filename": file.filename or "unknown.tdms",
                    "created_at": datetime.utcnow(),
                    "total_points": total_points
                })
                
                # Insert channels and data
                channels_info = await self._insert_channels_data(
                    dataset_id=dataset_id,
                    parsed_data=parsed_data
                )
                
                logger.info(f"Successfully ingested {len(channels_info)} channels")
                
                return {
                    "dataset": dataset_info,
                    "channels": channels_info,
                    "total_points": sum(ch["n_rows"] for ch in channels_info),
                    "status": "success"
                }
                
            finally:
                # Clean up temporary file
                if tmp_path.exists():
                    tmp_path.unlink()
    
    async def _write_upload_to_file(self, upload: UploadFile, path: Path) -> None:
        """Write uploaded file to disk."""
        async with aiofiles.open(path, 'wb') as f:
            while chunk := await upload.read(self.settings.UPLOAD_CHUNK_SIZE):
                await f.write(chunk)
    
    async def _insert_channels_data(
        self, 
        dataset_id: uuid.UUID, 
        parsed_data: Dict[str, Any]
    ) -> List[Dict[str, Any]]:
        """Insert channels and their data using repositories."""
        
        channels_info = []
        
        for group_name, group_data in parsed_data["groups"].items():
            for channel_name, ch_data in group_data["channels"].items():
                
                channel_id = uuid.uuid4()
                n_rows = len(ch_data["data"])
                
                # Create channel using repository
                channel_info = await self.channel_repo.create({
                    "channel_id": channel_id,
                    "dataset_id": dataset_id,
                    "group_name": group_name,
                    "channel_name": channel_name,
                    "unit": ch_data.get("unit", ""),
                    "has_time": ch_data.get("has_time", False),
                    "n_rows": n_rows,
                })
                
                # Insert sensor data (direct DB access for bulk insert performance)
                await self._insert_channel_data(
                    channel_id=channel_id,
                    channel_data=ch_data,
                    has_time=ch_data.get("has_time", False)
                )
                
                channels_info.append(channel_info)
                logger.info(f"Inserted channel {group_name}/{channel_name}: {n_rows} points")
        
        return channels_info
    
    async def _insert_channel_data(
        self, 
        channel_id: uuid.UUID, 
        channel_data: Dict[str, Any],
        has_time: bool
    ) -> None:
        """Insert time series data for a channel (keep direct DB access for performance)."""
        # Cette méthode garde l'accès direct à la DB pour les performances
        # car l'insertion de masse de données est critique
        
        data_rows = []
        values = channel_data["data"]
        timestamps = channel_data.get("timestamps")
        
        # Process data in batches
        batch_size = self.settings.BATCH_INSERT_SIZE
        
        for i in range(0, len(values), batch_size):
            batch_values = values[i:i + batch_size]
            batch_timestamps = timestamps[i:i + batch_size] if timestamps else None
            
            batch_rows = []
            for j, value in enumerate(batch_values):
                row = {
                    "channel_id": str(channel_id),
                    "index": i + j,
                    "value": float(value),
                }
                
                if has_time and batch_timestamps is not None:
                    timestamp = batch_timestamps[j]
                    if isinstance(timestamp, (int, float)):
                        row["timestamp"] = timestamp
                        row["timestamp_iso"] = datetime.fromtimestamp(timestamp).isoformat()
                    else:
                        parsed_ts = parse_tdms_timestamp(timestamp)
                        row["timestamp"] = parsed_ts
                        row["timestamp_iso"] = datetime.fromtimestamp(parsed_ts).isoformat()
                else:
                    row["timestamp"] = None
                    row["timestamp_iso"] = None
                
                batch_rows.append(row)
            
            # Insert batch (direct DB access for performance)
            table_name = "sensor_data_with_time" if has_time else "sensor_data"
            self.db.insert(table_name, batch_rows)
            
            if len(batch_rows) > 0:
                logger.debug(f"Inserted batch {i//batch_size + 1}: {len(batch_rows)} rows")