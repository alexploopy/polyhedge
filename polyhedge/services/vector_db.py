"""Vector database service for semantic market search using ChromaDB."""

from pathlib import Path
from typing import Callable, List, Optional

import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer

from polyhedge.logger import get_logger
from polyhedge.models.market import Market

logger = get_logger(__name__)

VECTOR_DB_PATH = Path("vector_db")
COLLECTION_NAME = "markets"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"  # Fast, efficient model (384 dimensions)


class VectorDB:
    """Vector database for semantic market search."""

    def __init__(self, db_path: Path = VECTOR_DB_PATH):
        self.db_path = db_path
        self.db_path.mkdir(exist_ok=True)

        # Initialize ChromaDB with persistent storage
        self.client = chromadb.PersistentClient(
            path=str(self.db_path),
            settings=ChromaSettings(
                anonymized_telemetry=False,
                allow_reset=True,
            ),
        )

        # Initialize embedding model
        logger.info(f"Loading embedding model: {EMBEDDING_MODEL}")
        self.model = SentenceTransformer(EMBEDDING_MODEL)
        logger.info(f"Embedding model loaded (dimension: {self.model.get_sentence_embedding_dimension()})")

        # Get or create collection
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Polymarket markets with semantic embeddings"},
        )
        logger.info(f"VectorDB initialized at {self.db_path}")

    def _generate_embedding_text(self, market: Market) -> str:
        """Generate text for embedding from market title and description."""
        parts = [market.question]
        if market.description:
            parts.append(market.description)
        return " ".join(parts)

    def _generate_embeddings(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for a list of texts."""
        logger.debug(f"Generating embeddings for {len(texts)} texts")
        embeddings = self.model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()

    def get_existing_ids(self) -> set[str]:
        """Get the set of market IDs already in the vector database."""
        try:
            # Get all IDs from the collection
            result = self.collection.get()
            if result and result.get("ids"):
                return set(result["ids"])
            return set()
        except Exception as e:
            logger.warning(f"Error getting existing IDs: {e}")
            return set()

    def add_markets(
        self,
        markets: List[Market],
        batch_size: int = 100,
        resume: bool = False,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ):
        """Add or update markets in the vector database.

        Args:
            markets: List of markets to add
            batch_size: Number of markets to process in each batch (for embedding generation)
            resume: If True, skip markets that are already in the database
            progress_callback: Optional callback function(current, total) for progress updates
        """
        if not markets:
            logger.warning("No markets to add to vector DB")
            return

        # Filter out existing markets if resume is enabled
        if resume:
            existing_ids = self.get_existing_ids()
            markets_to_add = [m for m in markets if m.id not in existing_ids]
            if len(markets_to_add) < len(markets):
                logger.info(f"Resume mode: skipping {len(markets) - len(markets_to_add)} existing markets")
            markets = markets_to_add

        if not markets:
            logger.info("All markets already exist in vector DB, nothing to add")
            return

        logger.info(f"Adding {len(markets)} markets to vector DB in batches of {batch_size}")

        # Process in batches
        total_batches = (len(markets) + batch_size - 1) // batch_size

        for batch_num in range(total_batches):
            start_idx = batch_num * batch_size
            end_idx = min(start_idx + batch_size, len(markets))
            batch = markets[start_idx:end_idx]

            logger.info(f"Processing batch {batch_num + 1}/{total_batches} ({len(batch)} markets)")

            # Prepare batch data
            ids = [m.id for m in batch]
            texts = [self._generate_embedding_text(m) for m in batch]

            # Generate embeddings for this batch
            logger.debug(f"Generating embeddings for batch {batch_num + 1}")
            embeddings = self._generate_embeddings(texts)

            # Store metadata
            metadatas = [
                {
                    "question": m.question,
                    "liquidity": m.liquidity or 0.0,
                    "volume": m.volume or 0.0,
                    "active": m.active,
                }
                for m in batch
            ]

            # Add to collection
            try:
                self.collection.upsert(
                    ids=ids,
                    embeddings=embeddings,
                    documents=texts,
                    metadatas=metadatas,
                )
                logger.info(f"Batch {batch_num + 1}/{total_batches} added successfully")

                # Call progress callback if provided
                if progress_callback:
                    progress_callback(batch_num + 1, total_batches)

            except Exception as e:
                logger.error(f"Error adding batch {batch_num + 1}: {e}")
                raise

        logger.info(f"Successfully added {len(markets)} markets to vector DB")

    def search(
        self,
        query: str,
        n_results: int = 10,
        min_liquidity: Optional[float] = None,
    ) -> List[tuple[str, float]]:
        """Search for markets using semantic similarity.

        Args:
            query: Natural language search query
            n_results: Number of results to return
            min_liquidity: Optional minimum liquidity filter

        Returns:
            List of (market_id, similarity_score) tuples
        """
        logger.info(f"Searching vector DB: '{query}' (n={n_results})")

        # Generate query embedding
        query_embedding = self._generate_embeddings([query])[0]

        # Build where filter using ChromaDB syntax
        where = None
        if min_liquidity is not None:
            # Use $and operator to combine conditions
            where = {
                "$and": [
                    {"active": {"$eq": True}},
                    {"liquidity": {"$gte": min_liquidity}},
                ]
            }
        else:
            where = {"active": {"$eq": True}}

        # Search
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            where=where,
        )

        # Extract results
        if not results["ids"] or not results["ids"][0]:
            logger.info("No results found")
            return []

        market_ids = results["ids"][0]
        distances = results["distances"][0]

        # Convert distances to similarity scores (cosine similarity)
        # ChromaDB returns L2 distances, convert to similarity
        similarities = [1 / (1 + d) for d in distances]

        results_list = list(zip(market_ids, similarities))
        logger.info(f"Found {len(results_list)} results")
        for i, (mid, score) in enumerate(results_list[:5]):
            logger.debug(f"  {i+1}. {mid} (similarity: {score:.3f})")

        return results_list

    def count(self) -> int:
        """Get the total number of markets in the vector DB."""
        return self.collection.count()

    def clear(self):
        """Clear all data from the vector database."""
        logger.warning("Clearing vector database")
        self.client.delete_collection(COLLECTION_NAME)
        self.collection = self.client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"description": "Polymarket markets with semantic embeddings"},
        )
        logger.info("Vector database cleared")
