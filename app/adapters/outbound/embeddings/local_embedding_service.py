"""
Local embedding service using sentence-transformers.

Implements IEmbeddingService protocol using sentence-transformers library
with the all-MiniLM-L6-v2 model (384 dimensions, padded to 1536).
"""
import asyncio
from typing import List, Optional
import logging

from app.domain.repositories import EmbeddingError
from app.domain.value_objects import Embedding, STANDARD_EMBEDDING_DIMENSION

logger = logging.getLogger(__name__)


class LocalEmbeddingService:
    """
    Local embedding service using sentence-transformers.
    
    Features:
    - Lazy loading to avoid startup delays
    - Device selection (CPU/GPU)
    - Padding 384-d vectors to 1536-d
    - Batch processing support
    - Model caching
    """
    
    DEFAULT_MODEL = "all-MiniLM-L6-v2"
    NATIVE_DIMENSION = 384
    
    def __init__(
        self,
        model_name: str = DEFAULT_MODEL,
        device: Optional[str] = None,
        target_dimension: int = STANDARD_EMBEDDING_DIMENSION,
        cache_dir: Optional[str] = None
    ):
        """
        Initialize local embedding service.
        
        Args:
            model_name: Sentence-transformers model name
            device: Device to use ('cpu', 'cuda', or None for auto)
            target_dimension: Target embedding dimension (default 1536)
            cache_dir: Directory for model caching
        """
        self.model_name = model_name
        self.device = device
        self.target_dimension = target_dimension
        self.cache_dir = cache_dir
        self._model = None
        self._load_lock = asyncio.Lock()
        
        logger.info(
            f"Initialized LocalEmbeddingService with model={model_name}, "
            f"device={device}, target_dim={target_dimension}"
        )
    
    async def _ensure_model_loaded(self):
        """Lazy load the sentence-transformers model."""
        if self._model is not None:
            return
        
        async with self._load_lock:
            # Double-check after acquiring lock
            if self._model is not None:
                return
            
            try:
                # Import here to avoid loading dependencies if not using local embeddings
                from sentence_transformers import SentenceTransformer
                
                logger.info(f"Loading sentence-transformers model: {self.model_name}")
                
                # Run model loading in thread pool to avoid blocking
                loop = asyncio.get_event_loop()
                self._model = await loop.run_in_executor(
                    None,
                    lambda: SentenceTransformer(
                        self.model_name,
                        device=self.device,
                        cache_folder=self.cache_dir
                    )
                )
                
                logger.info(f"Model {self.model_name} loaded successfully")
                
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
            # Truncate if needed (shouldn't happen with standard models)
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
            
            # Run encoding in thread pool to avoid blocking
            loop = asyncio.get_event_loop()
            vector = await loop.run_in_executor(
                None,
                lambda: self._model.encode(text, convert_to_numpy=True).tolist()
            )
            
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
            
            # Run batch encoding in thread pool
            loop = asyncio.get_event_loop()
            vectors = await loop.run_in_executor(
                None,
                lambda: self._model.encode(
                    valid_texts,
                    convert_to_numpy=True,
                    show_progress_bar=len(valid_texts) > 10
                ).tolist()
            )
            
            # Pad all vectors to target dimension
            padded_vectors = [self._pad_vector(v) for v in vectors]
            
            # Create embeddings
            embeddings = [Embedding(vector=v) for v in padded_vectors]
            
            # Restore original ordering (fill in None for invalid texts)
            result = [None] * len(texts)
            for i, embedding in zip(valid_indices, embeddings):
                result[i] = embedding
            
            # Replace None with error embeddings (zero vectors)
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
