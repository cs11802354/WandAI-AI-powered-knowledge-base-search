"""
OpenAI provider implementation.
Uses OpenAI API for embeddings and completions.
"""

from typing import List, Dict, Any
import openai
from openai import AsyncOpenAI
from app.services.ai_providers.base import AIProvider
from app.config import get_settings


class OpenAIProvider(AIProvider):
    """OpenAI API provider."""
    
    def __init__(self):
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.embedding_model = settings.embedding_model
        self.llm_model = settings.llm_model
        self._embedding_dimension = settings.embedding_dimension
    
    @property
    def name(self) -> str:
        return "OpenAI"
    
    @property
    def embedding_dimension(self) -> int:
        return self._embedding_dimension
    
    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding using OpenAI API."""
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            raise Exception(f"OpenAI embedding failed: {str(e)}")
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings in batch."""
        try:
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=texts
            )
            return [item.embedding for item in response.data]
        except Exception as e:
            raise Exception(f"OpenAI batch embedding failed: {str(e)}")
    
    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """Generate completion using OpenAI chat API."""
        try:
            response = await self.client.chat.completions.create(
                model=self.llm_model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens
            )
            return response.choices[0].message.content
        except Exception as e:
            raise Exception(f"OpenAI completion failed: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Check OpenAI API availability."""
        try:
            # Try a simple embedding request
            await self.generate_embedding("test")
            return {
                "status": "healthy",
                "provider": self.name,
                "embedding_model": self.embedding_model,
                "llm_model": self.llm_model
            }
        except Exception as e:
            return {
                "status": "unhealthy",
                "provider": self.name,
                "error": str(e)
            }