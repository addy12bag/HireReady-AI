import logging
import time
from abc import ABC, abstractmethod

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """Base class for all agents with logging and timing."""

    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    async def execute(self, **kwargs) -> dict:
        start = time.time()
        self.logger.info(f"Starting {self.__class__.__name__}")
        try:
            result = await self._execute(**kwargs)
            elapsed = time.time() - start
            self.logger.info(f"{self.__class__.__name__} completed in {elapsed:.2f}s")
            return result
        except Exception as e:
            elapsed = time.time() - start
            self.logger.error(f"{self.__class__.__name__} failed after {elapsed:.2f}s: {e}")
            raise

    @abstractmethod
    async def _execute(self, **kwargs) -> dict:
        ...
