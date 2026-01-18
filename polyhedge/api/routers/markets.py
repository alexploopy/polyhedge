"""Market search and listing endpoints."""

from fastapi import APIRouter, HTTPException, Depends
from typing import List

from polyhedge.api.schemas.request import MarketSearchRequest
from polyhedge.api.schemas.response import MarketSearchResponse
from polyhedge.services.concern_search import ConcernSearch
from polyhedge.services.market_search import MarketSearch
from polyhedge.config import Settings, get_settings
from polyhedge.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


def get_concern_search(settings: Settings = Depends(get_settings)) -> ConcernSearch:
    """Dependency to get ConcernSearch instance."""
    return ConcernSearch(settings)


def get_market_search(settings: Settings = Depends(get_settings)) -> MarketSearch:
    """Dependency to get MarketSearch instance."""
    return MarketSearch(settings, use_vector_search=False)


@router.post("/search", response_model=MarketSearchResponse)
async def search_markets(
    request: MarketSearchRequest,
    search_service: ConcernSearch = Depends(get_concern_search),
):
    """
    Search for markets using semantic search.

    - **query**: Search query string
    - **n_results**: Number of results to return (default: 50)
    """
    try:
        logger.info(f"Market search request: query='{request.query[:50]}...'")

        results = search_service.search(
            concern=request.query,
            n_results=request.n_results,
            min_liquidity=100.0,
        )

        markets = [market for market, score in results]

        logger.info(f"Found {len(markets)} markets")

        return MarketSearchResponse(markets=markets, total_count=len(markets))

    except Exception as e:
        logger.error(f"Error searching markets: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")


@router.get("/sample")
async def get_sample_markets(
    limit: int = 10, search_service: ConcernSearch = Depends(get_concern_search)
):
    """
    Get a sample of active markets.

    - **limit**: Number of markets to return (default: 10)
    """
    try:
        logger.info(f"Sample markets request: limit={limit}")

        # Use a generic query to get diverse markets
        results = search_service.search(
            concern="prediction market", n_results=limit, min_liquidity=1000.0
        )

        markets = [market for market, score in results]

        return {"markets": markets, "count": len(markets)}

    except Exception as e:
        logger.error(f"Error getting sample markets: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get sample markets: {str(e)}"
        )


@router.get("/{market_id}")
async def get_market_details(
    market_id: str, market_search: MarketSearch = Depends(get_market_search)
):
    """Get detailed stats for a specific market."""
    try:
        details = market_search.get_market_details(market_id)
        if not details:
            raise HTTPException(status_code=404, detail="Market not found")
        return details
    
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting market details: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        market_search.close()


@router.get("/history/{token_id}")
async def get_market_history(
    token_id: str, 
    interval: str = "1d",
    market_search: MarketSearch = Depends(get_market_search)
):
    """Get price history for a specific outcome token."""
    try:
        history = market_search.get_token_history(token_id, interval)
        if history is None:
            raise HTTPException(status_code=404, detail="History not found")
        return {"history": history}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting market history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        market_search.close()
