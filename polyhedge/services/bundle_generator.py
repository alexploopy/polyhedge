"""Bundle generator service for creating hedge recommendations."""

import anthropic

from polyhedge.config import Settings
from polyhedge.logger import get_logger
from polyhedge.models.hedge import HedgeBet, HedgeBundle
from polyhedge.models.market import Market, ScoredMarket
from polyhedge.models.risk import RiskAnalysis

logger = get_logger(__name__)


class BundleGenerator:
    """Generates hedge bundles from scored markets."""

    def __init__(self, settings: Settings):
        self.settings = settings
        self.max_markets = settings.max_markets_in_bundle
        self.default_budget = settings.default_budget
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key, timeout=300.0)
        self.model = settings.model
        self.max_tokens = settings.max_tokens
        logger.debug(f"BundleGenerator initialized (max_markets={self.max_markets}, default_budget=${self.default_budget})")

    def generate(
        self,
        scored_markets: list[ScoredMarket],
        risk_analysis: RiskAnalysis,
        budget: float | None = None,
    ) -> HedgeBundle:
        """Generate a hedge bundle from scored markets."""
        if budget is None:
            budget = self.default_budget
        
        logger.info(f"Generating bundle from {len(scored_markets)} scored markets with ${budget} budget")

        # Select top diverse markets
        selected = self._select_diverse_markets(scored_markets)
        logger.info(f"Selected {len(selected)} diverse markets for bundle")

        if not selected:
            logger.warning("No suitable markets found for hedging")
            return HedgeBundle(
                budget=budget,
                bets=[],
                total_allocated=0,
                coverage_summary="No suitable markets found for hedging.",
                risk_factors_covered=[],
            )

        # Allocate budget proportionally to scores
        bets = self._allocate_budget(selected, budget)
        logger.debug(f"Allocated budget across {len(bets)} bets")

        # Build coverage summary
        covered_factors = self._identify_covered_factors(selected, risk_analysis)
        coverage_summary = self._build_coverage_summary(bets, covered_factors)
        
        total_allocated = sum(b.allocation for b in bets)
        logger.info(f"Bundle complete: {len(bets)} bets, ${total_allocated:.2f} allocated, {len(covered_factors)} risk factors covered")

        return HedgeBundle(
            budget=budget,
            bets=bets,
            total_allocated=total_allocated,
            coverage_summary=coverage_summary,
            risk_factors_covered=covered_factors,
        )

    def _select_diverse_markets(
        self, scored_markets: list[ScoredMarket]
    ) -> list[ScoredMarket]:
        """Select top diverse markets, avoiding too similar ones."""
        if not scored_markets:
            return []

        # Include markets with any meaningful relevance (even weak correlations)
        # Threshold of 0.1 allows weak but real correlations
        candidates = [sm for sm in scored_markets if sm.adjusted_score >= 0.1]
        logger.debug(f"Found {len(candidates)} candidates with score >= 0.1")

        if not candidates:
            # Fall back to top markets if none meet threshold
            candidates = scored_markets[: self.max_markets]
            logger.debug(f"No candidates met threshold, using top {len(candidates)} markets")

        selected: list[ScoredMarket] = []
        seen_keywords: set[str] = set()

        for sm in candidates:
            if len(selected) >= self.max_markets:
                break

            # Check for diversity (avoid too similar markets)
            question_words = set(sm.market.question.lower().split())
            overlap = len(question_words & seen_keywords) / max(len(question_words), 1)

            if overlap < 0.5:  # Less than 50% overlap
                selected.append(sm)
                seen_keywords.update(question_words)
                logger.debug(f"Selected: {sm.market.question[:60]}... (score={sm.adjusted_score:.3f})")
            else:
                logger.debug(f"Skipped (too similar, {overlap:.0%} overlap): {sm.market.question[:40]}...")

        return selected

    def _allocate_budget(
        self, markets: list[ScoredMarket], budget: float
    ) -> list[HedgeBet]:
        """Allocate budget proportionally to adjusted scores."""
        if not markets:
            return []

        total_score = sum(m.adjusted_score for m in markets)
        if total_score == 0:
            # Equal allocation if all scores are zero
            total_score = len(markets)
            weights = [1 / len(markets)] * len(markets)
        else:
            weights = [m.adjusted_score / total_score for m in markets]

        bets = []
        for market, weight in zip(markets, weights):
            allocation = budget * weight
            price = self._get_outcome_price(market)
            payout_multiplier = 1 / price if price > 0 else 1
            potential_payout = allocation * payout_multiplier

            bet = HedgeBet(
                market=market,
                outcome=market.recommended_outcome,
                allocation=round(allocation, 2),
                allocation_percent=round(weight * 100, 1),
                current_price=price,
                potential_payout=round(potential_payout, 2),
                payout_multiplier=round(payout_multiplier, 2),
            )
            bets.append(bet)

        return bets

    def _get_outcome_price(self, market: ScoredMarket) -> float:
        """Get the price of the recommended outcome."""
        for outcome in market.market.outcomes:
            if outcome.name.lower() == market.recommended_outcome.lower():
                return outcome.price
        # Default to 0.5 if not found
        return 0.5

    def _identify_covered_factors(
        self, markets: list[ScoredMarket], risk_analysis: RiskAnalysis
    ) -> list[str]:
        """Identify which risk factors are covered by the selected markets."""
        covered = set()

        for sm in markets:
            explanation_lower = sm.correlation_explanation.lower()
            question_lower = sm.market.question.lower()
            text = f"{explanation_lower} {question_lower}"

            for factor in risk_analysis.risk_factors:
                # Check if any keywords match
                for keyword in factor.keywords:
                    if keyword.lower() in text:
                        covered.add(factor.name)
                        break

                # Also check factor name
                if factor.name.lower() in text:
                    covered.add(factor.name)

        return list(covered)

    def _build_coverage_summary(
        self, bets: list[HedgeBet], covered_factors: list[str]
    ) -> str:
        """Build a human-readable coverage summary."""
        if not bets:
            return "No hedges recommended."

        lines = [f"Hedge bundle with {len(bets)} market(s):"]

        if covered_factors:
            lines.append(f"Covers risk factors: {', '.join(covered_factors)}")

        total_payout = sum(b.potential_payout for b in bets)
        total_allocation = sum(b.allocation for b in bets)
        avg_multiplier = total_payout / total_allocation if total_allocation > 0 else 1

        lines.append(f"Average payout multiplier: {avg_multiplier:.1f}x")

        return " ".join(lines)

    def generate_etf_bundles(
        self,
        markets: list[Market],
        user_concern: str,
        budget: float,
        web_context: str = ""
    ) -> list[HedgeBundle]:
        """
        Create ETF-style themed bundles from filtered markets.
        
        Each bundle is a MUTUALLY EXCLUSIVE option - the user picks one.
        Each bundle receives the FULL budget allocation.

        Args:
            markets: Pre-filtered markets (typically 50 from Cerebras)
            user_concern: User's original concern
            budget: Total budget to allocate (each bundle gets full amount)
            web_context: Compressed web search context (optional)

        Returns:
            List of HedgeBundle objects, each representing a standalone hedge strategy
        """
        logger.info(f"Generating ETF bundles from {len(markets)} markets, budget=${budget}")

        if not markets:
            logger.warning("No markets provided for ETF bundle generation")
            return [HedgeBundle(
                budget=budget,
                bets=[],
                total_allocated=0,
                coverage_summary="No markets available for hedging.",
                risk_factors_covered=[],
            )]

        # Use Claude to analyze and group markets into themes with correlation scores
        themes = self._identify_market_themes(markets, user_concern, web_context)
        logger.info(f"Identified {len(themes)} themes")

        # Create a bundle for each theme - each bundle gets the FULL budget
        bundles = []
        for theme in themes:
            bundle = self._create_theme_bundle(
                theme,
                user_concern,
                budget  # Full budget for each bundle (mutually exclusive)
            )
            bundles.append(bundle)
            logger.debug(f"Created bundle for theme: {theme['name']}")

        return bundles

    def _identify_market_themes(
        self,
        markets: list[Market],
        user_concern: str,
        web_context: str = ""
    ) -> list[dict]:
        """Use Claude to identify market themes/categories."""

        logger.info("Identifying market themes with Claude")

        markets_summary = "\n".join([
            f"{i+1}. {m.question} (${m.liquidity:,.0f} liquidity)"
            for i, m in enumerate(markets)
        ])

        # Add web context section if available
        context_section = ""
        if web_context:
            context_section = f"""
RECENT WEB CONTEXT:
{web_context}

Use this context to better understand current events and trends related to the user's concern.

"""

        prompt = f"""You are organizing prediction markets into themed ETF-style portfolios for hedging.

USER'S CONCERN:
{user_concern}

{context_section}AVAILABLE MARKETS ({len(markets)} total):
{markets_summary}

TASK:
Group these markets into 3-5 coherent themes/categories that make sense as separate hedge portfolios.
Each theme should contain 6-8 markets (or as many valid ones as possible) to maximize diversification and coverage.
Focus on DIVERSIFICATION - including more markets reduces overall risk.
Each theme should represent a distinct hedging strategy or risk angle.
Consider the recent web context to create relevant, timely themes.

For each market in a theme, assign a correlation_score (0.0-1.0) indicating how strongly 
that market correlates with the user's concern. Higher scores = stronger hedge value.

Return JSON:
{{
  "themes": [
    {{
      "name": "Theme name",
      "description": "Why this theme hedges the concern",
      "markets": [
        {{"index": 1, "correlation_score": 0.9, "explanation": "One sentence explaining why...", "recommended_outcome": "Yes"}},
        {{"index": 3, "correlation_score": 0.7, "explanation": "One sentence explaining why...", "recommended_outcome": "No"}},
        ...
      ]
    }},
    ...
  ]
}}"""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                messages=[{"role": "user", "content": prompt}],
                tools=[{
                    "name": "organize_themes",
                    "description": "Organize markets into themed portfolios with correlation scores",
                    "input_schema": {
                        "type": "object",
                        "properties": {
                            "themes": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {"type": "string"},
                                        "description": {"type": "string"},
                                        "markets": {
                                            "type": "array",
                                            "items": {
                                                "type": "object",
                                                "properties": {
                                                    "index": {"type": "integer"},
                                                    "correlation_score": {"type": "number"},
                                                    "explanation": {"type": "string"},
                                                    "recommended_outcome": {"type": "string", "description": "The specific outcome to bet on (e.g. 'Yes', 'No', 'Trump'). Must match one of the market's available outcomes."}
                                                },
                                                "required": ["index", "correlation_score", "explanation", "recommended_outcome"]
                                            }
                                        }
                                    },
                                    "required": ["name", "description", "markets"]
                                }
                            }
                        },
                        "required": ["themes"]
                    }
                }]
            )

            # Extract themes from tool use
            for block in response.content:
                if block.type == "tool_use" and block.name == "organize_themes":
                    themes_data = block.input["themes"]

                    # Convert indices to actual markets with correlation scores
                    themes = []
                    for theme in themes_data:
                        theme_markets = []
                        for market_entry in theme["markets"]:
                            idx = market_entry["index"]
                            if 1 <= idx <= len(markets):
                                theme_markets.append({
                                    "market": markets[idx - 1],
                                    "correlation_score": market_entry.get("correlation_score", 0.5),
                                    "explanation": market_entry.get("explanation", ""),
                                    "recommended_outcome": market_entry.get("recommended_outcome", "")
                                })
                        themes.append({
                            "name": theme["name"],
                            "description": theme["description"],
                            "markets": theme_markets
                        })

                    logger.info(f"Claude organized markets into {len(themes)} themes")

                    # Log detailed theme assignments
                    for i, theme in enumerate(themes, 1):
                        logger.info(f"=== Theme {i}: {theme['name']} ===")
                        logger.info(f"    Description: {theme['description'][:100]}...")
                        logger.info(f"    Markets assigned: {len(theme['markets'])}")
                        for j, entry in enumerate(theme['markets'], 1):
                            market = entry['market']
                            score = entry['correlation_score']
                            question = market.question[:60] + "..." if len(market.question) > 60 else market.question
                            logger.info(f"      [{j}] (corr={score:.2f}) {question}")

                    return themes

        except Exception as e:
            logger.error(f"Error identifying themes with Claude: {e}")

        # Fallback: single theme with all markets (equal correlation)
        logger.warning("Falling back to single theme with all markets")
        return [{
            "name": "Primary Hedge",
            "description": "All relevant markets",
            "markets": [{"market": m, "correlation_score": 0.5} for m in markets]
        }]

    def _create_theme_bundle(
        self,
        theme: dict,
        user_concern: str,
        budget: float
    ) -> HedgeBundle:
        """Create a bundle for a specific theme with correlation-weighted allocation."""

        market_entries = theme["markets"]  # List of {"market": Market, "correlation_score": float}
        logger.debug(f"Creating bundle for theme '{theme['name']}' with {len(market_entries)} markets")

        if not market_entries:
            return HedgeBundle(
                budget=budget,
                bets=[],
                total_allocated=0,
                coverage_summary=f"{theme['name']}: No markets in theme",
                risk_factors_covered=[]
            )

        # Calculate total correlation score for weighted allocation
        total_correlation = sum(entry["correlation_score"] for entry in market_entries)
        if total_correlation == 0:
            total_correlation = len(market_entries)  # Equal weights if all zeros

        bets = []
        for entry in market_entries:
            market = entry["market"]
            correlation_score = entry["correlation_score"]
            
            # Weight allocation by correlation score
            weight = correlation_score / total_correlation
            allocation = budget * weight

            # Determine outcome to bet on
            outcome_name = entry.get("recommended_outcome", "")
            final_outcome = None
            
            if outcome_name and market.outcomes:
                # Try to find exact match first
                for o in market.outcomes:
                    if o.name.lower() == outcome_name.lower():
                        final_outcome = o
                        break
                
                # If no exact match (e.g. AI said "Trump" but outcome is "Donald Trump"), try partial match
                if not final_outcome:
                    for o in market.outcomes:
                        if outcome_name.lower() in o.name.lower() or o.name.lower() in outcome_name.lower():
                            final_outcome = o
                            break

            # Fallback to cheapest price if no valid outcome found or specified
            if not final_outcome and market.outcomes:
                 # Default to picking the cheapest option (highest leverage) if no specific recommendation
                 final_outcome = min(market.outcomes, key=lambda o: o.price)
            
            if not final_outcome:
                continue

            bet = HedgeBet(
                market=ScoredMarket(
                    market=market,
                    relevance_score=correlation_score,
                    adjusted_score=correlation_score,
                    correlation_explanation=entry.get("explanation", theme["description"]),
                    recommended_outcome=final_outcome.name,
                    correlation_direction="positive",
                    risk_factors_addressed=[]
                ),
                outcome=final_outcome.name,
                allocation=round(allocation, 2),
                allocation_percent=round(weight * 100, 1),
                current_price=final_outcome.price,
                potential_payout=round(allocation / final_outcome.price, 2) if final_outcome.price > 0 else 0,
                payout_multiplier=round(1 / final_outcome.price, 2) if final_outcome.price > 0 else 0
            )
            bets.append(bet)

        total_allocated = sum(b.allocation for b in bets)

        return HedgeBundle(
            budget=budget,
            bets=bets,
            total_allocated=total_allocated,
            coverage_summary=f"{theme['name']}: {theme['description']}",
            risk_factors_covered=[]
        )
