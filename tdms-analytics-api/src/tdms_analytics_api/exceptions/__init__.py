"""Custom exceptions for TDMS Analytics API."""

from .base import TDMSAnalyticsException, ValidationError
from .dataset import DatasetNotFoundError, DatasetCreationError, DatasetDeletionError
from .channel import ChannelNotFoundError, ChannelDataError

__all__ = [
    "TDMSAnalyticsException",
    "ValidationError", 
    "DatasetNotFoundError",
    "DatasetCreationError",
    "DatasetDeletionError",
    "ChannelNotFoundError",
    "ChannelDataError"
]