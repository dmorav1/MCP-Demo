"""
LangChain embedding adapter.

Wrapper that adapts LangChain embedding models to the IEmbeddingService protocol.
This allows future integration with LangChain's ecosystem of embedding providers.
"""
import asyncio
from typing import List, Optional, Any
import logging

from app.domain.repositories import EmbeddingError
from app.domain.value_objects import Embedding, STANDARD_EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)


class LangChainEmbeddingAdapter:
    """
    LangChain embedding adapter.
    
    Wraps any LangChain Embeddings class to implement IEmbeddingService protocol.
    
    Features:
    - Supports any LangChain embedding provider
    - Dimension normalization (padding/truncating)
    - Async and sync LangChain models supported
    """
    
    def __init__(
        self,
        langchain_embeddings: Any,
        target_dimension: int = STANDARD_EMBEDDING_DIMENSION
    ):
        """
        Initialize LangChain embedding adapter.
        
        Args:
            langchain_embeddings: An instance of a LangChain Embeddings class
            target_dimension: Target embedding dimension (default 1536)
        """
        self.langchain_embeddings = langchain_embeddings
        self.target_dimension = target_dimension
        
        # Check if the embeddings support async
        self._supports_async = hasattr(langchain_embeddings, 'aembed_query')
        
        logger.info(
            f"Initialized LangChainEmbeddingAdapter with "
            f"embeddings={type(langchain_embeddings).__name__}, "
            f"async={self._supports_async}, "
            f"target_dim={target_dimension}"
        )
    
    def _normalize_vector(self, vector: List[float]) -> List[float]:
        """
        Normalize vector to target dimension.
        
        Args:
            vector: Input vector
            
        Returns:
            Normalized vector of target dimension
        """
        if len(vector) == self.target_dimension:
            return vector
        
        if len(vector) > self.target_dimension:
            logger.warning(
                f"Vector dimension {len(vector)} exceeds target {self.target_dimension}, truncating"
            )
            return vector[:self.target_dimension]
        
        # Pad with zeros
        padded = vector + [0.0] * (self.target_dimension - len(vector))
        return padded
    
    async def generate_embedding(self, text: str) -> Embedding:
        """
        Generate an embedding for text content.
        
        Args:
            text: The text to embed
            
        Returns:
            The generated embedding (normalized to target dimension)
            
        Raises:
            EmbeddingError: If generation fails
        """
        if not text or not text.strip():
            raise EmbeddingError("Cannot generate embedding for empty text")
        
        try:
            if self._supports_async:
                # Use async method
                vector = await self.langchain_embeddings.aembed_query(text)
            else:
                # Run sync method in thread pool
                loop = asyncio.get_event_loop()
                vector = await loop.run_in_executor(
                    None,
                    lambda: self.langchain_embeddings.embed_query(text)
                )
            
            # Normalize to target dimension
            normalized_vector = self._normalize_vector(vector)
            
            return Embedding(vector=normalized_vector)
            
        except Exception as e:
            logger.error(f"Failed to generate embedding via LangChain: {e}")
            raise EmbeddingError(f"Embedding generation failed: {e}")
    
    async def generate_embeddings_batch(self, texts: List[str]) -> List[Embedding]:
        """
        Generate embeddings for multiple texts in batch.
        
        Args:
            texts: List of texts to embed
            
        Returns:
            List of embeddings in same order as input texts
            
        Raises:
            EmbeddingError: If batch generation fails
        """
        if not texts:
            return []
        
        # Filter out empty texts but remember their positions
        valid_indices = []
        valid_texts = []
        for i, text in enumerate(texts):
            if text and text.strip():
                valid_indices.append(i)
                valid_texts.append(text)
        
        if not valid_texts:
            raise EmbeddingError("No valid texts to embed")
        
        try:
            if self._supports_async:
                # Use async method
                vectors = await self.langchain_embeddings.aembed_documents(valid_texts)
            else:
                # Run sync method in thread pool
                loop = asyncio.get_event_loop()
                vectors = await loop.run_in_executor(
                    None,
                    lambda: self.langchain_embeddings.embed_documents(valid_texts)
                )
            
            # Normalize all vectors
            normalized_vectors = [self._normalize_vector(v) for v in vectors]
            
            # Create embeddings
            valid_embeddings = [Embedding(vector=v) for v in normalized_vectors]
            
            # Restore original ordering (fill in zero vectors for invalid texts)
            result = [None] * len(texts)
            for i, embedding in zip(valid_indices, valid_embeddings):
                result[i] = embedding
            
            # Replace None with zero embeddings
            for i, emb in enumerate(result):
                if emb is None:
                    logger.warning(f"Text at index {i} was empty, using zero embedding")
                    result[i] = Embedding(vector=[0.0] * self.target_dimension)
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings batch via LangChain: {e}")
            raise EmbeddingError(f"Batch embedding generation failed: {e}")
