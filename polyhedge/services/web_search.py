"""Web search service using Brave Search API."""

import time
import httpx

from polyhedge.config import Settings
from polyhedge.logger import get_logger

logger = get_logger(__name__)


class WebSearch:
    """Performs web searches using Brave Search API."""

    def __init__(self, settings: Settings):
        self.api_key = settings.brave_api_key
        self.client = httpx.Client(
            base_url="https://api.search.brave.com/res/v1",
            headers={"X-Subscription-Token": self.api_key},
            timeout=10.0,
        )
        logger.info("WebSearch initialized with Brave API")

    def search(self, query: str, count: int = 5, freshness: str = "pm") -> list[dict]:
        """Perform a single web search and return results.

        Args:
            query: Search query string
            count: Number of results to return
            freshness: Time filter - 'pd' (past day), 'pw' (past week),
                      'pm' (past month, default), 'py' (past year)
        """
        logger.debug(f"Searching for: {query} (freshness: {freshness})")
        try:
            response = self.client.get(
                "/web/search",
                params={"q": query, "count": count, "freshness": freshness},
            )
            response.raise_for_status()
            data = response.json()
            
            results = []
            for item in data.get("web", {}).get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "description": item.get("description", ""),
                    "url": item.get("url", ""),
                })
            logger.info(f"Search '{query}' returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Search failed for '{query}': {e}")
            return []

    def search_multiple(self, queries: list[str], delay: float = 1.0, freshness: str = "pm") -> dict[str, list[dict]]:
        """Perform multiple searches with a delay between each.

        Args:
            queries: List of search query strings
            delay: Delay in seconds between searches
            freshness: Time filter - 'pd' (past day), 'pw' (past week),
                      'pm' (past month, default), 'py' (past year)
        """
        logger.info(f"Starting {len(queries)} searches with {delay}s delay (freshness: {freshness})")
        all_results = {}
        for i, query in enumerate(queries):
            logger.debug(f"Search {i+1}/{len(queries)}: {query}")
            all_results[query] = self.search(query, freshness=freshness)
            if i < len(queries) - 1:
                time.sleep(delay)
        logger.info(f"Completed all {len(queries)} searches")
        return all_results

    def close(self):
        """Close the HTTP client."""
        logger.debug("Closing WebSearch client")
        self.client.close()
