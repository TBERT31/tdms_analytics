"""Base exceptions for TDMS Analytics API."""


class TDMSAnalyticsException(Exception):
    """Base exception for TDMS Analytics API."""
    
    def __init__(self, message: str, error_code: str = None):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


class ValidationError(TDMSAnalyticsException):
    """Exception raised for validation errors."""
    
    def __init__(self, message: str, field: str = None):
        self.field = field
        super().__init__(message, "VALIDATION_ERROR")


class DatabaseError(TDMSAnalyticsException):
    """Exception raised for database-related errors."""
    
    def __init__(self, message: str, original_error: Exception = None):
        self.original_error = original_error
        super().__init__(message, "DATABASE_ERROR")


class FileProcessingError(TDMSAnalyticsException):
    """Exception raised for file processing errors."""
    
    def __init__(self, message: str, filename: str = None):
        self.filename = filename
        super().__init__(message, "FILE_PROCESSING_ERROR")


class DownsamplingError(TDMSAnalyticsException):
    """Exception raised for downsampling errors."""
    
    def __init__(self, message: str, method: str = None):
        self.method = method
        super().__init__(message, "DOWNSAMPLING_ERROR")