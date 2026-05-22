import asyncio
import json
import logging

from groq import AsyncGroq
from pydantic import BaseModel

from app.llm.provider import LLMProvider
from app.config import get_settings

logger = logging.getLogger(__name__)


class GroqProvider(LLMProvider):
    def __init__(self):
        settings = get_settings()
        self.client = AsyncGroq(api_key=settings.groq_api_key, timeout=60.0)
        self.model = settings.llm_model or "llama-3.3-70b-versatile"
        self._semaphore = asyncio.Semaphore(30)

    async def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        async with self._semaphore:
            try:
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=temperature,
                )
                return response.choices[0].message.content
            except Exception as e:
                logger.error(f"Groq generate error: {e}")
                raise

    async def generate_json(
        self, prompt: str, system: str = "", schema: type[BaseModel] | None = None
    ) -> dict:
        async with self._semaphore:
            try:
                messages = []
                if system:
                    messages.append({"role": "system", "content": system})
                messages.append({"role": "user", "content": prompt})

                response = await self.client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    temperature=0.2,
                    response_format={"type": "json_object"},
                )
                return json.loads(response.choices[0].message.content)
            except Exception as e:
                logger.error(f"Groq generate_json error: {e}")
                raise

    async def embed(self, texts: list[str]) -> list[list[float]]:
        # Groq doesn't have embedding models — fall back to a simple approach
        # For production, use a dedicated embedding provider
        raise NotImplementedError("Groq does not provide embedding models. Use Gemini or a dedicated embedding provider.")
