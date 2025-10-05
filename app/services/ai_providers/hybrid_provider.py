"""
Hybrid provider with automatic fallback.
Tries local models first, falls back to OpenAI if needed.
"""

from typing import List, Dict, Any
import logging
from app.services.ai_providers.base import AIProvider
from app.services.ai_providers.openai_provider import OpenAIProvider
from app.services.ai_providers.local_provider import LocalProvider

logger = logging.getLogger(__name__)


class HybridProvider(AIProvider):
    """Hybrid provider with intelligent fallback."""
    
    def __init__(self):
        self.openai = OpenAIProvider()
        self.local = LocalProvider()
        
        # Strategy: use local for embeddings if available, always use OpenAI for completions
        self.use_local_embeddings = self.local.is_available
        
        logger.info(f"Hybrid provider initialized. Local embeddings: {self.use_local_embeddings}")
    
    @property
    def name(self) -> str:
        return "Hybrid"
    
    @property
    def embedding_dimension(self) -> int:
        """Return dimension based on active provider."""
        if self.use_local_embeddings:
            return self.local.embedding_dimension
        return self.openai.embedding_dimension
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding with fallback."""
        if self.use_local_embeddings:
            try:
                return await self.local.generate_embedding(text)
            except Exception as e:
                logger.warning(f"Local embedding failed, falling back to OpenAI: {str(e)}")
                return await self.openai.generate_embedding(text)
        
        return await self.openai.generate_embedding(text)
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate batch embeddings with fallback."""
        if self.use_local_embeddings:
            try:
                return await self.local.generate_embeddings_batch(texts)
            except Exception as e:
                logger.warning(f"Local batch embedding failed, falling back to OpenAI: {str(e)}")
                return await self.openai.generate_embeddings_batch(texts)
        
        return await self.openai.generate_embeddings_batch(texts)
    
    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """Always use OpenAI for completions (local LLM too resource-intensive)."""
        return await self.openai.generate_completion(messages, temperature, max_tokens)
    
    async def health_check(self) -> Dict[str, Any]:
        """Check health of both providers."""
        openai_health = await self.openai.health_check()
        local_health = await self.local.health_check()
        
        return {
            "status": "healthy" if openai_health["status"] == "healthy" else "degraded",
            "provider": self.name,
            "openai": openai_health,
            "local": local_health,
            "strategy": {
                "embeddings": "local" if self.use_local_embeddings else "openai",
                "completions": "openai"
            }
        }