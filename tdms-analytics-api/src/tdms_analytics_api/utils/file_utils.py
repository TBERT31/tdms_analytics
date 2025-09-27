"""File utilities for TDMS Analytics API."""

import tempfile
from pathlib import Path
from typing import Optional

from fastapi import UploadFile
from loguru import logger


def get_file_extension(filename: str) -> str:
    """
    Get file extension from filename.
    
    Args:
        filename: Name of the file
        
    Returns:
        File extension (lowercase, with dot)
    """
    return Path(filename).suffix.lower()


def validate_file_size(file: UploadFile, max_size: int) -> bool:
    """
    Validate file size.
    
    Args:
        file: Uploaded file
        max_size: Maximum allowed size in bytes
        
    Returns:
        True if file size is valid
    """
    if hasattr(file, 'size') and file.size:
        return file.size <= max_size
    return True  # Cannot determine size, allow it


def is_tdms_file(filename: str) -> bool:
    """
    Check if file is a TDMS file based on extension.
    
    Args:
        filename: Name of the file
        
    Returns:
        True if file appears to be TDMS
    """
    return get_file_extension(filename) == '.tdms'


def create_temp_file(suffix: str = '.tdms') -> Path:
    """
    Create a temporary file and return its path.
    
    Args:
        suffix: File suffix/extension
        
    Returns:
        Path to temporary file
    """
    temp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
    temp_file.close()
    return Path(temp_file.name)


def cleanup_temp_file(file_path: Path) -> None:
    """
    Clean up temporary file.
    
    Args:
        file_path: Path to temporary file
    """
    try:
        if file_path.exists():
            file_path.unlink()
            logger.debug(f"Cleaned up temporary file: {file_path}")
    except Exception as e:
        logger.warning(f"Failed to cleanup temporary file {file_path}: {e}")


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format.
    
    Args:
        size_bytes: Size in bytes
        
    Returns:
        Human-readable file size
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB", "TB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"