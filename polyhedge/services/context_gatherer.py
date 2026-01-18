"""Service for gathering and compressing web context about user concerns."""

from polyhedge.config import Settings
from polyhedge.logger import get_logger
from polyhedge.services.context_compressor import ContextCompressor
from polyhedge.services.web_search import WebSearch

logger = get_logger(__name__)


class ContextGatherer:
    """Gather web context and compress it for efficient LLM processing."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.web_search = WebSearch(settings)
        self.compressor = ContextCompressor(settings)
        logger.info("ContextGatherer initialized")

    def gather_concern_context(
        self,
        concern: str,
        num_results: int = 5,
        max_tokens: int = 1000
    ) -> str:
        """
        Gather and compress web context about a user's concern.

        Args:
            concern: User's primary concern
            num_results: Number of search results to fetch
            max_tokens: Maximum tokens in compressed output

        Returns:
            Compressed summary of web context (or empty string if disabled/failed)
        """
        logger.info(f"Gathering web context for: {concern[:100]}...")

        try:
            # Search the web for context
            search_results = self.web_search.search(
                query=concern,
                count=num_results,
                freshness="pm"  # Past month for recent context
            )

            if not search_results:
                logger.warning("No search results found")
                return ""

            logger.info(f"Found {len(search_results)} search results")

            # Compress the results
            compressed_context = self.compressor.compress_search_results(
                search_results=search_results,
                max_output_tokens=max_tokens
            )

            if compressed_context:
                logger.info(f"Compressed context: {len(compressed_context)} chars")
            else:
                logger.warning("Compression returned empty result")

            return compressed_context

        except Exception as e:
            logger.error(f"Error gathering context: {e}")
            return ""

    def gather_market_context(
        self,
        market_question: str,
        num_results: int = 3,
        max_tokens: int = 500
    ) -> str:
        """
        Gather compressed web context about a specific market.

        Args:
            market_question: Market question/title
            num_results: Number of search results
            max_tokens: Maximum tokens in output

        Returns:
            Compressed market context
        """
        logger.debug(f"Gathering context for market: {market_question[:60]}...")

        try:
            search_results = self.web_search.search(
                query=market_question,
                count=num_results,
                freshness="pw"  # Past week for market-specific context
            )

            if not search_results:
                return ""

            compressed = self.compressor.compress_search_results(
                search_results=search_results,
                max_output_tokens=max_tokens
            )

            return compressed

        except Exception as e:
            logger.error(f"Error gathering market context: {e}")
            return ""

    def close(self):
        """Clean up resources."""
        self.compressor.close()
        logger.debug("ContextGatherer closed")
