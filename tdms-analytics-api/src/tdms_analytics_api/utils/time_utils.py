"""Time utilities for TDMS data processing."""
import datetime as dt
from typing import Union

from dateutil import parser as date_parser
from loguru import logger


def parse_iso_to_timestamp(iso_string: str) -> float:
    """
    Parse ISO datetime string to Unix timestamp.
    
    Args:
        iso_string: ISO format datetime string
        
    Returns:
        Unix timestamp as float
    """
    try:
        # Handle various ISO formats
        dt_obj = date_parser.isoparse(iso_string)
        return dt_obj.timestamp()
    except Exception as e:
        logger.error(f"Failed to parse ISO string '{iso_string}': {e}")
        raise ValueError(f"Invalid ISO datetime format: {iso_string}")


def parse_tdms_timestamp(timestamp: Union[dt.datetime, float, int, str]) -> float:
    """
    Parse various TDMS timestamp formats to Unix timestamp.
    
    Args:
        timestamp: Timestamp in various formats
        
    Returns:
        Unix timestamp as float
    """
    try:
        if isinstance(timestamp, dt.datetime):
            return timestamp.timestamp()
        elif isinstance(timestamp, (int, float)):
            return float(timestamp)
        elif hasattr(timestamp, 'timestamp'):
            return timestamp.timestamp()
        elif isinstance(timestamp, str):
            # Try to parse as ISO string
            dt_obj = date_parser.isoparse(timestamp.replace('Z', '+00:00'))
            return dt_obj.timestamp()
        else:
            logger.warning(f"Unknown timestamp format: {type(timestamp)}")
            return 0.0
    except Exception as e:
        logger.warning(f"Failed to parse timestamp {timestamp}: {e}")
        return 0.0


def timestamp_to_iso(timestamp: float) -> str:
    """
    Convert Unix timestamp to ISO format string.
    
    Args:
        timestamp: Unix timestamp
        
    Returns:
        ISO format datetime string
    """
    try:
        dt_obj = dt.datetime.fromtimestamp(timestamp, tz=dt.timezone.utc)
        return dt_obj.isoformat()
    except Exception as e:
        logger.error(f"Failed to convert timestamp {timestamp} to ISO: {e}")
        raise ValueError(f"Invalid timestamp: {timestamp}")


def seconds_to_duration_string(seconds: float) -> str:
    """
    Convert seconds to human-readable duration string.
    
    Args:
        seconds: Duration in seconds
        
    Returns:
        Human-readable duration string
    """
    if seconds < 60:
        return f"{seconds:.2f}s"
    elif seconds < 3600:
        minutes = seconds / 60
        return f"{minutes:.2f}m"
    elif seconds < 86400:
        hours = seconds / 3600
        return f"{hours:.2f}h"
    else:
        days = seconds / 86400
        return f"{days:.2f}d"


def get_time_range_info(start_time: float, end_time: float) -> dict:
    """
    Get information about a time range.
    
    Args:
        start_time: Start timestamp
        end_time: End timestamp
        
    Returns:
        Dictionary with time range information
    """
    duration = end_time - start_time
    
    return {
        "start_timestamp": start_time,
        "end_timestamp": end_time,
        "start_iso": timestamp_to_iso(start_time),
        "end_iso": timestamp_to_iso(end_time),
        "duration_seconds": duration,
        "duration_string": seconds_to_duration_string(duration)
    }