"""
Local model provider implementation.
Uses sentence-transformers for embeddings and local models for completions.
"""

from typing import List, Dict, Any
import logging
from app.services.ai_providers.base import AIProvider

logger = logging.getLogger(__name__)


class LocalProvider(AIProvider):
    """Local model provider using sentence-transformers."""
    
    def __init__(self):
        self._model = None
        self._model_name = "all-MiniLM-L6-v2"
        self._embedding_dimension = 384
        self._available = False
        
        # Try to load model
        try:
            from sentence_transformers import SentenceTransformer
            self._model = SentenceTransformer(self._model_name)
            self._available = True
            logger.info(f"Local model loaded: {self._model_name}")
        except Exception as e:
            logger.warning(f"Local model not available: {str(e)}")
            self._available = False
    
    @property
    def name(self) -> str:
        return "Local"
    
    @property
    def embedding_dimension(self) -> int:
        return self._embedding_dimension
    
    @property
    def is_available(self) -> bool:
        return self._available
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using local model."""
        if not self._available:
            raise Exception("Local model not available")
        
        try:
            # Run synchronous encoding in executor to avoid blocking
            import asyncio
            loop = asyncio.get_event_loop()
            embedding = await loop.run_in_executor(
                None, 
                lambda: self._model.encode(text, convert_to_numpy=True)
            )
            return embedding.tolist()
        except Exception as e:
            raise Exception(f"Local embedding failed: {str(e)}")
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batch."""
        if not self._available:
            raise Exception("Local model not available")
        
        try:
            # Run synchronous encoding in executor to avoid blocking
            import asyncio
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: self._model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
            )
            return embeddings.tolist()
        except Exception as e:
            raise Exception(f"Local batch embedding failed: {str(e)}")
    
    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """
        Local completion not implemented.
        This would require a local LLM which is resource-intensive.
        """
        raise NotImplementedError(
            "Local completion not available. Use OpenAI provider for completions."
        )
    
    async def health_check(self) -> Dict[str, Any]:
        """Check local model availability."""
        if not self._available:
            return {
                "status": "unavailable",
                "provider": self.name,
                "error": "Model not loaded"
            }
        
        try:
            # Test embedding
            await self.generate_embedding("test")
            return {
                "status": "healthy",
                "provider": self.name,
                "model": self._model_name,
                "embedding_dimension": self._embedding_dimension
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": self.name,
                "error": str(e)
            }