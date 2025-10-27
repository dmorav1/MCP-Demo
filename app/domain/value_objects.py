"""
Domain value objects - Immutable objects that represent domain concepts.

These value objects enforce business rules and provide type safety
without any infrastructure dependencies.
"""
from typing import List, Optional
from dataclasses import dataclass
from datetime import datetime
from abc import ABC


@dataclass(frozen=True)
class ConversationId:
    """Strongly typed conversation identifier."""
    value: int
    
    def __post_init__(self):
        if self.value <= 0:
            raise ValueError("ConversationId must be positive")


@dataclass(frozen=True)
class ChunkId:
    """Strongly typed chunk identifier."""
    value: int
    
    def __post_init__(self):
        if self.value <= 0:
            raise ValueError("ChunkId must be positive")


@dataclass(frozen=True)
class ChunkText:
    """Represents conversation chunk text with business rules."""
    content: str
    
    def __post_init__(self):
        if not self.content or not self.content.strip():
            raise ValueError("ChunkText cannot be empty")
        if len(self.content) > 10000:  # Business rule: max chunk size
            raise ValueError("ChunkText too long (max 10000 characters)")
    
    @property
    def word_count(self) -> int:
        """Get approximate word count."""
        return len(self.content.split())


@dataclass(frozen=True)
class Embedding:
    """Represents a vector embedding with dimension validation."""
    vector: List[float]
    
    def __post_init__(self):
        if not self.vector:
            raise ValueError("Embedding vector cannot be empty")
        if len(self.vector) != 1536:  # Business rule: standard dimension
            raise ValueError(f"Embedding must be 1536 dimensions, got {len(self.vector)}")
        if not all(isinstance(x, (int, float)) for x in self.vector):
            raise ValueError("Embedding vector must contain only numbers")
    
    @property
    def dimension(self) -> int:
        """Get embedding dimension."""
        return len(self.vector)


@dataclass(frozen=True)
class SearchQuery:
    """Represents a search query with validation."""
    text: str
    
    def __post_init__(self):
        if not self.text or not self.text.strip():
            raise ValueError("SearchQuery cannot be empty")
        if len(self.text) > 1000:  # Business rule: reasonable query length
            raise ValueError("SearchQuery too long (max 1000 characters)")
    
    @property
    def normalized_text(self) -> str:
        """Get normalized query text."""
        return self.text.strip().lower()


@dataclass(frozen=True)
class RelevanceScore:
    """Represents a relevance score with validation."""
    value: float
    
    def __post_init__(self):
        if not 0.0 <= self.value <= 1.0:
            raise ValueError("RelevanceScore must be between 0.0 and 1.0")
    
    def is_relevant(self, threshold: float = 0.7) -> bool:
        """Check if score meets relevance threshold."""
        return self.value >= threshold
    
    def __lt__(self, other: 'RelevanceScore') -> bool:
        return self.value < other.value
    
    def __le__(self, other: 'RelevanceScore') -> bool:
        return self.value <= other.value
    
    def __gt__(self, other: 'RelevanceScore') -> bool:
        return self.value > other.value
    
    def __ge__(self, other: 'RelevanceScore') -> bool:
        return self.value >= other.value


@dataclass(frozen=True)
class AuthorInfo:
    """Represents author information."""
    name: Optional[str]
    author_type: str = "human"
    
    def __post_init__(self):
        if self.author_type not in ["human", "assistant", "system"]:
            raise ValueError("AuthorType must be 'human', 'assistant', or 'system'")


@dataclass(frozen=True)
class ConversationMetadata:
    """Represents conversation metadata."""
    scenario_title: Optional[str] = None
    original_title: Optional[str] = None
    url: Optional[str] = None
    created_at: Optional[datetime] = None
    
    def has_title(self) -> bool:
        """Check if conversation has any title."""
        return bool(self.scenario_title or self.original_title)


@dataclass(frozen=True)
class ChunkMetadata:
    """Represents chunk-specific metadata."""
    order_index: int
    author_info: AuthorInfo
    timestamp: Optional[datetime] = None
    
    def __post_init__(self):
        if self.order_index < 0:
            raise ValueError("OrderIndex cannot be negative")