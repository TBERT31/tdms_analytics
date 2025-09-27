"""Downsampling service with multiple algorithms."""
from typing import Dict, Any, List
import pandas as pd
from loguru import logger

from tdms_analytics_api.utils.lttb import smart_downsample_production
from tdms_analytics_api.enums.downsampling import DownsamplingMethod
from tdms_analytics_api.exceptions.base import DownsamplingError


class DownsamplingService:
    """Service for data downsampling operations."""
    
    @staticmethod
    def downsample_data(
        data: List[Dict[str, Any]], 
        target_points: int, 
        method: str = "lttb",
        prefer_speed: bool = False
    ) -> List[Dict[str, Any]]:
        """
        Downsample data using specified method.
        
        Args:
            data: List of data points with 'time' and 'value' keys
            target_points: Target number of points
            method: Downsampling method ('lttb', 'uniform', 'clickhouse')
            prefer_speed: Whether to prefer speed over accuracy
            
        Returns:
            Downsampled data
            
        Raises:
            DownsamplingError: If downsampling fails
        """
        if not data:
            return data
            
        if len(data) <= target_points:
            return data
        
        # Validate method
        valid_methods = [m.value for m in DownsamplingMethod]
        if method not in valid_methods:
            raise DownsamplingError(f"Invalid downsampling method: {method}. Valid methods: {valid_methods}")
        
        try:
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            # Validate DataFrame structure
            if 'time' not in df.columns or 'value' not in df.columns:
                raise DownsamplingError("Data must contain 'time' and 'value' columns")
            
            # Apply downsampling
            downsampled_df = smart_downsample_production(
                df, target_points, method, prefer_speed
            )
            
            # Convert back to list of dicts
            result = downsampled_df.to_dict('records')
            
            logger.info(f"Downsampled {len(data)} points to {len(result)} using {method}")
            return result
            
        except Exception as e:
            logger.error(f"Downsampling failed with method {method}: {e}")
            
            # Fallback to uniform sampling
            try:
                return DownsamplingService._uniform_fallback(data, target_points)
            except Exception as fallback_error:
                raise DownsamplingError(f"Downsampling and fallback both failed: {e}, {fallback_error}")
    
    @staticmethod
    def _uniform_fallback(data: List[Dict[str, Any]], target_points: int) -> List[Dict[str, Any]]:
        """Fallback uniform sampling when other methods fail."""
        step = max(1, len(data) // target_points)
        return data[::step][:target_points]
    
    @staticmethod
    def estimate_downsampling_time(data_size: int, method: str = "lttb") -> float:
        """
        Estimate downsampling time in seconds.
        
        Args:
            data_size: Number of input data points
            method: Downsampling method
            
        Returns:
            Estimated time in seconds
        """
        # Rough estimates based on typical performance
        time_per_point = {
            "uniform": 0.000001,     # Very fast
            "lttb": 0.000005,        # Fast
            "clickhouse": 0.000002,  # Fast (but depends on DB)
        }
        
        base_time = time_per_point.get(method, 0.000005)
        return data_size * base_time
    
    @staticmethod
    def get_optimal_method(
        data_size: int, 
        target_points: int, 
        time_constraint: float = None,
        quality_priority: bool = True
    ) -> str:
        """
        Get optimal downsampling method based on constraints.
        
        Args:
            data_size: Size of input data
            target_points: Target number of points
            time_constraint: Maximum allowed time in seconds
            quality_priority: Whether to prioritize quality over speed
            
        Returns:
            Recommended method name
        """
        reduction_ratio = data_size / target_points if target_points > 0 else 1
        
        # For small reductions, use uniform
        if reduction_ratio < 2:
            return "uniform"
        
        # Check time constraints
        if time_constraint:
            for method in ["uniform", "clickhouse", "lttb"]:
                estimated_time = DownsamplingService.estimate_downsampling_time(data_size, method)
                if estimated_time <= time_constraint:
                    return method
            return "uniform"  # Fastest fallback
        
        # Quality-based selection
        if quality_priority:
            if reduction_ratio < 10:
                return "lttb"
            elif reduction_ratio < 100:
                return "lttb"
            else:
                return "lttb"  # LTTB is generally best for time series
        else:
            # Speed priority
            if reduction_ratio < 10:
                return "uniform"
            else:
                return "clickhouse"
    
    @staticmethod
    def validate_downsampling_params(
        data_size: int,
        target_points: int,
        method: str,
        min_points: int = 10,
        max_points: int = 20000
    ) -> Dict[str, Any]:
        """
        Validate downsampling parameters.
        
        Args:
            data_size: Size of input data
            target_points: Target number of points
            method: Downsampling method
            min_points: Minimum allowed points
            max_points: Maximum allowed points
            
        Returns:
            Validation result with warnings/errors
        """
        result = {
            "valid": True,
            "warnings": [],
            "errors": [],
            "adjusted_target": target_points
        }
        
        # Validate method
        valid_methods = [m.value for m in DownsamplingMethod]
        if method not in valid_methods:
            result["errors"].append(f"Invalid method '{method}'. Valid: {valid_methods}")
            result["valid"] = False
        
        # Validate target points range
        if target_points < min_points:
            result["warnings"].append(f"Target points {target_points} below minimum {min_points}")
            result["adjusted_target"] = min_points
        elif target_points > max_points:
            result["warnings"].append(f"Target points {target_points} above maximum {max_points}")
            result["adjusted_target"] = max_points
        
        # Check if downsampling is needed
        if data_size <= target_points:
            result["warnings"].append("Data size smaller than target, no downsampling needed")
        
        # Check reduction ratio
        if data_size > 0:
            reduction_ratio = data_size / target_points
            if reduction_ratio > 1000:
                result["warnings"].append(f"High reduction ratio ({reduction_ratio:.1f}x), quality may be affected")
        
        return result
    
    @staticmethod
    def get_method_info(method: str) -> Dict[str, Any]:
        """
        Get information about a downsampling method.
        
        Args:
            method: Method name
            
        Returns:
            Method information
        """
        method_info = {
            "lttb": {
                "name": "Largest Triangle Three Buckets",
                "description": "Preserves visual characteristics of time series data",
                "quality": "High",
                "speed": "Medium",
                "best_for": "Time series visualization with trend preservation",
                "complexity": "O(n)"
            },
            "uniform": {
                "name": "Uniform Sampling", 
                "description": "Takes every nth point uniformly",
                "quality": "Low-Medium",
                "speed": "Very High",
                "best_for": "Quick previews, low quality requirements",
                "complexity": "O(n)"
            },
            "clickhouse": {
                "name": "ClickHouse Aggregation",
                "description": "Uses database aggregation functions",
                "quality": "Medium",
                "speed": "High",
                "best_for": "Large datasets with database processing",
                "complexity": "O(n)"
            }
        }
        
        return method_info.get(method, {
            "name": "Unknown",
            "description": "Unknown method",
            "quality": "Unknown",
            "speed": "Unknown",
            "best_for": "Unknown",
            "complexity": "Unknown"
        })