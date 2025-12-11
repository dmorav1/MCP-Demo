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
        await conversation_repository.save(sample_conversation_with_embeddings)
        
        # Create query vector identically matching first chunk (i=0, vector=[0.0]*1536)
        query_vector = [0.0] * 1536
        query_embedding = Embedding(vector=query_vector)
        
        # Search
        results = await vector_search_repository.similarity_search(
            query_embedding=query_embedding,
            top_k=10
        )
        
        # Should find results
        assert len(results) > 0
        
        # First result should be chunk 0 (most similar)
        # Result is (chunk, score) tuple
        assert results[0][0].id is not None
        # Should be almost perfect match (score ~1.0)
        assert results[0][1].value > 0.99
    
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
        
        results_5 = await vector_search_repository.similarity_search(
            query_embedding=query_embedding,
            top_k=5
        )
        assert len(results_5) == 5
        
        results_10 = await vector_search_repository.similarity_search(
            query_embedding=query_embedding,
            top_k=10
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
        
        # Create chunks with controlled similarity
        base_vector = [1.0] * 1536
        query_vector = list(base_vector)
        
        # Chunk 0: Identical to query (Score 1.0)
        vec0 = list(base_vector)
        
        # Chunk 1: One dimension different (Score ~0.5)
        vec1 = list(base_vector)
        vec1[0] = 0.0
        
        # Chunk 2: Two dimensions different (Score ~0.41)
        vec2 = list(base_vector)
        vec2[0] = 0.0
        vec2[1] = 0.0
        
        chunks = [
            ConversationChunk(
                id=None,
                conversation_id=ConversationId(2),
                text=ChunkText(content="Identical chunk"),
                metadata=ChunkMetadata(
                    order_index=0,
                    author_info=AuthorInfo(name="User", author_type="human"),
                    timestamp=datetime.now(),
                ),
                embedding=Embedding(vector=vec0),
            ),
            ConversationChunk(
                id=None,
                conversation_id=ConversationId(2),
                text=ChunkText(content="Visual 1 diff chunk"),
                metadata=ChunkMetadata(
                    order_index=1,
                    author_info=AuthorInfo(name="User", author_type="human"),
                    timestamp=datetime.now(),
                ),
                embedding=Embedding(vector=vec1),
            ),
            ConversationChunk(
                id=None,
                conversation_id=ConversationId(2),
                text=ChunkText(content="Visual 2 diff chunk"),
                metadata=ChunkMetadata(
                    order_index=2,
                    author_info=AuthorInfo(name="User", author_type="human"),
                    timestamp=datetime.now(),
                ),
                embedding=Embedding(vector=vec2),
            ),
        ]
        
        conv = Conversation(
            id=ConversationId(2),  # Explicitly set ID
            metadata=sample_conversation_metadata,
            chunks=chunks,
        )
        await conversation_repository.save(conv)
        
        # Verify persistence
        saved_conv = await conversation_repository.get_by_id(ConversationId(2))
        assert saved_conv is not None
        assert len(saved_conv.chunks) == 3
        # Ensure they have embeddings
        assert all(c.embedding is not None for c in saved_conv.chunks)
        
        # Search
        results = await vector_search_repository.similarity_search(
            query_embedding=Embedding(vector=query_vector),
            top_k=5  # Ask for more than 3 to be sure
        )
        
        print(f"DEBUG: Found {len(results)} results")
        for i, (chunk, score) in enumerate(results):
             print(f"Result {i}: ID={chunk.id}, Score={score.value}, Text={chunk.text.content}")
        
        # Verify results are in descending similarity order
        assert len(results) >= 3
        # Scores should be in descending order (higher score = more similar)
        scores = [r[1].value for r in results]
        assert scores == sorted(scores, reverse=True)
        assert scores[0] > 0.99  # Identical match
        assert 0.45 < scores[1] < 0.55  # 1 diff
        assert 0.35 < scores[2] < 0.45  # 2 diffs
    
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
        
        # Use similarity_search_with_threshold
        results = await vector_search_repository.similarity_search_with_threshold(
            query_embedding=query_embedding,
            top_k=10,
            threshold=0.9  # High threshold
        )
        
        # Should only return very similar results
        for result in results:
            assert result[1].value >= 0.9
    
    @pytest.mark.asyncio
    async def test_vector_search_empty_database(
        self, vector_search_repository
    ):
        """Test vector search on empty database."""
        query_embedding = Embedding(vector=[0.5] * 1536)
        
        results = await vector_search_repository.similarity_search(
            query_embedding=query_embedding,
            top_k=10
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
        results = await vector_search_repository.similarity_search(
            query_embedding=Embedding(vector=identical_vector),
            top_k=1
        )
        
        # Relevance score should be very close to 1.0 (identical vectors)
        assert len(results) == 1
        assert results[0][1].value > 0.999
    
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
        results = await vector_search_repository.similarity_search(
            query_embedding=query_embedding,
            top_k=10
        )
        
        # Should not return chunks without embeddings
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
        results = await vector_search_repository.similarity_search(
            query_embedding=query_embedding,
            top_k=10
        )
        elapsed = time.time() - start_time
        
        # Should complete quickly (< 0.5 seconds for 250 vectors)
        assert elapsed < 0.5
        assert len(results) == 10
        
        print(f"\\n⏱️  Vector search (250 vectors) completed in {elapsed:.3f}s")
