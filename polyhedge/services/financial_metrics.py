"""Calculate financial metrics for hedge portfolios."""

import numpy as np
from typing import List

from polyhedge.models.hedge import HedgeBundle, HedgeBet
from polyhedge.models.financial_metrics import PortfolioMetrics, BundleMetrics
from polyhedge.logger import get_logger

logger = get_logger(__name__)


class FinancialMetricsCalculator:
    """Calculate comprehensive financial metrics for hedge portfolios."""

    def calculate_portfolio_metrics(self, bundles: List[HedgeBundle]) -> PortfolioMetrics:
        """Calculate all portfolio-level metrics."""
        logger.info(f"Calculating portfolio metrics for {len(bundles)} bundles")

        if not bundles:
            return self._empty_metrics()

        # Calculate per-bundle metrics first
        bundle_metrics = [self._calculate_bundle_metrics(b) for b in bundles]

        # Aggregate portfolio-level metrics
        total_budget = bundles[0].budget if bundles else 0
        total_allocated = sum(b.total_allocated for b in bundles)
        total_markets = sum(len(b.bets) for b in bundles)

        # Calculate risk metrics
        overall_risk = self._calculate_overall_risk(bundles)
        volatility = self._calculate_portfolio_volatility(bundles)
        sharpe = self._calculate_sharpe_ratio(bundles, volatility)

        # Calculate diversification
        correlation = self._calculate_correlation_score(bundles)
        sector_diversity = self._calculate_sector_diversity(bundles)

        # Calculate payout metrics
        total_max_payout = sum(
            bet.potential_payout for bundle in bundles for bet in bundle.bets
        )

        weighted_avg_multiplier = self._calculate_weighted_avg_multiplier(bundles)
        expected_return = self._calculate_expected_return(bundles)

        logger.info(
            f"Portfolio metrics calculated: risk={overall_risk:.1f}, "
            f"sharpe={sharpe:.2f}, expected_return={expected_return:.2%}"
        )

        return PortfolioMetrics(
            total_budget=total_budget,
            total_allocated=total_allocated,
            num_bundles=len(bundles),
            total_markets=total_markets,
            overall_risk_score=overall_risk,
            portfolio_volatility=volatility,
            sharpe_ratio=sharpe,
            correlation_score=correlation,
            sector_diversity_score=sector_diversity,
            total_max_payout=total_max_payout,
            weighted_avg_multiplier=weighted_avg_multiplier,
            expected_return=expected_return,
            bundle_metrics=bundle_metrics,
        )

    def _calculate_bundle_metrics(self, bundle: HedgeBundle) -> BundleMetrics:
        """Calculate comprehensive metrics for a single bundle (standalone strategy)."""
        if not bundle.bets:
            theme_name = bundle.coverage_summary.split(":")[0] if ":" in bundle.coverage_summary else "Empty Bundle"
            return self._empty_bundle_metrics(theme_name)

        payouts = [bet.potential_payout for bet in bundle.bets]
        multipliers = [bet.payout_multiplier for bet in bundle.bets]
        prices = [bet.current_price for bet in bundle.bets]
        allocations = [bet.allocation for bet in bundle.bets]

        # Risk score based on Portfolio Volatility (accounting for diversification)
        # Var(Portfolio) = sum(weight_i^2 * p_i * (1-p_i)) assuming independence
        # This naturally rewards diversification (more bets = lower variance)
        
        # Calculate variance variance contribution of each bet
        total_alloc = sum(allocations)
        if total_alloc > 0:
            weights = [a / total_alloc for a in allocations]
            portfolio_variance = sum(
                (w**2) * p * (1 - p) 
                for w, p in zip(weights, prices)
            )
            portfolio_std_dev = np.sqrt(portfolio_variance)
            
            # Normalize: Max std dev is 0.5. We scale by 400 to make the risk score more sensitive.
            # A diversified bundle of 10-20 assets will now sit in the 40-60 range instead of 10-20.
            risk_score = min(float(portfolio_std_dev * 400), 100.0)
            
            # Ensure a minimum floor based on avg individual risk so it doesn't look suspiciously safe
            # Avg individual risk (old formula)
            avg_price_dist = np.mean([abs(p - 0.5) for p in prices])
            avg_ind_risk = (1 - avg_price_dist * 2) * 100
            
            # Blend: 70% portfolio risk (diversified), 30% avg individual risk
            # This ensures even a well-diversified bundle of risky assets keeps some risk signal
            risk_score = float(0.7 * risk_score + 0.3 * avg_ind_risk)
            
        else:
            risk_score = 0.0

        # Volatility based on price standard deviation
        volatility = float(np.std(prices)) if len(prices) > 1 else 0.0

        # Expected return for this bundle
        total_allocation = sum(allocations)
        if total_allocation > 0:
            expected_value = sum(
                bet.allocation * bet.current_price * bet.payout_multiplier
                for bet in bundle.bets
            )
            expected_return = float((expected_value - total_allocation) / total_allocation)
        else:
            expected_return = 0.0

        # Sharpe ratio for this bundle
        risk_free_rate = 0.05
        if volatility > 0:
            sharpe_ratio = float((expected_return - risk_free_rate) / volatility)
        else:
            sharpe_ratio = 0.0

        # Diversification score based on price variance
        price_variance = float(np.var(prices)) if len(prices) > 1 else 0.0
        diversification_score = min(price_variance * 400, 100)

        # Liquidity score
        liquidities = [bet.market.market.liquidity for bet in bundle.bets]
        avg_liquidity = np.mean(liquidities)
        liquidity_score = min(avg_liquidity / 100000 * 100, 100)

        # Total max payout
        total_max_payout = sum(payouts)

        # Extract theme name
        theme_name = bundle.coverage_summary.split(":")[0] if ":" in bundle.coverage_summary else "Bundle"

        logger.debug(
            f"Bundle '{theme_name}': risk={risk_score:.1f}, sharpe={sharpe_ratio:.2f}, "
            f"expected_return={expected_return:.2%}, volatility={volatility:.3f}"
        )

        return BundleMetrics(
            theme_name=theme_name,
            total_allocation=bundle.total_allocated,
            num_markets=len(bundle.bets),
            avg_payout_multiplier=float(np.mean(multipliers)),
            max_payout=max(payouts),
            min_payout=min(payouts),
            total_max_payout=total_max_payout,
            risk_score=risk_score,
            volatility=volatility,
            sharpe_ratio=sharpe_ratio,
            expected_return=expected_return,
            diversification_score=diversification_score,
            liquidity_score=liquidity_score,
        )

    def _calculate_overall_risk(self, bundles: List[HedgeBundle]) -> float:
        """Calculate overall portfolio risk (0-100)."""
        all_prices = [bet.current_price for bundle in bundles for bet in bundle.bets]

        if not all_prices:
            return 50.0

        # Risk = uncertainty. Prices near 0.5 = max uncertainty
        avg_price = np.mean(all_prices)
        uncertainty = 1 - abs(avg_price - 0.5) * 2

        return float(uncertainty * 100)

    def _calculate_portfolio_volatility(self, bundles: List[HedgeBundle]) -> float:
        """Estimate portfolio volatility based on outcome price variance."""
        all_prices = [bet.current_price for bundle in bundles for bet in bundle.bets]

        if len(all_prices) < 2:
            return 0.0

        return float(np.std(all_prices))

    def _calculate_sharpe_ratio(
        self, bundles: List[HedgeBundle], volatility: float
    ) -> float:
        """Calculate Sharpe ratio (simplified)."""
        if volatility == 0:
            return 0.0

        expected_return = self._calculate_expected_return(bundles)
        risk_free_rate = 0.05  # Assume 5% risk-free rate

        excess_return = expected_return - risk_free_rate
        return float(excess_return / volatility) if volatility > 0 else 0.0

    def _calculate_correlation_score(self, bundles: List[HedgeBundle]) -> float:
        """Estimate correlation between bundles (0 = uncorrelated, 1 = highly correlated)."""
        # Simplified: based on market question similarity
        # In production, would use actual market correlation data

        if len(bundles) < 2:
            return 0.0

        # For now, assume lower correlation with more bundles (diversification proxy)
        return max(0.0, 1.0 - (len(bundles) - 1) * 0.2)

    def _calculate_sector_diversity(self, bundles: List[HedgeBundle]) -> float:
        """Calculate sector diversity score (0-100)."""
        # Number of themes = proxy for sector diversity
        num_themes = len(bundles)

        # More themes = higher diversity, cap at 5 themes = 100 score
        return min(num_themes / 5 * 100, 100)

    def _calculate_weighted_avg_multiplier(self, bundles: List[HedgeBundle]) -> float:
        """Calculate weighted average payout multiplier."""
        total_allocation = sum(b.total_allocated for b in bundles)

        if total_allocation == 0:
            return 1.0

        weighted_sum = sum(
            bet.allocation * bet.payout_multiplier
            for bundle in bundles
            for bet in bundle.bets
        )

        return float(weighted_sum / total_allocation)

    def _calculate_expected_return(self, bundles: List[HedgeBundle]) -> float:
        """Calculate probability-weighted expected return."""
        total_allocation = sum(b.total_allocated for b in bundles)

        if total_allocation == 0:
            return 0.0

        # Expected return = sum(allocation * probability * payout) / total_allocation
        # For prediction markets, current price = probability
        expected_value = sum(
            bet.allocation * bet.current_price * bet.payout_multiplier
            for bundle in bundles
            for bet in bundle.bets
        )

        return float((expected_value - total_allocation) / total_allocation)

    def _empty_metrics(self) -> PortfolioMetrics:
        """Return empty metrics."""
        return PortfolioMetrics(
            total_budget=0,
            total_allocated=0,
            num_bundles=0,
            total_markets=0,
            overall_risk_score=0,
            portfolio_volatility=0,
            sharpe_ratio=0,
            correlation_score=0,
            sector_diversity_score=0,
            total_max_payout=0,
            weighted_avg_multiplier=1.0,
            expected_return=0,
            bundle_metrics=[],
        )

    def _empty_bundle_metrics(self, theme_name: str) -> BundleMetrics:
        """Return empty bundle metrics."""
        return BundleMetrics(
            theme_name=theme_name,
            total_allocation=0,
            num_markets=0,
            avg_payout_multiplier=1.0,
            max_payout=0,
            min_payout=0,
            risk_score=0,
            diversification_score=0,
            liquidity_score=0,
        )
