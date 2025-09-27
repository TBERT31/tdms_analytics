"""
Application configuration using Pydantic Settings
"""
from functools import lru_cache
from typing import List

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings."""
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )
    
    # App settings
    VERSION: str = "0.1.0"
    DEBUG: bool = Field(default=False, env="DEBUG")
    HOST: str = Field(default="0.0.0.0", env="HOST")
    PORT: int = Field(default=8000, env="PORT")
    
    # CORS
    ALLOWED_ORIGINS: List[str] = Field(
        default=["http://localhost:3000", "http://localhost:8080"],
        env="ALLOWED_ORIGINS"
    )
    
    # ClickHouse settings
    CLICKHOUSE_HOST: str = Field(default="localhost", env="CLICKHOUSE_HOST")
    CLICKHOUSE_PORT: int = Field(default=8123, env="CLICKHOUSE_PORT")
    CLICKHOUSE_USERNAME: str = Field(default="default", env="CLICKHOUSE_USERNAME")
    CLICKHOUSE_PASSWORD: str = Field(default="pass", env="CLICKHOUSE_PASSWORD")
    CLICKHOUSE_DATABASE: str = Field(default="default", env="CLICKHOUSE_DATABASE")
    CLICKHOUSE_SECURE: bool = Field(default=False, env="CLICKHOUSE_SECURE")
    
    # File upload settings
    MAX_FILE_SIZE: int = Field(default=500 * 1024 * 1024, env="MAX_FILE_SIZE")  # 500MB
    UPLOAD_CHUNK_SIZE: int = Field(default=1024 * 1024, env="UPLOAD_CHUNK_SIZE")  # 1MB
    
    # Data processing settings
    DEFAULT_POINTS: int = Field(default=2000, env="DEFAULT_POINTS")
    MAX_POINTS: int = Field(default=20000, env="MAX_POINTS")
    MIN_POINTS: int = Field(default=10, env="MIN_POINTS")
    DEFAULT_LIMIT: int = Field(default=50000, env="DEFAULT_LIMIT")
    MAX_LIMIT: int = Field(default=200000, env="MAX_LIMIT")
    MIN_LIMIT: int = Field(default=10000, env="MIN_LIMIT")
    
    # Performance settings
    BATCH_INSERT_SIZE: int = Field(default=100000, env="BATCH_INSERT_SIZE")
    ENABLE_LTTBC: bool = Field(default=True, env="ENABLE_LTTBC")
    
    @property
    def clickhouse_url(self) -> str:
        """Construct ClickHouse connection URL."""
        protocol = "https" if self.CLICKHOUSE_SECURE else "http"
        auth = ""
        if self.CLICKHOUSE_USERNAME:
            auth = f"{self.CLICKHOUSE_USERNAME}"
            if self.CLICKHOUSE_PASSWORD:
                auth += f":{self.CLICKHOUSE_PASSWORD}"
            auth += "@"
        
        return f"{protocol}://{auth}{self.CLICKHOUSE_HOST}:{self.CLICKHOUSE_PORT}"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()