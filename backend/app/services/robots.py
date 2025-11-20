"""
Robots.txt parsing and per-domain rate limiting module.
"""
import logging
import asyncio
from typing import Optional, Dict
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import aiohttp

logger = logging.getLogger(__name__)


class RobotsChecker:
    """
    Robots.txt checker with caching and per-domain rate limiting.
    
    Fetches and caches robots.txt files per domain, and checks if URLs
    are allowed to be crawled according to robots.txt rules.
    """
    
    def __init__(self, user_agent: str = "aigov-crawler/1.0"):
        """
        Initialize robots checker.
        
        Args:
            user_agent: User agent string to use for robots.txt checks
        """
        self.user_agent = user_agent
        self._robots_cache: Dict[str, Optional[RobotFileParser]] = {}
        self._last_fetch_time: Dict[str, float] = {}
        self._crawl_delays: Dict[str, float] = {}
        self._last_request_time: Dict[str, float] = {}
    
    async def _fetch_robots_txt(self, domain: str) -> Optional[str]:
        """
        Fetch robots.txt for a domain.
        
        Args:
            domain: Domain name (e.g., "example.com")
            
        Returns:
            robots.txt content as string, or None if not found/error
        """
        robots_url = f"https://{domain}/robots.txt"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(robots_url, timeout=aiohttp.ClientTimeout(total=10)) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        logger.debug(f"robots.txt not found for {domain} (status {response.status})")
                        return None
        except Exception as e:
            logger.debug(f"Error fetching robots.txt for {domain}: {e}")
            return None
    
    def _get_robots_parser(self, domain: str) -> Optional[RobotFileParser]:
        """
        Get or create RobotFileParser for a domain (synchronous, uses cached data).
        
        Args:
            domain: Domain name
            
        Returns:
            RobotFileParser instance or None
        """
        if domain in self._robots_cache:
            return self._robots_cache[domain]
        
        return None
    
    async def _load_robots_parser(self, domain: str) -> None:
        """
        Load robots.txt parser for a domain.
        
        Args:
            domain: Domain name
        """
        if domain in self._robots_cache:
            return
        
        robots_url = f"https://{domain}/robots.txt"
        
        try:
            # RobotFileParser.read() makes a synchronous HTTP request
            # We need to handle this in a thread pool for async compatibility
            import concurrent.futures
            
            def load_parser():
                parser = RobotFileParser()
                parser.set_url(robots_url)
                parser.read()  # Synchronous HTTP request
                return parser
            
            loop = asyncio.get_event_loop()
            parser = await loop.run_in_executor(None, load_parser)
            
            self._robots_cache[domain] = parser
            
            # Extract crawl delay
            user_agent_to_use = self.user_agent
            crawl_delay = parser.crawl_delay(user_agent_to_use)
            if crawl_delay:
                self._crawl_delays[domain] = crawl_delay
                
        except Exception as e:
            logger.debug(f"Error loading robots.txt for {domain}: {e}")
            self._robots_cache[domain] = None
    
    async def can_fetch(self, url: str, user_agent: Optional[str] = None) -> bool:
        """
        Check if a URL can be fetched according to robots.txt.
        
        Args:
            url: URL to check
            user_agent: Optional user agent (defaults to instance user_agent)
            
        Returns:
            True if URL can be fetched, False if disallowed
        """
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            if not domain:
                return True  # Can't determine domain, allow by default
            
            user_agent_to_use = user_agent or self.user_agent
            
            # Check cache first
            if domain not in self._robots_cache:
                # Load robots.txt parser
                await self._load_robots_parser(domain)
            
            # Check if allowed
            parser = self._robots_cache.get(domain)
            if parser is None:
                # No robots.txt or error - allow by default
                return True
            
            return parser.can_fetch(user_agent_to_use, url)
            
        except Exception as e:
            logger.warning(f"Error checking robots.txt for {url}: {e}")
            # On error, allow by default (fail open)
            return True
    
    def get_crawl_delay(self, domain: str, user_agent: Optional[str] = None) -> float:
        """
        Get the crawl delay for a domain from robots.txt.
        
        Args:
            domain: Domain name
            user_agent: Optional user agent
            
        Returns:
            Crawl delay in seconds (0 if not specified)
        """
        user_agent_to_use = user_agent or self.user_agent
        
        if domain in self._crawl_delays:
            return self._crawl_delays[domain]
        
        parser = self._get_robots_parser(domain)
        if parser:
            delay = parser.crawl_delay(user_agent_to_use)
            if delay:
                self._crawl_delays[domain] = delay
                return delay
        
        return 0.0
    
    async def wait_for_domain(self, domain: str) -> None:
        """
        Wait for the appropriate delay before crawling a domain.
        
        Args:
            domain: Domain name to wait for
        """
        delay = self.get_crawl_delay(domain)
        
        if delay > 0:
            last_request = self._last_request_time.get(domain, 0)
            time_since_last = asyncio.get_event_loop().time() - last_request
            
            if time_since_last < delay:
                wait_time = delay - time_since_last
                await asyncio.sleep(wait_time)
        
        self._last_request_time[domain] = asyncio.get_event_loop().time()

