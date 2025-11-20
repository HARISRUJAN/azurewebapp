from pydantic_settings import BaseSettings
from typing import List
from pydantic import Field, computed_field, field_validator
import os


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables.
    All sensitive values must be provided via environment variables in production.
    """
    
    # Database
    # For production, use PostgreSQL: postgresql://user:password@host:port/dbname
    database_url: str = Field(
        default="sqlite:///./aigov.db",
        description="Database connection URL. Use PostgreSQL for production."
    )
    
    # JWT - REQUIRED in production
    secret_key: str = Field(
        default="",
        description="Secret key for JWT token signing. REQUIRED in production. Generate with: openssl rand -hex 32"
    )
    algorithm: str = Field(default="HS256", description="JWT signing algorithm")
    access_token_expire_minutes: int = Field(default=30, description="JWT token expiration time in minutes")
    
    # LLM Provider Configuration
    # Groq is used for answer generation (primary) - REQUIRED
    groq_api_key: str = Field(
        default="",
        description="Groq API key for answer generation. REQUIRED. Get from https://console.groq.com/keys"
    )
    
    # OpenAI API key (optional - only needed if using OpenAI as fallback for generation)
    # Note: Embeddings use Nomic (sentence-transformers) - no API key needed
    openai_api_key: str = Field(
        default="",
        description="OpenAI API key (optional, only for fallback LLM generation). Embeddings use Nomic locally."
    )
    
    # Qdrant Vector Database
    qdrant_url: str = Field(
        default="http://localhost:6333",
        description="Qdrant vector database URL. Use Qdrant Cloud URL for production."
    )
    qdrant_api_key: str = Field(
        default="",
        description="Qdrant API key (required for Qdrant Cloud, optional for local)"
    )
    qdrant_collection_name: str = Field(
        default="aigov_documents",
        description="Qdrant collection name for document embeddings (legacy)"
    )
    qdrant_semantic_collection_name: str = Field(
        default="aigov_documents_semantic",
        description="Qdrant collection name for semantic chunked document embeddings"
    )
    
    # spaCy Configuration
    spacy_model_name: str = Field(
        default="en_core_web_md",
        description="spaCy model name for semantic chunking and entity extraction"
    )
    max_entities_per_chunk: int = Field(
        default=10,
        description="Maximum number of entities to extract per chunk (top N most frequent)"
    )
    
    # Qdrant HNSW Index Configuration
    qdrant_hnsw_m: int = Field(
        default=16,
        description="HNSW index parameter M: number of bi-directional links for each node (default: 16, range: 4-64)"
    )
    qdrant_hnsw_ef_construct: int = Field(
        default=100,
        description="HNSW index parameter ef_construct: size of dynamic candidate list during construction (default: 100, should be >= M)"
    )
    
    # CORS - stored as string in .env (CORS_ORIGINS), parsed to list
    cors_origins_str: str = Field(
        default="http://localhost:5173,http://localhost:3000",
        alias="CORS_ORIGINS",
        description="Comma-separated list of allowed CORS origins"
    )
    
    # Crawling Configuration
    crawl_max_depth: int = Field(
        default=1,
        description="Maximum crawl depth (0 = no limit, 1 = single page only, 2+ = follow links)"
    )
    crawl_max_pages_per_run: int = Field(
        default=30,
        description="Maximum number of pages to crawl per origin per run"
    )
    crawl_timeout_seconds: int = Field(
        default=15,
        description="Timeout in seconds for each URL crawl"
    )
    crawl_retry_attempts: int = Field(
        default=2,
        description="Maximum number of retry attempts for transient errors"
    )
    crawl_retry_delay_seconds: float = Field(
        default=1.0,
        description="Initial retry delay in seconds (exponential backoff)"
    )
    crawl_delay_between_requests: float = Field(
        default=1.0,
        description="Delay in seconds between requests for politeness"
    )
    crawl_respect_robots_txt: bool = Field(
        default=True,
        description="Whether to respect robots.txt rules"
    )
    crawl_user_agent: str = Field(
        default="aigov-crawler/1.0",
        description="User agent string for crawling"
    )
    crawl_allowed_paths_str: str = Field(
        default="",
        alias="CRAWL_ALLOWED_PATHS",
        description="Comma-separated list of URL path patterns to allow (regex patterns). Empty = allow all paths."
    )
    crawl_excluded_paths_str: str = Field(
        default="",
        alias="CRAWL_EXCLUDED_PATHS",
        description="Comma-separated list of URL path patterns to exclude (regex patterns). Common exclusions: /api/, /admin/, /login/, etc."
    )
    
    # Search API Configuration
    perplexity_api_key: str = Field(
        default="",
        description="Perplexity API key for query-seeded crawling. Get from https://www.perplexity.ai/settings/api"
    )
    search_api_provider: str = Field(
        default="perplexity",
        description="Search API provider: 'perplexity' or 'google'"
    )
    google_search_api_key: str = Field(
        default="",
        description="Google Custom Search API key (fallback for search-seeded crawling)"
    )
    google_search_engine_id: str = Field(
        default="",
        description="Google Custom Search Engine ID (fallback for search-seeded crawling)"
    )
    
    @computed_field
    @property
    def cors_origins(self) -> List[str]:
        """Parse CORS origins from comma-separated string"""
        return [origin.strip() for origin in self.cors_origins_str.split(',') if origin.strip()]
    
    @computed_field
    @property
    def crawl_allowed_paths(self) -> List[str]:
        """Parse allowed crawl paths from comma-separated string"""
        if not self.crawl_allowed_paths_str:
            return []
        return [path.strip() for path in self.crawl_allowed_paths_str.split(',') if path.strip()]
    
    @computed_field
    @property
    def crawl_excluded_paths(self) -> List[str]:
        """Parse excluded crawl paths from comma-separated string"""
        if not self.crawl_excluded_paths_str:
            return []
        return [path.strip() for path in self.crawl_excluded_paths_str.split(',') if path.strip()]
    
    @field_validator('secret_key')
    @classmethod
    def validate_secret_key(cls, v: str) -> str:
        """Validate secret key is set in production"""
        if not v or v == "":
            # Only warn in production, allow empty for development
            env = os.getenv("ENVIRONMENT", "development")
            if env == "production":
                raise ValueError(
                    "SECRET_KEY is required in production. "
                    "Set it via environment variable or .env file. "
                    "Generate with: openssl rand -hex 32"
                )
        elif len(v) < 32:
            raise ValueError("must be at least 32 characters long for security")
        return v
    
    @field_validator('groq_api_key')
    @classmethod
    def validate_groq_key(cls, v: str) -> str:
        """Validate Groq API key is set"""
        if not v or v == "":
            env = os.getenv("ENVIRONMENT", "development")
            if env == "production":
                raise ValueError(
                    "GROQ_API_KEY is required in production. "
                    "Get your API key from https://console.groq.com/keys"
                )
        return v
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()

