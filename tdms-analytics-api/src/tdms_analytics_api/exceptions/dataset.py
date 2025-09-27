"""Dataset-related exceptions."""

from .base import TDMSAnalyticsException, DatabaseError


class DatasetNotFoundError(TDMSAnalyticsException):
    """Exception raised when a dataset is not found."""
    
    def __init__(self, dataset_id: str):
        self.dataset_id = dataset_id
        message = f"Dataset with ID '{dataset_id}' not found"
        super().__init__(message, "DATASET_NOT_FOUND")


class DatasetCreationError(DatabaseError):
    """Exception raised when dataset creation fails."""
    
    def __init__(self, message: str, filename: str = None, original_error: Exception = None):
        self.filename = filename
        super().__init__(message, original_error)
        self.error_code = "DATASET_CREATION_ERROR"


class DatasetDeletionError(DatabaseError):
    """Exception raised when dataset deletion fails."""
    
    def __init__(self, message: str, dataset_id: str = None, original_error: Exception = None):
        self.dataset_id = dataset_id
        super().__init__(message, original_error)
        self.error_code = "DATASET_DELETION_ERROR"


class DatasetValidationError(TDMSAnalyticsException):
    """Exception raised for dataset validation errors."""
    
    def __init__(self, message: str, dataset_id: str = None):
        self.dataset_id = dataset_id
        super().__init__(message, "DATASET_VALIDATION_ERROR")