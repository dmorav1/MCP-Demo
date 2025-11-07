"""Integration tests for vector search with real pgvector."""
import pytest
import numpy as np

from app.domain.value_objects import Embedding


@pytest.mark.integration
class TestVectorSearchIntegration:
    """Integration tests for vector search with pgvector."""
    
    @pytest.mark.asyncio
    async def test_vector_search_basic(
        self, vector_search_repository, conversation_repository,
        sample_conversation_with_embeddings
    ):
        """Test basic vector similarity search."""
        # Save conversation with embeddings
        saved = await conversation_repository.save(sample_conversation_with_embeddings)
        
        # Create query vector similar to first chunk (i=0, value=0.0)
        query_vector = [0.05] * 1536
        query_embedding = Embedding(vector=query_vector)
        
        # Search
        results = await vector_search_repository.search_similar(
            embedding=query_embedding,
            limit=10
        )
        
        # Should find results
        assert len(results) > 0
        
        # First result should be chunk 0 (most similar)
        assert results[0].chunk_id is not None
    
    @pytest.mark.asyncio
    async def test_vector_search_with_limit(
        self, vector_search_repository, conversation_repository,
        sample_conversation_with_embeddings, sample_conversation_metadata
    ):
        """Test vector search respects limit parameter."""
        from app.domain.entities import Conversation, ConversationChunk
        from app.domain.value_objects import ChunkText, ChunkMetadata, AuthorInfo, ConversationId
        from datetime import datetime
        
        # Create multiple conversations with embeddings
        for i in range(5):
            chunks = []
            for j in range(3):
                vector = [float(i * j * 0.1)] * 1536
                chunk = ConversationChunk(
                    id=None,
                    conversation_id=ConversationId(1),
                    text=ChunkText(content=f"Chunk {i}-{j}"),
                    metadata=ChunkMetadata(
                        order_index=j,
                        author_info=AuthorInfo(name=f"User{i}", author_type="human"),
                        timestamp=datetime.now(),
                    ),
                    embedding=Embedding(vector=vector),
                )
                chunks.append(chunk)
            
            conv = Conversation(
                id=None,
                metadata=sample_conversation_metadata,
                chunks=chunks,
            )
            await conversation_repository.save(conv)
        
        # Search with different limits
        query_embedding = Embedding(vector=[0.1] * 1536)
        
        results_5 = await vector_search_repository.search_similar(
            embedding=query_embedding,
            limit=5
        )
        assert len(results_5) == 5
        
        results_10 = await vector_search_repository.search_similar(
            embedding=query_embedding,
            limit=10
        )
        assert len(results_10) == 10
    
    @pytest.mark.asyncio
    async def test_vector_search_ranking(
        self, vector_search_repository, conversation_repository,
        sample_conversation_metadata
    ):
        """Test that vector search returns results in similarity order."""
        from app.domain.entities import Conversation, ConversationChunk
        from app.domain.value_objects import (
            ChunkText, ChunkMetadata, AuthorInfo, ConversationId
        )
        from datetime import datetime
        
        # Create chunks with different embeddings
        # Chunk 0: very similar to query
        # Chunk 1: somewhat similar
        # Chunk 2: dissimilar
        query_vector = [1.0] * 1536
        
        chunks = [
            ConversationChunk(
                id=None,
                conversation_id=ConversationId(1),
                text=ChunkText(content="Very similar chunk"),
                metadata=ChunkMetadata(
                    order_index=0,
                    author_info=AuthorInfo(name="User", author_type="human"),
                    timestamp=datetime.now(),
                ),
                embedding=Embedding(vector=[0.95] * 1536),  # Very similar
            ),
            ConversationChunk(
                id=None,
                conversation_id=ConversationId(1),
                text=ChunkText(content="Somewhat similar chunk"),
                metadata=ChunkMetadata(
                    order_index=1,
                    author_info=AuthorInfo(name="User", author_type="human"),
                    timestamp=datetime.now(),
                ),
                embedding=Embedding(vector=[0.5] * 1536),  # Somewhat similar
            ),
            ConversationChunk(
                id=None,
                conversation_id=ConversationId(1),
                text=ChunkText(content="Dissimilar chunk"),
                metadata=ChunkMetadata(
                    order_index=2,
                    author_info=AuthorInfo(name="User", author_type="human"),
                    timestamp=datetime.now(),
                ),
                embedding=Embedding(vector=[0.0] * 1536),  # Dissimilar
            ),
        ]
        
        conv = Conversation(
            id=None,
            metadata=sample_conversation_metadata,
            chunks=chunks,
        )
        saved = await conversation_repository.save(conv)
        
        # Search
        results = await vector_search_repository.search_similar(
            embedding=Embedding(vector=query_vector),
            limit=3
        )
        
        # Verify results are in descending similarity order
        assert len(results) == 3
        # Distances should be in ascending order (lower distance = more similar)
        distances = [r.distance for r in results]
        assert distances == sorted(distances)
    
    @pytest.mark.asyncio
    async def test_vector_search_with_threshold(
        self, vector_search_repository, conversation_repository,
        sample_conversation_with_embeddings
    ):
        """Test vector search with similarity threshold."""
        # Save conversation
        await conversation_repository.save(sample_conversation_with_embeddings)
        
        # Search with high threshold (only very similar results)
        query_embedding = Embedding(vector=[0.0] * 1536)
        
        results = await vector_search_repository.search_similar(
            embedding=query_embedding,
            limit=10,
            threshold=0.01  # Very strict threshold
        )
        
        # Should only return very similar results
        # All results should have distance <= threshold
        for result in results:
            assert result.distance <= 0.01
    
    @pytest.mark.asyncio
    async def test_vector_search_empty_database(
        self, vector_search_repository
    ):
        """Test vector search on empty database."""
        query_embedding = Embedding(vector=[0.5] * 1536)
        
        results = await vector_search_repository.search_similar(
            embedding=query_embedding,
            limit=10
        )
        
        # Should return empty list, not error
        assert results == []
    
    @pytest.mark.asyncio
    async def test_vector_cosine_similarity(
        self, vector_search_repository, conversation_repository,
        sample_conversation_metadata
    ):
        """Test cosine similarity calculation correctness."""
        from app.domain.entities import Conversation, ConversationChunk
        from app.domain.value_objects import (
            ChunkText, ChunkMetadata, AuthorInfo, ConversationId
        )
        from datetime import datetime
        
        # Create chunks with known vectors
        # Identical vectors should have distance close to 0
        identical_vector = [1.0] * 1536
        
        chunk = ConversationChunk(
            id=None,
            conversation_id=ConversationId(1),
            text=ChunkText(content="Test chunk"),
            metadata=ChunkMetadata(
                order_index=0,
                author_info=AuthorInfo(name="User", author_type="human"),
                timestamp=datetime.now(),
            ),
            embedding=Embedding(vector=identical_vector),
        )
        
        conv = Conversation(
            id=None,
            metadata=sample_conversation_metadata,
            chunks=[chunk],
        )
        await conversation_repository.save(conv)
        
        # Search with identical vector
        results = await vector_search_repository.search_similar(
            embedding=Embedding(vector=identical_vector),
            limit=1
        )
        
        # Distance should be very close to 0 (identical vectors)
        assert len(results) == 1
        assert results[0].distance < 0.001  # Near perfect match
    
    @pytest.mark.asyncio
    async def test_vector_search_excludes_null_embeddings(
        self, vector_search_repository, conversation_repository,
        sample_conversation
    ):
        """Test that search only returns chunks with embeddings."""
        # Save conversation without embeddings
        await conversation_repository.save(sample_conversation)
        
        # Search
        query_embedding = Embedding(vector=[0.5] * 1536)
        results = await vector_search_repository.search_similar(
            embedding=query_embedding,
            limit=10
        )
        
        # Should not return chunks without embeddings
        # In this case, should return empty since no chunks have embeddings
        assert results == []


