"""TDMS file parser service."""
import datetime as dt
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np
from loguru import logger
from nptdms import TdmsFile


class TDMSParser:
    """Service for parsing TDMS files."""
    
    def parse_file(self, file_path: Path) -> Dict[str, Any]:
        """
        Parse a TDMS file and extract data.
        
        Args:
            file_path: Path to the TDMS file
            
        Returns:
            Parsed data structure with groups and channels
        """
        logger.info(f"Parsing TDMS file: {file_path}")
        
        try:
            with TdmsFile.read(file_path) as tdms_file:
                parsed_data = {
                    "file_info": self._extract_file_info(tdms_file),
                    "groups": {}
                }
                
                # Process each group
                for group in tdms_file.groups():
                    group_name = group.name
                    logger.debug(f"Processing group: {group_name}")
                    
                    group_data = {
                        "properties": dict(group.properties) if group.properties else {},
                        "channels": {}
                    }
                    
                    # Process each channel in the group
                    for channel in group.channels():
                        channel_name = channel.name
                        logger.debug(f"Processing channel: {group_name}/{channel_name}")
                        
                        channel_data = self._extract_channel_data(channel)
                        group_data["channels"][channel_name] = channel_data
                    
                    parsed_data["groups"][group_name] = group_data
                
                logger.info(f"Successfully parsed {len(parsed_data['groups'])} groups")
                return parsed_data
                
        except Exception as e:
            logger.error(f"Failed to parse TDMS file {file_path}: {e}")
            raise
    
    def _extract_file_info(self, tdms_file: TdmsFile) -> Dict[str, Any]:
        """Extract file-level information."""
        return {
            "properties": dict(tdms_file.properties) if tdms_file.properties else {},
            "group_count": len(list(tdms_file.groups())),
        }
    
    def _extract_channel_data(self, channel) -> Dict[str, Any]:
        """
        Extract data and metadata from a TDMS channel.
        
        Args:
            channel: TDMS channel object
            
        Returns:
            Channel data with values, timestamps, and metadata
        """
        try:
            # Get channel data
            data = channel[:]
            
            # Convert to appropriate numpy array
            if data is not None:
                if hasattr(data, 'dtype'):
                    # Already a numpy array
                    values = data.astype(np.float32)
                else:
                    # Convert to numpy array
                    values = np.array(data, dtype=np.float32)
            else:
                values = np.array([], dtype=np.float32)
            
            # Extract properties
            properties = dict(channel.properties) if channel.properties else {}
            
            # Determine if channel has time data
            has_time = self._has_time_data(channel, properties)
            
            # Extract timestamps if available
            timestamps = None
            if has_time:
                timestamps = self._extract_timestamps(channel, properties, len(values))
            
            # Extract unit
            unit = self._extract_unit(properties)
            
            return {
                "data": values.tolist(),  # Convert to list for JSON serialization
                "timestamps": timestamps.tolist() if timestamps is not None else None,
                "has_time": has_time,
                "unit": unit,
                "properties": properties,
                "length": len(values)
            }
            
        except Exception as e:
            logger.error(f"Failed to extract channel data: {e}")
            raise
    
    def _has_time_data(self, channel, properties: Dict[str, Any]) -> bool:
        """Determine if channel has time information."""
        # Check for waveform properties indicating time data
        time_indicators = [
            "wf_start_time",
            "wf_increment", 
            "waveform_data",
            "NI_WaveformTime"
        ]
        
        return any(key in properties for key in time_indicators)
    
    def _extract_timestamps(
        self, 
        channel, 
        properties: Dict[str, Any], 
        data_length: int
    ) -> Optional[np.ndarray]:
        """Extract or generate timestamps for the channel."""
        
        try:
            # Method 1: Direct time channel
            if hasattr(channel, 'time_track') and channel.time_track is not None:
                time_data = channel.time_track()
                if time_data is not None:
                    return self._convert_timestamps_to_unix(time_data)
            
            # Method 2: Waveform properties
            start_time = properties.get("wf_start_time")
            increment = properties.get("wf_increment")
            
            if start_time is not None and increment is not None:
                # Generate timestamps from start time and increment
                if isinstance(start_time, dt.datetime):
                    start_timestamp = start_time.timestamp()
                else:
                    # Handle TDMS timestamp format
                    start_timestamp = self._parse_tdms_timestamp(start_time)
                
                timestamps = np.arange(data_length, dtype=np.float64) * float(increment)
                timestamps += start_timestamp
                
                return timestamps
            
            # Method 3: Check for other time properties
            if "NI_WaveformTime" in properties:
                # Handle NI-specific time format
                return self._extract_ni_timestamps(properties, data_length)
            
            return None
            
        except Exception as e:
            logger.warning(f"Failed to extract timestamps: {e}")
            return None
    
    def _convert_timestamps_to_unix(self, timestamps) -> np.ndarray:
        """Convert various timestamp formats to Unix timestamps."""
        if hasattr(timestamps, '__iter__'):
            # Array of timestamps
            result = []
            for ts in timestamps:
                if isinstance(ts, dt.datetime):
                    result.append(ts.timestamp())
                elif isinstance(ts, (int, float)):
                    result.append(float(ts))
                else:
                    result.append(self._parse_tdms_timestamp(ts))
            return np.array(result, dtype=np.float64)
        else:
            # Single timestamp
            if isinstance(timestamps, dt.datetime):
                return np.array([timestamps.timestamp()], dtype=np.float64)
            elif isinstance(timestamps, (int, float)):
                return np.array([float(timestamps)], dtype=np.float64)
            else:
                return np.array([self._parse_tdms_timestamp(timestamps)], dtype=np.float64)
    
    def _parse_tdms_timestamp(self, timestamp) -> float:
        """Parse TDMS-specific timestamp formats."""
        try:
            if isinstance(timestamp, dt.datetime):
                return timestamp.timestamp()
            elif isinstance(timestamp, (int, float)):
                return float(timestamp)
            elif hasattr(timestamp, 'timestamp'):
                return timestamp.timestamp()
            else:
                # Try to parse as string
                if isinstance(timestamp, str):
                    dt_obj = dt.datetime.fromisoformat(timestamp.replace('Z', '+00:00'))
                    return dt_obj.timestamp()
                else:
                    logger.warning(f"Unknown timestamp format: {type(timestamp)}")
                    return 0.0
        except Exception as e:
            logger.warning(f"Failed to parse timestamp {timestamp}: {e}")
            return 0.0
    
    def _extract_ni_timestamps(self, properties: Dict[str, Any], data_length: int) -> Optional[np.ndarray]:
        """Extract NI-specific timestamp format."""
        # Implementation for NI-specific timestamp extraction
        # This would depend on the specific NI format used
        return None
    
    def _extract_unit(self, properties: Dict[str, Any]) -> str:
        """Extract measurement unit from channel properties."""
        # Try different possible unit property names
        unit_keys = [
            "NI_UnitDescription",
            "unit_string", 
            "unit",
            "Unit",
            "units"
        ]
        
        for key in unit_keys:
            if key in properties:
                unit = properties[key]
                if isinstance(unit, str) and unit.strip():
                    return unit.strip()
        
        return ""  # Default empty unit