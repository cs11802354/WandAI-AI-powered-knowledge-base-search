"""
Enhanced semantic search service with conflict resolution.
Uses pgvector for fast similarity search + metadata-based ranking.
"""

from sqlalchemy.orm import Session
from sqlalchemy import text
from app.models.database import DocumentChunk, Document
from app.services.embedding_service import generate_embedding
from typing import List, Dict, Optional
import logging
from functools import lru_cache
import hashlib
import json

logger = logging.getLogger(__name__)

# Simple in-memory cache for search results
_search_cache = {}
_cache_max_size = 100


def _get_cache_key(query: str, top_k: int, use_recency: bool) -> str:
    """Generate cache key for search query."""
    cache_data = f"{query}|{top_k}|{use_recency}"
    return hashlib.md5(cache_data.encode()).hexdigest()


def clear_search_cache():
    """
    Clear the search cache.
    Should be called when documents are uploaded/updated to ensure fresh results.
    """
    global _search_cache
    _search_cache.clear()
    logger.info("Search cache cleared")


async def semantic_search(
    db: Session, 
    query: str, 
    top_k: int = 10,
    use_recency_boost: bool = True,
    recency_weight: float = 0.3,
    similarity_threshold: float = 0.0
) -> List[Dict]:
    """
    Perform optimized semantic search with conflict resolution.
    
    Args:
        db: Database session
        query: Search query
        top_k: Number of results to return
        use_recency_boost: Apply recency score for conflict resolution
        recency_weight: Weight for recency (0.0-1.0), higher = prioritize newer content
        similarity_threshold: Minimum similarity score (0.0-1.0)
    
    Returns:
        List of search results with ranking scores
    """
    try:
        logger.info(f"Search: query='{query}', top_k={top_k}, recency_boost={use_recency_boost}")
        
        # Check cache
        cache_key = _get_cache_key(query, top_k, use_recency_boost)
        if cache_key in _search_cache:
            logger.info("Cache hit!")
            return _search_cache[cache_key]
        
        # Step 1: Generate embedding for query
        query_embedding = await generate_embedding(query)
        logger.info(f"Embedding generated: dim={len(query_embedding)}")
        
        # Step 2: Use pgvector for FAST similarity search
        # This uses the HNSW index we created - MUCH faster than Python calculation!
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        # Fetch more results than needed for reranking
        search_limit = top_k * 3 if use_recency_boost else top_k
        
        # Optimized SQL with vector similarity calculation in PostgreSQL
        # Note: Using f-string for vector literal since pgvector doesn't support parameter binding
        sql = text(f"""
            SELECT 
                dc.id,
                dc.chunk_text,
                dc.chunk_index,
                dc.document_id,
                dc.recency_score,
                dc.document_metadata,
                dc.created_at,
                d.filename,
                d.uploaded_at,
                d.version,
                -- Cosine similarity (1 = identical, 0 = orthogonal, -1 = opposite)
                1 - (dc.embedding <=> '{embedding_str}'::vector) as similarity
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE dc.embedding IS NOT NULL
                AND dc.is_active = true
                AND d.is_active = true
            ORDER BY dc.embedding <=> '{embedding_str}'::vector
            LIMIT :search_limit
        """)
        
        result = db.execute(sql, {"search_limit": search_limit})
        
        rows = result.fetchall()
        logger.info(f"Retrieved {len(rows)} chunks from database")
        
        if not rows:
            logger.warning("No chunks found in database")
            return []
        
        # Step 3: Build search results with metadata
        search_results = []
        for row in rows:
            try:
                chunk_id, chunk_text, chunk_index, document_id, recency_score, \
                metadata, created_at, filename, uploaded_at, version, similarity = row
                
                # Skip results below threshold
                if similarity < similarity_threshold:
                    continue
                
                # Calculate hybrid score (similarity + recency)
                if use_recency_boost and recency_score is not None:
                    # Hybrid ranking: combine similarity and recency
                    hybrid_score = (
                        similarity * (1 - recency_weight) +
                        recency_score * recency_weight
                    )
                else:
                    hybrid_score = similarity
                
                # Extract useful metadata
                entities = metadata.get("entities", {}) if metadata else {}
                data_types = metadata.get("data_types", []) if metadata else []
                temporal_info = metadata.get("temporal_info", {}) if metadata else {}
                
                search_results.append({
                    "chunk_id": chunk_id,
                    "text": chunk_text,
                    "chunk_index": chunk_index,
                    "document_id": document_id,
                    "filename": filename,
                    "version": version,
                    "uploaded_at": uploaded_at.isoformat() if uploaded_at else None,
                    "created_at": created_at.isoformat() if created_at else None,
                    "similarity": float(similarity),
                    "recency_score": float(recency_score) if recency_score else 0.5,
                    "hybrid_score": float(hybrid_score),
                    "metadata": {
                        "entities": entities,
                        "data_types": data_types,
                        "temporal_info": temporal_info
                    }
                })
                
            except Exception as e:
                logger.error(f"Error processing chunk {row[0]}: {e}")
                continue
        
        # Step 4: Sort by hybrid score and return top_k
        search_results.sort(key=lambda x: x["hybrid_score"], reverse=True)
        final_results = search_results[:top_k]
        
        logger.info(f"Returning {len(final_results)} results (sorted by hybrid_score)")
        
        # Cache results (simple LRU)
        if len(_search_cache) >= _cache_max_size:
            # Remove oldest entry
            _search_cache.pop(next(iter(_search_cache)))
        _search_cache[cache_key] = final_results
        
        return final_results
        
    except Exception as e:
        logger.error(f"ERROR in semantic_search: {e}", exc_info=True)
        return []


