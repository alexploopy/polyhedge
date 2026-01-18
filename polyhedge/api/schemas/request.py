"""API request models."""

from pydantic import BaseModel, Field


class HedgeRequest(BaseModel):
    """Request model for hedge generation."""

    concern: str = Field(..., description="User's primary concern or risk", min_length=1)
    budget: float = Field(
        default=100.0, ge=0, description="Budget for hedging in USD"
    )
    num_markets: int = Field(
        default=500, ge=10, le=1000, description="Number of markets to search"
    )


class MarketSearchRequest(BaseModel):
    """Request model for market search."""

    query: str = Field(..., description="Search query", min_length=1)
    n_results: int = Field(
        default=50, ge=1, le=500, description="Number of results to return"
    )
