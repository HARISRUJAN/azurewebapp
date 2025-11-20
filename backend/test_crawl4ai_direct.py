"""Direct test of Crawl4AI to diagnose issues"""
import asyncio
import sys
import os

# Set encoding for Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    os.environ['NO_COLOR'] = '1'
    os.environ['TERM'] = 'dumb'

async def test_crawl4ai():
    try:
        print("Importing Crawl4AI...")
        from crawl4ai import AsyncWebCrawler
        print("[OK] Crawl4AI imported successfully")
        
        print("Creating AsyncWebCrawler instance...")
        crawler = AsyncWebCrawler(headless=True, verbose=False)
        print("[OK] AsyncWebCrawler instance created")
        
        print("Entering context manager...")
        await crawler.__aenter__()
        print("[OK] Context manager entered successfully")
        
        print("Crawling https://example.com...")
        result = await crawler.arun(url='https://example.com')
        print(f"[OK] Crawl completed. Result type: {type(result)}")
        
        if result:
            print(f"[OK] Result has markdown: {hasattr(result, 'markdown')}")
            if hasattr(result, 'markdown') and result.markdown:
                print(f"[OK] Markdown length: {len(result.markdown)}")
        
        print("Exiting context manager...")
        await crawler.__aexit__(None, None, None)
        print("[OK] Context manager exited successfully")
        
        print("\n[SUCCESS] ALL TESTS PASSED")
        
    except NotImplementedError as e:
        print(f"\n[ERROR] NotImplementedError: {e}")
        print(f"Error type: {type(e)}")
        print(f"Error args: {e.args}")
        import traceback
        traceback.print_exc()
    except Exception as e:
        print(f"\n[ERROR] Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_crawl4ai())

