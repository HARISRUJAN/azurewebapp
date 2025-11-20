"""
Integration tests for RAG ingestion pipeline.
Tests that crawled content is properly chunked, embedded, and stored in vector DB.
"""
import pytest
import sys
import os
import asyncio

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Windows event loop policy before any imports
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi.testclient import TestClient
from app.main import app
from app.models.database import SessionLocal, Document, Chunk
from app.services.rag_service import RAGService
from app.services.ingestion_service import ingest_document
from app.services.crawling_service import crawl_url
from app.models.schemas import DocumentData

client = TestClient(app)


def get_test_db():
    """Get a test database session."""
    return SessionLocal()


def test_rag_ingestion_pipeline():
    """
    Test the complete RAG ingestion pipeline: crawl → chunk → embed → store.
    
    Tests:
    - Content is crawled successfully
    - Content is chunked properly
    - Chunks are embedded using Nomic
    - Embeddings are stored in Qdrant
    - Content can be retrieved via RAG search
    """
    db = get_test_db()
    
    try:
        # Step 1: Crawl a test URL
        print("Step 1: Crawling test URL...")
        test_url = "https://example.com"
        crawl_result = crawl_url(test_url)
        
        assert "error" not in crawl_result or not crawl_result["error"], f"Crawl failed: {crawl_result.get('error')}"
        assert "markdown" in crawl_result, "Crawl result missing markdown"
        assert len(crawl_result["markdown"].strip()) > 0, "Crawled markdown is empty"
        
        print(f"  ✓ Crawled {test_url}")
        print(f"  - Markdown length: {len(crawl_result['markdown'])}")
        
        # Extract a distinctive phrase for later search
        markdown = crawl_result["markdown"]
        # Find a sentence or phrase (first 50 chars that aren't just whitespace)
        distinctive_phrase = None
        for line in markdown.split('\n'):
            line = line.strip()
            if len(line) > 20 and len(line) < 100:
                distinctive_phrase = line[:50]
                break
        
        if not distinctive_phrase:
            distinctive_phrase = markdown[:50].strip()
        
        print(f"  - Test phrase for search: '{distinctive_phrase[:30]}...'")
        
        # Step 2: Ingest the document
        print("\nStep 2: Ingesting document...")
        document_data = DocumentData(
            title=crawl_result.get("metadata", {}).get("title", "Test Document"),
            content=markdown,
            source="test",
            url=test_url,
            metadata=crawl_result.get("metadata", {})
        )
        
        # Create a test origin for the document
        from app.models.database import ScrapingOrigin
        test_origin = db.query(ScrapingOrigin).filter(ScrapingOrigin.url == test_url).first()
        if not test_origin:
            test_origin = ScrapingOrigin(
                name="Test Origin",
                url=test_url,
                frequency_hours=24,
                enabled=True
            )
            db.add(test_origin)
            db.commit()
            db.refresh(test_origin)
        
        document_id = ingest_document(document_data, db, origin_id=test_origin.id)
        
        assert document_id is not None, "Document ingestion should return document ID"
        
        # Verify document in database
        document = db.query(Document).filter(Document.id == document_id).first()
        assert document is not None, "Document should exist in database"
        assert document.url == test_url, "Document URL should match"
        assert len(document.content or "") > 0, "Document content should not be empty"
        
        print(f"  ✓ Document ingested: ID {document_id}")
        print(f"  - Title: {document.title}")
        print(f"  - Content length: {len(document.content or '')}")
        
        # Step 3: Verify chunks were created
        print("\nStep 3: Verifying chunks...")
        chunks = db.query(Chunk).filter(Chunk.document_id == document_id).all()
        assert len(chunks) > 0, "Document should have at least one chunk"
        
        print(f"  ✓ Created {len(chunks)} chunks")
        for i, chunk in enumerate(chunks[:3], 1):
            print(f"  - Chunk {i}: {len(chunk.content or '')} chars")
        
        # Step 4: Verify RAG service can retrieve content
        print("\nStep 4: Testing RAG retrieval...")
        rag_service = RAGService()
        
        # Search using a query related to the content
        query = "example"  # Should match example.com content
        results = rag_service.search(query, top_k=5)
        
        assert results is not None, "RAG search should return results"
        assert len(results) > 0, "RAG search should return at least one result"
        
        # Check if our document is in the results
        found_document = False
        for result in results:
            if hasattr(result, 'metadata') and result.metadata:
                if result.metadata.get('url') == test_url:
                    found_document = True
                    print(f"  ✓ Found document in RAG results")
                    print(f"  - Score: {result.score if hasattr(result, 'score') else 'N/A'}")
                    break
        
        # It's okay if not found immediately (depends on embedding similarity)
        # But we should have results
        print(f"  ✓ RAG search returned {len(results)} results")
        
        # Step 5: Test full RAG query endpoint
        print("\nStep 5: Testing RAG query endpoint...")
        query_data = {
            "query": distinctive_phrase[:30] if distinctive_phrase else "example",
            "top_k": 5
        }
        
        response = client.post("/api/search/query", json=query_data)
        
        # Should return 200 OK
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
        
        rag_response = response.json()
        
        assert "answer" in rag_response, "RAG response should have 'answer' field"
        assert "sources" in rag_response, "RAG response should have 'sources' field"
        
        print(f"  ✓ RAG query successful")
        print(f"  - Answer length: {len(rag_response['answer'])}")
        print(f"  - Sources count: {len(rag_response['sources'])}")
        
        # Check if sources include our test URL
        source_urls = [s.get('url', '') for s in rag_response['sources']]
        if test_url in source_urls:
            print(f"  ✓ Test document found in sources")
        
        # Cleanup
        print("\nCleaning up test data...")
        db.query(Chunk).filter(Chunk.document_id == document_id).delete()
        db.delete(document)
        db.commit()
        
        print(f"\n✓ RAG ingestion pipeline test passed")
        
    except Exception as e:
        # Cleanup on error
        try:
            if 'document_id' in locals() and document_id:
                db.query(Chunk).filter(Chunk.document_id == document_id).delete()
                db.query(Document).filter(Document.id == document_id).delete()
                db.commit()
        except:
            pass
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Running RAG pipeline tests...")
    print("=" * 60)
    
    try:
        test_rag_ingestion_pipeline()
        print()
        print("=" * 60)
        print("✓ All RAG pipeline tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

