import asyncio
import json
import logging

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.llm.provider import LLMProvider
from app.config import get_settings

logger = logging.getLogger(__name__)


class GeminiProvider(LLMProvider):
    def __init__(self):
        settings = get_settings()
        self.client = genai.Client(api_key=settings.gemini_api_key)
        self.model = settings.llm_model
        self._semaphore = asyncio.Semaphore(15)

    async def generate(self, prompt: str, system: str = "", temperature: float = 0.7) -> str:
        async with self._semaphore:
            try:
                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        system_instruction=system or None,
                        temperature=temperature,
                    ),
                )
                return response.text
            except Exception as e:
                logger.error(f"Gemini generate error: {e}")
                raise

    async def generate_json(
        self, prompt: str, system: str = "", schema: type[BaseModel] | None = None
    ) -> dict:
        async with self._semaphore:
            try:
                config = types.GenerateContentConfig(
                    system_instruction=system or None,
                    temperature=0.3,
                    response_mime_type="application/json",
                )
                if schema:
                    config.response_schema = schema

                response = await asyncio.to_thread(
                    self.client.models.generate_content,
                    model=self.model,
                    contents=prompt,
                    config=config,
                )
                return json.loads(response.text)
            except Exception as e:
                logger.error(f"Gemini generate_json error: {e}")
                raise

    async def embed(self, texts: list[str]) -> list[list[float]]:
        try:
            result = await asyncio.to_thread(
                self.client.models.embed_content,
                model="models/text-embedding-004",
                contents=texts,
            )
            return [e.values for e in result.embeddings]
        except Exception as e:
            logger.error(f"Gemini embed error: {e}")
            raise
