"""
Question-answering service using RAG (Retrieval-Augmented Generation).
Combines semantic search with LLM to answer questions.
Now supports multiple AI providers with automatic fallback.
"""

from sqlalchemy.orm import Session
from app.services.search_service import semantic_search
from app.config import get_settings
from app.services.ai_providers import OpenAIProvider, HybridProvider

settings = get_settings()

# Initialize provider for completions (always use OpenAI or Hybrid)
def get_completion_provider():
    """Get provider for text completion."""
    provider_type = settings.ai_provider.lower()
    
    if provider_type == "local":
        # Local doesn't support completions, use OpenAI
        return OpenAIProvider()
    elif provider_type == "hybrid":
        return HybridProvider()
    else:
        return OpenAIProvider()

_completion_provider = get_completion_provider()


async def answer_question(db: Session, question: str, top_k: int = 5) -> dict:
    """
    Answer a question using RAG (Retrieval-Augmented Generation).
    
    Process:
    1. Search for relevant chunks (Retrieval)
    2. Build context from chunks
    3. Send to LLM with question (Generation)
    4. Return answer with sources
    
    Args:
        db: Database session
        question: User's question
        top_k: Number of chunks to use as context
        
    Returns:
        Dict with answer and sources
        
    Note: Now async and uses configured provider
    """
    # Step 1: Retrieve relevant chunks
    search_results = await semantic_search(db, question, top_k)
    
    if not search_results:
        return {
            "answer": "I couldn't find relevant information to answer this question.",
            "sources": [],
            "provider": _completion_provider.name
        }
    
    # Step 2: Build context from retrieved chunks
    context_parts = []
    for idx, result in enumerate(search_results, 1):
        context_parts.append(
            f"[Source {idx} - {result['filename']}]:\n{result['text']}"
        )
    
    context = "\n\n".join(context_parts)
    
    # Step 3: Create prompt for LLM
    prompt = f"""Based on the following context from our knowledge base, please answer the question.
If the answer is not in the context, say so.

Context:
{context}

Question: {question}

Answer:"""
    
    # Step 4: Get answer from LLM using provider
    messages = [
        {"role": "system", "content": "You are a helpful assistant that answers questions based on provided context. Always cite your sources."},
        {"role": "user", "content": prompt}
    ]
    
    answer = await _completion_provider.generate_completion(
        messages=messages,
        temperature=0.3  # Lower = more factual, less creative
    )
    
    # Step 5: Format response with sources
    sources = [
        {
            "filename": result['filename'],
            "text": result['text'][:200] + "...",  # First 200 chars
            "similarity": result['similarity']
        }
        for result in search_results
    ]
    
    return {
        "answer": answer,
        "sources": sources,
        "question": question,
        "provider": _completion_provider.name
    }


async def health_check():
    """
    Check health of Q&A provider.
    
    Returns:
        Health status dict
    """
    return await _completion_provider.health_check()