"""
Repository port interfaces - Define contracts for data access without implementation details.

These interfaces follow the Dependency Inversion Principle:
- Domain defines the interface
- Infrastructure provides the implementation
- No infrastructure dependencies in this file
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Protocol

from .entities import Conversation, ConversationChunk, SearchResults
from .value_objects import (
    ConversationId, ChunkId, SearchQuery, Embedding, RelevanceScore
)


class IConversationRepository(ABC):
    """Repository interface for conversation persistence operations."""
    
    @abstractmethod
    async def save(self, conversation: Conversation) -> Conversation:
        """
        Persist a conversation and return it with assigned ID.
        
        Args:
            conversation: The conversation to save
            
        Returns:
            The saved conversation with ID assigned
            
        Raises:
            RepositoryError: If save operation fails
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, conversation_id: ConversationId) -> Optional[Conversation]:
        """
        Retrieve a conversation by ID.
        
        Args:
            conversation_id: The conversation identifier
            
        Returns:
            The conversation if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def get_all(self, skip: int = 0, limit: int = 100) -> List[Conversation]:
        """
        Retrieve conversations with pagination.
        
        Args:
            skip: Number of conversations to skip
            limit: Maximum number of conversations to return
            
        Returns:
            List of conversations ordered by creation date (newest first)
        """
        pass
    
    @abstractmethod
    async def delete(self, conversation_id: ConversationId) -> bool:
        """
        Delete a conversation and all its chunks.
        
        Args:
            conversation_id: The conversation identifier
            
        Returns:
            True if deleted, False if not found
            
        Raises:
            RepositoryError: If deletion fails
        """
        pass
    
    @abstractmethod
    async def exists(self, conversation_id: ConversationId) -> bool:
        """
        Check if a conversation exists.
        
        Args:
            conversation_id: The conversation identifier
            
        Returns:
            True if conversation exists, False otherwise
        """
        pass
    
    @abstractmethod
    async def count(self) -> int:
        """
        Get total number of conversations.
        
        Returns:
            Total conversation count
        """
        pass


class IChunkRepository(ABC):
    """Repository interface for conversation chunk operations."""
    
    @abstractmethod
    async def save_chunks(self, chunks: List[ConversationChunk]) -> List[ConversationChunk]:
        """
        Save multiple chunks in a batch operation.
        
        Args:
            chunks: List of chunks to save
            
        Returns:
            Saved chunks with IDs assigned
            
        Raises:
            RepositoryError: If batch save fails
        """
        pass
    
    @abstractmethod
    async def get_by_conversation(self, conversation_id: ConversationId) -> List[ConversationChunk]:
        """
        Get all chunks for a conversation.
        
        Args:
            conversation_id: The conversation identifier
            
        Returns:
            List of chunks ordered by order_index
        """
        pass
    
    @abstractmethod
    async def get_by_id(self, chunk_id: ChunkId) -> Optional[ConversationChunk]:
        """
        Retrieve a chunk by ID.
        
        Args:
            chunk_id: The chunk identifier
            
        Returns:
            The chunk if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def update_embedding(self, chunk_id: ChunkId, embedding: Embedding) -> bool:
        """
        Update the embedding for a specific chunk.
        
        Args:
            chunk_id: The chunk identifier
            embedding: The new embedding
            
        Returns:
            True if updated successfully, False if chunk not found
            
        Raises:
            RepositoryError: If update fails
        """
        pass
    
    @abstractmethod
    async def get_chunks_without_embeddings(self) -> List[ConversationChunk]:
        """
        Get all chunks that don't have embeddings yet.
        
        Returns:
            List of chunks without embeddings
        """
        pass


class IVectorSearchRepository(ABC):
    """Repository interface for vector similarity search operations."""
    
    @abstractmethod
    async def similarity_search(
        self, 
        query_embedding: Embedding, 
        top_k: int = 10
    ) -> List[tuple[ConversationChunk, RelevanceScore]]:
        """
        Perform vector similarity search.
        
        Args:
            query_embedding: The query vector
            top_k: Maximum number of results to return
            
        Returns:
            List of (chunk, relevance_score) tuples ordered by relevance
            
        Raises:
            RepositoryError: If search fails
        """
        pass
    
    @abstractmethod
    async def similarity_search_with_threshold(
        self, 
        query_embedding: Embedding, 
        threshold: float = 0.7,
        top_k: int = 10
    ) -> List[tuple[ConversationChunk, RelevanceScore]]:
        """
        Perform vector similarity search with relevance threshold.
        
        Args:
            query_embedding: The query vector
            threshold: Minimum relevance score (0.0 to 1.0)
            top_k: Maximum number of results to return
            
        Returns:
            List of (chunk, relevance_score) tuples above threshold
            
        Raises:
            RepositoryError: If search fails
        """
        pass


class IEmbeddingRepository(ABC):
    """Repository interface for embedding storage and retrieval."""
    
    @abstractmethod
    async def store_embedding(self, chunk_id: ChunkId, embedding: Embedding) -> bool:
        """
        Store an embedding for a chunk.
        
        Args:
            chunk_id: The chunk identifier
            embedding: The embedding vector
            
        Returns:
            True if stored successfully
            
        Raises:
            RepositoryError: If storage fails
        """
        pass
    
    @abstractmethod
    async def get_embedding(self, chunk_id: ChunkId) -> Optional[Embedding]:
        """
        Retrieve an embedding for a chunk.
        
        Args:
            chunk_id: The chunk identifier
            
        Returns:
            The embedding if found, None otherwise
        """
        pass
    
    @abstractmethod
    async def has_embedding(self, chunk_id: ChunkId) -> bool:
        """
        Check if a chunk has an embedding.
        
        Args:
            chunk_id: The chunk identifier
            
        Returns:
            True if chunk has embedding, False otherwise
        """
        pass
    
    @abstractmethod
    async def get_chunks_needing_embeddings(self) -> List[ChunkId]:
        """
        Get chunk IDs that need embeddings generated.
        
        Returns:
            List of chunk IDs without embeddings
        """
        pass


class IEmbeddingService(Protocol):
    """Protocol for embedding generation services."""
    
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
        ...
    
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
        ...


# Domain exceptions
class DomainError(Exception):
    """Base exception for domain layer errors."""
    pass


class RepositoryError(DomainError):
    """Exception for repository operation failures."""
    pass


class EmbeddingError(DomainError):
    """Exception for embedding generation failures."""
    pass


class ValidationError(DomainError):
    """Exception for domain validation failures."""
    pass