"""Text compression service using The Token Company API."""

import httpx
from typing import Optional

from polyhedge.config import Settings
from polyhedge.logger import get_logger

logger = get_logger(__name__)


class ContextCompressor:
    """Compress text using The Token Company's bear-1 model."""

    def __init__(self, settings: Settings):
        self.api_key = getattr(settings, 'token_company_api_key', None)
        if not self.api_key:
            logger.warning("TOKEN_COMPANY_API_KEY not set, compression disabled")
            self.client = None
        else:
            self.client = httpx.Client(
                base_url="https://api.thetokencompany.com/v1",
                headers={"Authorization": f"Bearer {self.api_key}"},
                timeout=30.0,
            )
            logger.info("ContextCompressor initialized")

    def compress(
        self,
        text: str,
        aggressiveness: float = 0.5,
        max_output_tokens: Optional[int] = None,
        min_output_tokens: Optional[int] = None
    ) -> str:
        """
        Compress text using The Token Company API.

        Args:
            text: Text to compress
            aggressiveness: Compression level (0.0-1.0, default 0.5)
            max_output_tokens: Maximum output length
            min_output_tokens: Minimum output length

        Returns:
            Compressed text (or original if compression fails/disabled)
        """
        if not self.client:
            logger.debug("Compression disabled, returning original text")
            return text

        if not text or len(text) < 100:
            logger.debug("Text too short to compress, returning original")
            return text

        logger.info(f"Compressing {len(text)} chars with aggressiveness={aggressiveness}")

        try:
            response = self.client.post(
                "/compress",
                json={
                    "model": "bear-1",
                    "input": text,
                    "compression_settings": {
                        "aggressiveness": aggressiveness,
                        "max_output_tokens": max_output_tokens,
                        "min_output_tokens": min_output_tokens,
                    }
                }
            )
            response.raise_for_status()

            data = response.json()
            compressed = data["output"]
            original_tokens = data["original_input_tokens"]
            output_tokens = data["output_tokens"]
            compression_ratio = (1 - output_tokens / original_tokens) * 100 if original_tokens > 0 else 0

            logger.info(
                f"Compressed {original_tokens} → {output_tokens} tokens "
                f"({compression_ratio:.1f}% reduction)"
            )

            return compressed

        except Exception as e:
            logger.error(f"Compression failed: {e}, returning original text")
            return text

    def compress_search_results(
        self,
        search_results: list[dict],
        max_output_tokens: int = 1000
    ) -> str:
        """
        Compress web search results into a concise summary.

        Args:
            search_results: List of search result dicts with 'title', 'snippet', etc.
            max_output_tokens: Maximum tokens in output

        Returns:
            Compressed summary of search results
        """
        if not search_results:
            return ""

        # Format search results as text
        formatted = []
        for i, result in enumerate(search_results[:10], 1):  # Limit to top 10
            title = result.get('title', 'No title')
            snippet = result.get('description', result.get('snippet', 'No description'))
            formatted.append(f"{i}. {title}\n   {snippet}")

        full_text = "\n\n".join(formatted)

        # Compress with moderate aggressiveness
        compressed = self.compress(
            text=full_text,
            aggressiveness=0.6,  # Moderate compression
            max_output_tokens=max_output_tokens
        )

        return compressed

    def close(self):
        """Clean up HTTP client."""
        if self.client:
            self.client.close()
            logger.debug("ContextCompressor client closed")
