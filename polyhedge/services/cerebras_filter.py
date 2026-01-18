"""Cerebras-powered fast market filtering service."""

import json
import httpx
from typing import List

from polyhedge.config import Settings
from polyhedge.logger import get_logger
from polyhedge.models.market import Market

logger = get_logger(__name__)


class CerebrasMarketFilter:
    """Fast batch filtering using Cerebras Llama 3.1-8b."""

    def __init__(self, settings: Settings):
        self.api_key = settings.cerebras_api_key
        if not self.api_key:
            raise ValueError(
                "CEREBRAS_API_KEY not configured. "
                "Add it to your .env file to use the streamlined workflow."
            )

        self.client = httpx.Client(
            base_url="https://api.cerebras.ai/v1",
            headers={"Authorization": f"Bearer {self.api_key}"},
            timeout=30.0,  # Increased timeout for larger batches
        )
        logger.info("CerebrasMarketFilter initialized")

    def filter_batch(
        self,
        markets: List[Market],
        user_concern: str,
        top_k: int = 10,
        web_context: str = ""
    ) -> List[Market]:
        """
        Filter a batch of markets and return the top K most relevant.

        Args:
            markets: List of markets to filter (typically 100)
            user_concern: User's primary concern text
            top_k: Number of top markets to return (default: 10)
            web_context: Compressed web search context (optional)

        Returns:
            List of top K markets sorted by relevance
        """
        logger.info(f"Filtering {len(markets)} markets to top {top_k}")

        # Format markets for prompt
        markets_list = []
        for i, m in enumerate(markets, 1):
            markets_list.append(
                f"{i}. ID: {m.id}\n"
                f"   Question: {m.question}\n"
                f"   Liquidity: ${m.liquidity:,.0f}"
            )
        markets_text = "\n\n".join(markets_list)

        # Add web context section if available
        context_section = ""
        if web_context:
            context_section = f"""
RECENT WEB CONTEXT:
{web_context}

Use this context to better understand the user's concern and current events.

"""

        # Construct prompt
        prompt = f"""You are a financial risk analyst helping users find prediction markets to hedge their concerns.

USER'S CONCERN:
{user_concern}

{context_section}AVAILABLE MARKETS:
{markets_text}

TASK:
Identify the top {top_k} markets most relevant for hedging this concern. Consider:
- Direct correlations (market outcome directly affects the concern)
- Leading indicators (market predicts conditions that cause the concern)
- Indirect hedges (market outcomes offset financial impact of the concern)
- Recent events and context from web search results

Return a JSON object with:
{{
  "top_market_ids": ["id1", "id2", ...],
  "reasoning": "Brief explanation of selection strategy"
}}

Only include market IDs from the list above. Order by relevance (most relevant first)."""

        try:
            response = self.client.post(
                "/chat/completions",
                json={
                    "model": "llama-3.3-70b",
                    "messages": [
                        {
                            "role": "system",
                            "content": "You are a financial analyst that outputs JSON."
                        },
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.0,
                    "max_completion_tokens": 2048,  # Allow for reasoning
                }
            )
            response.raise_for_status()

            data = response.json()
            content = json.loads(data["choices"][0]["message"]["content"])

            selected_ids = content.get("top_market_ids", [])
            reasoning = content.get("reasoning", "No reasoning provided")

            logger.debug(f"Cerebras selection reasoning: {reasoning}")
            logger.info(f"Selected {len(selected_ids)} markets from batch")

            # Return markets in order of selection
            id_to_market = {m.id: m for m in markets}
            filtered = [id_to_market[mid] for mid in selected_ids if mid in id_to_market]

            return filtered[:top_k]  # Ensure we don't exceed top_k

        except Exception as e:
            logger.error(f"Cerebras filtering error: {e}")
            # Fallback: return top K by liquidity if Cerebras fails
            logger.warning("Falling back to liquidity-based selection")
            sorted_by_liq = sorted(markets, key=lambda m: m.liquidity or 0, reverse=True)
            return sorted_by_liq[:top_k]

    def filter_in_batches(
        self,
        markets: List[Market],
        user_concern: str,
        batch_size: int = 100,
        top_k_per_batch: int = 10,
        web_context: str = ""
    ) -> List[Market]:
        """
        Filter large list of markets in batches.

        Args:
            markets: Full list of markets (e.g., 500)
            user_concern: User's concern
            batch_size: Markets per batch (default: 100)
            top_k_per_batch: Top markets to keep per batch (default: 10)
            web_context: Compressed web search context (optional)

        Returns:
            Combined list of filtered markets (batch_count × top_k_per_batch)
        """
        total_batches = (len(markets) + batch_size - 1) // batch_size
        logger.info(
            f"Processing {len(markets)} markets in {total_batches} batches "
            f"of {batch_size}, keeping top {top_k_per_batch} per batch"
        )

        all_filtered = []

        for batch_num in range(total_batches):
            start = batch_num * batch_size
            end = min(start + batch_size, len(markets))
            batch = markets[start:end]

            logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} markets)")

            filtered = self.filter_batch(batch, user_concern, top_k_per_batch, web_context)
            all_filtered.extend(filtered)

            logger.info(
                f"Batch {batch_num + 1}/{total_batches} complete, "
                f"kept {len(filtered)} markets"
            )

        logger.info(f"Total filtered markets: {len(all_filtered)}")
        return all_filtered

    def close(self):
        """Clean up HTTP client."""
        self.client.close()
        logger.debug("CerebrasMarketFilter client closed")
