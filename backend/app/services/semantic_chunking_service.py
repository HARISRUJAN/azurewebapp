"""
Semantic Chunking Service using spaCy

This service implements semantic chunking where 1 paragraph = 1 chunk,
with entity extraction using spaCy NER (Named Entity Recognition).

Features:
- Paragraph-based chunking (handles \n\n, \n, markdown paragraphs)
- Entity extraction using spaCy NER
- Top N most frequent entities per chunk
- Edge case handling:
  - Very short paragraphs (<50 chars): merge with next paragraph
  - Very long paragraphs (>2000 chars): split at sentence boundaries
  - No paragraph breaks: fall back to sentence-based chunking
"""

import logging
from typing import List, Dict, Optional
import spacy
from collections import Counter

from app.core.config import settings

logger = logging.getLogger(__name__)


class SemanticChunkingService:
    """
    Service for semantic chunking using spaCy.
    
    Chunks documents by paragraphs (1 paragraph = 1 chunk) and extracts
    entities using spaCy's Named Entity Recognition (NER).
    """
    
    def __init__(self):
        """Initialize spaCy model for chunking and entity extraction."""
        try:
            model_name = settings.spacy_model_name
            logger.info(f"Loading spaCy model: {model_name}")
            self.nlp = spacy.load(model_name)
            logger.info(f"Successfully loaded spaCy model: {model_name}")
        except OSError as e:
            error_msg = (
                f"Failed to load spaCy model '{settings.spacy_model_name}'. "
                f"Please install it with: python -m spacy download {settings.spacy_model_name}"
            )
            logger.error(error_msg)
            raise Exception(error_msg) from e
        except Exception as e:
            logger.exception(f"Error initializing spaCy model: {str(e)}")
            raise
    
    def extract_entities(self, text: str) -> List[Dict]:
        """
        Extract named entities from text using spaCy NER.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of entity dictionaries with:
            - text: Entity text
            - label: Entity label (e.g., "ORG", "PERSON", "GPE")
            - start: Start character position in text
            - end: End character position in text
        """
        if not text or not text.strip():
            return []
        
        doc = self.nlp(text)
        entities = []
        
        for ent in doc.ents:
            entities.append({
                "text": ent.text,
                "label": ent.label_,
                "start": ent.start_char,
                "end": ent.end_char
            })
        
        return entities
    
    def _filter_top_entities(self, entities: List[Dict], max_entities: int) -> List[Dict]:
        """
        Filter to top N most frequent entities per chunk.
        
        Args:
            entities: List of entity dictionaries
            max_entities: Maximum number of entities to return
            
        Returns:
            Filtered list of entities (top N most frequent)
        """
        if not entities or len(entities) <= max_entities:
            return entities
        
        # Count entity frequencies (by text)
        entity_counts = Counter(entity["text"].lower() for entity in entities)
        
        # Get top N most frequent entities
        top_entity_texts = {text for text, _ in entity_counts.most_common(max_entities)}
        
        # Filter entities to include only top N, preserving order
        filtered = []
        seen = set()
        for entity in entities:
            entity_key = entity["text"].lower()
            if entity_key in top_entity_texts and entity_key not in seen:
                filtered.append(entity)
                seen.add(entity_key)
                if len(filtered) >= max_entities:
                    break
        
        return filtered
    
    def _split_into_paragraphs(self, content: str) -> List[str]:
        """
        Split content into paragraphs.
        
        Handles:
        - Double newlines (\n\n) - standard paragraph breaks
        - Single newlines (\n) - markdown-style paragraphs
        - Markdown paragraph markers
        
        Args:
            content: Document content to split
            
        Returns:
            List of paragraph strings
        """
        if not content:
            return []
        
        # First, try splitting by double newlines (most common)
        paragraphs = [p.strip() for p in content.split('\n\n') if p.strip()]
        
        # If no double newlines, try single newlines
        if len(paragraphs) <= 1:
            paragraphs = [p.strip() for p in content.split('\n') if p.strip()]
        
        # If still only one paragraph, check for markdown-style breaks
        if len(paragraphs) <= 1:
            # Try splitting by markdown paragraph markers
            import re
            markdown_breaks = re.split(r'\n{2,}', content)
            paragraphs = [p.strip() for p in markdown_breaks if p.strip()]
        
        return paragraphs if paragraphs else [content.strip()]
    
    def _split_long_paragraph(self, paragraph: str, max_length: int = 2000) -> List[str]:
        """
        Split a very long paragraph at sentence boundaries using spaCy.
        
        Args:
            paragraph: Paragraph text to split
            max_length: Maximum length before splitting (default: 2000 chars)
            
        Returns:
            List of paragraph chunks (split at sentence boundaries)
        """
        if len(paragraph) <= max_length:
            return [paragraph]
        
        doc = self.nlp(paragraph)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        if not sentences:
            return [paragraph]
        
        chunks = []
        current_chunk = ""
        
        for sentence in sentences:
            # If adding this sentence would exceed max_length, start a new chunk
            if current_chunk and len(current_chunk) + len(sentence) + 1 > max_length:
                chunks.append(current_chunk.strip())
                current_chunk = sentence
            else:
                if current_chunk:
                    current_chunk += " " + sentence
                else:
                    current_chunk = sentence
        
        if current_chunk:
            chunks.append(current_chunk.strip())
        
        return chunks if chunks else [paragraph]
    
    def _chunk_by_sentences(self, content: str) -> List[str]:
        """
        Fallback: chunk by sentences when no paragraph breaks are found.
        
        Args:
            content: Document content to chunk
            
        Returns:
            List of sentence-based chunks
        """
        doc = self.nlp(content)
        sentences = [sent.text.strip() for sent in doc.sents if sent.text.strip()]
        
        # Group sentences into chunks (approximately 3-5 sentences per chunk)
        chunks = []
        current_chunk = ""
        sentences_per_chunk = 4
        
        for i, sentence in enumerate(sentences):
            if current_chunk:
                current_chunk += " " + sentence
            else:
                current_chunk = sentence
            
            # Create chunk every N sentences or at the end
            if (i + 1) % sentences_per_chunk == 0 or i == len(sentences) - 1:
                if current_chunk.strip():
                    chunks.append(current_chunk.strip())
                current_chunk = ""
        
        return chunks if chunks else [content.strip()]
    
    def chunk_by_paragraphs(self, content: str) -> List[Dict]:
        """
        Chunk document by paragraphs (1 paragraph = 1 chunk) with entity extraction.
        
        Handles edge cases:
        - Very short paragraphs (<50 chars): merge with next paragraph
        - Very long paragraphs (>2000 chars): split at sentence boundaries
        - No paragraph breaks: fall back to sentence-based chunking
        
        Args:
            content: Full document text to chunk
            
        Returns:
            List of chunk dictionaries with:
            - content: Chunk text
            - entities: List of extracted entities (top N most frequent)
        """
        if not content or not content.strip():
            return []
        
        # Split into paragraphs
        paragraphs = self._split_into_paragraphs(content)
        
        # If no paragraphs found, fall back to sentence-based chunking
        if len(paragraphs) <= 1 and len(content) > 100:
            logger.debug("No paragraph breaks found, using sentence-based chunking")
            sentences = self._chunk_by_sentences(content)
            chunks = []
            for sentence_chunk in sentences:
                entities = self.extract_entities(sentence_chunk)
                filtered_entities = self._filter_top_entities(
                    entities, 
                    settings.max_entities_per_chunk
                )
                chunks.append({
                    "content": sentence_chunk,
                    "entities": filtered_entities
                })
            return chunks
        
        # Process paragraphs
        chunks = []
        i = 0
        
        while i < len(paragraphs):
            paragraph = paragraphs[i].strip()
            
            # Skip empty paragraphs
            if not paragraph:
                i += 1
                continue
            
            # Handle very short paragraphs: merge with next
            if len(paragraph) < 50 and i < len(paragraphs) - 1:
                # Merge with next paragraph
                merged = paragraph + " " + paragraphs[i + 1].strip()
                paragraph = merged
                i += 1  # Skip next paragraph since we merged it
            
            # Handle very long paragraphs: split at sentence boundaries
            if len(paragraph) > 2000:
                sub_chunks = self._split_long_paragraph(paragraph)
                for sub_chunk in sub_chunks:
                    entities = self.extract_entities(sub_chunk)
                    filtered_entities = self._filter_top_entities(
                        entities,
                        settings.max_entities_per_chunk
                    )
                    chunks.append({
                        "content": sub_chunk,
                        "entities": filtered_entities
                    })
            else:
                # Normal paragraph: extract entities
                entities = self.extract_entities(paragraph)
                filtered_entities = self._filter_top_entities(
                    entities,
                    settings.max_entities_per_chunk
                )
                chunks.append({
                    "content": paragraph,
                    "entities": filtered_entities
                })
            
            i += 1
        
        return chunks


# Global semantic chunking service instance
semantic_chunking_service = SemanticChunkingService()

