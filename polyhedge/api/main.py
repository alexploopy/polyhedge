"""FastAPI application for PolyHedge."""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from polyhedge.api.routers import hedge, markets, admin
from polyhedge.api.schemas.response import HealthResponse
from polyhedge.logger import get_logger

logger = get_logger(__name__)

# Create FastAPI application
app = FastAPI(
    title="PolyHedge API",
    description="IRL Insurance via Polymarket - Hedge real-life risks with prediction markets",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS middleware - allow requests from Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Next.js dev server
        "http://127.0.0.1:3000",
        "http://localhost:8000",  # For testing
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(hedge.router, prefix="/api/hedge", tags=["hedge"])
app.include_router(markets.router, prefix="/api/markets", tags=["markets"])
app.include_router(admin.router, prefix="/api/admin", tags=["admin"])


@app.on_event("startup")
async def startup_event():
    """Initialize application on startup."""
    logger.info("Starting PolyHedge API server")
    logger.info("API documentation available at /docs")


@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down PolyHedge API server")


@app.get("/", response_model=HealthResponse)
async def root():
    """Root endpoint with basic API information."""
    return HealthResponse(status="running", version="1.0.0")


@app.get("/health", response_model=HealthResponse)
async def health():
    """Health check endpoint."""
    return HealthResponse(status="healthy", version="1.0.0")
