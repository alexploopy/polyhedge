"""Relevance scoring service using LLM and heuristics."""

import json

import anthropic
import httpx

from polyhedge.config import Settings
from polyhedge.logger import get_logger
from polyhedge.models.market import Market, ScoredMarket
from polyhedge.models.risk import RiskAnalysis

logger = get_logger(__name__)


BATCH_FILTER_TOOL = {
    "name": "filter_relevant_markets",
    "description": "Identify which markets from a batch could be relevant for hedging",
    "input_schema": {
        "type": "object",
        "properties": {
            "relevant_market_ids": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of market IDs that have ANY potential relevance (direct or indirect) to the user's risks",
            },
        },
        "required": ["relevant_market_ids"],
    },
}

SCORING_TOOL = {
    "name": "score_markets",
    "description": "Score multiple prediction markets for relevance to user's risk factors",
    "input_schema": {
        "type": "object",
        "properties": {
            "scored_markets": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "market_id": {
                            "type": "string",
                            "description": "The market ID being scored",
                        },
                        "relevance_score": {
                            "type": "number",
                            "minimum": 0,
                            "maximum": 1,
                            "description": "How relevant this market is to the user's risks (0-1)",
                        },
                        "correlation_direction": {
                            "type": "string",
                            "enum": ["positive", "negative"],
                            "description": "positive = market YES correlates with risk occurring",
                        },
                        "correlation_explanation": {
                            "type": "string",
                            "description": "Brief explanation of the correlation",
                        },
                        "recommended_outcome": {
                            "type": "string",
                            "description": "Which outcome to bet on to hedge",
                        },
                    },
                    "required": [
                        "market_id",
                        "relevance_score",
                        "correlation_direction",
                        "correlation_explanation",
                        "recommended_outcome",
                    ],
                },
            },
        },
        "required": ["scored_markets"],
    },
}

FILTER_SYSTEM_PROMPT = """You are a financial analyst finding prediction markets that could hedge real-life risks.

Your job is to identify ALL markets that have ANY potential connection to the user's situation, including:
- DIRECT correlations (e.g., "recession" market for job loss risk)
- INDIRECT correlations (e.g., "interest rates" for housing market risk)
- WEAK correlations (e.g., "temperature in Toronto" for outdoor wedding weather risk)
- GEOGRAPHIC matches (e.g., any market mentioning the user's location)
- TEMPORAL matches (e.g., markets about events happening around the same time)

Be INCLUSIVE - it's better to include a marginally relevant market than miss one.
The user wants to find hedging opportunities even if the correlation is weak.

Return the IDs of ALL markets that could possibly be used to hedge the user's risks."""

SCORING_SYSTEM_PROMPT = """You are a financial analyst specializing in prediction markets and risk hedging.

Score each market's relevance to the user's risks. Consider ALL types of correlations:

Scoring guide:
- 0.8-1.0: Directly related to the user's core risk
- 0.6-0.8: Strongly related or a leading indicator
- 0.4-0.6: Moderately related, clear correlation
- 0.2-0.4: Weakly related, indirect but real correlation
- 0.1-0.2: Tangentially related, speculative correlation

IMPORTANT: Do NOT score 0 unless there is truly no conceivable connection.
Even weak correlations (0.1-0.3) can be valuable hedges if they're the best available.

For correlation direction:
- POSITIVE: Market YES outcome occurs when user's risk materializes
- NEGATIVE: Market YES outcome occurs when user's risk does NOT materialize

For recommended outcome:
- To hedge, bet on the outcome that pays when the user's risk occurs
- If positive correlation: recommend YES
- If negative correlation: recommend NO"""


