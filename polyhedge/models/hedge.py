"""Hedge recommendation data models."""

from pydantic import BaseModel, Field

from polyhedge.models.market import ScoredMarket


class HedgeBet(BaseModel):
    """A single recommended bet in the hedge bundle."""

    market: ScoredMarket
    outcome: str = Field(description="Outcome to bet on (e.g., 'Yes' or 'No')")
    allocation: float = Field(ge=0, description="Dollar amount to allocate")
    allocation_percent: float = Field(ge=0, le=100, description="Percentage of budget")
    current_price: float = Field(ge=0, le=1, description="Current price of the outcome")
    potential_payout: float = Field(ge=0, description="Potential payout if bet wins")
    payout_multiplier: float = Field(ge=1, description="Multiplier on investment if wins")


class HedgeBundle(BaseModel):
    """Complete hedge recommendation bundle."""

    budget: float = Field(ge=0, description="Total budget for hedging")
    bets: list[HedgeBet] = Field(description="Recommended bets")
    total_allocated: float = Field(ge=0, description="Total amount allocated")
    coverage_summary: str = Field(description="Summary of risks covered")
    risk_factors_covered: list[str] = Field(description="Which risk factors are hedged")
