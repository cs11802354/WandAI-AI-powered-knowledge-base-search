"""
AI Provider abstraction layer.
Supports OpenAI, local models, and hybrid fallback.
"""

from app.services.ai_providers.base import AIProvider
from app.services.ai_providers.openai_provider import OpenAIProvider
from app.services.ai_providers.local_provider import LocalProvider
from app.services.ai_providers.hybrid_provider import HybridProvider

__all__ = [
    'AIProvider',
    'OpenAIProvider',
    'LocalProvider',
    'HybridProvider'
]