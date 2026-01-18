"""Admin endpoints for database management."""

from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks
from pydantic import BaseModel

from polyhedge.services.cache import MarketCache
from polyhedge.services.market_search import MarketSearch
from polyhedge.config import Settings, get_settings
from polyhedge.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


class UpdateMarketsResponse(BaseModel):
    """Response for market cache update."""

    status: str
    message: str
    markets_cached: int = 0


class UpdateVectorsResponse(BaseModel):
    """Response for vector database update."""

    status: str
    message: str
    vectors_created: int = 0


def get_market_cache(settings: Settings = Depends(get_settings)) -> MarketCache:
    """Dependency to get MarketCache instance."""
    return MarketCache()


def get_market_search(settings: Settings = Depends(get_settings)) -> MarketSearch:
    """Dependency to get MarketSearch instance."""
    return MarketSearch(settings, use_vector_search=False)


@router.post("/update-markets", response_model=UpdateMarketsResponse)
async def update_markets(
    market_search: MarketSearch = Depends(get_market_search),
):
    """
    Update the market cache by fetching all markets from Polymarket.

    This endpoint fetches and caches all active markets from the Polymarket API.
    """
    try:
        logger.info("Starting market cache update")

        # Run cache update
        num_markets = market_search.update_cache()

        logger.info(f"Market cache updated: {num_markets} markets cached")

        return UpdateMarketsResponse(
            status="success",
            message=f"Successfully cached {num_markets} markets",
            markets_cached=num_markets,
        )

    except Exception as e:
        logger.error(f"Error updating markets: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to update markets: {str(e)}"
        )
    finally:
        # Clean up HTTP client
        if hasattr(market_search, 'close'):
            market_search.close()


@router.post("/update-vectors", response_model=UpdateVectorsResponse)
async def update_vectors(
    batch_size: int = 100,
    resume: bool = False,
    cache: MarketCache = Depends(get_market_cache),
):
    """
    Update the vector database by generating embeddings for cached markets.

    - **batch_size**: Number of markets to process per batch (default: 100)
    - **resume**: Whether to resume from previous progress (default: false)
    """
    try:
        logger.info(
            f"Starting vector update: batch_size={batch_size}, resume={resume}"
        )

        # Check if vector database is available
        if not cache.vector_db:
            raise HTTPException(
                status_code=500,
                detail="Vector database not available. Check chromadb installation.",
            )

        # Run vector update
        num_vectors = cache.update_vector_db(batch_size=batch_size, resume=resume)

        logger.info(f"Vector database updated: {num_vectors} vectors created")

        return UpdateVectorsResponse(
            status="success",
            message=f"Successfully created {num_vectors} vectors",
            vectors_created=num_vectors,
        )

    except Exception as e:
        logger.error(f"Error updating vectors: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to update vectors: {str(e)}"
        )


@router.get("/cache-status")
async def get_cache_status(
    cache: MarketCache = Depends(get_market_cache),
):
    """
    Get the current status of the market cache and vector database.
    """
    try:
        # Get cache stats
        markets = cache.get_markets()
        cache_count = len(markets) if markets else 0

        # Get vector stats
        vector_count = 0
        if cache.vector_db:
            try:
                existing_ids = cache.vector_db.get_existing_ids()
                vector_count = len(existing_ids)
            except Exception as e:
                logger.warning(f"Could not get vector count: {e}")

        return {
            "markets_cached": cache_count,
            "vectors_created": vector_count,
            "cache_up_to_date": cache_count > 0,
            "vectors_up_to_date": vector_count > 0,
        }

    except Exception as e:
        logger.error(f"Error getting cache status: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, detail=f"Failed to get cache status: {str(e)}"
        )
