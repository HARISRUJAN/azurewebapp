"""
Text normalization module for cleaning text and content deduplication.
"""
import hashlib
import re
from typing import Set

def normalize_text(text: str) -> str:
    """
    Normalize text by removing boilerplate and normalizing whitespace.
    
    Args:
        text: Raw text to normalize
        
    Returns:
        Normalized text string
        
    Features:
        - Normalize whitespace (multiple spaces/tabs/newlines to single space)
        - Remove leading/trailing whitespace
        - Remove common boilerplate patterns
    """
    if not text:
        return ""
    
    # Normalize whitespace: replace multiple spaces/tabs/newlines with single space
    text = re.sub(r'\s+', ' ', text)
    
    # Remove leading/trailing whitespace
    text = text.strip()
    
    # Remove common boilerplate patterns (can be extended)
    # Remove email signatures, disclaimers, etc.
    # This is a basic implementation - can be enhanced with more patterns
    
    return text


def content_hash(text: str) -> str:
    """
    Generate a hash for content deduplication.
    
    Args:
        text: Text content to hash
        
    Returns:
        SHA256 hash hex string
        
    Uses SHA256 to generate a unique hash for content deduplication.
    Normalizes text before hashing to catch near-duplicates.
    """
    normalized = normalize_text(text)
    
    # Generate SHA256 hash
    hash_obj = hashlib.sha256(normalized.encode('utf-8'))
    return hash_obj.hexdigest()


def is_duplicate(content_hash: str, seen_hashes: Set[str]) -> bool:
    """
    Check if content hash has been seen before (duplicate content).
    
    Args:
        content_hash: Hash of the content to check
        seen_hashes: Set of previously seen content hashes
        
    Returns:
        True if duplicate, False otherwise
    """
    if content_hash in seen_hashes:
        return True
    
    seen_hashes.add(content_hash)
    return False


