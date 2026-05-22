from abc import ABC, abstractmethod
from pydantic import BaseModel


class LLMProvider(ABC):
    @abstractmethod
    async def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        """Generate a text response."""
        ...

    @abstractmethod
    async def generate_json(
        self, prompt: str, system: str = "", schema: type[BaseModel] | None = None
    ) -> dict:
        """Generate a JSON response, optionally validated against a Pydantic schema."""
        ...

    @abstractmethod
    async def embed(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for a list of texts."""
        ...
