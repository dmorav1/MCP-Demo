"""
Domain entities - Core business objects with identity and behavior.

These entities contain pure business logic and have zero infrastructure dependencies.
They enforce business rules and maintain consistency.
"""
from typing import List, Optional, Dict, Any
from dataclasses import dataclass, field
from datetime import datetime

from .value_objects import (
    ConversationId, ChunkId, ChunkText, Embedding, AuthorInfo,
    ConversationMetadata, ChunkMetadata, RelevanceScore
)


@dataclass
class ConversationChunk:
    """
    Domain entity representing a conversation chunk.
    
    Business rules:
    - Chunks belong to exactly one conversation
    - Order index must be unique within conversation
    - Embedding is optional but required for search
    """
    id: Optional[ChunkId]
    conversation_id: ConversationId
    text: ChunkText
    metadata: ChunkMetadata
    embedding: Optional[Embedding] = None
    
    def __post_init__(self):
        # Validate business rules
        if self.metadata.order_index < 0:
            raise ValueError("Chunk order_index cannot be negative")
    
    def has_embedding(self) -> bool:
        """Check if chunk has an embedding for search."""
        return self.embedding is not None
    
    def can_be_searched(self) -> bool:
        """Check if chunk can participate in vector search."""
        return self.has_embedding()
    
    def get_author_name(self) -> Optional[str]:
        """Get the author name for this chunk."""
        return self.metadata.author_info.name
    
    def get_author_type(self) -> str:
        """Get the author type for this chunk."""
        return self.metadata.author_info.author_type
    
    def word_count(self) -> int:
        """Get word count of this chunk."""
        return self.text.word_count
    
    def attach_embedding(self, embedding: Embedding) -> 'ConversationChunk':
        """Create a new chunk with embedding attached."""
        return ConversationChunk(
            id=self.id,
            conversation_id=self.conversation_id,
            text=self.text,
            metadata=self.metadata,
            embedding=embedding
        )


@dataclass
class Conversation:
    """
    Domain entity representing a conversation.
    
    Business rules:
    - Conversations must have at least one chunk to be valid
    - Chunk order indices must be sequential starting from 0
    - Only conversations with embedded chunks can be searched
    """
    id: Optional[ConversationId]
    metadata: ConversationMetadata
    chunks: List[ConversationChunk] = field(default_factory=list)
    
    def __post_init__(self):
        # Ensure all chunks belong to this conversation
        if self.id:
            for chunk in self.chunks:
                if chunk.conversation_id != self.id:
                    raise ValueError("All chunks must belong to this conversation")
        
        # Validate chunk ordering
        self._validate_chunk_ordering()
    
    def _validate_chunk_ordering(self):
        """Validate that chunks have proper sequential ordering."""
        if not self.chunks:
            return
        
        expected_indices = set(range(len(self.chunks)))
        actual_indices = {chunk.metadata.order_index for chunk in self.chunks}
        
        if expected_indices != actual_indices:
            raise ValueError("Chunk order indices must be sequential starting from 0")
    
    def add_chunk(self, chunk: ConversationChunk):
        """Add a chunk to this conversation."""
        if self.id and chunk.conversation_id != self.id:
            raise ValueError("Chunk must belong to this conversation")
        
        # Set the order index
        chunk.metadata = ChunkMetadata(
            order_index=len(self.chunks),
            author_info=chunk.metadata.author_info,
            timestamp=chunk.metadata.timestamp
        )
        
        self.chunks.append(chunk)
    
    def get_chunk_count(self) -> int:
        """Get the number of chunks in this conversation."""
        return len(self.chunks)
    
    def get_embedded_chunk_count(self) -> int:
        """Get the number of chunks that have embeddings."""
        return sum(1 for chunk in self.chunks if chunk.has_embedding())
    
    def is_searchable(self) -> bool:
        """Check if conversation has any searchable chunks."""
        return any(chunk.can_be_searched() for chunk in self.chunks)
    
    def get_searchable_chunks(self) -> List[ConversationChunk]:
        """Get all chunks that can be searched (have embeddings)."""
        return [chunk for chunk in self.chunks if chunk.can_be_searched()]
    
    def get_total_word_count(self) -> int:
        """Get total word count across all chunks."""
        return sum(chunk.word_count() for chunk in self.chunks)
    
    def get_title(self) -> Optional[str]:
        """Get the most appropriate title for this conversation."""
        if self.metadata.scenario_title:
            return self.metadata.scenario_title
        return self.metadata.original_title
    
    def has_url(self) -> bool:
        """Check if conversation has an associated URL."""
        return bool(self.metadata.url)
    
    def get_author_names(self) -> List[str]:
        """Get unique author names from all chunks."""
        names = set()
        for chunk in self.chunks:
            if chunk.get_author_name():
                names.add(chunk.get_author_name())
        return sorted(list(names))
    
    def get_chunks_by_author(self, author_name: str) -> List[ConversationChunk]:
        """Get all chunks by a specific author."""
        return [chunk for chunk in self.chunks 
                if chunk.get_author_name() == author_name]
    
    def update_metadata(self, metadata: ConversationMetadata) -> 'Conversation':
        """Create a new conversation with updated metadata."""
        return Conversation(
            id=self.id,
            metadata=metadata,
            chunks=self.chunks
        )


