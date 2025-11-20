"""
Link extraction module for extracting links from HTML content.
"""
import logging
from typing import List
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


def extract_links(html: str, base_url: str) -> List[str]:
    """
    Extract all links from HTML content and return as absolute URLs.
    
    Args:
        html: HTML content as string
        base_url: Base URL for resolving relative URLs
        
    Returns:
        List of absolute URL strings
        
    Features:
        - Parses HTML with BeautifulSoup
        - Extracts <a href> tags
        - Resolves relative URLs to absolute using urljoin()
        - Filters out javascript:, mailto:, # fragments, and other non-HTTP links
    """
    links = []
    
    try:
        soup = BeautifulSoup(html, 'html.parser')
        
        # Find all <a> tags with href attributes
        for anchor in soup.find_all('a', href=True):
            href = anchor.get('href', '').strip()
            
            if not href:
                continue
            
            # Skip non-HTTP links
            if href.startswith(('javascript:', 'mailto:', 'tel:', 'data:', '#')):
                continue
            
            # Skip anchor-only links (fragments)
            if href.startswith('#'):
                continue
            
            try:
                # Resolve relative URLs to absolute
                absolute_url = urljoin(base_url, href)
                
                # Parse to validate and normalize
                parsed = urlparse(absolute_url)
                
                # Only include http/https URLs
                if parsed.scheme not in ('http', 'https'):
                    continue
                
                # Must have a netloc (domain)
                if not parsed.netloc:
                    continue
                
                links.append(absolute_url)
                
            except Exception as e:
                logger.debug(f"Error processing link {href}: {e}")
                continue
        
        # Remove duplicates while preserving order
        seen = set()
        unique_links = []
        for link in links:
            if link not in seen:
                seen.add(link)
                unique_links.append(link)
        
        return unique_links
        
    except Exception as e:
        logger.error(f"Error extracting links from HTML: {e}")
        return []


