"""
Enhanced text chunking service.
Splits documents with smart semantic boundaries and rich metadata.
Supports conflict resolution through entity extraction and temporal analysis.
"""

import tiktoken
import re
from typing import List, Dict, Tuple
from datetime import datetime
from app.config import get_settings

settings = get_settings()


def count_tokens(text: str) -> int:
    """Count number of tokens in text."""
    encoding = tiktoken.get_encoding("cl100k_base")
    return len(encoding.encode(text))


def extract_entities(text: str) -> Dict[str, List[str]]:
    """
    Extract entities from text for conflict resolution.
    
    Extracts:
    - Employee IDs (id=X, emp_id=X, employee_id=X)
    - Names (proper nouns)
    - Email addresses
    - Phone numbers
    - Monetary amounts ($X, USD X)
    - Dates
    - Product/Project IDs
    
    Returns:
        Dict of entity types and their values
    """
    entities = {
        "ids": [],
        "emails": [],
        "phone_numbers": [],
        "amounts": [],
        "dates": [],
        "names": []
    }
    
    # Extract IDs (id=1, emp_id=123, employee_id=456)
    id_patterns = [
        r'\bid[=:]\s*(\d+)\b',
        r'\bemp_id[=:]\s*(\d+)\b',
        r'\bemployee_id[=:]\s*(\d+)\b',
        r'\buser_id[=:]\s*(\d+)\b',
        r'\bproject_id[=:]\s*(\d+)\b',
        r'\bproduct_id[=:]\s*(\d+)\b',
        r'\bID[:#]\s*(\w+)\b'
    ]
    for pattern in id_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities["ids"].extend(matches)
    
    # Extract email addresses
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    entities["emails"] = re.findall(email_pattern, text)
    
    # Extract phone numbers
    phone_pattern = r'\b(?:\+?1[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b'
    entities["phone_numbers"] = re.findall(phone_pattern, text)
    
    # Extract monetary amounts ($100, USD 150, 200$)
    amount_patterns = [
        r'\$\s*(\d+(?:,\d{3})*(?:\.\d{2})?)',
        r'(\d+(?:,\d{3})*(?:\.\d{2})?)\s*(?:USD|usd|dollars?)',
        r'(?:USD|usd)\s*(\d+(?:,\d{3})*(?:\.\d{2})?)'
    ]
    for pattern in amount_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities["amounts"].extend(matches)
    
    # Extract dates (YYYY-MM-DD, MM/DD/YYYY, Jan 2024, etc.)
    date_patterns = [
        r'\b\d{4}-\d{2}-\d{2}\b',
        r'\b\d{1,2}/\d{1,2}/\d{4}\b',
        r'\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b',
        r'\b\d{1,2}\s+(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{4}\b'
    ]
    for pattern in date_patterns:
        matches = re.findall(pattern, text, re.IGNORECASE)
        entities["dates"].extend(matches)
    
    # Extract names (capitalized words, basic heuristic)
    name_pattern = r'\b([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\b'
    entities["names"] = re.findall(name_pattern, text)
    
    # Remove duplicates
    for key in entities:
        entities[key] = list(set(entities[key]))
    
    return entities


def classify_data_type(text: str, entities: Dict[str, List[str]]) -> List[str]:
    """
    Classify the type of data in this chunk.
    
    Returns:
        List of data types (can have multiple)
    """
    data_types = []
    text_lower = text.lower()
    
    # Salary/Compensation data
    if re.search(r'\bsalary\b|\bcompensation\b|\bpay\b|\bwage\b', text_lower):
        if entities["amounts"]:
            data_types.append("salary_data")
    
    # Contact information
    if entities["emails"] or entities["phone_numbers"]:
        data_types.append("contact_info")
    
    # Status/State information
    if re.search(r'\bstatus\b|\bstate\b|\bphase\b|\bcompleted\b|\bin progress\b|\bpending\b', text_lower):
        data_types.append("status_data")
    
    # Policy/Rules
    if re.search(r'\bpolicy\b|\brule\b|\bguideline\b|\bprocedure\b|\bmust\b|\bshall\b|\brequired\b', text_lower):
        data_types.append("policy_data")
    
    # Pricing/Financial
    if entities["amounts"] and re.search(r'\bprice\b|\bcost\b|\bfee\b|\bbudget\b|\brevenue\b', text_lower):
        data_types.append("financial_data")
    
    # Personnel/HR
    if entities["names"] and re.search(r'\bemployee\b|\bmanager\b|\bteam\b|\bdepartment\b|\bhr\b', text_lower):
        data_types.append("personnel_data")
    
    # Project/Product
    if re.search(r'\bproject\b|\bproduct\b|\bfeature\b|\brelease\b|\bversion\b', text_lower):
        data_types.append("project_data")
    
    # If no specific type found, mark as general
    if not data_types:
        data_types.append("general")
    
    return data_types


