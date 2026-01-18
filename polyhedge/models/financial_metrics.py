"""Financial metrics data models."""

from pydantic import BaseModel, Field
from typing import List


class BundleMetrics(BaseModel):
    """Metrics for a single themed bundle (standalone hedge strategy)."""

    theme_name: str = Field(..., description="Name of the themed bundle")
    total_allocation: float = Field(..., description="Total USD allocated to this bundle")
    num_markets: int = Field(..., description="Number of markets in this bundle")
    
    # Payout metrics
    avg_payout_multiplier: float = Field(..., description="Average payout multiplier across markets")
    max_payout: float = Field(..., description="Maximum potential payout from a single market")
    min_payout: float = Field(..., description="Minimum potential payout from a single market")
    total_max_payout: float = Field(0, description="Total max payout if all bets win")
    
    # Risk metrics
    risk_score: float = Field(..., ge=0, le=100, description="Risk score (0-100, higher = riskier)")
    volatility: float = Field(0, description="Estimated volatility based on price variance")
    sharpe_ratio: float = Field(0, description="Risk-adjusted return estimate")
    expected_return: float = Field(0, description="Probability-weighted expected return")
    
    # Diversification metrics
    diversification_score: float = Field(..., ge=0, le=100, description="Diversification score (0-100, higher = more diverse)")
    liquidity_score: float = Field(..., ge=0, le=100, description="Average liquidity score (0-100)")


class PortfolioMetrics(BaseModel):
    """Overall portfolio-level metrics."""

    # Budget allocation
    total_budget: float = Field(..., description="Total budget available")
    total_allocated: float = Field(..., description="Total amount allocated across all bundles")
    num_bundles: int = Field(..., description="Number of themed bundles")
    total_markets: int = Field(..., description="Total number of markets across all bundles")

    # Risk metrics
    overall_risk_score: float = Field(..., ge=0, le=100, description="Overall portfolio risk score (0-100)")
    portfolio_volatility: float = Field(..., description="Estimated portfolio volatility")
    sharpe_ratio: float = Field(..., description="Risk-adjusted return estimate")

    # Diversification
    correlation_score: float = Field(..., ge=0, le=1, description="Inter-bundle correlation (0=uncorrelated, 1=highly correlated)")
    sector_diversity_score: float = Field(..., ge=0, le=100, description="Sector diversity score (0-100)")

    # Payouts
    total_max_payout: float = Field(..., description="Maximum potential payout if all bets win")
    weighted_avg_multiplier: float = Field(..., description="Weighted average payout multiplier")
    expected_return: float = Field(..., description="Probability-weighted expected return")

    # Per-bundle breakdown
    bundle_metrics: List[BundleMetrics] = Field(..., description="Metrics for each bundle")
