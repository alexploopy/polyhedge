"""Direct concern-to-markets search service."""

from polyhedge.config import Settings
from polyhedge.logger import get_logger
from polyhedge.models.market import Market
from polyhedge.services.cache import MarketCache

logger = get_logger(__name__)


class ConcernSearch:
    """Search markets directly from user concern via vector embeddings."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.cache = MarketCache(use_vectors=True)
        logger.info("ConcernSearch initialized with vector DB")

    def search(
        self,
        concern: str,
        n_results: int = 500,
        min_liquidity: float = 100.0
    ) -> list[tuple[Market, float]]:
        """
        Search for markets related to user concern.

        Args:
            concern: User's primary concern (raw text)
            n_results: Number of markets to return (default: 500)
            min_liquidity: Minimum market liquidity filter

        Returns:
            List of (Market, similarity_score) tuples, sorted by relevance
        """
        if not self.cache.vector_db:
            raise ValueError("Vector DB not available. Run 'polyhedge update-vectors' first.")

        logger.info(f"Searching for markets related to: {concern[:100]}...")
        logger.info(f"Retrieving top {n_results} markets with min_liquidity={min_liquidity}")

        # Direct semantic search
        results = self.cache.search_semantic(
            query=concern,
            n_results=n_results,
            min_liquidity=min_liquidity
        )

        logger.info(f"Found {len(results)} markets")

        return results

    def close(self):
        """Clean up resources."""
        pass  # MarketCache manages its own connections
