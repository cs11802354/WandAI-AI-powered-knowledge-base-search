"""
Base interface for AI providers.
All providers must implement these methods.
"""

from abc import ABC, abstractmethod
from typing import List, Dict, Any


class AIProvider(ABC):
    """Abstract base class for AI providers."""
    
    @abstractmethod
    async def generate_embedding(self, text: str) -> List[float]:
        """
        Generate embedding vector for text.
        
        Args:
            text: Input text to embed
            
        Returns:
            List of floats representing the embedding vector
        """
        pass
    
    @abstractmethod
    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """
        Generate embeddings for multiple texts (batch operation).
        
        Args:
            texts: List of input texts
            
        Returns:
            List of embedding vectors
        """
        pass
    
    @abstractmethod
    async def generate_completion(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 500
    ) -> str:
        """
        Generate text completion/chat response.
        
        Args:
            messages: Chat messages in OpenAI format
            temperature: Sampling temperature (0-1)
            max_tokens: Maximum tokens to generate
            
        Returns:
            Generated text response
        """
        pass
    
    @abstractmethod
    async def health_check(self) -> Dict[str, Any]:
        """
        Check if provider is healthy and available.
        
        Returns:
            Dict with status and details
        """
        pass
    
    @property
    @abstractmethod
    def name(self) -> str:
        """Provider name."""
        pass
    
    @property
    @abstractmethod
    def embedding_dimension(self) -> int:
        """Dimension of embedding vectors."""
        pass