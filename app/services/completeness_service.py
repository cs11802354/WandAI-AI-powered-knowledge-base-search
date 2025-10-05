"""
Completeness checking service.
Analyzes knowledge base for gaps in coverage.
"""

from sqlalchemy.orm import Session
from openai import OpenAI
from app.services.search_service import semantic_search
from app.config import get_settings
from typing import List

settings = get_settings()
client = OpenAI(api_key=settings.openai_api_key)


async def check_completeness(db: Session, requirements: List[str]) -> dict:
    """
    Check if knowledge base covers all required topics.
    
    Process:
    1. For each requirement, search knowledge base
    2. Use LLM to analyze coverage
    3. Identify gaps
    
    Args:
        db: Database session
        requirements: List of topics that should be covered
        
    Returns:
        Dict with coverage analysis and gaps
    """
    analysis = []
    
    for requirement in requirements:
        # Search for content related to this requirement
        results = await semantic_search(db, requirement, top_k=3)
        
        if not results:
            analysis.append({
                "requirement": requirement,
                "covered": False,
                "confidence": 0.0,
                "summary": "No relevant information found",
                "sources": []
            })
            continue
        
        # Get best match similarity
        best_similarity = results[0]['similarity']
        
        # Build context from results
        context = "\n\n".join([r['text'] for r in results])
        
        # Ask LLM to analyze coverage
        prompt = f"""Analyze if the following content adequately covers the topic: "{requirement}"

Content:
{context}

Does this content cover the topic? Provide:
1. Yes/No
2. Brief explanation (2-3 sentences)
3. What's missing (if anything)"""
        
        response = client.chat.completions.create(
            model=settings.llm_model,
            messages=[
                {"role": "system", "content": "You are an expert at analyzing documentation completeness."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2
        )
        
        llm_analysis = response.choices[0].message.content
        
        # Determine if covered (based on similarity threshold)
        covered = best_similarity > 0.7
        
        analysis.append({
            "requirement": requirement,
            "covered": covered,
            "confidence": best_similarity,
            "summary": llm_analysis,
            "sources": [
                {"filename": r['filename'], "similarity": r['similarity']}
                for r in results
            ]
        })
    
    # Calculate overall completeness
    total_requirements = len(requirements)
    covered_requirements = sum(1 for a in analysis if a['covered'])
    completeness_percentage = (covered_requirements / total_requirements * 100) if total_requirements > 0 else 0
    
    # Identify gaps
    gaps = [a['requirement'] for a in analysis if not a['covered']]
    
    return {
        "completeness_percentage": completeness_percentage,
        "total_requirements": total_requirements,
        "covered_count": covered_requirements,
        "gaps": gaps,
        "detailed_analysis": analysis
    }
