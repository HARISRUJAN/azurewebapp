from typing import List, Optional
from qdrant_client import QdrantClient
from qdrant_client.models import Distance, VectorParams, PointStruct, HnswConfigDiff
from app.core.config import settings

class VectorService:
    def __init__(self):
        self.client = None
        self.collection_name = settings.qdrant_collection_name
        self.semantic_collection_name = settings.qdrant_semantic_collection_name
        self._initialized = False
    
    def _init_client(self):
        """Lazy initialization of Qdrant client"""
        if not self._initialized:
            import logging
            logger = logging.getLogger(__name__)
            try:
                # Support both local and cloud Qdrant
                if settings.qdrant_api_key:
                    # Qdrant Cloud with API key
                    logger.debug(f"Initializing Qdrant client with API key at {settings.qdrant_url}")
                    self.client = QdrantClient(
                        url=settings.qdrant_url,
                        api_key=settings.qdrant_api_key
                    )
                else:
                    # Local Qdrant or cloud without API key
                    logger.debug(f"Initializing Qdrant client without API key at {settings.qdrant_url}")
                    self.client = QdrantClient(url=settings.qdrant_url)
                
                # Test connection by getting collections
                try:
                    self.client.get_collections()
                    logger.info(f"Successfully connected to Qdrant at {settings.qdrant_url}")
                except Exception as conn_error:
                    error_type = type(conn_error).__name__
                    error_str = str(conn_error) if str(conn_error) else repr(conn_error)
                    logger.error(f"Failed to connect to Qdrant at {settings.qdrant_url} ({error_type}): {error_str}")
                    
                    # Provide specific error messages
                    if "authentication" in error_str.lower() or "unauthorized" in error_str.lower():
                        raise Exception(f"Qdrant authentication failed ({error_type}: {error_str}). Please check your Qdrant API key.") from conn_error
                    elif "connection" in error_str.lower() or "timeout" in error_str.lower():
                        raise Exception(f"Qdrant connection failed ({error_type}: {error_str}). Please check if Qdrant is accessible at {settings.qdrant_url}") from conn_error
                    else:
                        raise Exception(f"Qdrant connection test failed ({error_type}: {error_str})") from conn_error
                
                self._ensure_collection()
                self._ensure_semantic_collection()
                self._initialized = True
            except Exception as init_error:
                logger.exception(f"Error initializing Qdrant client: {str(init_error)}")
                raise
    
    def _ensure_collection(self):
        """Create collection if it doesn't exist"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.client:
            self._init_client()
        
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.collection_name not in collection_names:
                logger.info(f"Creating Qdrant collection '{self.collection_name}' with 768-dimensional vectors and HNSW index")
                # Configure HNSW index for better search performance
                hnsw_config = HnswConfigDiff(
                    m=settings.qdrant_hnsw_m,
                    ef_construct=settings.qdrant_hnsw_ef_construct
                )
                self.client.create_collection(
                    collection_name=self.collection_name,
                    vectors_config=VectorParams(
                        size=768,  # Nomic embed-text-v1 embedding size (768 dimensions)
                        distance=Distance.COSINE,
                        hnsw_config=hnsw_config
                    )
                )
                logger.info(f"Successfully created Qdrant collection '{self.collection_name}' with HNSW index (m={settings.qdrant_hnsw_m}, ef_construct={settings.qdrant_hnsw_ef_construct})")
            else:
                # Verify collection configuration matches our requirements
                collection_info = self.client.get_collection(self.collection_name)
                logger.debug(f"Qdrant collection '{self.collection_name}' already exists")
                logger.debug(f"Collection config: vectors={collection_info.config.params.vectors.size}, distance={collection_info.config.params.vectors.distance}")
                
                # Verify vector size matches (768 for Nomic)
                if hasattr(collection_info.config.params.vectors, 'size'):
                    vector_size = collection_info.config.params.vectors.size
                    if vector_size != 768:
                        logger.warning(f"Collection vector size mismatch: expected 768, got {vector_size}. This may cause issues.")
        except Exception as e:
            error_type = type(e).__name__
            error_str = str(e) if str(e) else repr(e)
            logger.exception(f"Error ensuring Qdrant collection exists ({error_type}): {error_str}")
            raise Exception(f"Failed to ensure Qdrant collection '{self.collection_name}': {error_str}") from e
    
    def _ensure_semantic_collection(self):
        """Create semantic collection if it doesn't exist"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self.client:
            self._init_client()
        
        try:
            collections = self.client.get_collections().collections
            collection_names = [col.name for col in collections]
            
            if self.semantic_collection_name not in collection_names:
                logger.info(f"Creating Qdrant semantic collection '{self.semantic_collection_name}' with 768-dimensional vectors and HNSW index")
                # Configure HNSW index for better search performance
                hnsw_config = HnswConfigDiff(
                    m=settings.qdrant_hnsw_m,
                    ef_construct=settings.qdrant_hnsw_ef_construct
                )
                self.client.create_collection(
                    collection_name=self.semantic_collection_name,
                    vectors_config=VectorParams(
                        size=768,  # Nomic embed-text-v1 embedding size (768 dimensions)
                        distance=Distance.COSINE,
                        hnsw_config=hnsw_config
                    )
                )
                logger.info(f"Successfully created Qdrant semantic collection '{self.semantic_collection_name}' with HNSW index (m={settings.qdrant_hnsw_m}, ef_construct={settings.qdrant_hnsw_ef_construct})")
            else:
                # Verify collection configuration matches our requirements
                collection_info = self.client.get_collection(self.semantic_collection_name)
                logger.debug(f"Qdrant semantic collection '{self.semantic_collection_name}' already exists")
                logger.debug(f"Collection config: vectors={collection_info.config.params.vectors.size}, distance={collection_info.config.params.vectors.distance}")
                
                # Verify vector size matches (768 for Nomic)
                if hasattr(collection_info.config.params.vectors, 'size'):
                    vector_size = collection_info.config.params.vectors.size
                    if vector_size != 768:
                        logger.warning(f"Semantic collection vector size mismatch: expected 768, got {vector_size}. This may cause issues.")
        except Exception as e:
            error_type = type(e).__name__
            error_str = str(e) if str(e) else repr(e)
            logger.exception(f"Error ensuring Qdrant semantic collection exists ({error_type}): {error_str}")
            raise Exception(f"Failed to ensure Qdrant semantic collection '{self.semantic_collection_name}': {error_str}") from e
    
    def add_embeddings(
        self,
        embeddings: List[List[float]],
        ids: List[str],
        payloads: List[dict],
        collection_name: Optional[str] = None
    ):
        """
        Add embeddings to Qdrant vector database.
        
        Args:
            embeddings: List of embedding vectors (each is 768-dimensional for Nomic)
            ids: List of point IDs (UUIDs as strings)
            payloads: List of metadata dictionaries for each point
            collection_name: Optional collection name (defaults to semantic collection)
        """
        import logging
        logger = logging.getLogger(__name__)
        
        if not self._initialized:
            self._init_client()
        
        if not embeddings or not ids or not payloads:
            logger.warning("Empty embeddings, ids, or payloads provided to add_embeddings")
            return
        
        if len(embeddings) != len(ids) or len(ids) != len(payloads):
            raise ValueError(f"Mismatch in lengths: embeddings={len(embeddings)}, ids={len(ids)}, payloads={len(payloads)}")
        
        logger.debug(f"Preparing {len(embeddings)} points for Qdrant upsert")
        
        points = [
            PointStruct(
                id=point_id,
                vector=embedding,
                payload=payload
            )
            for point_id, embedding, payload in zip(ids, embeddings, payloads)
        ]
        
        try:
            target_collection = collection_name or self.semantic_collection_name
            logger.debug(f"Connecting to Qdrant at {settings.qdrant_url}")
            self.client.upsert(
                collection_name=target_collection,
                points=points
            )
            logger.info(f"Successfully upserted {len(points)} points to Qdrant collection '{target_collection}'")
        except Exception as e:
            error_type = type(e).__name__
            error_details = str(e) if str(e) else repr(e)
            logger.exception(f"Qdrant upsert error ({error_type}): {error_details}")
            
            # Provide more specific error messages based on error type
            if "Connection" in error_type or "connect" in error_details.lower() or "timeout" in error_details.lower():
                raise Exception(f"Qdrant connection failed ({error_type}: {error_details}). Please check if Qdrant is accessible at {settings.qdrant_url}") from e
            elif "collection" in error_details.lower() and "not found" in error_details.lower():
                target_collection = collection_name or self.semantic_collection_name
                raise Exception(f"Qdrant collection '{target_collection}' not found ({error_type}: {error_details}). Please ensure the collection exists.") from e
            elif "authentication" in error_details.lower() or "unauthorized" in error_details.lower() or "forbidden" in error_details.lower():
                raise Exception(f"Qdrant authentication failed ({error_type}: {error_details}). Please check your Qdrant API key and permissions.") from e
            elif "rate limit" in error_details.lower() or "quota" in error_details.lower():
                raise Exception(f"Qdrant rate limit or quota exceeded ({error_type}: {error_details}). Please check your Qdrant Cloud plan limits.") from e
            else:
                raise Exception(f"Qdrant operation failed ({error_type}: {error_details})") from e
    
    def search(
        self,
        query_embedding: List[float],
        top_k: int = 5,
        filter_conditions: Optional[dict] = None,
        collection_name: Optional[str] = None
    ) -> List[dict]:
        """Search for similar embeddings"""
        import logging
        logger = logging.getLogger(__name__)
        
        if not self._initialized:
            self._init_client()
        
        target_collection = collection_name or self.semantic_collection_name
        
        # Ensure the collection exists before searching
        if target_collection == self.semantic_collection_name:
            self._ensure_semantic_collection()
        elif target_collection == self.collection_name:
            self._ensure_collection()
        
        try:
            # Check if collection has any points
            collection_count = self.client.count(target_collection).count
            if collection_count == 0:
                logger.warning(f"Collection '{target_collection}' exists but is empty. No documents have been ingested yet.")
                return []
            
            search_result = self.client.search(
                collection_name=target_collection,
                query_vector=query_embedding,
                limit=top_k,
                query_filter=filter_conditions
            )
            
            results = []
            for result in search_result:
                results.append({
                    "id": result.id,
                    "score": result.score,
                    "payload": result.payload
                })
            
            logger.debug(f"Search returned {len(results)} results from collection '{target_collection}'")
            return results
        
        except Exception as e:
            error_type = type(e).__name__
            error_details = str(e) if str(e) else repr(e)
            logger.exception(f"Qdrant search error ({error_type}): {error_details}")
            
            # Provide more specific error messages
            if "collection" in error_details.lower() and "not found" in error_details.lower():
                raise Exception(f"Qdrant collection '{target_collection}' not found. Please ensure documents have been ingested.") from e
            elif "connection" in error_details.lower() or "timeout" in error_details.lower():
                raise Exception(f"Qdrant connection failed ({error_type}: {error_details}). Please check if Qdrant is accessible at {settings.qdrant_url}") from e
            else:
                raise Exception(f"Qdrant search failed ({error_type}: {error_details})") from e
    
    def delete_points(self, point_ids: List[str], collection_name: Optional[str] = None):
        """Delete points by IDs"""
        if not self._initialized:
            self._init_client()
        target_collection = collection_name or self.semantic_collection_name
        self.client.delete(
            collection_name=target_collection,
            points_selector=point_ids
        )


# Lazy initialization - will connect when first used
vector_service = VectorService()

