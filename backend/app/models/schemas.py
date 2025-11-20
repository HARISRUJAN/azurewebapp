from pydantic import BaseModel, EmailStr
from typing import Optional, List, Dict
from datetime import datetime
from app.models.database import UserRole


# Auth schemas
class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    username: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: int
    username: str
    email: str
    role: UserRole
    is_active: bool
    
    class Config:
        from_attributes = True


# Scraping Origin schemas
class ScrapingOriginBase(BaseModel):
    name: str
    url: str
    frequency_hours: int = 24
    enabled: bool = True


class ScrapingOriginCreate(ScrapingOriginBase):
    pass


class ScrapingOriginUpdate(BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    frequency_hours: Optional[int] = None
    enabled: Optional[bool] = None


class ScrapingOriginResponse(ScrapingOriginBase):
    id: int
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None
    qdrant_status: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True


# Document schemas
class DocumentBase(BaseModel):
    title: str
    source: str
    url: Optional[str] = None
    content: str
    metadata: Optional[str] = None


class DocumentCreate(DocumentBase):
    origin_id: Optional[int] = None


class DocumentResponse(DocumentBase):
    id: int
    ingestion_date: datetime
    origin_id: Optional[int] = None
    
    class Config:
        from_attributes = True


# Chunk schemas
class ChunkResponse(BaseModel):
    id: int
    document_id: int
    content: str
    chunk_index: int
    metadata: Optional[str] = None
    
    class Config:
        from_attributes = True


# RAG schemas
class DocumentChunk(BaseModel):
    content: str
    document_title: str
    document_source: str
    document_url: Optional[str] = None
    chunk_index: int
    entities: Optional[List[Dict]] = None  # Extracted entities from spaCy NER
    metadata: Optional[dict] = None


class RAGQuery(BaseModel):
    question: str
    top_k: int = 5


class RAGResponse(BaseModel):
    answer: str
    citations: List[DocumentChunk]


# Ingestion schemas
class DocumentIngest(BaseModel):
    title: str
    source: str
    url: Optional[str] = None
    content: str
    metadata: Optional[dict] = None


# Health schemas
class OriginStatus(BaseModel):
    origin_id: int
    origin_name: str
    last_run: Optional[datetime] = None
    last_status: Optional[str] = None
    qdrant_status: Optional[str] = None
    enabled: bool


class QdrantHealth(BaseModel):
    connected: bool
    url: str
    collection_name: str
    collection_exists: bool
    points_count: Optional[int] = None
    vector_size: Optional[int] = None
    error: Optional[str] = None


class QdrantCollectionsHealth(BaseModel):
    """Health status for both Qdrant collections"""
    connected: bool
    url: str
    legacy_collection: Optional[QdrantHealth] = None  # Old collection (aigov_documents)
    semantic_collection: Optional[QdrantHealth] = None  # New semantic collection
    error: Optional[str] = None


class SystemHealth(BaseModel):
    status: str
    origins: List[OriginStatus]
    qdrant: Optional[QdrantHealth] = None  # Legacy: single collection
    qdrant_collections: Optional[QdrantCollectionsHealth] = None  # New: both collections

