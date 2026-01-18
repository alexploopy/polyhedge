"""Market data models."""

from pydantic import BaseModel, Field


class Outcome(BaseModel):
    """A single outcome option in a market."""

    name: str
    price: float = Field(ge=0, le=1, description="Price between 0 and 1")


class Market(BaseModel):
    """A Polymarket prediction market."""

    id: str
    question: str
    description: str = ""
    outcomes: list[Outcome] = Field(default_factory=list)
    liquidity: float = Field(default=0, ge=0)
    volume: float = Field(default=0, ge=0)
    end_date: str | None = None
    active: bool = True
    slug: str | None = None  # URL slug for Polymarket link
    
    @property
    def url(self) -> str | None:
        """Get the Polymarket URL for this market."""
        if self.slug:
            return f"https://polymarket.com/event/{self.slug}"
        return None


class ScoredMarket(BaseModel):
    """A market with relevance scoring."""

    market: Market
    relevance_score: float = Field(ge=0, le=1, description="How relevant to user's risks")
    correlation_direction: str = Field(description="positive or negative correlation")
    correlation_explanation: str = Field(description="Why this market correlates")
    recommended_outcome: str = Field(description="Which outcome to bet on for hedge")
    adjusted_score: float = Field(ge=0, description="Score after heuristic adjustments")
