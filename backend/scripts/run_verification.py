"""
Automated verification script to run all end-to-end tests.
This script runs the golden test suite to verify the entire system.
"""
import sys
import os
import json
import asyncio
import time
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Set Windows event loop policy before any imports
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

from fastapi.testclient import TestClient
from app.main import app

# Import test modules
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "tests"))
from test_crawl_integration import test_simple_html_crawl, test_indiaai_pdf_crawl
from test_admin_crawl_flow import test_admin_crawl_flow
from test_rag_pipeline import test_rag_ingestion_pipeline

client = TestClient(app)


def load_golden_test_urls():
    """Load golden test URLs configuration."""
    script_dir = Path(__file__).parent
    config_path = script_dir / "golden_test_urls.json"
    
    if not config_path.exists():
        print(f"Warning: Golden test URLs config not found at {config_path}")
        return None
    
    with open(config_path, 'r', encoding='utf-8') as f:
        return json.load(f)


def test_golden_url(url_config):
    """Test a single golden URL."""
    name = url_config.get("name", "Unknown")
    url = url_config.get("url", "")
    expected = url_config.get("expected_results", {})
    
    print(f"\nTesting: {name}")
    print(f"  URL: {url}")
    
    try:
        start_time = time.time()
        response = client.get(f"/api/crawl?url={url}", timeout=expected.get("timeout_seconds", 60))
        elapsed = time.time() - start_time
        
        if response.status_code != expected.get("status_code", 200):
            print(f"  ✗ Failed: Expected status {expected.get('status_code', 200)}, got {response.status_code}")
            return False
        
        data = response.json()
        
        # Check for errors
        if "error" in data and data["error"]:
            print(f"  ✗ Failed: {data['error']}")
            return False
        
        # Verify expected results
        if expected.get("has_markdown"):
            if "markdown" not in data or not data["markdown"]:
                print(f"  ✗ Failed: Missing or empty markdown")
                return False
            
            min_length = expected.get("min_markdown_length", 0)
            if len(data["markdown"]) < min_length:
                print(f"  ✗ Failed: Markdown too short ({len(data['markdown'])} < {min_length})")
                return False
        
        if expected.get("has_content"):
            has_content = False
            if "markdown" in data and data["markdown"]:
                has_content = True
            elif "text" in data and data["text"]:
                has_content = True
            
            if not has_content:
                print(f"  ✗ Failed: Missing content")
                return False
            
            min_length = expected.get("min_content_length", 0)
            content_length = len(data.get("markdown", "") or data.get("text", ""))
            if content_length < min_length:
                print(f"  ✗ Failed: Content too short ({content_length} < {min_length})")
                return False
        
        if expected.get("has_title"):
            if "metadata" not in data or "title" not in data["metadata"]:
                print(f"  ✗ Failed: Missing title in metadata")
                return False
        
        if expected.get("title_contains"):
            title = data.get("metadata", {}).get("title", "").lower()
            for keyword in expected["title_contains"]:
                if keyword.lower() not in title:
                    print(f"  ✗ Failed: Title doesn't contain '{keyword}'")
                    return False
        
        print(f"  ✓ Passed ({elapsed:.2f}s)")
        print(f"    - Markdown length: {len(data.get('markdown', ''))}")
        if "metadata" in data and "title" in data["metadata"]:
            print(f"    - Title: {data['metadata']['title']}")
        
        return True
        
    except Exception as e:
        print(f"  ✗ Failed: {type(e).__name__}: {e}")
        return False


def run_all_verification_tests():
    """Run all verification tests."""
    print("=" * 70)
    print("End-to-End Verification Test Suite")
    print("=" * 70)
    
    results = {
        "passed": 0,
        "failed": 0,
        "tests": []
    }
    
    # Test 1: Simple HTML crawl
    print("\n[1/5] Testing simple HTML crawl...")
    try:
        test_simple_html_crawl()
        results["passed"] += 1
        results["tests"].append({"name": "Simple HTML Crawl", "status": "passed"})
    except Exception as e:
        results["failed"] += 1
        results["tests"].append({"name": "Simple HTML Crawl", "status": "failed", "error": str(e)})
        print(f"  ✗ Failed: {e}")
    
    # Test 2: PDF crawl
    print("\n[2/5] Testing PDF crawl...")
    try:
        test_indiaai_pdf_crawl()
        results["passed"] += 1
        results["tests"].append({"name": "PDF Crawl", "status": "passed"})
    except Exception as e:
        results["failed"] += 1
        results["tests"].append({"name": "PDF Crawl", "status": "failed", "error": str(e)})
        print(f"  ✗ Failed: {e}")
    
    # Test 3: Admin crawl flow
    print("\n[3/5] Testing admin crawl flow...")
    try:
        test_admin_crawl_flow()
        results["passed"] += 1
        results["tests"].append({"name": "Admin Crawl Flow", "status": "passed"})
    except Exception as e:
        results["failed"] += 1
        results["tests"].append({"name": "Admin Crawl Flow", "status": "failed", "error": str(e)})
        print(f"  ✗ Failed: {e}")
    
    # Test 4: RAG pipeline
    print("\n[4/5] Testing RAG ingestion pipeline...")
    try:
        test_rag_ingestion_pipeline()
        results["passed"] += 1
        results["tests"].append({"name": "RAG Ingestion Pipeline", "status": "passed"})
    except Exception as e:
        results["failed"] += 1
        results["tests"].append({"name": "RAG Ingestion Pipeline", "status": "failed", "error": str(e)})
        print(f"  ✗ Failed: {e}")
    
    # Test 5: Golden test URLs
    print("\n[5/5] Testing golden test URLs...")
    config = load_golden_test_urls()
    if config:
        test_urls = config.get("test_urls", [])
        golden_passed = 0
        golden_failed = 0
        
        for url_config in test_urls:
            if test_golden_url(url_config):
                golden_passed += 1
            else:
                golden_failed += 1
        
        results["passed"] += golden_passed
        results["failed"] += golden_failed
        results["tests"].append({
            "name": "Golden Test URLs",
            "status": "passed" if golden_failed == 0 else "partial",
            "passed": golden_passed,
            "failed": golden_failed
        })
    else:
        print("  ⚠ Skipped: Golden test URLs config not found")
        results["tests"].append({"name": "Golden Test URLs", "status": "skipped"})
    
    # Summary
    print("\n" + "=" * 70)
    print("Test Summary")
    print("=" * 70)
    print(f"Passed: {results['passed']}")
    print(f"Failed: {results['failed']}")
    print(f"Total: {results['passed'] + results['failed']}")
    
    for test in results["tests"]:
        status_icon = "✓" if test["status"] == "passed" else "✗" if test["status"] == "failed" else "⚠"
        print(f"{status_icon} {test['name']}: {test['status']}")
        if "error" in test:
            print(f"    Error: {test['error']}")
    
    print("=" * 70)
    
    if results["failed"] == 0:
        print("✓ All verification tests passed!")
        return 0
    else:
        print(f"✗ {results['failed']} test(s) failed")
        return 1


if __name__ == "__main__":
    exit_code = run_all_verification_tests()
    sys.exit(exit_code)

