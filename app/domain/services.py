"""
Domain services - Pure business logic with zero infrastructure dependencies.

These services orchestrate domain operations and enforce business rules
without any knowledge of databases, APIs, or external systems.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from .entities import Conversation, ConversationChunk, SearchResults, SearchResult
from .value_objects import (
    ConversationId, ChunkText, AuthorInfo, ChunkMetadata, 
    SearchQuery, RelevanceScore, ConversationMetadata, Embedding,
    STANDARD_EMBEDDING_DIMENSION
)
from .repositories import ValidationError


@dataclass
class ChunkingParameters:
    """Parameters for conversation chunking."""
    max_chunk_size: int = 1000
    split_on_speaker_change: bool = True
    preserve_message_boundaries: bool = True


class ConversationChunkingService:
    """
    Domain service for chunking conversations.
    
    Implements business rules for how conversations should be split
    into manageable chunks for embedding and search.
    """
    
    def __init__(self, parameters: ChunkingParameters = None):
        self.parameters = parameters or ChunkingParameters()
    
    def chunk_conversation_messages(
        self, 
        messages: List[Dict[str, Any]],
        conversation_id: ConversationId
    ) -> List[ConversationChunk]:
        """
        Chunk a list of conversation messages into searchable chunks.
        
        Business rules:
        - Chunks should not exceed max_chunk_size characters
        - Split on speaker changes if enabled
        - Preserve message boundaries when possible
        - Assign sequential order indices
        
        Args:
            messages: List of message dictionaries with 'content', 'author_name', etc.
            conversation_id: The conversation these chunks belong to
            
        Returns:
            List of conversation chunks
            
        Raises:
            ValidationError: If messages are invalid
        """
        if not messages:
            raise ValidationError("Cannot chunk empty message list")
        
        chunks = []
        current_chunk_content = ""
        current_messages = []
        last_author = None
        
        for message in messages:
            # Validate message format
            content = message.get('content', '').strip()
            if not content:
                continue
            
            author_name = message.get('author_name')
            author_type = message.get('author_type', 'human')
            timestamp = message.get('timestamp')
            
            # Format message for chunk
            formatted_message = f"{author_name or 'Unknown'}: {content}"
            
            # Check if we should split the chunk
            should_split = (
                # Split on speaker change
                (self.parameters.split_on_speaker_change and 
                 last_author is not None and 
                 author_name != last_author) or
                # Split if adding this message would exceed max size
                (len(current_chunk_content + formatted_message + "\n") > self.parameters.max_chunk_size and
                 current_chunk_content)
            )
            
            if should_split:
                # Create chunk from accumulated content
                chunk = self._create_chunk_from_messages(
                    current_chunk_content,
                    current_messages,
                    conversation_id,
                    len(chunks)
                )
                chunks.append(chunk)
                
                # Reset for next chunk
                current_chunk_content = ""
                current_messages = []
            
            # Add message to current chunk
            current_chunk_content += formatted_message + "\n"
            current_messages.append(message)
            last_author = author_name
        
        # Create final chunk if there's remaining content
        if current_chunk_content.strip():
            chunk = self._create_chunk_from_messages(
                current_chunk_content,
                current_messages,
                conversation_id,
                len(chunks)
            )
            chunks.append(chunk)
        
        if not chunks:
            raise ValidationError("No valid chunks created from messages")
        
        return chunks
    
    def _create_chunk_from_messages(
        self,
        content: str,
        messages: List[Dict[str, Any]],
        conversation_id: ConversationId,
        order_index: int
    ) -> ConversationChunk:
        """Create a conversation chunk from accumulated messages."""
        if not messages:
            raise ValidationError("Cannot create chunk from empty messages")
        
        # Use the last message's metadata as representative
        last_message = messages[-1]
        
        chunk_text = ChunkText(content.strip())
        author_info = AuthorInfo(
            name=last_message.get('author_name'),
            author_type=last_message.get('author_type', 'human')
        )
        
        metadata = ChunkMetadata(
            order_index=order_index,
            author_info=author_info,
            timestamp=last_message.get('timestamp')
        )
        
        return ConversationChunk(
            id=None,  # Will be assigned when saved
            conversation_id=conversation_id,
            text=chunk_text,
            metadata=metadata
        )


class EmbeddingValidationService:
    """
    Domain service for validating embeddings.
    
    Enforces business rules about embedding format, dimension, and quality.
    """
    
    REQUIRED_DIMENSION = STANDARD_EMBEDDING_DIMENSION
    MIN_VALID_VALUES = 100  # Minimum non-zero values for quality check
    
    def validate_embedding(self, embedding: Embedding) -> bool:
        """
        Validate an embedding meets business requirements.
        
        Args:
            embedding: The embedding to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If embedding is invalid
        """
        # Check dimension
        if embedding.dimension != self.REQUIRED_DIMENSION:
            raise ValidationError(
                f"Embedding dimension must be {self.REQUIRED_DIMENSION}, got {embedding.dimension}"
            )
        
        # Check for reasonable distribution of values
        non_zero_count = sum(1 for x in embedding.vector if abs(x) > 1e-8)
        if non_zero_count < self.MIN_VALID_VALUES:
            raise ValidationError(
                f"Embedding appears to be of poor quality (only {non_zero_count} non-zero values)"
            )
        
        return True
    
    def validate_embedding_batch(self, embeddings: List[Embedding]) -> bool:
        """
        Validate a batch of embeddings.
        
        Args:
            embeddings: List of embeddings to validate
            
        Returns:
            True if all are valid
            
        Raises:
            ValidationError: If any embedding is invalid
        """
        if not embeddings:
            raise ValidationError("Cannot validate empty embedding batch")
        
        for i, embedding in enumerate(embeddings):
            try:
                self.validate_embedding(embedding)
            except ValidationError as e:
                raise ValidationError(f"Embedding {i} invalid: {e}")
        
        return True


class SearchRelevanceService:
    """
    Domain service for determining search relevance and ranking.
    
    Implements business rules for what constitutes relevant search results.
    """
    
    DEFAULT_RELEVANCE_THRESHOLD = 0.7
    HIGH_RELEVANCE_THRESHOLD = 0.8
    
    def calculate_relevance_score(self, distance: float) -> RelevanceScore:
        """
        Convert vector distance to relevance score.
        
        Business rule: Lower distance = higher relevance
        Score is normalized to 0.0-1.0 range.
        
        Args:
            distance: L2 distance from vector search
            
        Returns:
            Relevance score between 0.0 and 1.0
        """
        # Convert L2 distance to similarity score
        # Assuming distances typically range from 0.0 to 2.0
        similarity = max(0.0, 1.0 - (distance / 2.0))
        return RelevanceScore(similarity)
    
    def is_result_relevant(self, score: RelevanceScore, threshold: Optional[float] = None) -> bool:
        """
        Determine if a result meets relevance threshold.
        
        Args:
            score: The relevance score
            threshold: Custom threshold (uses default if None)
            
        Returns:
            True if result is relevant
        """
        threshold = threshold or self.DEFAULT_RELEVANCE_THRESHOLD
        return score.value >= threshold
    
    def rank_search_results(
        self, 
        results: List[tuple[ConversationChunk, RelevanceScore]]
    ) -> List[tuple[ConversationChunk, RelevanceScore]]:
        """
        Rank search results according to business rules.
        
        Primary: Relevance score (highest first)
        Secondary: Chunk order within conversation (earliest first)
        
        Args:
            results: List of (chunk, score) tuples
            
        Returns:
            Ranked list of (chunk, score) tuples
        """
        return sorted(
            results,
            key=lambda x: (-x[1].value, x[0].metadata.order_index)
        )
    
    def filter_relevant_results(
        self,
        results: List[tuple[ConversationChunk, RelevanceScore]],
        threshold: Optional[float] = None
    ) -> List[tuple[ConversationChunk, RelevanceScore]]:
        """
        Filter results to only include relevant ones.
        
        Args:
            results: List of (chunk, score) tuples
            threshold: Custom relevance threshold
            
        Returns:
            Filtered list of relevant results
        """
        threshold = threshold or self.DEFAULT_RELEVANCE_THRESHOLD
        return [
            (chunk, score) for chunk, score in results
            if self.is_result_relevant(score, threshold)
        ]


class ConversationValidationService:
    """
    Domain service for validating conversations.
    
    Enforces business rules about conversation structure and content.
    """
    
    MIN_CHUNKS_FOR_SEARCH = 1
    MAX_CHUNKS_PER_CONVERSATION = 1000
    MIN_CHUNK_WORD_COUNT = 3
    
    def validate_conversation(self, conversation: Conversation) -> bool:
        """
        Validate a conversation meets business requirements.
        
        Args:
            conversation: The conversation to validate
            
        Returns:
            True if valid
            
        Raises:
            ValidationError: If conversation is invalid
        """
        # Check minimum chunks
        if conversation.get_chunk_count() < self.MIN_CHUNKS_FOR_SEARCH:
            raise ValidationError(
                f"Conversation must have at least {self.MIN_CHUNKS_FOR_SEARCH} chunk"
            )
        
        # Check maximum chunks
        if conversation.get_chunk_count() > self.MAX_CHUNKS_PER_CONVERSATION:
            raise ValidationError(
                f"Conversation cannot have more than {self.MAX_CHUNKS_PER_CONVERSATION} chunks"
            )
        
        # Validate each chunk
        for i, chunk in enumerate(conversation.chunks):
            try:
                self._validate_chunk(chunk)
            except ValidationError as e:
                raise ValidationError(f"Chunk {i} invalid: {e}")
        
        # Check chunk ordering
        self._validate_chunk_ordering(conversation)
        
        return True
    
    def _validate_chunk(self, chunk: ConversationChunk) -> bool:
        """Validate individual chunk."""
        # Check minimum word count
        if chunk.word_count() < self.MIN_CHUNK_WORD_COUNT:
            raise ValidationError(
                f"Chunk must have at least {self.MIN_CHUNK_WORD_COUNT} words"
            )
        
        return True
    
    def _validate_chunk_ordering(self, conversation: Conversation) -> bool:
        """Validate chunk ordering is sequential."""
        expected_indices = list(range(len(conversation.chunks)))
        actual_indices = [chunk.metadata.order_index for chunk in conversation.chunks]
        
        if actual_indices != expected_indices:
            raise ValidationError("Chunk order indices must be sequential starting from 0")
        
        return True
    
    def can_conversation_be_searched(self, conversation: Conversation) -> bool:
        """
        Check if conversation can participate in search.
        
        Args:
            conversation: The conversation to check
            
        Returns:
            True if conversation can be searched
        """
        return (
            conversation.get_chunk_count() >= self.MIN_CHUNKS_FOR_SEARCH and
            conversation.get_embedded_chunk_count() > 0
        )