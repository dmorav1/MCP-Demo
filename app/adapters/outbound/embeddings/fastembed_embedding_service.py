"""
FastEmbed embedding service adapter.

Implements IEmbeddingService protocol using FastEmbed library
as an alternative to sentence-transformers with similar features.
"""
import asyncio
from typing import List, Optional
import logging

from app.domain.repositories import EmbeddingError
from app.domain.value_objects import Embedding, STANDARD_EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)


class FastEmbedEmbeddingService:
    """
    FastEmbed embedding service adapter.
    
    Features:
    - Lazy loading
    - Fast inference optimized for CPU
    - Model caching
    - Batch processing
    - Padding to target dimension
    """
    
    DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"  # 384 dimensions
    
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        target_dimension: int = STANDARD_EMBEDDING_DIMENSION,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize FastEmbed embedding service.
        
        Args:
            model_name: FastEmbed model name
            target_dimension: Target embedding dimension (default 1536)
            cache_dir: Directory for model caching
        """
        self.model_name = model_name
        self.target_dimension = target_dimension
        self.cache_dir = cache_dir
        self._model = None
        self._load_lock = asyncio.Lock()
        
        logger.info(
            f"Initialized FastEmbedEmbeddingService with model={model_name}, "
            f"target_dim={target_dimension}"
        )
    
    async def _ensure_model_loaded(self):
        """Lazy load the FastEmbed model."""
        if self._model is not None:
            return
        
        async with self._load_lock:
            # Double-check after acquiring lock
            if self._model is not None:
                return
            
            try:
                # Note: fastembed is an optional dependency
                # If not installed, this will fail gracefully
                try:
                    from fastembed import TextEmbedding
                except ImportError:
                    raise EmbeddingError(
                        "fastembed library not installed. "
                        "Install with: pip install fastembed"
                    )
                
                logger.info(f"Loading FastEmbed model: {self.model_name}")
                
                # Run model loading in thread pool
                loop = asyncio.get_event_loop()
                self._model = await loop.run_in_executor(
                    None,
                    lambda: TextEmbedding(
                        model_name=self.model_name,
                        cache_dir=self.cache_dir
                    )
                )
                
                logger.info(f"Model {self.model_name} loaded successfully")
                
            except EmbeddingError:
                raise
            except Exception as e:
                logger.error(f"Failed to load model {self.model_name}: {e}")
                raise EmbeddingError(f"Failed to load embedding model: {e}")
    
    def _pad_vector(self, vector: List[float]) -> List[float]:
        """
        Pad a vector to target dimension with zeros.
        
        Args:
            vector: Input vector
            
        Returns:
            Padded vector of target dimension
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
            The generated embedding (padded to target dimension)
            
        Raises:
            EmbeddingError: If generation fails
        """
        if not text or not text.strip():
            raise EmbeddingError("Cannot generate embedding for empty text")
        
        try:
            await self._ensure_model_loaded()
            
            # Run embedding in thread pool
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: list(self._model.embed([text]))
            )
            
            if not embeddings or len(embeddings) != 1:
                raise EmbeddingError("Unexpected embedding output format")
            
            vector = embeddings[0].tolist()
            
            # Pad to target dimension
            padded_vector = self._pad_vector(vector)
            
            return Embedding(vector=padded_vector)
            
        except EmbeddingError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate embedding: {e}")
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
            await self._ensure_model_loaded()
            
            # Run batch embedding in thread pool
            loop = asyncio.get_event_loop()
            embeddings = await loop.run_in_executor(
                None,
                lambda: list(self._model.embed(valid_texts))
            )
            
            # Convert to lists and pad
            vectors = [emb.tolist() for emb in embeddings]
            padded_vectors = [self._pad_vector(v) for v in vectors]
            
            # Create embeddings
            valid_embeddings = [Embedding(vector=v) for v in padded_vectors]
            
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
            
        except EmbeddingError:
            raise
        except Exception as e:
            logger.error(f"Failed to generate embeddings batch: {e}")
            raise EmbeddingError(f"Batch embedding generation failed: {e}")
