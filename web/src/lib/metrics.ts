
import { HedgeBundle, BundleMetrics, PortfolioMetrics, HedgeBet } from './types';

// Calculate risk score based on portfolio variance (mirrors Python implementation)
function calculateRiskScore(bets: HedgeBet[]): number {
    if (!bets.length) return 0;

    const prices = bets.map(b => b.current_price || 0.5); // Fallback to 0.5 if 0
    const allocations = bets.map(b => b.allocation);
    const totalAlloc = allocations.reduce((a, b) => a + b, 0);

    if (totalAlloc <= 0) return 0;

    const weights = allocations.map(a => a / totalAlloc);

    // Variance = sum(w^2 * p * (1-p)) assuming independence
    const portfolioVariance = weights.reduce((sum, w, i) => {
        const p = prices[i];
        return sum + (w * w * p * (1 - p));
    }, 0);

    const portfolioStdDev = Math.sqrt(portfolioVariance);

    // Normalize: Max std dev is 0.5. We scale by 400 to make the risk score more sensitive.
    // A diversified bundle of 10-20 assets will now sit in the 40-60 range instead of 10-20.
    let riskScore = Math.min(portfolioStdDev * 400, 100.0);

    // Blend with avg individual risk (30%)
    const avgPriceDist = prices.reduce((sum, p) => sum + Math.abs(p - 0.5), 0) / prices.length;
    const avgIndRisk = (1 - avgPriceDist * 2) * 100;

    return (0.7 * riskScore) + (0.3 * avgIndRisk);
}

export function calculateBundleMetrics(bundle: HedgeBundle): BundleMetrics {
    const bets = bundle.bets;
    if (!bets.length) {
        return {
            theme_name: bundle.coverage_summary.split(':')[0] || "Bundle",
            total_allocation: 0,
            num_markets: 0,
            avg_payout_multiplier: 1,
            max_payout: 0,
            min_payout: 0,
            total_max_payout: 0,
            risk_score: 0,
            volatility: 0,
            sharpe_ratio: 0,
            expected_return: 0,
            diversification_score: 0,
            liquidity_score: 0
        };
    }

    const totalAllocation = bets.reduce((sum, b) => sum + b.allocation, 0);
    const payouts = bets.map(b => b.potential_payout);
    const totalMaxPayout = payouts.reduce((sum, p) => sum + p, 0);
    const riskScore = calculateRiskScore(bets);

    // Weighted avg multiplier
    const weightedSum = bets.reduce((sum, b) => sum + (b.allocation * b.payout_multiplier), 0);
    const avgMultiplier = totalAllocation > 0 ? weightedSum / totalAllocation : 1;

    return {
        theme_name: bundle.coverage_summary.split(':')[0] || "Bundle",
        total_allocation: totalAllocation,
        num_markets: bets.length,
        avg_payout_multiplier: avgMultiplier,
        max_payout: Math.max(...payouts),
        min_payout: Math.min(...payouts),
        total_max_payout: totalMaxPayout,
        risk_score: riskScore,
        volatility: 0, // Simplified for frontend (not critical for display)
        sharpe_ratio: 0, // Simplified
        expected_return: 0, // Simplified
        diversification_score: 0, // Simplified
        liquidity_score: 0 // Simplified
    };
}

export function calculatePortfolioMetrics(bundles: HedgeBundle[]): PortfolioMetrics {
    const bundleMetrics = bundles.map(calculateBundleMetrics);

    const totalAllocated = bundles.reduce((sum, b) => sum + b.total_allocated, 0);
    const totalMaxPayout = bundleMetrics.reduce((sum, m) => sum + m.total_max_payout, 0);

    // Simplified portfolio risk (average of bundles for now, or could implement full portfolio math)
    // For now, let's use the average risk score weight by size
    const totalRiskWeight = bundleMetrics.reduce((sum, m) => sum + (m.risk_score * m.total_allocation), 0);
    const overallRisk = totalAllocated > 0 ? totalRiskWeight / totalAllocated : 0;

    return {
        total_budget: bundles[0]?.budget || 0, // Assuming shared budget passed down
        total_allocated: totalAllocated,
        num_bundles: bundles.length,
        total_markets: bundles.reduce((sum, b) => sum + b.bets.length, 0),
        overall_risk_score: overallRisk,
        portfolio_volatility: 0,
        sharpe_ratio: 0,
        correlation_score: 0,
        sector_diversity_score: 0,
        total_max_payout: totalMaxPayout,
        weighted_avg_multiplier: 0,
        expected_return: 0,
        bundle_metrics: bundleMetrics
    };
}