@dataclass(frozen=True)
class SearchResult:
    """
    Domain entity representing a search result.
    
    Business rules:
    - Must have a valid conversation and chunk
    - Relevance score must be between 0.0 and 1.0
    """
    conversation: Conversation
    matched_chunk: ConversationChunk
    relevance_score: RelevanceScore
    
    def __post_init__(self):
        # Validate that the chunk belongs to the conversation
        if not any(chunk.id == self.matched_chunk.id for chunk in self.conversation.chunks):
            raise ValueError("Matched chunk must belong to the conversation")
        
        # Validate that the chunk can be searched
        if not self.matched_chunk.can_be_searched():
            raise ValueError("Matched chunk must be searchable (have embedding)")
    
    def is_highly_relevant(self, threshold: float = 0.8) -> bool:
        """Check if this result is highly relevant."""
        return self.relevance_score.is_relevant(threshold)
    
    def get_conversation_title(self) -> Optional[str]:
        """Get the conversation title for this result."""
        return self.conversation.get_title()
    
    def get_chunk_text(self) -> str:
        """Get the text content of the matched chunk."""
        return self.matched_chunk.text.content
    
    def get_author_name(self) -> Optional[str]:
        """Get the author of the matched chunk."""
        return self.matched_chunk.get_author_name()


@dataclass
class SearchResults:
    """
    Domain entity representing a collection of search results.
    
    Business rules:
    - Results must be ordered by relevance (highest first)
    - All results must be for the same query
    """
    query_text: str
    results: List[SearchResult] = field(default_factory=list)
    
    def __post_init__(self):
        # Ensure results are sorted by relevance
        self.results.sort(key=lambda r: r.relevance_score.value, reverse=True)
    
    def get_result_count(self) -> int:
        """Get the number of results."""
        return len(self.results)
    
    def get_highly_relevant_results(self, threshold: float = 0.8) -> List[SearchResult]:
        """Get results above the relevance threshold."""
        return [r for r in self.results if r.is_highly_relevant(threshold)]
    
    def get_unique_conversations(self) -> List[Conversation]:
        """Get unique conversations from all results."""
        seen_ids = set()
        conversations = []
        
        for result in self.results:
            conv_id = result.conversation.id
            if conv_id not in seen_ids:
                seen_ids.add(conv_id)
                conversations.append(result.conversation)
        
        return conversations
    
    def limit_results(self, max_results: int) -> 'SearchResults':
        """Create a new SearchResults with limited results."""
        return SearchResults(
            query_text=self.query_text,
            results=self.results[:max_results]
        )