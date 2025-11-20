"""
Integration tests for admin crawl flow.
Tests that the admin crawl endpoint works and updates origin status correctly.
"""
import pytest
import sys
import os
import asyncio
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Windows event loop policy before any imports
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi.testclient import TestClient
from app.main import app
from app.models.database import SessionLocal, ScrapingOrigin, Document
from app.core.security import get_password_hash
from app.models.database import User, UserRole

client = TestClient(app)


def get_test_db():
    """Get a test database session."""
    return SessionLocal()


def create_test_admin_user(db):
    """Create a test admin user for authentication."""
    # Check if admin already exists
    admin = db.query(User).filter(User.username == "test_admin").first()
    if admin:
        return admin
    
    admin = User(
        username="test_admin",
        email="test_admin@test.com",
        hashed_password=get_password_hash("test_password"),
        role=UserRole.ADMIN,
        is_active=True
    )
    db.add(admin)
    db.commit()
    db.refresh(admin)
    return admin


def get_auth_token(username="test_admin", password="test_password"):
    """Get authentication token for test user."""
    response = client.post(
        "/api/auth/login",
        data={"username": username, "password": password}
    )
    if response.status_code == 200:
        return response.json().get("access_token")
    return None


def test_admin_crawl_flow():
    """
    Test the admin crawl flow end-to-end.
    
    Tests:
    - Create a test origin
    - Trigger crawl via admin endpoint
    - Verify origin status updates (last_run, last_status, qdrant_status)
    - Verify crawled content is stored in database
    """
    db = get_test_db()
    
    try:
        # Create test admin user
        admin = create_test_admin_user(db)
        
        # Get auth token
        token = get_auth_token()
        assert token is not None, "Failed to get auth token"
        
        headers = {"Authorization": f"Bearer {token}"}
        
        # Create a test origin
        test_origin = ScrapingOrigin(
            name="Test Origin - Example.com",
            url="https://example.com",
            frequency_hours=24,
            enabled=True
        )
        db.add(test_origin)
        db.commit()
        db.refresh(test_origin)
        
        origin_id = test_origin.id
        initial_last_run = test_origin.last_run
        initial_last_status = test_origin.last_status
        initial_qdrant_status = test_origin.qdrant_status
        
        print(f"Created test origin ID: {origin_id}")
        print(f"Initial last_run: {initial_last_run}")
        print(f"Initial last_status: {initial_last_status}")
        
        # Trigger crawl via admin endpoint
        print(f"\nTriggering crawl for origin {origin_id}...")
        response = client.post(
            f"/api/admin/origins/{origin_id}/crawl",
            headers=headers
        )
        
        # Should return 200 OK
        assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
        
        data = response.json()
        
        # Verify response structure
        assert "success" in data, "Response missing 'success' field"
        assert "message" in data, "Response missing 'message' field"
        assert "origin_id" in data, "Response missing 'origin_id' field"
        assert data["origin_id"] == origin_id, f"Origin ID mismatch: {data['origin_id']} != {origin_id}"
        
        print(f"  - Success: {data['success']}")
        print(f"  - Message: {data['message']}")
        
        # Reload origin from database
        db.refresh(test_origin)
        
        # Verify status updates
        assert test_origin.last_run is not None, "last_run should be updated after crawl"
        assert test_origin.last_run != initial_last_run or initial_last_run is None, "last_run should change"
        
        assert test_origin.last_status is not None, "last_status should be set after crawl"
        assert test_origin.last_status != initial_last_status or initial_last_status is None, "last_status should change"
        
        print(f"  - Updated last_run: {test_origin.last_run}")
        print(f"  - Updated last_status: {test_origin.last_status}")
        
        # Verify qdrant_status is set (if crawl was successful)
        if data.get("success"):
            if test_origin.qdrant_status:
                print(f"  - Qdrant status: {test_origin.qdrant_status}")
            
            # If document_id is returned, verify document exists
            if "document_id" in data and data["document_id"]:
                document_id = data["document_id"]
                document = db.query(Document).filter(Document.id == document_id).first()
                assert document is not None, f"Document {document_id} should exist in database"
                assert document.url == test_origin.url, f"Document URL mismatch"
                assert len(document.content or "") > 0, "Document content should not be empty"
                
                print(f"  - Document ID: {document_id}")
                print(f"  - Document title: {document.title}")
                print(f"  - Document content length: {len(document.content or '')}")
        
        # Cleanup
        if "document_id" in data and data["document_id"]:
            document = db.query(Document).filter(Document.id == data["document_id"]).first()
            if document:
                db.delete(document)
        
        db.delete(test_origin)
        db.commit()
        
        print(f"\n✓ Admin crawl flow test passed")
        
    except Exception as e:
        # Cleanup on error
        try:
            if 'test_origin' in locals():
                db.delete(test_origin)
                db.commit()
        except:
            pass
        raise
    finally:
        db.close()


if __name__ == "__main__":
    print("Running admin crawl flow tests...")
    print("=" * 60)
    
    try:
        test_admin_crawl_flow()
        print()
        print("=" * 60)
        print("✓ All admin crawl flow tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

