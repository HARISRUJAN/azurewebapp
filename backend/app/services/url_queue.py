"""
URL Queue module for BFS-style crawling with depth tracking and URL deduplication.
"""
import logging
from typing import Optional, Tuple, Dict, Set
from urllib.parse import urlparse, urlunparse, parse_qs, urlencode
from collections import deque

logger = logging.getLogger(__name__)


def canonicalize_url(url: str) -> str:
    """
    Canonicalize a URL by normalizing scheme, hostname, removing fragments,
    tracking parameters, and normalizing trailing slashes.
    
    Args:
        url: URL to canonicalize
        
    Returns:
        Canonicalized URL string
        
    Rules:
        - Lowercase hostname
        - Remove fragments (#...)
        - Remove tracking params: utm_*, ref=, source=, fbclid=, gclid=
        - Normalize trailing slashes (keep for root, remove for paths)
        - Preserve query params that matter (e.g., page=, id=)
    """
    try:
        parsed = urlparse(url)
        
        # Normalize scheme and hostname (lowercase)
        scheme = parsed.scheme.lower()
        netloc = parsed.netloc.lower()
        
        # Remove fragment
        fragment = ""
        
        # Normalize path (remove trailing slash except for root)
        path = parsed.path
        if path and path != "/" and path.endswith("/"):
            path = path.rstrip("/")
        elif not path:
            path = "/"
        
        # Filter query parameters (remove tracking params)
        query_params = parse_qs(parsed.query, keep_blank_values=True)
        
        # Tracking parameters to remove
        tracking_params = {
            'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
            'ref', 'source', 'fbclid', 'gclid', 'gclsrc', 'dclid', 'wbraid', 'gbraid',
            '_ga', '_gid', 'mc_cid', 'mc_eid'
        }
        
        # Remove tracking parameters
        filtered_params = {
            k: v for k, v in query_params.items()
            if k.lower() not in tracking_params
        }
        
        # Rebuild query string
        query = urlencode(filtered_params, doseq=True) if filtered_params else ""
        
        # Reconstruct URL
        canonical = urlunparse((scheme, netloc, path, parsed.params, query, fragment))
        
        return canonical
        
    except Exception as e:
        logger.warning(f"Error canonicalizing URL {url}: {e}, returning original")
        return url


class URLQueue:
    """
    URL queue for BFS-style crawling with depth tracking and deduplication.
    
    Maintains a queue of URLs to crawl, tracking depth and metadata for each URL.
    Uses canonicalized URLs for deduplication to avoid crawling the same page twice.
    """
    
    def __init__(self):
        """Initialize an empty URL queue."""
        self._queue: deque = deque()  # Queue of (url, depth, metadata) tuples
        self._seen_urls: Set[str] = set()  # Set of canonicalized URLs already seen
        self._depth_map: Dict[str, int] = {}  # Map of canonical URL to minimum depth found
    
    def push(self, url: str, depth: int, metadata: Optional[Dict] = None) -> bool:
        """
        Add a URL to the queue if it hasn't been seen before.
        
        Args:
            url: URL to add
            depth: Depth level (0 = seed URL, 1+ = discovered links)
            metadata: Optional metadata dict (source_query, root_domain, mode, etc.)
            
        Returns:
            True if URL was added, False if it was already seen
        """
        canonical = canonicalize_url(url)
        
        # Check if we've seen this URL before
        if canonical in self._seen_urls:
            # If we've seen it at a lower depth, don't add it again
            if canonical in self._depth_map and self._depth_map[canonical] <= depth:
                return False
            # If this is a shorter path, update the depth
            self._depth_map[canonical] = min(self._depth_map.get(canonical, depth), depth)
            return False
        
        # Add to queue
        self._queue.append((url, depth, metadata or {}))
        self._seen_urls.add(canonical)
        self._depth_map[canonical] = depth
        
        return True
    
    def pop(self) -> Optional[Tuple[str, int, Dict]]:
        """
        Get the next URL from the queue (BFS order).
        
        Returns:
            Tuple of (url, depth, metadata) or None if queue is empty
        """
        if not self._queue:
            return None
        
        return self._queue.popleft()
    
    def has_seen(self, url: str) -> bool:
        """
        Check if a URL has already been seen (canonicalized).
        
        Args:
            url: URL to check
            
        Returns:
            True if URL has been seen, False otherwise
        """
        canonical = canonicalize_url(url)
        return canonical in self._seen_urls
    
    def size(self) -> int:
        """Get the current size of the queue."""
        return len(self._queue)
    
    def empty(self) -> bool:
        """Check if the queue is empty."""
        return len(self._queue) == 0
    
    def get_seen_count(self) -> int:
        """Get the number of unique URLs seen (including those already processed)."""
        return len(self._seen_urls)
    
    def clear(self):
        """Clear the queue and seen URLs set."""
        self._queue.clear()
        self._seen_urls.clear()
        self._depth_map.clear()