@pytest.mark.integration
@pytest.mark.slow
class TestVectorSearchPerformance:
    """Performance tests for vector search."""
    
    @pytest.mark.asyncio
    async def test_search_performance_with_many_vectors(
        self, vector_search_repository, conversation_repository,
        sample_conversation_metadata
    ):
        """Test search performance with large number of vectors."""
        import time
        from app.domain.entities import Conversation, ConversationChunk
        from app.domain.value_objects import (
            ChunkText, ChunkMetadata, AuthorInfo, ConversationId
        )
        from datetime import datetime
        
        # Create 50 conversations with 5 chunks each = 250 vectors
        for i in range(50):
            chunks = []
            for j in range(5):
                # Random-ish vector
                vector = [float((i + j) % 100) / 100.0] * 1536
                chunk = ConversationChunk(
                    id=None,
                    conversation_id=ConversationId(1),
                    text=ChunkText(content=f"Chunk {i}-{j}"),
                    metadata=ChunkMetadata(
                        order_index=j,
                        author_info=AuthorInfo(name=f"User{i}", author_type="human"),
                        timestamp=datetime.now(),
                    ),
                    embedding=Embedding(vector=vector),
                )
                chunks.append(chunk)
            
            conv = Conversation(
                id=None,
                metadata=sample_conversation_metadata,
                chunks=chunks,
            )
            await conversation_repository.save(conv)
        
        # Measure search time
        query_embedding = Embedding(vector=[0.5] * 1536)
        
        start_time = time.time()
        results = await vector_search_repository.search_similar(
            embedding=query_embedding,
            limit=10
        )
        elapsed = time.time() - start_time
        
        # Should complete quickly (< 0.5 seconds for 250 vectors)
        assert elapsed < 0.5
        assert len(results) == 10
        
        print(f"\n⏱️  Vector search (250 vectors) completed in {elapsed:.3f}s")
