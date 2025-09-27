"""Ingestion service for TDMS files."""
import tempfile
import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List

import aiofiles
from clickhouse_connect.driver import Client
from fastapi import UploadFile
from loguru import logger

from tdms_analytics_api.config import get_settings
from tdms_analytics_api.services.tdms_parser import TDMSParser


class IngestionService:
    """Service for ingesting TDMS files."""
    
    def __init__(self, db_client: Client):
        self.db = db_client
        self.settings = get_settings()
        self.parser = TDMSParser()
    
    async def ingest_tdms_file(self, file: UploadFile) -> Dict[str, Any]:
        """Ingest a TDMS file into ClickHouse."""
        tmp_path = None
        try:
            logger.info(f"Starting ingestion of {file.filename}")
            
            # Test ClickHouse connection first
            try:
                test_result = self.db.query("SELECT 1")
                logger.info(f"ClickHouse connection test: {test_result.result_set}")
            except Exception as e:
                logger.error(f"ClickHouse connection failed: {e}")
                raise Exception(f"Database connection failed: {e}")
            
            # Check table structure
            try:
                tables = self.db.query("SHOW TABLES").result_set
                logger.info(f"Available tables: {[row[0] for row in tables]}")
                
                # Check datasets table structure
                desc_result = self.db.query("DESCRIBE TABLE datasets")
                logger.info(f"Datasets table structure: {desc_result.result_set}")
                
            except Exception as e:
                logger.error(f"Table structure check failed: {e}")
                raise Exception(f"Table structure error: {e}")
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.tdms', delete=False) as tmp_file:
                tmp_path = Path(tmp_file.name)
            
            logger.info(f"Created temp file: {tmp_path}")
            
            # Write uploaded file
            await self._write_upload_to_file(file, tmp_path)
            logger.info("File written to temp location")
            
            # Parse TDMS file
            logger.info(f"Parsing TDMS file: {file.filename}")
            parsed_data = self.parser.parse_file(tmp_path)
            logger.info("TDMS file parsed successfully")
            
            # Calculate total points
            total_points = 0
            for group_name, group_data in parsed_data.get("groups", {}).items():
                for ch_name, ch_data in group_data.get("channels", {}).items():
                    data_length = len(ch_data.get("data", []))
                    total_points += data_length
                    logger.info(f"Channel {group_name}/{ch_name}: {data_length} points")
            
            logger.info(f"Total points calculated: {total_points}")
            
            # Create dataset with manual SQL
            dataset_id = uuid.uuid4()
            dataset_id_str = str(dataset_id)
            filename = file.filename or "unknown.tdms"
            
            logger.info(f"Inserting dataset manually: {dataset_id_str}")
            
            try:
                # Use direct SQL INSERT instead of client.insert()
                insert_sql = """
                INSERT INTO datasets (dataset_id, filename, created_at, total_points) 
                VALUES (%(dataset_id)s, %(filename)s, %(created_at)s, %(total_points)s)
                """
                
                params = {
                    'dataset_id': dataset_id_str,
                    'filename': filename,
                    'created_at': '2024-01-01 12:00:00',
                    'total_points': total_points
                }
                
                logger.info(f"SQL: {insert_sql}")
                logger.info(f"Params: {params}")
                
                self.db.command(insert_sql, params)
                logger.info("Dataset inserted with SQL command")
                
                # Verify insertion
                verify_result = self.db.query(
                    "SELECT COUNT(*) FROM datasets WHERE dataset_id = %(id)s", 
                    {"id": dataset_id_str}
                )
                count = verify_result.result_set[0][0] if verify_result.result_set else 0
                logger.info(f"Dataset verification count: {count}")
                
                if count == 0:
                    raise Exception("Dataset not found after insertion")
                
            except Exception as e:
                logger.error(f"Dataset insertion failed completely: {e}")
                raise Exception(f"Cannot insert dataset: {str(e)}")

            # Insert channels and data
            logger.info("Starting channel insertion...")
            channels_info = []
            
            for group_name, group_data in parsed_data.get("groups", {}).items():
                logger.info(f"Processing group: {group_name}")
                
                for channel_name, ch_data in group_data.get("channels", {}).items():
                    logger.info(f"Processing channel: {group_name}/{channel_name}")
                    
                    channel_id = uuid.uuid4()
                    channel_id_str = str(channel_id)
                    data_values = ch_data.get("data", [])
                    n_rows = len(data_values)
                    has_time = bool(ch_data.get("has_time", False))
                    
                    # Insert channel with SQL
                    try:
                        channel_sql = """
                        INSERT INTO channels (channel_id, dataset_id, group_name, channel_name, unit, has_time, n_rows) 
                        VALUES (%(channel_id)s, %(dataset_id)s, %(group_name)s, %(channel_name)s, %(unit)s, %(has_time)s, %(n_rows)s)
                        """
                        
                        channel_params = {
                            'channel_id': channel_id_str,
                            'dataset_id': dataset_id_str,
                            'group_name': group_name,
                            'channel_name': channel_name,
                            'unit': ch_data.get("unit", ""),
                            'has_time': has_time,
                            'n_rows': n_rows
                        }
                        
                        self.db.command(channel_sql, channel_params)
                        logger.info(f"Channel {channel_name} inserted with SQL")
                        
                        # Insert sensor data in smaller chunks
                        if n_rows > 0:
                            await self._insert_channel_data_sql(
                                channel_id_str=channel_id_str,
                                data_values=data_values,
                                has_time=has_time
                            )
                            logger.info(f"Data for channel {channel_name} inserted")
                        
                        channels_info.append({
                            "channel_id": channel_id_str,
                            "dataset_id": dataset_id_str,
                            "group_name": group_name,
                            "channel_name": channel_name,
                            "unit": ch_data.get("unit", ""),
                            "has_time": has_time,
                            "n_rows": n_rows,
                        })
                        
                    except Exception as e:
                        logger.error(f"Channel insertion failed: {e}")
                        raise Exception(f"Channel {channel_name} insertion failed: {str(e)}")
            
            logger.info(f"Successfully processed {len(channels_info)} channels")
            
            result = {
                "dataset": {
                    "dataset_id": dataset_id_str,
                    "filename": filename,
                    "created_at": "2024-01-01 12:00:00",
                    "total_points": total_points
                },
                "channels": channels_info,
                "total_points": total_points,
                "status": "success"
            }
            
            logger.info("Ingestion completed successfully")
            return result
                
        except Exception as e:
            logger.error(f"Ingestion failed: {e}")
            raise Exception(f"Ingestion failed: {str(e)}")
            
        finally:
            # Clean up temporary file
            if tmp_path and tmp_path.exists():
                try:
                    tmp_path.unlink()
                    logger.info("Temp file cleaned up")
                except Exception as e:
                    logger.warning(f"Failed to cleanup {tmp_path}: {e}")
    
    async def _write_upload_to_file(self, upload: UploadFile, path: Path) -> None:
        """Write uploaded file to disk."""
        try:
            async with aiofiles.open(path, 'wb') as f:
                while chunk := await upload.read(self.settings.UPLOAD_CHUNK_SIZE):
                    await f.write(chunk)
        except Exception as e:
            logger.error(f"Failed to write upload to file: {e}")
            raise
    
    async def _insert_channel_data_sql(
        self, 
        channel_id_str: str,
        data_values: List[float],
        has_time: bool
    ) -> None:
        """Insert time series data using SQL commands."""
        
        try:
            # Use much smaller batches for huge datasets
            batch_size = 10000  # Smaller batches for stability
            total_batches = (len(data_values) + batch_size - 1) // batch_size
            
            logger.info(f"Inserting {len(data_values)} values in {total_batches} batches of {batch_size}")
            
            for i in range(0, len(data_values), batch_size):
                batch_values = data_values[i:i + batch_size]
                
                # Build values string for SQL
                values_list = []
                for j, value in enumerate(batch_values):
                    index = i + j
                    if has_time:
                        values_list.append(f"('{channel_id_str}', {index}, {float(value)}, 0.0, '')")
                    else:
                        values_list.append(f"('{channel_id_str}', {index}, {float(value)})")
                
                values_str = ",".join(values_list)
                
                if has_time:
                    sql = f"INSERT INTO sensor_data_with_time (channel_id, index, value, timestamp, timestamp_iso) VALUES {values_str}"
                else:
                    sql = f"INSERT INTO sensor_data (channel_id, index, value) VALUES {values_str}"
                
                self.db.command(sql)
                
                batch_num = i // batch_size + 1
                logger.info(f"Inserted batch {batch_num}/{total_batches}")
                
        except Exception as e:
            logger.error(f"Failed to insert channel data: {e}")
            raise