def detect_temporal_indicators(text: str) -> Dict[str, any]:
    """
    Detect temporal indicators for recency scoring.
    
    Critical for conflict resolution!
    """
    temporal_info = {
        "has_temporal_indicator": False,
        "recency_score": 0.5,  # Default: neutral (0-1 scale)
        "keywords": [],
        "is_current": False,
        "is_historical": False,
        "confidence": "medium"
    }
    
    text_lower = text.lower()
    
    # CURRENT/LATEST indicators (HIGH recency score)
    current_patterns = {
        r'\bcurrent(?:ly)?\b': 0.9,
        r'\blatest\b': 0.9,
        r'\bnow\b': 0.85,
        r'\btoday\b': 0.85,
        r'\bpresent\b': 0.8,
        r'\bas of now\b': 0.9,
        r'\bupdated\b': 0.85,
        r'\brecent(?:ly)?\b': 0.8,
        r'\bactive\b': 0.75,
        r'\beffective\b': 0.7
    }
    
    # HISTORICAL indicators (LOW recency score)
    historical_patterns = {
        r'\bprevious(?:ly)?\b': 0.3,
        r'\bold\b': 0.2,
        r'\bformer(?:ly)?\b': 0.25,
        r'\bwas\b': 0.4,
        r'\bpast\b': 0.3,
        r'\barchived\b': 0.1,
        r'\bdeprecated\b': 0.1,
        r'\bexpired\b': 0.1,
        r'\bobsolete\b': 0.1
    }
    
    max_score = 0.5
    
    # Check current patterns
    for pattern, score in current_patterns.items():
        if re.search(pattern, text_lower):
            temporal_info["has_temporal_indicator"] = True
            temporal_info["is_current"] = True
            temporal_info["keywords"].append(pattern.strip(r'\b'))
            max_score = max(max_score, score)
    
    # Check historical patterns
    for pattern, score in historical_patterns.items():
        if re.search(pattern, text_lower):
            temporal_info["has_temporal_indicator"] = True
            temporal_info["is_historical"] = True
            temporal_info["keywords"].append(pattern.strip(r'\b'))
            if not temporal_info["is_current"]:  # Only lower score if not also current
                max_score = min(max_score, score)
    
    temporal_info["recency_score"] = max_score
    
    # Set confidence based on number of indicators
    if len(temporal_info["keywords"]) >= 2:
        temporal_info["confidence"] = "high"
    elif len(temporal_info["keywords"]) == 1:
        temporal_info["confidence"] = "medium"
    else:
        temporal_info["confidence"] = "low"
    
    return temporal_info


def detect_content_type(text: str) -> str:
    """Detect the type of content structure."""
    text_stripped = text.strip()
    
    if re.match(r'^#{1,6}\s+\w+', text_stripped):
        return "heading"
    if re.match(r'^[\*\-\+•]\s+', text_stripped, re.MULTILINE):
        return "list"
    if '|' in text_stripped and text_stripped.count('|') > 2:
        return "table"
    if re.match(r'^```', text_stripped):
        return "code"
    
    return "paragraph"


def find_semantic_boundaries(text: str) -> List[int]:
    """
    Find natural break points in text.
    Prefer breaking at paragraph boundaries, headings, or list items.
    """
    boundaries = [0]
    
    # Split by double newlines (paragraphs)
    paragraphs = re.split(r'\n\s*\n', text)
    
    position = 0
    for para in paragraphs:
        position += len(para) + 2  # +2 for the newlines
        if position < len(text):
            boundaries.append(position)
    
    return boundaries


def chunk_text(text: str, chunk_size: int = None, overlap: int = None) -> List[str]:
    """
    Basic chunking (backward compatible).
    For enhanced chunking with metadata, use chunk_text_enhanced().
    """
    if chunk_size is None:
        chunk_size = settings.chunk_size
    if overlap is None:
        overlap = settings.chunk_overlap
    
    encoding = tiktoken.get_encoding("cl100k_base")
    tokens = encoding.encode(text)
    
    chunks = []
    start = 0
    
    while start < len(tokens):
        end = start + chunk_size
        chunk_tokens = tokens[start:end]
        chunk_text = encoding.decode(chunk_tokens)
        chunks.append(chunk_text)
        start = end - overlap
        
        if start >= len(tokens):
            break
    
    return chunks


def chunk_text_enhanced(
    text: str,
    chunk_size: int = None,
    overlap: int = None,
    document_metadata: Dict = None
) -> List[Dict]:
    """
    Enhanced chunking with rich metadata for conflict resolution.
    
    Returns:
        List of dicts with chunk text and metadata
    """
    if chunk_size is None:
        chunk_size = settings.chunk_size
    if overlap is None:
        overlap = settings.chunk_overlap
    
    # Get basic chunks
    basic_chunks = chunk_text(text, chunk_size, overlap)
    
    # Enhance each chunk with metadata
    enhanced_chunks = []
    
    for idx, text_chunk in enumerate(basic_chunks):
        # Extract entities
        entities = extract_entities(text_chunk)
        
        # Classify data type
        data_types = classify_data_type(text_chunk, entities)
        
        # Detect temporal indicators
        temporal_info = detect_temporal_indicators(text_chunk)
        
        # Detect content structure type
        content_type = detect_content_type(text_chunk)
        
        # Build comprehensive metadata
        chunk_metadata = {
            "chunk_index": idx,
            "chunk_length": len(text_chunk),
            "token_count": count_tokens(text_chunk),
            "content_type": content_type,
            "data_types": data_types,
            "entities": entities,
            "temporal_info": temporal_info,
            "recency_score": temporal_info["recency_score"],
            "created_at": datetime.utcnow().isoformat()
        }
        
        # Add document-level metadata if provided
        if document_metadata:
            chunk_metadata["document_metadata"] = document_metadata
        
        enhanced_chunks.append({
            "text": text_chunk,
            "metadata": chunk_metadata
        })
    
    return enhanced_chunks