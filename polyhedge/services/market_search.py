"""Market search service using Polymarket Gamma API."""

import json
import httpx

from polyhedge.config import Settings
from polyhedge.logger import get_logger
from polyhedge.models.market import Market, Outcome
from polyhedge.models.risk import RiskAnalysis
from polyhedge.services.cache import MarketCache

logger = get_logger(__name__)


class MarketSearch:
    """Searches Polymarket for relevant prediction markets."""

    def __init__(self, settings: Settings, use_vector_search: bool = True):
        self.base_url = settings.gamma_api_base_url
        self.client = httpx.Client(timeout=30.0)
        self.cache = MarketCache(use_vectors=use_vector_search)
        self.use_vector_search = use_vector_search
        logger.info(f"MarketSearch initialized with base URL: {self.base_url} (vector search: {use_vector_search})")

    def search(self, risk_analysis: RiskAnalysis, use_cache_only: bool = True) -> list[Market]:
        """Search for markets relevant to the identified risks.

        Args:
            risk_analysis: The risk analysis containing risk factors
            use_cache_only: If True, only use cached markets. If False, fetch from API if cache is empty.
        """
        logger.info("=== Starting Market Search ===")

        # Ensure markets are loaded (from cache or fetch)
        if not use_cache_only:
            _ = self._fetch_all_markets()
        else:
            # Check cache only
            cached = self.cache.get_markets()
            if not cached:
                logger.error("No cached markets found. Run 'polyhedge update-cache' first.")
                raise ValueError("Market cache is empty. Please run 'polyhedge update-cache' to fetch markets first.")

        if self.use_vector_search and self.cache.vector_db:
            logger.info("Using vector search for semantic matching")
            return self._search_with_vectors(risk_analysis)
        else:
            logger.info("Using keyword-based search")
            return self._search_with_keywords(risk_analysis)

    def _search_with_vectors(self, risk_analysis: RiskAnalysis) -> list[Market]:
        """Search for markets using vector semantic search."""
        all_markets: dict[str, Market] = {}
        market_scores: dict[str, float] = {}

        # Search for each risk factor
        for factor in risk_analysis.risk_factors:
            # Combine name, description, and keywords for better semantic matching
            query = f"{factor.name}. {factor.description}. {' '.join(factor.keywords)}"
            logger.debug(f"Vector search for: {factor.name}")

            # Get semantically similar markets
            results = self.cache.search_semantic(
                query,
                n_results=50,
                min_liquidity=100,
            )

            for market, score in results:
                if market.id not in all_markets:
                    all_markets[market.id] = market
                    market_scores[market.id] = score
                else:
                    # Keep highest score if market appears in multiple searches
                    market_scores[market.id] = max(market_scores[market.id], score)

        # Sort by semantic similarity score
        markets = sorted(
            all_markets.values(),
            key=lambda m: market_scores[m.id],
            reverse=True,
        )

        logger.info(f"Vector search found {len(markets)} relevant markets")
        return markets

    def update_cache(self) -> int:
        """Fetch all markets from API and update the cache.

        Returns:
            Number of markets cached
        """
        logger.info("=== Updating Market Cache ===")
        markets = self._fetch_all_markets()
        logger.info(f"Cache updated with {len(markets)} markets")
        return len(markets)

    def _search_with_keywords(self, risk_analysis: RiskAnalysis) -> list[Market]:
        """Search for markets using keyword matching (legacy method)."""
        all_markets: dict[str, Market] = {}

        # Collect keywords for prioritization in sorting
        all_keywords: set[str] = set()

        for factor in risk_analysis.risk_factors:
            all_keywords.update(kw.lower() for kw in factor.keywords)
            all_keywords.update(q.lower() for q in factor.search_queries)

        logger.debug(f"Keywords for sorting: {list(all_keywords)[:20]}...")

        # Get markets from cache
        cached = self.cache.get_markets()
        if cached:
            for market in cached:
                all_markets[market.id] = market

        markets = list(all_markets.values())
        logger.info(f"Total unique markets: {len(markets)}")

        # Sort markets: keyword matches first, then by liquidity
        def sort_key(market: Market) -> tuple[int, float]:
            text = f"{market.question.lower()} {market.description.lower()}"
            has_keyword = any(kw in text for kw in all_keywords)
            return (0 if has_keyword else 1, -market.liquidity)

        markets.sort(key=sort_key)
        logger.info("Markets sorted by keyword relevance and liquidity")

        return markets

    def _fetch_all_markets(self, max_markets: int = 50000) -> list[Market]:
        """Fetch all active markets using cache if available."""
        logger.info("Fetching all markets")
        
        # Try to get from cache first
        cached_markets = self.cache.get_markets()
        if cached_markets:
            logger.info(f"Cache hit: loaded {len(cached_markets)} markets from cache")
            return cached_markets
        
        logger.info("Cache miss: fetching from API")
        all_markets: dict[str, Market] = {}

        # Fetch from /markets endpoint
        logger.info("Fetching from /markets endpoint")
        markets_from_markets = self._fetch_from_markets_endpoint(max_markets)
        logger.info(f"Got {len(markets_from_markets)} markets from /markets")
        for m in markets_from_markets:
            all_markets[m.id] = m

        # Fetch from /events endpoint
        logger.info("Fetching from /events endpoint")
        markets_from_events = self._fetch_from_events_endpoint(max_markets)
        logger.info(f"Got {len(markets_from_events)} markets from /events")
        for m in markets_from_events:
            all_markets[m.id] = m

        markets_list = list(all_markets.values())
        logger.info(f"Total unique markets after dedup: {len(markets_list)}")
        
        # Save to cache
        self.cache.save_markets(markets_list)
        logger.info("Markets saved to cache")
        
        return markets_list

    def _fetch_from_markets_endpoint(self, max_markets: int) -> list[Market]:
        """Fetch active markets from the /markets endpoint with pagination."""
        all_markets = []
        offset = 0
        batch_size = 500

        while True:
            try:
                url = f"{self.base_url}/markets"
                params = {
                    "limit": batch_size,
                    "offset": offset,
                    "active": "true",
                    "closed": "false",
                    "enable_order_book": "true",
                }
                logger.debug(f"Fetching /markets offset={offset}")
                response = self.client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if not data:
                    logger.debug("No more data from /markets")
                    break

                for item in data:
                    market = self._parse_market(item)
                    if market:
                        all_markets.append(market)

                logger.debug(f"Batch: {len(data)} items, total: {len(all_markets)}")
                
                if len(all_markets) >= max_markets:
                    logger.info(f"Reached max_markets limit: {max_markets}")
                    break
                
                offset += batch_size
                if len(data) < batch_size:
                    break
            except Exception as e:
                logger.error(f"Error fetching /markets at offset {offset}: {e}")
                break

        return all_markets

    def _fetch_from_events_endpoint(self, max_markets: int) -> list[Market]:
        """Fetch markets from the /events endpoint (includes multi-outcome markets, etc.)."""
        all_markets = []
        offset = 0
        batch_size = 500

        while True:
            try:
                url = f"{self.base_url}/events"
                params = {
                    "limit": batch_size,
                    "offset": offset,
                    "active": "true",
                    "closed": "false",
                    "enable_order_book": "true",
                }
                logger.debug(f"Fetching /events offset={offset}")
                response = self.client.get(url, params=params)
                response.raise_for_status()
                data = response.json()

                if not data:
                    logger.debug("No more data from /events")
                    break

                for event in data:
                    nested_markets = event.get("markets", [])
                    event_title = event.get("title", "")
                    event_description = event.get("description", "")

                    event_slug = event.get("slug", "")

                    for item in nested_markets:
                        if not item.get("description"):
                            item["description"] = event_description
                        item["_event_title"] = event_title
                        item["_event_slug"] = event_slug

                        market = self._parse_market(item)
                        if market:
                            all_markets.append(market)

                logger.debug(f"Events batch: {len(data)} events, total markets: {len(all_markets)}")
                
                if len(all_markets) >= max_markets:
                    logger.info(f"Reached max_markets limit: {max_markets}")
                    break

                offset += batch_size
                if len(data) < batch_size:
                    break
            except Exception as e:
                logger.error(f"Error fetching /events at offset {offset}: {e}")
                break

        return all_markets

    def _parse_market(self, item: dict) -> Market | None:
        """Parse a market from API response."""
        try:
            outcomes = self._parse_outcomes(item)

            # Use direct field access with fallback - unnecessary defensive loops removed
            liquidity = float(item.get("liquidity") or item.get("liquidityNum") or 0)
            volume = float(item.get("volume") or item.get("volumeNum") or 0)
            
            # Get slug for Polymarket URL
            # Prioritize parent event slug if available (for multi-outcome markets)
            slug = item.get("_event_slug") or item.get("slug") or item.get("conditionId") or item.get("id")

            return Market(
                id=str(item.get("id", "")),
                question=item.get("question", ""),
                description=item.get("description", ""),
                outcomes=outcomes,
                liquidity=liquidity,
                volume=volume,
                end_date=item.get("endDate"),
                active=True,  # Filtered by API parameters
                slug=slug,
            )
        except Exception:
            return None

    def _parse_outcomes(self, item: dict) -> list[Outcome]:
        """Parse outcomes from market data."""
        outcomes = []

        if "outcomePrices" in item and item["outcomePrices"]:
            prices = item["outcomePrices"]
            if isinstance(prices, str):
                try:
                    prices = json.loads(prices)
                except json.JSONDecodeError:
                    prices = []

            outcome_names = ["Yes", "No"]
            if "outcomes" in item and item["outcomes"]:
                raw_outcomes = item["outcomes"]
                if isinstance(raw_outcomes, str):
                    try:
                        outcome_names = json.loads(raw_outcomes)
                    except json.JSONDecodeError:
                        pass
                elif isinstance(raw_outcomes, list):
                    outcome_names = raw_outcomes

            for i, price in enumerate(prices):
                name = outcome_names[i] if i < len(outcome_names) else f"Outcome {i+1}"
                try:
                    outcomes.append(Outcome(name=name, price=float(price)))
                except (ValueError, TypeError):
                    pass

        return outcomes

    def get_market_details(self, market_id: str) -> dict | None:
        """Fetch detailed stats for a single market from Polymarket API."""
        try:
            url = f"{self.base_url}/markets/{market_id}"
            response = self.client.get(url)
            response.raise_for_status()
            data = response.json()
            
            # Parse stringified JSON fields
            for field in ["outcomes", "outcomePrices", "clobTokenIds"]:
                if field in data and isinstance(data[field], str):
                    try:
                        data[field] = json.loads(data[field])
                    except json.JSONDecodeError:
                        logger.warning(f"Failed to parse {field} for market {market_id}")
                        data[field] = []
            
            return data
        except Exception as e:
            logger.error(f"Error fetching market details for {market_id}: {e}")
            return None

    
    def get_token_history(self, token_id: str, interval: str = "1d") -> list[dict] | None:
        """Fetch price history for a specific token (outcome)."""
        try:
            # Polymarket CLOB History API
            url = "https://clob.polymarket.com/prices-history"
            params = {
                "market": token_id,
                "interval": interval,
                "fidelity": 60  # Minute-level fidelity if possible, or adjusting based on interval
            }
            response = self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
            return data.get("history", [])
        except Exception as e:
            logger.error(f"Error fetching history for token {token_id}: {e}")
            return None

    def close(self):
        """Close the HTTP client."""
        self.client.close()
