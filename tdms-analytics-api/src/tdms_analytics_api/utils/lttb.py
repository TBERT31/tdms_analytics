"""
LTTB downsampling utilities for time series data.
"""
import numpy as np
import pandas as pd
from loguru import logger

try:
    import lttb
    HAS_LTTB = True
except ImportError:
    HAS_LTTB = False
    logger.warning("lttb package not available")

try:
    import lttbc
    HAS_LTTBC = True
except ImportError:
    HAS_LTTBC = False
    logger.warning("lttbc package not available - using fallback")


def downsample_with_lttb(df: pd.DataFrame, target_points: int) -> pd.DataFrame:
    """
    Utilise la librairie lttb officielle, testée et éprouvée.
    
    Args:
        df: DataFrame avec colonnes 'time' et 'value'
        target_points: nombre de points cibles
        
    Returns:
        DataFrame downsamplé
    """
    if not HAS_LTTB:
        raise ImportError("lttb package required: pip install lttb")
    
    if len(df) <= target_points:
        return df.copy()
    
    # Préparer les données au format attendu par lttb
    # Format: array 2D avec [temps, valeurs]
    if 'time' in df.columns and 'value' in df.columns:
        
        # Convertir les timestamps datetime en float si nécessaire
        time_values = df['time'].values
        if pd.api.types.is_datetime64_any_dtype(df['time']):
            # Convertir en timestamps Unix (secondes)
            time_values = pd.to_datetime(df['time']).astype('int64') / 1e9
        else:
            time_values = time_values.astype(float)
        
        # Créer le tableau 2D requis par lttb
        data_array = np.column_stack([
            time_values,
            df['value'].astype(float).values
        ])
        
        # Appliquer LTTB
        downsampled = lttb.downsample(data_array, n_out=target_points)
        
        # Reconstruire le DataFrame
        result_df = pd.DataFrame({
            'time': downsampled[:, 0],
            'value': downsampled[:, 1]
        })
        
        # Reconvertir les timestamps si nécessaire
        if pd.api.types.is_datetime64_any_dtype(df['time']):
            result_df['time'] = pd.to_datetime(result_df['time'], unit='s')
        else:
            result_df['time'] = result_df['time'].astype(df['time'].dtype)
            
        return result_df
    
    else:
        raise ValueError("DataFrame doit avoir les colonnes 'time' et 'value'")


def downsample_with_lttbc(df: pd.DataFrame, target_points: int) -> pd.DataFrame:
    """
    Version ultra-rapide avec lttbc (extension C).
    
    Args:
        df: DataFrame avec colonnes 'time' et 'value'
        target_points: nombre de points cibles
        
    Returns:
        DataFrame downsamplé
    """
    if not HAS_LTTBC:
        raise ImportError("lttbc package required: pip install lttbc")
    
    if len(df) <= target_points:
        return df.copy()
    
    # Même logique mais avec lttbc
    time_values = df['time'].values
    if pd.api.types.is_datetime64_any_dtype(df['time']):
        time_values = pd.to_datetime(df['time']).astype('int64') / 1e9
    else:
        time_values = time_values.astype(float)
    
    # lttbc prend des arrays séparés (plus rapide)
    downsampled_indices = lttbc.downsample(
        time_values, 
        df['value'].astype(float).values, 
        target_points
    )
    
    return df.iloc[downsampled_indices].copy()


def uniform_downsample(df: pd.DataFrame, target_points: int) -> pd.DataFrame:
    """
    Downsampling uniforme simple (fallback).
    
    Args:
        df: DataFrame avec colonnes 'time' et 'value'
        target_points: nombre de points cibles
        
    Returns:
        DataFrame downsamplé
    """
    if len(df) <= target_points:
        return df.copy()
    
    # Sélection uniforme des points
    step = len(df) / target_points
    indices = np.round(np.arange(0, len(df), step)).astype(int)
    indices = np.unique(np.clip(indices, 0, len(df) - 1))
    
    return df.iloc[indices].copy()


def smart_downsample_production(
    df: pd.DataFrame, 
    target_points: int, 
    method: str = "lttb",
    prefer_speed: bool = False
) -> pd.DataFrame:
    """
    Downsampling production avec librairies éprouvées.
    
    Args:
        df: DataFrame avec colonnes 'time' et 'value'
        target_points: nombre de points cibles
        method: "lttb", "uniform", ou "clickhouse"
        prefer_speed: True = utilise lttbc (plus rapide), False = utilise lttb (plus stable)
        
    Returns:
        DataFrame downsamplé
    """
    if len(df) <= target_points:
        return df.copy()
    
    if method == "uniform":
        return uniform_downsample(df, target_points)
    
    elif method == "lttb":
        if prefer_speed and HAS_LTTBC:
            try:
                return downsample_with_lttbc(df, target_points)
            except Exception as e:
                logger.warning(f"lttbc failed, falling back to lttb: {e}")
        
        if HAS_LTTB:
            return downsample_with_lttb(df, target_points)
        else:
            logger.warning("No LTTB library available, using uniform downsampling")
            return uniform_downsample(df, target_points)
    
    elif method == "clickhouse":
        # Pour les cas où ClickHouse fait le downsampling
        # (implémentation spécifique selon les besoins)
        return uniform_downsample(df, target_points)
    
    else:
        raise ValueError(f"Unknown downsampling method: {method}")


def get_optimal_method(data_size: int, target_points: int) -> str:
    """
    Détermine la méthode optimale selon la taille des données.
    
    Args:
        data_size: taille des données originales
        target_points: nombre de points cibles
        
    Returns:
        méthode recommandée
    """
    ratio = data_size / target_points
    
    if ratio < 2:
        return "uniform"  # Peu de réduction nécessaire
    elif ratio < 100:
        return "lttb"  # LTTB standard
    else:
        return "lttb" if HAS_LTTBC else "uniform"  # LTTBC pour gros volumes