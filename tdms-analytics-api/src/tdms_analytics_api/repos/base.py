"""Base repository class."""
from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional
from uuid import UUID

from clickhouse_connect.driver import Client
from loguru import logger


class BaseRepository(ABC):
    """Base repository class for data access."""
    
    def __init__(self, db_client: Client):
        self.db = db_client
    
    @abstractmethod
    async def find_by_id(self, entity_id: UUID) -> Optional[Dict[str, Any]]:
        """Find entity by ID."""
        pass
    
    @abstractmethod
    async def find_all(self) -> List[Dict[str, Any]]:
        """Find all entities."""
        pass
    
    @abstractmethod
    async def create(self, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create new entity."""
        pass
    
    @abstractmethod
    async def update(self, entity_id: UUID, entity_data: Dict[str, Any]) -> Dict[str, Any]:
        """Update existing entity."""
        pass
    
    @abstractmethod
    async def delete(self, entity_id: UUID) -> bool:
        """Delete entity."""
        pass
    
    def _execute_query(self, query: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Execute a query with error handling."""
        try:
            return self.db.query(query, params or {})
        except Exception as e:
            logger.error(f"Query execution failed: {query[:100]}... Error: {e}")
            raise
    
    def _execute_command(self, command: str, params: Optional[Dict[str, Any]] = None) -> None:
        """Execute a command with error handling."""
        try:
            self.db.command(command, params or {})
        except Exception as e:
            logger.error(f"Command execution failed: {command[:100]}... Error: {e}")
            raise
    
    def _insert_data(self, table: str, data: List[Dict[str, Any]]) -> None:
        """Insert data with error handling."""
        try:
            self.db.insert(table, data)
        except Exception as e:
            logger.error(f"Insert failed for table {table}: {e}")
            raise