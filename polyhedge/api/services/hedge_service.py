"""Orchestrate hedge generation workflow for API."""

import time
from typing import AsyncGenerator, Dict, Any

from polyhedge.config import Settings
from polyhedge.services.concern_search import ConcernSearch
from polyhedge.services.cerebras_filter import CerebrasMarketFilter
from polyhedge.services.bundle_generator import BundleGenerator
from polyhedge.services.context_gatherer import ContextGatherer
from polyhedge.services.financial_metrics import FinancialMetricsCalculator
from polyhedge.api.schemas.response import HedgeResponse
from polyhedge.logger import get_logger

logger = get_logger(__name__)


class HedgeService:
    """Orchestrate hedge generation workflow."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.concern_search = ConcernSearch(settings)
        self.cerebras_filter = CerebrasMarketFilter(settings)
        self.bundle_generator = BundleGenerator(settings)
        self.context_gatherer = ContextGatherer(settings)
        self.metrics_calculator = FinancialMetricsCalculator()
        logger.info("HedgeService initialized")

    def generate_hedge(
        self, concern: str, budget: float, num_markets: int
    ) -> HedgeResponse:
        """Generate hedge recommendations (synchronous)."""
        start_time = time.time()
        logger.info(
            f"Generating hedge for concern: '{concern[:50]}...', "
            f"budget=${budget}, num_markets={num_markets}"
        )

        # Step 1: Gather web context
        logger.info("Step 1: Gathering web context")
        web_context = self.context_gatherer.gather_concern_context(
            concern=concern, num_results=5, max_tokens=3000
        )

        # Step 2: Search markets
        logger.info(f"Step 2: Searching {num_markets} markets")
        search_results = self.concern_search.search(
            concern=concern, n_results=num_markets, min_liquidity=100.0
        )

        market_list = [m for m, score in search_results]
        logger.info(f"Found {len(market_list)} markets")

        # Step 3: Filter with Cerebras
        logger.info("Step 3: Filtering markets with Cerebras")
        filtered_markets = self.cerebras_filter.filter_in_batches(
            markets=market_list,
            user_concern=concern,
            batch_size=100,
            top_k_per_batch=10,
            web_context=web_context,
        )
        logger.info(f"Filtered to {len(filtered_markets)} markets")

        # Step 4: Generate bundles
        logger.info("Step 4: Generating themed bundles")
        bundles = self.bundle_generator.generate_etf_bundles(
            markets=filtered_markets,
            user_concern=concern,
            budget=budget,
            web_context=web_context,
        )
        logger.info(f"Generated {len(bundles)} bundles")

        # Step 5: Calculate financial metrics
        logger.info("Step 5: Calculating financial metrics")
        metrics = self.metrics_calculator.calculate_portfolio_metrics(bundles)

        execution_time = time.time() - start_time
        logger.info(f"Hedge generation complete in {execution_time:.2f}s")

        return HedgeResponse(
            bundles=bundles,
            metrics=metrics,
            web_context_summary=(
                web_context[:200] + "..." if len(web_context) > 200 else web_context
            ),
            execution_time_seconds=execution_time,
        )

    async def generate_hedge_stream(
        self, concern: str, budget: float, num_markets: int
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """Generate hedge recommendations with streaming progress updates."""
        start_time = time.time()
        logger.info(f"Starting streaming hedge generation for: '{concern[:50]}...'")

        try:
            # Event 1: Started
            yield {
                "type": "started",
                "data": {"concern": concern, "budget": budget},
            }

            # Restore context gathering (Backend only, no frontend events)
            web_context = self.context_gatherer.gather_concern_context(
                concern=concern, num_results=5, max_tokens=1000
            )

            # Event 3: Searching markets
            yield {
                "type": "progress",
                "data": {
                    "step": "search",
                    "message": f"Searching {num_markets} markets...",
                },
            }

            search_results = self.concern_search.search(
                concern=concern, n_results=num_markets, min_liquidity=100.0
            )

            market_list = [m for m, score in search_results]

            yield {
                "type": "search_complete",
                "data": {"markets_found": len(market_list)},
            }

            # Event 4: Filtering
            yield {
                "type": "progress",
                "data": {"step": "filter", "message": "Filtering markets with AI..."},
            }

            filtered_markets = self.cerebras_filter.filter_in_batches(
                markets=market_list,
                user_concern=concern,
                batch_size=100,
                top_k_per_batch=10,
                web_context=web_context,
            )

            yield {
                "type": "filter_complete",
                "data": {"markets_filtered": len(filtered_markets)},
            }

            # Event 5: Bundles
            yield {
                "type": "progress",
                "data": {"step": "bundles", "message": "Generating themed portfolios..."},
            }

            bundles = self.bundle_generator.generate_etf_bundles(
                markets=filtered_markets,
                user_concern=concern,
                budget=budget,
                web_context=web_context,
            )

            yield {
                "type": "bundles_complete",
                "data": {"num_bundles": len(bundles)},
            }

            # Event 6: Metrics
            metrics = self.metrics_calculator.calculate_portfolio_metrics(bundles)

            execution_time = time.time() - start_time
            logger.info(f"Streaming hedge generation complete in {execution_time:.2f}s")

            # Final Event: Complete (Hide context summary from frontend)
            yield {
                "type": "complete",
                "data": {
                    "bundles": [b.model_dump() for b in bundles],
                    "metrics": metrics.model_dump(),
                    "web_context_summary": "",  # Hidden from frontend
                    "execution_time_seconds": execution_time,
                },
            }

        except Exception as e:
            logger.error(f"Error in hedge stream: {e}", exc_info=True)
            yield {"type": "error", "data": {"message": str(e)}}

    def close(self):
        """Clean up resources."""
        try:
            self.cerebras_filter.close()
            logger.info("HedgeService resources closed")
        except Exception as e:
            logger.warning(f"Error closing HedgeService resources: {e}")
