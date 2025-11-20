"""
Integration tests for Crawl4AI endpoints.
Tests that crawling works end-to-end without NotImplementedError.
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

client = TestClient(app)


def test_simple_html_crawl():
    """
    Smoke test: Verify that crawling a simple HTML page works.
    
    Tests:
    - API endpoint responds successfully
    - Response contains url, markdown, metadata
    - No NotImplementedError occurs
    - Markdown content is non-empty
    """
    response = client.get("/api/crawl?url=https://example.com")
    
    # Should return 200 OK
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    
    # Verify response structure
    assert "url" in data, "Response missing 'url' field"
    assert data["url"] == "https://example.com", f"URL mismatch: {data['url']}"
    
    assert "markdown" in data, "Response missing 'markdown' field"
    assert isinstance(data["markdown"], str), "Markdown should be a string"
    assert len(data["markdown"].strip()) > 0, "Markdown should not be empty"
    
    assert "metadata" in data, "Response missing 'metadata' field"
    assert isinstance(data["metadata"], dict), "Metadata should be a dictionary"
    
    # Verify metadata has title
    if "title" in data["metadata"]:
        assert isinstance(data["metadata"]["title"], str), "Title should be a string"
        assert len(data["metadata"]["title"].strip()) > 0, "Title should not be empty"
    
    # Verify no error field (or error is None/empty)
    if "error" in data:
        assert not data["error"] or data["error"] == "", f"Unexpected error: {data['error']}"
    
    print(f"✓ Simple HTML crawl test passed")
    print(f"  - URL: {data['url']}")
    print(f"  - Markdown length: {len(data['markdown'])}")
    print(f"  - Title: {data['metadata'].get('title', 'N/A')}")


def test_indiaai_pdf_crawl():
    """
    Test crawling the IndiaAI PDF to verify PDF handling works.
    
    Tests:
    - PDF URL can be crawled
    - Response contains readable content (not empty, not random bytes)
    - Metadata includes PDF-related information
    """
    pdf_url = "https://indiaai.s3.ap-south-1.amazonaws.com/docs/guidelines-governance.pdf"
    
    response = client.get(f"/api/crawl?url={pdf_url}")
    
    # Should return 200 OK
    assert response.status_code == 200, f"Expected 200, got {response.status_code}. Response: {response.text}"
    
    data = response.json()
    
    # Verify response structure
    assert "url" in data, "Response missing 'url' field"
    assert pdf_url in data["url"], f"URL mismatch: {data['url']}"
    
    # PDF should have content (markdown or text)
    has_content = False
    content_length = 0
    
    if "markdown" in data and data["markdown"]:
        has_content = True
        content_length = len(data["markdown"])
    elif "text" in data and data["text"]:
        has_content = True
        content_length = len(data["text"])
    
    assert has_content, "PDF crawl should return content (markdown or text)"
    assert content_length > 100, f"PDF content seems too short ({content_length} chars). Expected substantial content."
    
    # Verify metadata
    assert "metadata" in data, "Response missing 'metadata' field"
    metadata = data["metadata"]
    
    # Check for PDF-related metadata
    if "content_type" in metadata:
        assert "pdf" in metadata["content_type"].lower(), f"Expected PDF content type, got: {metadata['content_type']}"
    
    # Verify no error
    if "error" in data:
        assert not data["error"] or data["error"] == "", f"Unexpected error: {data['error']}"
    
    print(f"✓ IndiaAI PDF crawl test passed")
    print(f"  - URL: {data['url']}")
    print(f"  - Content length: {content_length}")
    print(f"  - Content type: {metadata.get('content_type', 'N/A')}")


def test_crawl_error_handling():
    """
    Test that invalid URLs are handled gracefully.
    """
    # Test with invalid URL
    response = client.get("/api/crawl?url=not-a-valid-url")
    
    # Should return 400 or 500 with error message
    assert response.status_code in [400, 500], f"Expected 400/500 for invalid URL, got {response.status_code}"
    
    data = response.json()
    
    # Should have error detail
    if "detail" in data:
        assert len(data["detail"]) > 0, "Error detail should not be empty"
    elif "error" in data:
        assert len(data["error"]) > 0, "Error message should not be empty"
    
    print(f"✓ Error handling test passed")


if __name__ == "__main__":
    print("Running crawl integration tests...")
    print("=" * 60)
    
    try:
        test_simple_html_crawl()
        print()
        test_indiaai_pdf_crawl()
        print()
        test_crawl_error_handling()
        print()
        print("=" * 60)
        print("✓ All crawl integration tests passed!")
    except AssertionError as e:
        print(f"\n✗ Test failed: {e}")
        sys.exit(1)
    except Exception as e:
        print(f"\n✗ Unexpected error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

