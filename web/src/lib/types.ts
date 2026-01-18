// Market types
export interface Outcome {
  name: string;
  price: number;
}

export interface Market {
  id: string;
  question: string;
  description?: string;
  outcomes: Outcome[];
  liquidity: number;
  volume?: number;
  end_date?: string;
  active: boolean;
  slug?: string;
}

// Scored Market (used in bets)
export interface ScoredMarket {
  market: Market;
  relevance_score: number;
  adjusted_score: number;
  correlation_explanation: string;
  recommended_outcome: string;
  correlation_direction: string;
  risk_factors_addressed: string[];
}

// Hedge Bet
export interface HedgeBet {
  market: ScoredMarket;
  outcome: string;
  allocation: number;
  allocation_percent: number;
  current_price: number;
  potential_payout: number;
  payout_multiplier: number;
}

// Hedge Bundle
export interface HedgeBundle {
  budget: number;
  bets: HedgeBet[];
  total_allocated: number;
  coverage_summary: string;
  risk_factors_covered: string[];
}

// Financial Metrics
export interface BundleMetrics {
  theme_name: string;
  total_allocation: number;
  num_markets: number;
  avg_payout_multiplier: number;
  max_payout: number;
  min_payout: number;
  total_max_payout: number;
  risk_score: number;
  volatility: number;
  sharpe_ratio: number;
  expected_return: number;
  diversification_score: number;
  liquidity_score: number;
}

export interface PortfolioMetrics {
  total_budget: number;
  total_allocated: number;
  num_bundles: number;
  total_markets: number;
  overall_risk_score: number;
  portfolio_volatility: number;
  sharpe_ratio: number;
  correlation_score: number;
  sector_diversity_score: number;
  total_max_payout: number;
  weighted_avg_multiplier: number;
  expected_return: number;
  bundle_metrics: BundleMetrics[];
}

// API Request/Response types
export interface HedgeRequest {
  concern: string;
  budget: number;
  num_markets?: number;
}

export interface HedgeResponse {
  bundles: HedgeBundle[];
  metrics: PortfolioMetrics;
  web_context_summary: string;
  execution_time_seconds: number;
}

// SSE Event types
export interface SSEEvent {
  type: 'started' | 'progress' | 'context_complete' | 'search_complete' |
  'filter_complete' | 'bundles_complete' | 'complete' | 'error';
  data: any;
}
