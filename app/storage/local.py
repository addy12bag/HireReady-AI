from pathlib import Path

from app.storage.base import StorageProvider
from app.config import get_settings


class LocalFilesystemStorage(StorageProvider):
    def __init__(self):
        self.base_path = Path(get_settings().storage_path)
        self.base_path.mkdir(parents=True, exist_ok=True)

    async def save(self, key: str, data: bytes) -> str:
        file_path = self.base_path / key
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(data)
        return str(file_path)

    async def load(self, key: str) -> bytes:
        file_path = self.base_path / key
        return file_path.read_bytes()

    async def delete(self, key: str) -> None:
        file_path = self.base_path / key
        if file_path.exists():
            file_path.unlink()


def get_storage() -> LocalFilesystemStorage:
    return LocalFilesystemStorage()
