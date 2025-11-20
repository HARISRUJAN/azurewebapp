"""Simple test script to check Crawl4AI setup"""
import asyncio
import sys
import os

# Set encoding for Windows
if sys.platform == 'win32':
    os.environ['PYTHONIOENCODING'] = 'utf-8'
    os.environ['PYTHONUTF8'] = '1'
    os.environ['NO_COLOR'] = '1'
    os.environ['TERM'] = 'dumb'

async def test_crawl():
    try:
        from crawl4ai import AsyncWebCrawler
        print("Crawl4AI imported successfully")
        
        async with AsyncWebCrawler(headless=True, verbose=False) as crawler:
            print("Crawler initialized")
            result = await crawler.arun(url='https://example.com')
            print(f"Result type: {type(result)}")
            print(f"Result: {result}")
            if result:
                print(f"Has markdown: {hasattr(result, 'markdown')}")
                if hasattr(result, 'markdown'):
                    print(f"Markdown length: {len(result.markdown) if result.markdown else 0}")
    except NotImplementedError as e:
        print(f"NotImplementedError: {e}")
        print("This usually means Playwright browsers are not installed.")
        print("Run: playwright install chromium")
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_crawl())


