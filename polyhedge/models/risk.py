"""Risk analysis data models."""

from pydantic import BaseModel, Field


class RiskFactor(BaseModel):
    """A single identified risk factor from user's situation."""

    name: str = Field(description="Short name for the risk factor")
    description: str = Field(description="Detailed description of the risk")
    category: str = Field(description="Category: economic, political, health, tech, etc.")
    keywords: list[str] = Field(description="Keywords for market search")
    search_queries: list[str] = Field(description="Specific queries for finding relevant markets")


class RiskAnalysis(BaseModel):
    """Complete risk analysis of user's situation."""

    situation_summary: str = Field(description="Brief summary of user's situation")
    risk_factors: list[RiskFactor] = Field(description="Identified risk factors")
    overall_risk_level: str = Field(description="low, medium, or high")