class RelevanceScorer:
    """Scores markets for relevance to user's risks."""

    def __init__(self, settings: Settings):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.model = settings.model
        self.max_tokens = settings.max_tokens

        # Cerebras client for optimized high-volume filtering
        self.cerebras_key = settings.cerebras_api_key
        self.cerebras_client = None
        if self.cerebras_key:
            self.cerebras_client = httpx.Client(
                base_url="https://api.cerebras.ai/v1",
                headers={"Authorization": f"Bearer {self.cerebras_key}"},
                timeout=10.0,
            )
            logger.info("RelevanceScorer initialized with Cerebras for fast filtering")
        else:
            logger.info("RelevanceScorer initialized (no Cerebras, using Claude for filtering)")

    def score_markets(
        self, markets: list[Market], risk_analysis: RiskAnalysis
    ) -> list[ScoredMarket]:
        """Score all markets for relevance to the user's risks."""
        logger.info("=== Starting Relevance Scoring ===")
        logger.info(f"Total markets to process: {len(markets)}")
        
        if not markets:
            logger.warning("No markets to score")
            return []

        risk_context = self._build_risk_context(risk_analysis)
        logger.debug(f"Risk context:\n{risk_context}")

        # Phase 1: Batch filter to find potentially relevant markets
        logger.info("Phase 1: Filtering markets for relevance")
        relevant_ids = self._batch_filter_markets(markets, risk_context)
        logger.info(f"Phase 1 complete: {len(relevant_ids)} potentially relevant markets")

        if not relevant_ids:
            logger.warning("No relevant markets found after filtering")
            return []

        # Get only relevant markets
        relevant_markets = [m for m in markets if m.id in relevant_ids]

        # Phase 2: Score the relevant markets in batches
        logger.info(f"Phase 2: Scoring {len(relevant_markets)} markets")
        scored_markets = self._batch_score_markets(relevant_markets, risk_context)
        logger.info(f"Phase 2 complete: {len(scored_markets)} markets scored")

        # Apply heuristic adjustments
        logger.info("Applying heuristic adjustments")
        scored_markets = self._apply_heuristics(scored_markets)

        # Sort by adjusted score
        scored_markets.sort(key=lambda x: x.adjusted_score, reverse=True)
        
        if scored_markets:
            logger.info(f"Top 5 markets by score:")
            for i, sm in enumerate(scored_markets[:5]):
                logger.info(f"  {i+1}. {sm.market.question[:60]}... (score: {sm.adjusted_score:.3f})")

        return scored_markets

    def _build_risk_context(self, risk_analysis: RiskAnalysis) -> str:
        """Build context string from risk analysis."""
        lines = [
            f"User Situation: {risk_analysis.situation_summary}",
            f"Overall Risk Level: {risk_analysis.overall_risk_level}",
            "",
            "Risk Factors:",
        ]

        for factor in risk_analysis.risk_factors:
            lines.append(f"- {factor.name} ({factor.category}): {factor.description}")
            lines.append(f"  Keywords: {', '.join(factor.keywords)}")

        return "\n".join(lines)

    def _batch_filter_markets(
        self, markets: list[Market], risk_context: str
    ) -> set[str]:
        """Filter markets in batches to find potentially relevant ones."""
        relevant_ids: set[str] = set()
        batch_size = 100 if self.cerebras_client else 50 
        total_batches = (len(markets) + batch_size - 1) // batch_size
        logger.info(f"Filtering in {total_batches} batches of {batch_size}")

        for i in range(0, len(markets), batch_size):
            batch = markets[i : i + batch_size]
            batch_num = i // batch_size + 1
            
            if self.cerebras_client:
                logger.debug(f"Batch {batch_num}/{total_batches}: Cerebras filtering {len(batch)} markets")
                batch_relevant = self._filter_batch_cerebras(batch, risk_context)
            else:
                logger.debug(f"Batch {batch_num}/{total_batches}: Claude filtering {len(batch)} markets")
                batch_relevant = self._filter_batch(batch, risk_context)
            
            logger.debug(f"Batch {batch_num} found {len(batch_relevant)} relevant markets")
            relevant_ids.update(batch_relevant)

        return relevant_ids

    def _filter_batch_cerebras(self, markets: list[Market], risk_context: str) -> set[str]:
        """Filter a batch using Cerebras Llama 3 (optimized path)."""
        markets_list = []
        for m in markets:
            markets_list.append(f"ID: {m.id}\nQuestion: {m.question}")
        
        markets_text = "\n\n".join(markets_list)

        prompt = f"""You are a financial risk analyst.
User Risk Profile:
{risk_context}

Task: Identify markets relevant to hedging these risks.
Markets:
{markets_text}

Return a JSON object with a single key 'relevant_market_ids' containing a list of strings (IDs).
Only include markets with potential correlation. If none, return empty list."""

        try:
            response = self.cerebras_client.post(
                "/chat/completions",
                json={
                    "model": "llama3.1-8b",
                    "messages": [
                        {"role": "system", "content": "You are a helpful analyst that outputs JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    "response_format": {"type": "json_object"},
                    "temperature": 0.0,
                    "max_completion_tokens": 1024
                }
            )
            response.raise_for_status()
            data = response.json()
            content = json.loads(data["choices"][0]["message"]["content"])
            ids = set(content.get("relevant_market_ids", []))
            logger.debug(f"Cerebras returned {len(ids)} relevant IDs")
            return ids
        except Exception as e:
            logger.error(f"Cerebras filter error: {e}")
            return set()

    def _filter_batch(self, markets: list[Market], risk_context: str) -> set[str]:
        """Filter a batch of markets for relevance."""
        markets_list = []
        for m in markets:
            markets_list.append(f"ID: {m.id}\nQuestion: {m.question}")

        markets_text = "\n\n".join(markets_list)

        prompt = f"""Given the user's risk profile:

{risk_context}

Review these prediction markets and identify ALL that could potentially be used to hedge the user's risks (including weak or indirect correlations):

{markets_text}

Return the IDs of all potentially relevant markets."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=FILTER_SYSTEM_PROMPT,
                tools=[BATCH_FILTER_TOOL],
                tool_choice={"type": "tool", "name": "filter_relevant_markets"},
                messages=[{"role": "user", "content": prompt}],
            )

            for block in response.content:
                if block.type == "tool_use" and block.name == "filter_relevant_markets":
                    ids = set(block.input.get("relevant_market_ids", []))
                    logger.debug(f"Claude filter returned {len(ids)} relevant IDs")
                    return ids
        except Exception as e:
            logger.error(f"Claude filter error: {e}")

        return set()

    def _batch_score_markets(
        self, markets: list[Market], risk_context: str
    ) -> list[ScoredMarket]:
        """Score markets in batches."""
        scored_markets = []
        batch_size = 10
        total_batches = (len(markets) + batch_size - 1) // batch_size
        logger.info(f"Scoring in {total_batches} batches of {batch_size}")

        for i in range(0, len(markets), batch_size):
            batch = markets[i : i + batch_size]
            batch_num = i // batch_size + 1
            logger.debug(f"Scoring batch {batch_num}/{total_batches}")
            batch_scored = self._score_batch(batch, risk_context)
            logger.debug(f"Batch {batch_num} scored {len(batch_scored)} markets")
            scored_markets.extend(batch_scored)

        return scored_markets

    def _score_batch(
        self, markets: list[Market], risk_context: str
    ) -> list[ScoredMarket]:
        """Score a batch of markets."""
        market_map = {m.id: m for m in markets}
        markets_text = "\n\n".join(self._format_market(m) for m in markets)

        prompt = f"""Given the user's risk profile:

{risk_context}

Score each of these prediction markets for hedging potential:

{markets_text}

Provide relevance scores and recommendations for each market."""

        try:
            response = self.client.messages.create(
                model=self.model,
                max_tokens=self.max_tokens,
                system=SCORING_SYSTEM_PROMPT,
                tools=[SCORING_TOOL],
                tool_choice={"type": "tool", "name": "score_markets"},
                messages=[{"role": "user", "content": prompt}],
            )

            for block in response.content:
                if block.type == "tool_use" and block.name == "score_markets":
                    scored = []
                    for item in block.input.get("scored_markets", []):
                        market_id = item.get("market_id")
                        if market_id in market_map:
                            scored.append(
                                ScoredMarket(
                                    market=market_map[market_id],
                                    relevance_score=item["relevance_score"],
                                    correlation_direction=item["correlation_direction"],
                                    correlation_explanation=item[
                                        "correlation_explanation"
                                    ],
                                    recommended_outcome=item["recommended_outcome"],
                                    adjusted_score=item["relevance_score"],
                                )
                            )
                    return scored
        except Exception as e:
            logger.error(f"Scoring batch error: {e}")

        return []

    def _format_market(self, market: Market) -> str:
        """Format market info for LLM."""
        lines = [
            f"Market ID: {market.id}",
            f"Question: {market.question}",
        ]

        if market.description:
            lines.append(f"Description: {market.description[:300]}")

        if market.outcomes:
            outcomes_str = ", ".join(
                f"{o.name}: ${o.price:.2f}" for o in market.outcomes
            )
            lines.append(f"Outcomes: {outcomes_str}")

        lines.append(f"Liquidity: ${market.liquidity:,.0f}")

        return "\n".join(lines)

    def _apply_heuristics(
        self, scored_markets: list[ScoredMarket]
    ) -> list[ScoredMarket]:
        """Apply heuristic adjustments to scores."""
        logger.debug(f"Applying heuristics to {len(scored_markets)} markets")
        
        for sm in scored_markets:
            adjusted = sm.relevance_score
            original = adjusted

            # Boost for high liquidity
            if sm.market.liquidity > 100000:
                adjusted *= 1.15
            elif sm.market.liquidity > 50000:
                adjusted *= 1.10
            elif sm.market.liquidity > 10000:
                adjusted *= 1.05
            elif sm.market.liquidity < 1000:
                adjusted *= 0.8

            # Penalize extreme prices
            recommended_price = self._get_recommended_price(sm)
            if recommended_price is not None:
                if recommended_price > 0.9 or recommended_price < 0.1:
                    adjusted *= 0.7
                elif recommended_price > 0.8 or recommended_price < 0.2:
                    adjusted *= 0.85

            # Boost for high volume
            if sm.market.volume > 1000000:
                adjusted *= 1.10
            elif sm.market.volume > 100000:
                adjusted *= 1.05

            # Cap at 1.0
            sm.adjusted_score = min(adjusted, 1.0)
            
            if abs(sm.adjusted_score - original) > 0.05:
                logger.debug(f"Score adjusted: {original:.3f} -> {sm.adjusted_score:.3f} for {sm.market.question[:50]}...")

        return scored_markets

    def _get_recommended_price(self, sm: ScoredMarket) -> float | None:
        """Get the price of the recommended outcome."""
        for outcome in sm.market.outcomes:
            if outcome.name.lower() == sm.recommended_outcome.lower():
                return outcome.price
        return None
