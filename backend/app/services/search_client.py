"""
Search API client for query-seeded crawling.
Supports Perplexity API (primary) and Google Custom Search API (fallback).
"""
import logging
from typing import List, Optional
import aiohttp
from app.core.config import settings

logger = logging.getLogger(__name__)


class SearchClient:
    """
    Search API client for getting seed URLs from natural language queries.
    
    Supports multiple providers:
    - Perplexity API (primary)
    - Google Custom Search API (fallback)
    """
    
    def __init__(self):
        """Initialize search client with API keys from settings."""
        self.provider = getattr(settings, 'search_api_provider', 'perplexity')
        self.perplexity_api_key = getattr(settings, 'perplexity_api_key', '')
        self.google_search_api_key = getattr(settings, 'google_search_api_key', '')
        self.google_search_engine_id = getattr(settings, 'google_search_engine_id', '')
    
    async def get_seed_urls(self, query: str, top_k: int = 10) -> List[str]:
        """
        Get seed URLs from a search query.
        
        Args:
            query: Natural language search query (e.g., "EU AI Act high-risk obligations")
            top_k: Number of URLs to return (default: 10)
            
        Returns:
            List of URL strings from search results
        """
        if self.provider == 'perplexity' and self.perplexity_api_key:
            return await self._get_perplexity_urls(query, top_k)
        elif self.provider == 'google' and self.google_search_api_key and self.google_search_engine_id:
            return await self._get_google_urls(query, top_k)
        else:
            logger.warning(f"Search API not configured (provider={self.provider}). Returning empty list.")
            return []
    
    async def _get_perplexity_urls(self, query: str, top_k: int) -> List[str]:
        """
        Get URLs from Perplexity API.
        
        Args:
            query: Search query
            top_k: Number of URLs to return
            
        Returns:
            List of URLs
        """
        try:
            url = "https://api.perplexity.ai/chat/completions"
            headers = {
                "Authorization": f"Bearer {self.perplexity_api_key}",
                "Content-Type": "application/json"
            }
            payload = {
                "model": "llama-3.1-sonar-large-128k-online",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are a helpful assistant that extracts URLs from search results. Return only a JSON array of URLs, nothing else."
                    },
                    {
                        "role": "user",
                        "content": f"Search for: {query}. Return the top {top_k} authoritative URLs as a JSON array of strings."
                    }
                ],
                "max_tokens": 2000,
                "temperature": 0.1
            }
            
            async with aiohttp.ClientSession() as session:
                async with session.post(url, json=payload, headers=headers, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        content = data.get('choices', [{}])[0].get('message', {}).get('content', '')
                        
                        # Try to extract URLs from the response
                        # Perplexity may return URLs in various formats
                        urls = self._extract_urls_from_text(content)
                        return urls[:top_k]
                    else:
                        error_text = await response.text()
                        logger.error(f"Perplexity API error (status {response.status}): {error_text}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error calling Perplexity API: {e}")
            return []
    
    async def _get_google_urls(self, query: str, top_k: int) -> List[str]:
        """
        Get URLs from Google Custom Search API.
        
        Args:
            query: Search query
            top_k: Number of URLs to return
            
        Returns:
            List of URLs
        """
        try:
            url = "https://www.googleapis.com/customsearch/v1"
            params = {
                "key": self.google_search_api_key,
                "cx": self.google_search_engine_id,
                "q": query,
                "num": min(top_k, 10)  # Google API max is 10 per request
            }
            
            urls = []
            async with aiohttp.ClientSession() as session:
                async with session.get(url, params=params, timeout=aiohttp.ClientTimeout(total=30)) as response:
                    if response.status == 200:
                        data = await response.json()
                        items = data.get('items', [])
                        urls = [item.get('link', '') for item in items if item.get('link')]
                        return urls[:top_k]
                    else:
                        error_text = await response.text()
                        logger.error(f"Google Search API error (status {response.status}): {error_text}")
                        return []
                        
        except Exception as e:
            logger.error(f"Error calling Google Search API: {e}")
            return []
    
    def _extract_urls_from_text(self, text: str) -> List[str]:
        """
        Extract URLs from text (handles JSON arrays, plain text, etc.).
        
        Args:
            text: Text that may contain URLs
            
        Returns:
            List of extracted URLs
        """
        import re
        import json
        
        urls = []
        
        # Try to parse as JSON array first
        try:
            parsed = json.loads(text)
            if isinstance(parsed, list):
                urls = [str(item) for item in parsed if isinstance(item, str) and item.startswith(('http://', 'https://'))]
                return urls
        except:
            pass
        
        # Extract URLs using regex
        url_pattern = r'https?://[^\s<>"{}|\\^`\[\]]+'
        found_urls = re.findall(url_pattern, text)
        
        # Clean up URLs (remove trailing punctuation)
        cleaned_urls = []
        for url in found_urls:
            # Remove trailing punctuation
            url = url.rstrip('.,;:!?)')
            if url.startswith(('http://', 'https://')):
                cleaned_urls.append(url)
        
        return cleaned_urls


# Global search client instance
search_client = SearchClient()


