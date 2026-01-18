import json
import sqlite3
import time
from pathlib import Path
from typing import Callable, List, Optional

from polyhedge.logger import get_logger
from polyhedge.models.market import Market
from polyhedge.services.vector_db import VectorDB

logger = get_logger(__name__)

DB_PATH = Path("polyhedge.db")


class MarketCache:
    """SQLite cache for market data with individual rows per market."""

    def __init__(self, db_path: Path = DB_PATH, use_vectors: bool = True):
        self.db_path = db_path
        self.use_vectors = use_vectors
        self._init_db()

        # Initialize vector database
        if self.use_vectors:
            self.vector_db = VectorDB()
            logger.debug(f"MarketCache initialized with db: {self.db_path} and vector DB")
        else:
            self.vector_db = None
            logger.debug(f"MarketCache initialized with db: {self.db_path} (no vector DB)")

    def _init_db(self):
        """Initialize the database table."""
        with sqlite3.connect(self.db_path) as conn:
            # Create proper market table with individual rows
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS markets (
                    id TEXT PRIMARY KEY,
                    question TEXT NOT NULL,
                    description TEXT,
                    outcomes TEXT,
                    liquidity REAL,
                    volume REAL,
                    end_date TEXT,
                    active INTEGER,
                    data TEXT NOT NULL,
                    cached_at REAL NOT NULL
                )
                """
            )
            conn.execute("CREATE INDEX IF NOT EXISTS idx_markets_liquidity ON markets(liquidity)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_markets_question ON markets(question)")
            conn.commit()
        logger.debug("Database table initialized")

    def get_markets(self) -> Optional[List[Market]]:
        """Retrieve all markets from cache."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT COUNT(*) FROM markets")
            count = cursor.fetchone()[0]
            
            if count == 0:
                logger.info("Cache miss: no cached markets found")
                return None
            
            # Get cache age from first row
            cursor = conn.execute("SELECT cached_at FROM markets LIMIT 1")
            cached_at = cursor.fetchone()[0]
            cache_age = time.time() - cached_at
            
            cursor = conn.execute("SELECT data FROM markets")
            rows = cursor.fetchall()
            
            try:
                markets = [Market(**json.loads(row[0])) for row in rows]
                active_markets = [m for m in markets if m.active]
                if len(active_markets) != len(markets):
                    logger.debug(
                        f"Filtered out {len(markets) - len(active_markets)} inactive markets from cache"
                    )
                logger.info(
                    f"Cache hit: {len(active_markets)} markets (cached {cache_age/60:.1f} min ago)"
                )
                return active_markets
            except Exception as e:
                logger.error(f"Cache parse error: {e}")
                return None

    def save_markets(self, markets: List[Market]):
        """Save markets to cache (one row per market).

        Note: This only saves to the SQLite database, not the vector database.
        Use update_vector_db() separately to update vector embeddings.
        """
        logger.info(f"Saving {len(markets)} markets to cache...")
        start = time.time()

        with sqlite3.connect(self.db_path) as conn:
            # Clear existing data
            conn.execute("DELETE FROM markets")

            # Insert markets in batches
            batch_size = 1000
            cached_at = time.time()

            for i in range(0, len(markets), batch_size):
                batch = markets[i:i + batch_size]
                rows = []
                for m in batch:
                    outcomes_str = json.dumps([o.model_dump() for o in m.outcomes]) if m.outcomes else None
                    rows.append((
                        m.id,
                        m.question,
                        m.description,
                        outcomes_str,
                        m.liquidity,
                        m.volume,
                        m.end_date,
                        1 if m.active else 0,
                        json.dumps(m.model_dump()),
                        cached_at
                    ))

                conn.executemany(
                    """
                    INSERT OR REPLACE INTO markets
                    (id, question, description, outcomes, liquidity, volume, end_date, active, data, cached_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    rows
                )
                logger.debug(f"Saved batch {i // batch_size + 1} ({len(batch)} markets)")

            conn.commit()

        elapsed = time.time() - start
        logger.info(f"Cache save complete in {elapsed:.2f}s")

    def update_vector_db(
        self,
        batch_size: int = 100,
        resume: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ):
        """Update vector database with markets from cache.

        Args:
            batch_size: Number of markets to process in each batch
            resume: If True, skip markets already in vector DB
            progress_callback: Optional callback function(current, total) for progress updates
        """
        if not self.use_vectors or not self.vector_db:
            logger.warning("Vector DB not available")
            return 0

        markets = self.get_markets()
        if not markets:
            logger.warning("No markets in cache to add to vector DB")
            return 0

        logger.info(f"Updating vector DB with {len(markets)} markets from cache")
        self.vector_db.add_markets(
            markets,
            batch_size=batch_size,
            resume=resume,
            progress_callback=progress_callback,
        )
        return len(markets)

    def search_semantic(
        self,
        query: str,
        n_results: int = 10,
        min_liquidity: Optional[float] = None,
    ) -> List[tuple[Market, float]]:
        """Search markets using semantic similarity.

        Args:
            query: Natural language search query
            n_results: Number of results to return
            min_liquidity: Optional minimum liquidity filter

        Returns:
            List of (Market, similarity_score) tuples
        """
        if not self.use_vectors or not self.vector_db:
            logger.warning("Vector search not available, vector DB not initialized")
            return []

        logger.info(f"Semantic search: '{query}'")

        # Search vector DB for similar market IDs
        results = self.vector_db.search(query, n_results, min_liquidity)

        if not results:
            return []

        # Fetch full market data from SQLite
        market_ids = [mid for mid, _ in results]
        placeholders = ",".join(["?"] * len(market_ids))

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"SELECT id, data FROM markets WHERE id IN ({placeholders})",
                market_ids,
            )
            rows = cursor.fetchall()

        # Create a map of id -> market
        id_to_market = {}
        for row in rows:
            try:
                market = Market(**json.loads(row[1]))
                id_to_market[row[0]] = market
            except Exception as e:
                logger.error(f"Failed to parse market {row[0]}: {e}")

        # Return markets in the order of similarity scores
        result_markets = []
        for market_id, score in results:
            if market_id in id_to_market:
                result_markets.append((id_to_market[market_id], score))

        logger.info(f"Retrieved {len(result_markets)} markets from semantic search")
        return result_markets
