"""Downsampling method enums."""
from enum import Enum


class DownsamplingMethod(str, Enum):
    """Downsampling methods for time series data."""
    
    LTTB = "lttb"
    UNIFORM = "uniform"
    CLICKHOUSE = "clickhouse"