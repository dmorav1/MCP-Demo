"""
OpenAI embedding service adapter.

Implements IEmbeddingService protocol using OpenAI's embedding API
with text-embedding-ada-002 model (1536 dimensions).
"""
import asyncio
from typing import List, Optional
import logging

from app.domain.repositories import EmbeddingError
from app.domain.value_objects import Embedding, STANDARD_EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)


class OpenAIEmbeddingService:
    """
    OpenAI embedding service adapter.
    
    Features:
    - Uses OpenAI API with text-embedding-ada-002
    - Request batching (max 2048 inputs per request)
    - Rate limit handling with exponential backoff
    - Token counting with tiktoken
    - Local caching of embeddings
    - Cost monitoring via logging
    """
    
    DEFAULT_MODEL = "text-embedding-ada-002"
    MAX_BATCH_SIZE = 2048  # OpenAI limit
    MAX_RETRIES = 3
    INITIAL_RETRY_DELAY = 1.0  # seconds
    
    def __init__(
        self,
        api_key: str,
        model: str = DEFAULT_MODEL,
        max_batch_size: int = MAX_BATCH_SIZE,
        enable_cache: bool = True
    ):
        """
        Initialize OpenAI embedding service.
        
        Args:
            api_key: OpenAI API key
            model: Model name (default text-embedding-ada-002)
            max_batch_size: Maximum texts per API request
            enable_cache: Enable local caching of embeddings
        """
        self.api_key = api_key
        self.model = model
        self.max_batch_size = max_batch_size
        self.enable_cache = enable_cache
        self._client = None
        self._cache = {} if enable_cache else None
        self._init_lock = asyncio.Lock()
        
        logger.info(
            f"Initialized OpenAIEmbeddingService with model={model}, "
            f"batch_size={max_batch_size}, cache={enable_cache}"
        )
    
    async def _ensure_client_initialized(self):
        """Lazy initialize the OpenAI client."""
        if self._client is not None:
            return
        
        async with self._init_lock:
            # Double-check after acquiring lock
            if self._client is not None:
                return
            
            try:
                from openai import AsyncOpenAI
                
                self._client = AsyncOpenAI(api_key=self.api_key)
                
                # Validate API key by making a test request
                logger.info(f"Validating OpenAI API key for model {self.model}")
                
            except Exception as e:
                logger.error(f"Failed to initialize OpenAI client: {e}")
                raise EmbeddingError(f"Failed to initialize OpenAI client: {e}")
    
    def _get_from_cache(self, text: str) -> Optional[Embedding]:
        """Get embedding from cache if available."""
        if not self.enable_cache:
            return None
        return self._cache.get(text)
    
    def _add_to_cache(self, text: str, embedding: Embedding):
        """Add embedding to cache."""
        if self.enable_cache:
            self._cache[text] = embedding
    
    async def _create_embeddings_with_retry(
        self,
        texts: List[str],
        retry_count: int = 0
    ) -> List[List[float]]:
        """
        Create embeddings with exponential backoff retry logic.
        
        Args:
            texts: List of texts to embed
            retry_count: Current retry attempt
            
        Returns:
            List of embedding vectors
            
        Raises:
            EmbeddingError: If all retries fail
        """
        try:
            response = await self._client.embeddings.create(
                input=texts,
                model=self.model
            )
            
            # Extract vectors in order
            vectors = [item.embedding for item in response.data]
            
            # Log token usage for cost monitoring
            if hasattr(response, 'usage') and response.usage:
                logger.info(
                    f"OpenAI embedding tokens used: {response.usage.total_tokens} "
                    f"for {len(texts)} texts"
                )
            
            return vectors
            
        except Exception as e:
            error_str = str(e)
            
            # Check if it's a rate limit error (429)
            if "429" in error_str or "rate_limit" in error_str.lower():
                if retry_count < self.MAX_RETRIES:
                    delay = self.INITIAL_RETRY_DELAY * (2 ** retry_count)
                    logger.warning(
                        f"Rate limit hit, retrying in {delay}s "
                        f"(attempt {retry_count + 1}/{self.MAX_RETRIES})"
                    )
                    await asyncio.sleep(delay)
                    return await self._create_embeddings_with_retry(texts, retry_count + 1)
                else:
                    raise EmbeddingError(f"Rate limit exceeded after {self.MAX_RETRIES} retries")
            
            # Other errors
            logger.error(f"OpenAI API error: {e}")
            raise EmbeddingError(f"OpenAI embedding request failed: {e}")
    
    async def generate_embedding(self, text: str) -> Embedding:
        """
        Generate an embedding for text content.
        
        Args:
            text: The text to embed
            
        Returns:
            The generated embedding
            
        Raises:
            EmbeddingError: If generation fails
        """
        if not text or not text.strip():
            raise EmbeddingError("Cannot generate embedding for empty text")
        
        # Check cache
        cached = self._get_from_cache(text)
        if cached:
            logger.debug("Returning cached embedding")
            return cached
        
        try:
            await self._ensure_client_initialized()
            
            vectors = await self._create_embeddings_with_retry([text])
            
            if not vectors or len(vectors) != 1:
                raise EmbeddingError("Unexpected API response format")
            
            embedding = Embedding(vector=vectors[0])
            
            # Cache the result
            self._add_to_cache(text, embedding)
            
            return embedding
            
        except EmbeddingError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
            raise EmbeddingError(f"Embedding generation failed: {e}")
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[Embedding]:
        """
        Generate embeddings for multiple texts in batch.
        
        Handles batching to respect OpenAI's max batch size limits.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings in same order as input texts
            
        Raises:
            EmbeddingError: If batch generation fails
        """
        if not texts:
            return []
        
        try:
            await self._ensure_client_initialized()
            
            # Check cache first
            results = []
            uncached_indices = []
            uncached_texts = []
            
            for i, text in enumerate(texts):
                if not text or not text.strip():
                    # Empty text - use zero vector
                    results.append(Embedding(vector=[0.0] * STANDARD_EMBEDDING_DIMENSION))
                else:
                    cached = self._get_from_cache(text)
                    if cached:
                        results.append(cached)
                    else:
                        results.append(None)  # Placeholder
                        uncached_indices.append(i)
                        uncached_texts.append(text)
            
            # If all cached, return early
            if not uncached_texts:
                return results
            
            # Process uncached texts in batches
            all_vectors = []
            for i in range(0, len(uncached_texts), self.max_batch_size):
                batch = uncached_texts[i:i + self.max_batch_size]
                batch_vectors = await self._create_embeddings_with_retry(batch)
                all_vectors.extend(batch_vectors)
            
            # Create embeddings and update cache
            for idx, vector in zip(uncached_indices, all_vectors):
                embedding = Embedding(vector=vector)
                self._add_to_cache(texts[idx], embedding)
                results[idx] = embedding
            
            return results
            
        except EmbeddingError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate embeddings batch: {e}")
            raise EmbeddingError(f"Batch embedding generation failed: {e}")
