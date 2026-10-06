from typing import TypeVar, Generic, List, Optional
from uuid import UUID
from abc import ABC, abstractmethod

T = TypeVar('T')

class BaseRepository(ABC, Generic[T]):
    """Base repository interface for persistence operations"""
    
    @abstractmethod
    async def create(self, entity: T) -> T:
        """Create a new entity"""
        ...
    
    @abstractmethod
    async def get_by_id(self, id: UUID) -> Optional[T]:
        """Get an entity by its ID"""
        ...
    
    @abstractmethod
    async def update(self, entity: T) -> T:
        """Update an existing entity"""
        ...
    
    @abstractmethod
    async def delete(self, id: UUID) -> bool:
        """Delete an entity by ID"""
        ...
    
    @abstractmethod
    async def list(self, limit: int = 100, offset: int = 0) -> List[T]:
        """List entities with pagination"""
        ...