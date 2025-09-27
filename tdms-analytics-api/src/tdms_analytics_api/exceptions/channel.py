"""Channel-related exceptions."""

from .base import TDMSAnalyticsException, DatabaseError


class ChannelNotFoundError(TDMSAnalyticsException):
    """Exception raised when a channel is not found."""
    
    def __init__(self, channel_id: str):
        self.channel_id = channel_id
        message = f"Channel with ID '{channel_id}' not found"
        super().__init__(message, "CHANNEL_NOT_FOUND")


class ChannelDataError(DatabaseError):
    """Exception raised for channel data-related errors."""
    
    def __init__(self, message: str, channel_id: str = None, original_error: Exception = None):
        self.channel_id = channel_id
        super().__init__(message, original_error)
        self.error_code = "CHANNEL_DATA_ERROR"


class ChannelValidationError(TDMSAnalyticsException):
    """Exception raised for channel validation errors."""
    
    def __init__(self, message: str, channel_id: str = None):
        self.channel_id = channel_id
        super().__init__(message, "CHANNEL_VALIDATION_ERROR")


class TimeRangeError(TDMSAnalyticsException):
    """Exception raised for time range-related errors."""
    
    def __init__(self, message: str, channel_id: str = None):
        self.channel_id = channel_id
        super().__init__(message, "TIME_RANGE_ERROR")