async def semantic_search_with_filters(
    db: Session,
    query: str,
    top_k: int = 10,
    data_types: Optional[List[str]] = None,
    entity_ids: Optional[List[str]] = None,
    min_recency_score: Optional[float] = None
) -> List[Dict]:
    """
    Advanced search with metadata filtering for conflict resolution.
    
    Args:
        db: Database session
        query: Search query
        top_k: Number of results
        data_types: Filter by data types (e.g., ['salary_data', 'personnel_data'])
        entity_ids: Filter by specific entity IDs (e.g., ['1', '123'])
        min_recency_score: Only return chunks with recency >= this value
    
    Example:
        # Find current salary info for employee ID 1
        results = await semantic_search_with_filters(
            db, 
            "salary Manish Kumar",
            data_types=['salary_data'],
            entity_ids=['1'],
            min_recency_score=0.7  # Only "current" information
        )
    """
    try:
        logger.info(f"Filtered search: query='{query}', filters={{data_types={data_types}, entity_ids={entity_ids}, min_recency={min_recency_score}}}")
        
        # Generate embedding
        query_embedding = await generate_embedding(query)
        embedding_str = '[' + ','.join(map(str, query_embedding)) + ']'
        
        # Build dynamic SQL with filters
        where_clauses = ["dc.embedding IS NOT NULL", "dc.is_active = true", "d.is_active = true"]
        params = {"search_limit": top_k * 3}
        
        # Filter by recency score
        if min_recency_score is not None:
            where_clauses.append("dc.recency_score >= :min_recency")
            params["min_recency"] = min_recency_score
        
        # Filter by data types (JSONB query)
        if data_types:
            where_clauses.append("dc.document_metadata @> :data_types_filter")
            params["data_types_filter"] = json.dumps({"data_types": data_types})
        
        # Filter by entity IDs (JSONB query)
        if entity_ids:
            where_clauses.append("dc.document_metadata -> 'entities' -> 'ids' ?| :entity_ids")
            params["entity_ids"] = entity_ids
        
        where_clause = " AND ".join(where_clauses)
        
        # Use f-string for vector literal (pgvector doesn't support parameter binding)
        sql = text(f"""
            SELECT 
                dc.id,
                dc.chunk_text,
                dc.chunk_index,
                dc.document_id,
                dc.recency_score,
                dc.document_metadata,
                dc.created_at,
                d.filename,
                d.uploaded_at,
                1 - (dc.embedding <=> '{embedding_str}'::vector) as similarity
            FROM document_chunks dc
            JOIN documents d ON dc.document_id = d.id
            WHERE {where_clause}
            ORDER BY dc.embedding <=> '{embedding_str}'::vector
            LIMIT :search_limit
        """)
        
        result = db.execute(sql, params)
        rows = result.fetchall()
        
        logger.info(f"Filtered search returned {len(rows)} chunks")
        
        # Build results (same as semantic_search)
        search_results = []
        for row in rows:
            chunk_id, chunk_text, chunk_index, document_id, recency_score, \
            metadata, created_at, filename, uploaded_at, similarity = row
            
            entities = metadata.get("entities", {}) if metadata else {}
            data_types_found = metadata.get("data_types", []) if metadata else []
            
            search_results.append({
                "chunk_id": chunk_id,
                "text": chunk_text,
                "filename": filename,
                "similarity": float(similarity),
                "recency_score": float(recency_score) if recency_score else 0.5,
                "metadata": {
                    "entities": entities,
                    "data_types": data_types_found
                }
            })
        
        # Sort by recency_score (prioritize newest)
        search_results.sort(key=lambda x: (x["similarity"], x["recency_score"]), reverse=True)
        
        return search_results[:top_k]
        
    except Exception as e:
        logger.error(f"ERROR in filtered search: {e}", exc_info=True)
        return []


def clear_search_cache():
    """Clear the search cache."""
    global _search_cache
    _search_cache = {}
    logger.info("Search cache cleared")