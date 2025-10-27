"""
Domain events - Represent significant business events that have occurred.

These events capture important business moments and enable:
- Audit logging
- Event-driven architecture
- Integration between bounded contexts
- Observability and monitoring
"""
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, Any, Optional, List
from uuid import uuid4

from .value_objects import ConversationId, ChunkId, SearchQuery, RelevanceScore


class DomainEvent(ABC):
    """Base class for all domain events."""
    
    def __init__(self, event_id: Optional[str] = None, occurred_at: Optional[datetime] = None):
        self.event_id = event_id or str(uuid4())
        self.occurred_at = occurred_at or datetime.now()
    
    @abstractmethod
    def get_event_type(self) -> str:
        """Get the type identifier for this event."""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary for serialization."""
        return {
            'event_id': self.event_id,
            'event_type': self.get_event_type(),
            'occurred_at': self.occurred_at.isoformat(),
            'data': self._get_event_data()
        }
    
    @abstractmethod
    def _get_event_data(self) -> Dict[str, Any]:
        """Get event-specific data for serialization."""
        pass


class ConversationCreated(DomainEvent):
    """Event fired when a new conversation is created."""
    
    def __init__(
        self,
        conversation_id: ConversationId,
        title: Optional[str],
        chunk_count: int,
        total_word_count: int,
        event_id: Optional[str] = None,
        occurred_at: Optional[datetime] = None
    ):
        super().__init__(event_id, occurred_at)
        self.conversation_id = conversation_id
        self.title = title
        self.chunk_count = chunk_count
        self.total_word_count = total_word_count
    
    def get_event_type(self) -> str:
        return "conversation.created"
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'conversation_id': self.conversation_id.value,
            'title': self.title,
            'chunk_count': self.chunk_count,
            'total_word_count': self.total_word_count
        }


class ConversationDeleted(DomainEvent):
    """Event fired when a conversation is deleted."""
    
    def __init__(
        self,
        conversation_id: ConversationId,
        title: Optional[str],
        chunk_count: int,
        event_id: Optional[str] = None,
        occurred_at: Optional[datetime] = None
    ):
        super().__init__(event_id, occurred_at)
        self.conversation_id = conversation_id
        self.title = title
        self.chunk_count = chunk_count
    
    def get_event_type(self) -> str:
        return "conversation.deleted"
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'conversation_id': self.conversation_id.value,
            'title': self.title,
            'chunk_count': self.chunk_count
        }


class ChunksCreated(DomainEvent):
    """Event fired when conversation chunks are created."""
    
    def __init__(
        self,
        conversation_id: ConversationId,
        chunk_ids: List[ChunkId],
        chunking_strategy: str,
        event_id: Optional[str] = None,
        occurred_at: Optional[datetime] = None
    ):
        super().__init__(event_id, occurred_at)
        self.conversation_id = conversation_id
        self.chunk_ids = chunk_ids
        self.chunking_strategy = chunking_strategy
    
    def get_event_type(self) -> str:
        return "chunks.created"
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'conversation_id': self.conversation_id.value,
            'chunk_ids': [chunk_id.value for chunk_id in self.chunk_ids],
            'chunk_count': len(self.chunk_ids),
            'chunking_strategy': self.chunking_strategy
        }


class EmbeddingsGenerated(DomainEvent):
    """Event fired when embeddings are generated for chunks."""
    
    def __init__(
        self,
        conversation_id: ConversationId,
        chunk_ids: List[ChunkId],
        embedding_provider: str,
        embedding_dimension: int,
        event_id: Optional[str] = None,
        occurred_at: Optional[datetime] = None
    ):
        super().__init__(event_id, occurred_at)
        self.conversation_id = conversation_id
        self.chunk_ids = chunk_ids
        self.embedding_provider = embedding_provider
        self.embedding_dimension = embedding_dimension
    
    def get_event_type(self) -> str:
        return "embeddings.generated"
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'conversation_id': self.conversation_id.value,
            'chunk_ids': [chunk_id.value for chunk_id in self.chunk_ids],
            'chunk_count': len(self.chunk_ids),
            'embedding_provider': self.embedding_provider,
            'embedding_dimension': self.embedding_dimension
        }


class EmbeddingGenerationFailed(DomainEvent):
    """Event fired when embedding generation fails."""
    
    def __init__(
        self,
        conversation_id: ConversationId,
        chunk_id: ChunkId,
        error_message: str,
        embedding_provider: str,
        event_id: Optional[str] = None,
        occurred_at: Optional[datetime] = None
    ):
        super().__init__(event_id, occurred_at)
        self.conversation_id = conversation_id
        self.chunk_id = chunk_id
        self.error_message = error_message
        self.embedding_provider = embedding_provider
    
    def get_event_type(self) -> str:
        return "embeddings.generation_failed"
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'conversation_id': self.conversation_id.value,
            'chunk_id': self.chunk_id.value,
            'error_message': self.error_message,
            'embedding_provider': self.embedding_provider
        }


class SearchPerformed(DomainEvent):
    """Event fired when a search is performed."""
    
    def __init__(
        self,
        query: SearchQuery,
        result_count: int,
        top_relevance_score: Optional[RelevanceScore] = None,
        search_duration_ms: Optional[int] = None,
        event_id: Optional[str] = None,
        occurred_at: Optional[datetime] = None
    ):
        super().__init__(event_id, occurred_at)
        self.query = query
        self.result_count = result_count
        self.top_relevance_score = top_relevance_score
        self.search_duration_ms = search_duration_ms
    
    def get_event_type(self) -> str:
        return "search.performed"
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'query_text': self.query.text,
            'query_normalized': self.query.normalized_text,
            'result_count': self.result_count,
            'top_relevance_score': self.top_relevance_score.value if self.top_relevance_score else None,
            'search_duration_ms': self.search_duration_ms
        }


class SearchFailed(DomainEvent):
    """Event fired when a search operation fails."""
    
    def __init__(
        self,
        query: SearchQuery,
        error_message: str,
        error_type: str,
        event_id: Optional[str] = None,
        occurred_at: Optional[datetime] = None
    ):
        super().__init__(event_id, occurred_at)
        self.query = query
        self.error_message = error_message
        self.error_type = error_type
    
    def get_event_type(self) -> str:
        return "search.failed"
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'query_text': self.query.text,
            'query_normalized': self.query.normalized_text,
            'error_message': self.error_message,
            'error_type': self.error_type
        }


class ConversationIngested(DomainEvent):
    """Event fired when a conversation is fully ingested (created + embedded)."""
    
    def __init__(
        self,
        conversation_id: ConversationId,
        title: Optional[str],
        chunk_count: int,
        embedded_chunk_count: int,
        source_url: Optional[str] = None,
        event_id: Optional[str] = None,
        occurred_at: Optional[datetime] = None
    ):
        super().__init__(event_id, occurred_at)
        self.conversation_id = conversation_id
        self.title = title
        self.chunk_count = chunk_count
        self.embedded_chunk_count = embedded_chunk_count
        self.source_url = source_url
    
    def get_event_type(self) -> str:
        return "conversation.ingested"
    
    def _get_event_data(self) -> Dict[str, Any]:
        return {
            'conversation_id': self.conversation_id.value,
            'title': self.title,
            'chunk_count': self.chunk_count,
            'embedded_chunk_count': self.embedded_chunk_count,
            'source_url': self.source_url,
            'embedding_coverage': self.embedded_chunk_count / self.chunk_count if self.chunk_count > 0 else 0.0
        }


class DomainEventPublisher:
    """
    Publisher for domain events.
    
    In Phase 1, this is a simple in-memory implementation.
    Later phases can add persistence, external publishing, etc.
    """
    
    def __init__(self):
        self._handlers: Dict[str, List[callable]] = {}
        self._events: List[DomainEvent] = []
    
    def publish(self, event: DomainEvent) -> None:
        """
        Publish a domain event.
        
        Args:
            event: The domain event to publish
        """
        # Store event for audit purposes
        self._events.append(event)
        
        # Notify handlers
        event_type = event.get_event_type()
        handlers = self._handlers.get(event_type, [])
        
        for handler in handlers:
            try:
                handler(event)
            except Exception as e:
                # In production, this would be logged properly
                # For now, just continue with other handlers
                pass
    
    def subscribe(self, event_type: str, handler: callable) -> None:
        """
        Subscribe to events of a specific type.
        
        Args:
            event_type: The type of event to subscribe to
            handler: Function to call when event occurs
        """
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)
    
    def get_events(self, event_type: Optional[str] = None) -> List[DomainEvent]:
        """
        Get published events, optionally filtered by type.
        
        Args:
            event_type: Optional event type filter
            
        Returns:
            List of events
        """
        if event_type is None:
            return self._events.copy()
        
        return [event for event in self._events if event.get_event_type() == event_type]
    
    def clear_events(self) -> None:
        """Clear the event history."""
        self._events.clear()
    
    def get_event_count(self, event_type: Optional[str] = None) -> int:
        """
        Get count of published events.
        
        Args:
            event_type: Optional event type filter
            
        Returns:
            Number of events
        """
        return len(self.get_events(event_type))


# Global event publisher instance for Phase 1
# In later phases, this will be injected via DI container
_domain_event_publisher = DomainEventPublisher()


def get_domain_event_publisher() -> DomainEventPublisher:
    """Get the global domain event publisher."""
    return _domain_event_publisher


def publish_domain_event(event: DomainEvent) -> None:
    """
    Convenience function to publish a domain event.
    
    Args:
        event: The domain event to publish
    """
    _domain_event_publisher.publish(event)