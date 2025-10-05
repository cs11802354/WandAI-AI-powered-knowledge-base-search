"""
Configuration settings loaded from environment variables.
This keeps secrets out of code and makes the app configurable.
"""

from pydantic_settings import BaseSettings
from functools import lru_cache


class Settings(BaseSettings):
    """
    Application settings.
    These are loaded from .env file automatically.
    """
    
    # OpenAI Configuration
    openai_api_key: str
    
    # Database Configuration
    database_url: str
    
    # Redis Configuration
    redis_url: str
    
    # Application Settings
    chunk_size: int = 1000
    chunk_overlap: int = 100
    max_file_size_mb: int = 100
    
    # Embedding Configuration
    embedding_model: str = "text-embedding-3-small"
    embedding_dimension: int = 1536
    
    # LLM Configuration
    llm_model: str = "gpt-4o-mini"
    
    # AI Provider Settings (NEW)
    ai_provider: str = "hybrid"  # Options: "openai", "local", "hybrid"
    
    # Local Model Configuration (NEW)
    local_embedding_model: str = "all-MiniLM-L6-v2"
    local_embedding_dimension: int = 384
    
    # Hybrid Fallback Settings (NEW)
    enable_local_fallback: bool = True
    prefer_local_embeddings: bool = True
    
    class Config:
        env_file = ".env"
        case_sensitive = False


@lru_cache()
def get_settings() -> Settings:
    """
    Cached settings instance.
    lru_cache means we only create this once, then reuse it.
    """
    return Settings()