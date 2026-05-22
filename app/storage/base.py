from abc import ABC, abstractmethod


class StorageProvider(ABC):
    @abstractmethod
    async def save(self, key: str, data: bytes) -> str:
        """Save data and return the storage path."""
        ...

    @abstractmethod
    async def load(self, key: str) -> bytes:
        """Load data by key."""
        ...

    @abstractmethod
    async def delete(self, key: str) -> None:
        """Delete data by key."""
        ...
