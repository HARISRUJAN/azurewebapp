"""
Seed initial documents into the system from PDF files.

This script processes PDF documents from the data folder and ingests them
into the system using the ingestion service. Documents are:
1. Extracted from PDF files using PDF service
2. Chunked using LangChain text splitter
3. Embedded using Nomic embeddings
4. Stored in Qdrant vector database
5. Saved to SQLite database

PDF Documents Processed:
- NIST AI Risk Management Framework (nist.ai.100-1.pdf)
- European Union Artificial Intelligence Act (EU AI act.pdf)
"""
import sys
import os
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.models.database import SessionLocal
from app.models.schemas import DocumentIngest
from app.services.ingestion_service import ingestion_service
from app.services.pdf_service import pdf_service


def seed_documents():
    """
    Process and ingest PDF documents from the data folder.
    
    This function:
    1. Locates PDF files in the data folder
    2. Extracts full text from each PDF
    3. Ingests documents into the system (chunking, embedding, storage)
    4. Provides progress indicators during processing
    """
    db = SessionLocal()
    try:
        print("=" * 60)
        print("Seeding documents from PDF files")
        print("=" * 60)
        
        # Check if documents already exist
        from app.models.database import Document
        existing = db.query(Document).filter(Document.title.like("%NIST%")).first()
        if existing:
            print("\n[WARNING] Documents already seeded. Skipping to avoid duplicates.")
            print("   To re-seed, delete existing documents from the database first.")
            return
        
        # Get the data directory path (backend/data/)
        script_dir = Path(__file__).parent
        data_dir = script_dir.parent / "data"
        
        if not data_dir.exists():
            print(f"\n[ERROR] Data directory not found at {data_dir}")
            print("   Please ensure PDF files are in the backend/data/ folder")
            return
        
        # Define PDF documents with metadata
        pdf_documents = [
            {
                "filename": "nist.ai.100-1.pdf",
                "title": "NIST AI Risk Management Framework (AI RMF 1.0)",
                "source": "NIST",
                "url": "https://www.nist.gov/itl/ai-risk-management-framework",
                "metadata": {
                    "type": "framework",
                    "jurisdiction": "US",
                    "year": "2023"
                }
            },
            {
                "filename": "EU AI act.pdf",
                "title": "European Union Artificial Intelligence Act",
                "source": "European Union",
                "url": "https://digital-strategy.ec.europa.eu/en/policies/regulatory-framework-ai",
                "metadata": {
                    "type": "regulation",
                    "jurisdiction": "EU",
                    "year": "2024"
                }
            }
        ]
        
        # Process each PDF document
        processed_count = 0
        for doc_config in pdf_documents:
            pdf_path = data_dir / doc_config["filename"]
            
            if not pdf_path.exists():
                print(f"\n[WARNING] PDF not found: {doc_config['filename']}")
                print(f"   Expected location: {pdf_path}")
                continue
            
            try:
                print(f"\n[PROCESSING] {doc_config['title']}")
                print(f"   File: {doc_config['filename']}")
                
                # Extract text from PDF
                print("   Extracting text from PDF...")
                text_content = pdf_service.extract_text_from_pdf(str(pdf_path))
                
                if not text_content or len(text_content.strip()) < 100:
                    print(f"   [WARNING] Extracted text seems too short ({len(text_content)} chars)")
                    print("   Continuing anyway...")
                
                print(f"   [OK] Extracted {len(text_content):,} characters")
                
                # Create document ingest object
                document = DocumentIngest(
                    title=doc_config["title"],
                    source=doc_config["source"],
                    url=doc_config["url"],
                    content=text_content,
                    metadata=doc_config["metadata"]
                )
                
                # Ingest document (chunking, embedding, storage)
                print("   Ingesting document (chunking, embedding, storing)...")
                ingested_doc = ingestion_service.ingest_document(db, document)
                
                print(f"   [OK] Successfully ingested: {ingested_doc.title}")
                print(f"      Document ID: {ingested_doc.id}")
                processed_count += 1
                
            except FileNotFoundError:
                print(f"   [ERROR] PDF file not found: {pdf_path}")
                continue
            except Exception as e:
                print(f"   [ERROR] Processing {doc_config['filename']}: {e}")
                import traceback
                traceback.print_exc()
                continue
        
        # Summary
        print("\n" + "=" * 60)
        if processed_count > 0:
            print(f"[OK] Successfully processed {processed_count} document(s)")
            print("\nDocuments are now available for querying via the RAG system.")
        else:
            print("[WARNING] No documents were processed.")
            print("   Please check that PDF files exist in backend/data/ folder")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n[ERROR] Error seeding documents: {e}")
        import traceback
        traceback.print_exc()
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_documents()
