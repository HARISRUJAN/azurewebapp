"""
Hybrid crawler module for query-seeded and domain-seeded crawling.
"""
import logging
from typing import List, Dict, Optional
from urllib.parse import urlparse
from app.services.search_client import search_client
from app.services.crawling_service import crawl_multi_page
from app.core.config import settings

logger = logging.getLogger(__name__)


class HybridCrawler:
    """
    Hybrid crawler supporting both query-seeded and domain-seeded modes.
    
    Query-seeded mode:
    - Uses search API to get seed URLs from natural language queries
    - Crawls with shallow depth (1-2) for freshness and broad coverage
    
    Domain-seeded mode:
    - Starts from a base URL/domain
    - Crawls internal links more deeply (2-3) with strict limits
    - Only follows same-domain links
    """
    
    def __init__(self):
        """Initialize hybrid crawler."""
        self.search_client = search_client
    
    async def crawl_query_seeded(
        self,
        query: str,
        top_k: int = 10,
        max_depth: int = 1,
        max_pages: int = 30,
        allowed_paths: Optional[List[str]] = None,
        excluded_paths: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Crawl using query-seeded mode.
        
        Args:
            query: Natural language search query (e.g., "EU AI Act high-risk obligations")
            top_k: Number of seed URLs to get from search API (default: 10)
            max_depth: Maximum crawl depth (default: 1 for freshness)
            max_pages: Maximum number of pages to crawl (default: 30)
            allowed_paths: List of regex patterns for allowed paths
            excluded_paths: List of regex patterns for excluded paths
            
        Returns:
            List of crawl result dictionaries
        """
        logger.info(f"Starting query-seeded crawl: query='{query}', top_k={top_k}, max_depth={max_depth}, max_pages={max_pages}")
        
        # Get seed URLs from search API
        seed_urls = await self.search_client.get_seed_urls(query, top_k=top_k)
        
        if not seed_urls:
            logger.warning(f"No seed URLs found for query: {query}")
            return []
        
        logger.info(f"Found {len(seed_urls)} seed URLs from search API")
        
        # Use default path filters if not provided
        if allowed_paths is None:
            allowed_paths = getattr(settings, 'crawl_allowed_paths', [])
        
        if excluded_paths is None:
            excluded_paths = getattr(settings, 'crawl_excluded_paths', [])
        
        # Crawl with shallow depth (query-seeded allows cross-domain)
        results = await crawl_multi_page(
            start_urls=seed_urls,
            max_depth=max_depth,
            max_pages=max_pages,
            allowed_paths=allowed_paths,
            excluded_paths=excluded_paths,
            same_domain_only=False,  # Allow cross-domain for query-seeded
            base_domain=None
        )
        
        # Add metadata to all results
        for result in results:
            result["metadata"]["source_query"] = query
            result["metadata"]["mode"] = "query"
        
        logger.info(f"Query-seeded crawl completed: {len(results)} pages crawled")
        return results
    
    async def crawl_domain_seeded(
        self,
        base_url: str,
        max_depth: int = 2,
        max_pages: int = 50,
        allowed_paths: Optional[List[str]] = None,
        excluded_paths: Optional[List[str]] = None
    ) -> List[Dict]:
        """
        Crawl using domain-seeded mode.
        
        Args:
            base_url: Starting URL/domain (e.g., "https://digital-strategy.ec.europa.eu/")
            max_depth: Maximum crawl depth (default: 2 for deeper exploration)
            max_pages: Maximum number of pages to crawl (default: 50)
            allowed_paths: List of regex patterns for allowed paths
            excluded_paths: List of regex patterns for excluded paths
            
        Returns:
            List of crawl result dictionaries
        """
        logger.info(f"Starting domain-seeded crawl: base_url='{base_url}', max_depth={max_depth}, max_pages={max_pages}")
        
        # Parse base domain
        parsed = urlparse(base_url)
        base_domain = parsed.netloc.lower()
        
        if not base_domain:
            logger.error(f"Invalid base URL: {base_url}")
            return []
        
        # Use default path filters if not provided
        if allowed_paths is None:
            allowed_paths = getattr(settings, 'crawl_allowed_paths', [])
        
        if excluded_paths is None:
            excluded_paths = getattr(settings, 'crawl_excluded_paths', [])
        
        # Crawl with same-domain restriction and deeper depth
        results = await crawl_multi_page(
            start_urls=[base_url],
            max_depth=max_depth,
            max_pages=max_pages,
            allowed_paths=allowed_paths,
            excluded_paths=excluded_paths,
            same_domain_only=True,  # Strict same-domain for domain-seeded
            base_domain=base_domain
        )
        
        # Add metadata to all results
        for result in results:
            result["metadata"]["root_domain"] = base_domain
            result["metadata"]["mode"] = "domain"
        
        logger.info(f"Domain-seeded crawl completed: {len(results)} pages crawled")
        return results
    
    async def _crawl_with_queue(
        self,
        start_urls: List[str],
        mode: str,
        metadata: Dict,
        max_depth: int = 2,
        max_pages: int = 30,
        allowed_paths: Optional[List[str]] = None,
        excluded_paths: Optional[List[str]] = None,
        same_domain_only: bool = True,
        base_domain: Optional[str] = None
    ) -> List[Dict]:
        """
        Internal method for crawling with a URL queue.
        
        This is used by both query-seeded and domain-seeded modes.
        """
        results = await crawl_multi_page(
            start_urls=start_urls,
            max_depth=max_depth,
            max_pages=max_pages,
            allowed_paths=allowed_paths,
            excluded_paths=excluded_paths,
            same_domain_only=same_domain_only,
            base_domain=base_domain
        )
        
        # Add mode metadata to all results
        for result in results:
            result["metadata"].update(metadata)
            result["metadata"]["mode"] = mode
        
        return results


# Global hybrid crawler instance
hybrid_crawler = HybridCrawler()

