"""
File processing service.
Extracts text from PDF, DOCX, and TXT files.
"""

import hashlib
from typing import BinaryIO
import PyPDF2
from docx import Document as DocxDocument


def calculate_file_hash(file_content: bytes) -> str:
    """
    Calculate SHA256 hash of file for duplicate detection.
    
    Args:
        file_content: Raw file bytes
        
    Returns:
        Hexadecimal hash string
    """
    return hashlib.sha256(file_content).hexdigest()


def extract_text_from_pdf(file_path: str) -> str:
    """
    Extract text from PDF file.
    
    Args:
        file_path: Path to PDF file
        
    Returns:
        Extracted text
    """
    text = []
    
    with open(file_path, 'rb') as file:
        pdf_reader = PyPDF2.PdfReader(file)
        
        for page in pdf_reader.pages:
            page_text = page.extract_text()
            if page_text:
                text.append(page_text)
    
    return "\n\n".join(text)


def extract_text_from_docx(file_path: str) -> str:
    """
    Extract text from DOCX file.
    
    Args:
        file_path: Path to DOCX file
        
    Returns:
        Extracted text
    """
    doc = DocxDocument(file_path)
    paragraphs = [paragraph.text for paragraph in doc.paragraphs]
    return "\n\n".join(paragraphs)


def extract_text_from_txt(file_path: str) -> str:
    """
    Extract text from TXT file.
    
    Args:
        file_path: Path to TXT file
        
    Returns:
        File content
    """
    with open(file_path, 'r', encoding='utf-8') as file:
        return file.read()


def extract_text(file_path: str, filename: str) -> str:
    """
    Extract text from file based on extension.
    
    Args:
        file_path: Path to file
        filename: Original filename
        
    Returns:
        Extracted text
    """
    extension = filename.lower().split('.')[-1]
    
    if extension == 'pdf':
        return extract_text_from_pdf(file_path)
    elif extension == 'docx':
        return extract_text_from_docx(file_path)
    elif extension == 'txt':
        return extract_text_from_txt(file_path)
    else:
        raise ValueError(f"Unsupported file type: {extension}")
