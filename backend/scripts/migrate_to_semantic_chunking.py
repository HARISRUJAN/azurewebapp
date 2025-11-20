"""
Migration script to re-chunk existing documents using semantic chunking.

This script:
1. Reads all documents from the database
2. Re-chunks them using semantic chunking (spaCy paragraph-based)
3. Re-embeds and stores in the new semantic collection
4. Optionally deletes old collection points
5. Updates chunk records in the database

Usage:
    python backend/scripts/migrate_to_semantic_chunking.py [--delete-old] [--dry-run]
"""

import sys
import os
import argparse
import logging
from pathlib import Path

# Add backend to path
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from sqlalchemy.orm import Session
from app.models.database import get_db, Document, Chunk
from app.services.rag_service import rag_service
from app.services.vector_service import vector_service
from app.core.config import settings
from app.models.schemas import DocumentIngest

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


def migrate_document(db: Session, document: Document, delete_old: bool = False, dry_run: bool = False):
    """
    Migrate a single document to semantic chunking.
    
    Args:
        db: Database session
        document: Document to migrate
        delete_old: Whether to delete old collection points
        dry_run: If True, don't actually make changes
    """
    logger.info(f"Migrating document ID {document.id}: {document.title}")
    
    try:
        # Step 1: Re-chunk using semantic chunking
        logger.debug(f"Re-chunking document {document.id} using semantic chunking")
        semantic_chunks = rag_service.chunk_document(document.content)
        logger.info(f"Document {document.id} chunked into {len(semantic_chunks)} semantic chunks")
        
        if not semantic_chunks:
            logger.warning(f"Document {document.id} resulted in zero chunks, skipping")
            return False
        
        if dry_run:
            logger.info(f"[DRY RUN] Would migrate document {document.id} with {len(semantic_chunks)} chunks")
            return True
        
        # Step 2: Delete old chunks from database and Qdrant
        logger.debug(f"Deleting old chunks for document {document.id}")
        old_chunks = db.query(Chunk).filter(Chunk.document_id == document.id).all()
        old_point_ids = [chunk.embedding_id for chunk in old_chunks if chunk.embedding_id]
        
        if old_point_ids and delete_old:
            try:
                # Delete from old collection
                vector_service.delete_points(
                    old_point_ids,
                    collection_name=settings.qdrant_collection_name
                )
                logger.debug(f"Deleted {len(old_point_ids)} points from old collection")
            except Exception as e:
                logger.warning(f"Error deleting old points (may not exist): {str(e)}")
        
        # Delete chunk records from database
        db.query(Chunk).filter(Chunk.document_id == document.id).delete()
        db.flush()
        
        # Step 3: Store new semantic chunks
        logger.debug(f"Storing {len(semantic_chunks)} semantic chunks for document {document.id}")
        chunk_ids = rag_service.store_document_chunks(
            document_id=document.id,
            title=document.title,
            source=document.source,
            url=document.url,
            chunks=semantic_chunks,
            chunk_metadata=None
        )
        
        # Step 4: Store new chunk records in database
        import json
        for idx, (chunk_dict, point_id) in enumerate(zip(semantic_chunks, chunk_ids)):
            chunk_content = chunk_dict["content"]
            chunk_entities = chunk_dict.get("entities", [])
            
            chunk_meta = {}
            if document.document_metadata:
                try:
                    chunk_meta = json.loads(document.document_metadata)
                except:
                    pass
            if chunk_entities:
                chunk_meta["entities"] = chunk_entities
            
            db_chunk = Chunk(
                document_id=document.id,
                content=chunk_content,
                chunk_index=idx,
                embedding_id=point_id,
                chunk_metadata=json.dumps(chunk_meta) if chunk_meta else None
            )
            db.add(db_chunk)
        
        db.commit()
        logger.info(f"✓ Successfully migrated document {document.id} with {len(semantic_chunks)} semantic chunks")
        return True
        
    except Exception as e:
        logger.exception(f"Error migrating document {document.id}: {str(e)}")
        db.rollback()
        return False


def main():
    parser = argparse.ArgumentParser(description="Migrate existing documents to semantic chunking")
    parser.add_argument(
        "--delete-old",
        action="store_true",
        help="Delete points from old collection after migration"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be migrated without making changes"
    )
    args = parser.parse_args()
    
    logger.info("=" * 60)
    logger.info("Semantic Chunking Migration Script")
    logger.info("=" * 60)
    
    if args.dry_run:
        logger.info("DRY RUN MODE - No changes will be made")
    
    if args.delete_old:
        logger.warning("Will delete old collection points after migration")
    
    db = next(get_db())
    
    try:
        # Get all documents
        documents = db.query(Document).all()
        logger.info(f"Found {len(documents)} documents to migrate")
        
        if not documents:
            logger.info("No documents to migrate")
            return
        
        # Initialize services
        logger.info("Initializing RAG and vector services...")
        _ = rag_service  # Initialize RAG service
        vector_service._init_client()  # Initialize vector service
        logger.info("Services initialized")
        
        # Migrate each document
        success_count = 0
        fail_count = 0
        
        for doc in documents:
            if migrate_document(db, doc, delete_old=args.delete_old, dry_run=args.dry_run):
                success_count += 1
            else:
                fail_count += 1
        
        logger.info("=" * 60)
        logger.info(f"Migration complete!")
        logger.info(f"  Success: {success_count}")
        logger.info(f"  Failed: {fail_count}")
        logger.info(f"  Total: {len(documents)}")
        logger.info("=" * 60)
        
        if not args.dry_run:
            # Show collection stats
            try:
                legacy_count = vector_service.client.count(settings.qdrant_collection_name).count
                semantic_count = vector_service.client.count(settings.qdrant_semantic_collection_name).count
                logger.info(f"\nCollection Statistics:")
                logger.info(f"  Legacy collection ({settings.qdrant_collection_name}): {legacy_count} points")
                logger.info(f"  Semantic collection ({settings.qdrant_semantic_collection_name}): {semantic_count} points")
            except Exception as e:
                logger.warning(f"Could not get collection stats: {str(e)}")
        
    except Exception as e:
        logger.exception(f"Fatal error during migration: {str(e)}")
        return 1
    finally:
        db.close()
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

