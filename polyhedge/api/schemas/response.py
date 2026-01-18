"""API response models."""

from pydantic import BaseModel, Field
from typing import List

from polyhedge.models.hedge import HedgeBundle
from polyhedge.models.financial_metrics import PortfolioMetrics
from polyhedge.models.market import Market


class HedgeResponse(BaseModel):
    """Response model for hedge generation."""

    bundles: List[HedgeBundle] = Field(..., description="Themed hedge bundles")
    metrics: PortfolioMetrics = Field(..., description="Portfolio financial metrics")
    web_context_summary: str = Field(
        ..., description="Summary of web context gathered"
    )
    execution_time_seconds: float = Field(
        ..., description="Total execution time in seconds"
    )


class MarketSearchResponse(BaseModel):
    """Response model for market search."""

    markets: List[Market] = Field(..., description="List of markets matching the query")
    total_count: int = Field(..., description="Total number of markets found")


class HealthResponse(BaseModel):
    """Response model for health check."""

    status: str = Field(..., description="Health status")
    version: str = Field(default="1.0.0", description="API version")
