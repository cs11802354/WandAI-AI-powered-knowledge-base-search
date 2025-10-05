"""
Embedding service for generating vector embeddings.
Converts text into numbers that capture semantic meaning.
Now supports multiple AI providers with automatic fallback.
"""

from typing import List
from app.config import get_settings
from app.services.ai_providers import OpenAIProvider, LocalProvider, HybridProvider
import numpy as np

settings = get_settings()

# Target dimension for database storage (OpenAI's dimension)
TARGET_DIMENSION = 1536

# Initialize provider based on configuration
def get_provider():
    """Get the configured AI provider."""
    provider_type = settings.ai_provider.lower()
    
    if provider_type == "openai":
        return OpenAIProvider()
    elif provider_type == "local":
        return LocalProvider()
    elif provider_type == "hybrid":
        return HybridProvider()
    else:
        # Default to hybrid for safety
        return HybridProvider()

# Global provider instance (created once)
_provider = get_provider()


def normalize_embedding_dimension(embedding: List[float], target_dim: int = TARGET_DIMENSION) -> List[float]:
    """
    Normalize embedding to target dimension.
    - If smaller: pad with zeros
    - If larger: truncate (shouldn't happen)
    - If same: return as-is
    
    This allows local models (384-dim) to work with OpenAI's dimension (1536-dim).
    """
    current_dim = len(embedding)
    
    if current_dim == target_dim:
        return embedding
    elif current_dim < target_dim:
        # Pad with zeros
        padding = [0.0] * (target_dim - current_dim)
        return embedding + padding
    else:
        # Truncate (shouldn't happen, but handle it)
        return embedding[:target_dim]


async def generate_embedding(text: str) -> List[float]:
    """
    Generate embedding for a single text.
    
    Args:
        text: Text to embed
        
    Returns:
        List of floats (the vector) - normalized to TARGET_DIMENSION
        
    Note: Now async and uses configured provider
    """
    embedding = await _provider.generate_embedding(text)
    return normalize_embedding_dimension(embedding)


async def generate_embeddings_batch(texts: List[str]) -> List[List[float]]:
    """
    Generate embeddings for multiple texts (more efficient).
    
    Args:
        texts: List of texts to embed
        
    Returns:
        List of embeddings - all normalized to TARGET_DIMENSION
        
    Note: Now async and uses configured provider
    """
    embeddings = await _provider.generate_embeddings_batch(texts)
    return [normalize_embedding_dimension(emb) for emb in embeddings]


def get_embedding_dimension() -> int:
    """
    Get the dimension of embeddings from current provider.
    
    Returns:
        Embedding dimension (e.g., 1536 for OpenAI, 384 for local)
    """
    return _provider.embedding_dimension


def get_provider_name() -> str:
    """
    Get the name of current provider.
    
    Returns:
        Provider name
    """
    return _provider.name


async def health_check():
    """
    Check health of embedding provider.
    
    Returns:
        Health status dict
    """
    return await _provider.health_check()