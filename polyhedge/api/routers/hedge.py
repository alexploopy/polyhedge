"""Hedge recommendation endpoints."""

import json
from fastapi import APIRouter, HTTPException, Depends
from sse_starlette.sse import EventSourceResponse

from polyhedge.api.schemas.request import HedgeRequest
from polyhedge.api.schemas.response import HedgeResponse
from polyhedge.api.services.hedge_service import HedgeService
from polyhedge.config import Settings, get_settings
from polyhedge.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


def get_hedge_service(settings: Settings = Depends(get_settings)) -> HedgeService:
    """Dependency to get HedgeService instance."""
    return HedgeService(settings)


@router.post("/", response_model=HedgeResponse)
async def create_hedge(
    request: HedgeRequest, service: HedgeService = Depends(get_hedge_service)
):
    """
    Create hedge recommendations for a user's concern.

    - **concern**: User's primary concern or risk
    - **budget**: Budget for hedging (default: $100)
    - **num_markets**: Number of markets to search (default: 500)
    """
    try:
        logger.info(f"Received hedge request: concern='{request.concern[:50]}...'")

        result = service.generate_hedge(
            concern=request.concern,
            budget=request.budget,
            num_markets=request.num_markets,
        )

        logger.info("Hedge request completed successfully")
        return result

    except ValueError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error generating hedge: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@router.post("/stream")
async def create_hedge_stream(
    request: HedgeRequest, service: HedgeService = Depends(get_hedge_service)
):
    """
    Create hedge recommendations with real-time progress updates via SSE.

    Returns Server-Sent Events (SSE) with progress updates:
    - **started**: Initial event with request details
    - **progress**: Progress update with current step
    - **context_complete**: Web context gathering complete
    - **search_complete**: Market search complete
    - **filter_complete**: Market filtering complete
    - **bundles_complete**: Bundle generation complete
    - **complete**: Final event with full results
    - **error**: Error event if something goes wrong
    """
    logger.info(f"Received streaming hedge request: concern='{request.concern[:50]}...'")

    async def event_generator():
        try:
            async for event in service.generate_hedge_stream(
                concern=request.concern,
                budget=request.budget,
                num_markets=request.num_markets,
            ):
                yield {"event": event["type"], "data": json.dumps(event["data"])}

        except Exception as e:
            logger.error(f"Error in streaming: {e}", exc_info=True)
            yield {"event": "error", "data": json.dumps({"message": str(e)})}

    return EventSourceResponse(event_generator())
