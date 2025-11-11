"""
RAG Edge Case Tests.

Tests queries with no relevant context, ambiguous queries, very long queries,
special characters, and other edge cases.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.application.rag_service import RAGService
from app.application.dto import SearchResultDTO
from app.domain.value_objects import Embedding


@pytest.fixture
def edge_case_config():
    """Create configuration for edge case tests."""
    config = Mock()
    config.provider = "openai"
    config.model = "gpt-3.5-turbo"
    config.temperature = 0.7
    config.max_tokens = 2000
    config.openai_api_key = "test-key"
    config.top_k = 5
    config.max_context_tokens = 3500
    config.enable_cache = False
    config.max_retries = 3
    config.timeout_seconds = 60
    config.enable_token_tracking = True
    config.enable_latency_tracking = True
    config.enable_streaming = False
    config.enable_conversation_memory = False
    return config


@pytest.mark.unit
class TestNoRelevantContext:
    """Test queries with no relevant context."""
    
    @pytest.mark.asyncio
    async def test_query_with_no_results(self, edge_case_config):
        """Test handling query when no relevant chunks are found."""
        mock_vector_repo = AsyncMock()
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding.return_value = Embedding(vector=[0.1] * 1536)
        
        # Return empty results
        mock_vector_repo.similarity_search.return_value = []
        
        service = RAGService(
            vector_search_repository=mock_vector_repo,
            embedding_service=mock_embedding_service,
            config=edge_case_config
        )
        
        result = await service.ask("Query with no relevant context")
        
        assert result["answer"] is not None
        assert result["sources"] == []
        assert result["confidence"] == 0.0
        assert result["metadata"]["chunks_retrieved"] == 0
    
    @pytest.mark.asyncio
    async def test_query_with_low_relevance_chunks(self, edge_case_config):
        """Test handling query with only low-relevance chunks."""
        mock_vector_repo = AsyncMock()
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding.return_value = Embedding(vector=[0.1] * 1536)
        
        # Return low-score chunks
        low_score_chunks = [
            (Mock(
                chunk_id=Mock(value=f"chunk-{i}"),
                conversation_id=Mock(value="conv-1"),
                text=Mock(value=f"Unrelated content {i}"),
                author_info=Mock(name="User", author_type="human"),
                metadata=Mock(order_index=i)
            ), Mock(value=0.3 + i*0.01))  # Low scores
            for i in range(3)
        ]
        
        mock_vector_repo.similarity_search.return_value = low_score_chunks
        
        service = RAGService(
            vector_search_repository=mock_vector_repo,
            embedding_service=mock_embedding_service,
            config=edge_case_config
        )
        
        with patch.object(service, '_get_llm') as mock_get_llm:
            mock_llm = AsyncMock()
            mock_chain = AsyncMock()
            mock_chain.ainvoke.return_value = "I cannot find relevant information in the context."
            mock_get_llm.return_value = mock_llm
            
            with patch('app.application.rag_service.RunnablePassthrough'), \
                 patch('app.application.rag_service.PromptTemplate'), \
                 patch('app.application.rag_service.StrOutputParser'):
                
                result = await service.ask("Unrelated query")
                
                # Should have low confidence
                assert result["confidence"] < 0.6


@pytest.mark.unit
class TestAmbiguousQueries:
    """Test handling of ambiguous queries."""
    
    @pytest.mark.asyncio
    async def test_vague_query(self, edge_case_config):
        """Test handling of vague, ambiguous query."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=edge_case_config
        )
        
        vague_queries = [
            "Tell me about it",
            "How does that work?",
            "What about the thing?",
            "Why is it like that?"
        ]
        
        # These should still be sanitized successfully
        for query in vague_queries:
            sanitized = service._sanitize_query(query)
            assert len(sanitized) >= 3
            assert sanitized == query.strip()
    
    @pytest.mark.asyncio
    async def test_multi_part_question(self, edge_case_config):
        """Test handling of multi-part questions."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=edge_case_config
        )
        
        multi_part_query = "What is Python, how is it different from Java, and what are its main uses?"
        
        sanitized = service._sanitize_query(multi_part_query)
        assert sanitized == multi_part_query
        assert "Python" in sanitized
        assert "Java" in sanitized


@pytest.mark.unit
class TestVeryLongQueries:
    """Test handling of very long queries."""
    
    @pytest.mark.asyncio
    async def test_query_length_truncation(self, edge_case_config):
        """Test that very long queries are truncated."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=edge_case_config
        )
        
        # Query longer than 1000 characters
        very_long_query = "What is Python? " * 100  # ~1600 characters
        
        sanitized = service._sanitize_query(very_long_query)
        
        # Should be truncated to 1000 characters
        assert len(sanitized) == 1000
    
    @pytest.mark.asyncio
    async def test_query_at_length_boundary(self, edge_case_config):
        """Test query exactly at 1000 character boundary."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=edge_case_config
        )
        
        # Exactly 1000 characters
        boundary_query = "x" * 1000
        
        sanitized = service._sanitize_query(boundary_query)
        
        # Should not be truncated
        assert len(sanitized) == 1000
    
    @pytest.mark.asyncio
    async def test_context_truncation_with_long_query(self, edge_case_config):
        """Test context truncation when query is long."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=edge_case_config
        )
        
        long_context = "Context text. " * 500  # ~7000 characters
        
        truncated = service._truncate_context(long_context, max_tokens=500)
        
        # Should be truncated
        assert len(truncated) < len(long_context)
        assert "[... context truncated ...]" in truncated


@pytest.mark.unit
class TestSpecialCharacters:
    """Test handling of special characters and formatting."""
    
    @pytest.mark.asyncio
    async def test_query_with_special_characters(self, edge_case_config):
        """Test query with various special characters."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=edge_case_config
        )
        
        special_char_queries = [
            "What is Python's syntax?",  # Apostrophe
            "How does Python != Java?",  # Operators
            "Python (the language)",     # Parentheses
            "Python: features & benefits",  # Colon & ampersand
            "What about @decorators?",   # @ symbol
            "List items: 1) first, 2) second",  # Numbers & punctuation
            "Price is $100 or €90",      # Currency symbols
        ]
        
        for query in special_char_queries:
            sanitized = service._sanitize_query(query)
            # Should preserve special characters
            assert len(sanitized) >= 3
    
    @pytest.mark.asyncio
    async def test_query_with_code_snippets(self, edge_case_config):
        """Test query containing code snippets."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=edge_case_config
        )
        
        code_query = "How does the function `def hello(): return 'world'` work?"
        
        sanitized = service._sanitize_query(code_query)
        assert "def hello()" in sanitized
        assert "`" in sanitized  # Backticks preserved
    
    @pytest.mark.asyncio
    async def test_query_with_unicode(self, edge_case_config):
        """Test query with Unicode characters."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=edge_case_config
        )
        
        unicode_queries = [
            "What is Python's rôle in AI?",  # Accented characters
            "Python vs C++",                  # Plus symbols
            "Python → popular language",      # Arrow
            "Python ≠ Java",                  # Not equal symbol
        ]
        
        for query in unicode_queries:
            try:
                sanitized = service._sanitize_query(query)
                assert len(sanitized) >= 3
            except UnicodeError:
                pytest.fail(f"Unicode handling failed for: {query}")


@pytest.mark.unit
class TestEmptyAndWhitespace:
    """Test handling of empty and whitespace queries."""
    
    @pytest.mark.asyncio
    async def test_empty_query(self, edge_case_config):
        """Test handling of empty query."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=edge_case_config
        )
        
        with pytest.raises(ValueError, match="Query cannot be empty"):
            service._sanitize_query("")
    
    @pytest.mark.asyncio
    async def test_whitespace_only_query(self, edge_case_config):
        """Test handling of whitespace-only query."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=edge_case_config
        )
        
        with pytest.raises(ValueError, match="Query cannot be empty"):
            service._sanitize_query("   \t\n   ")
    
    @pytest.mark.asyncio
    async def test_query_with_excessive_whitespace(self, edge_case_config):
        """Test query with excessive internal whitespace."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=edge_case_config
        )
        
        query_with_spaces = "What    is     Python?"
        
        sanitized = service._sanitize_query(query_with_spaces)
        
        # Should normalize to single spaces
        assert sanitized == "What is Python?"


@pytest.mark.unit
class TestMultilingualQueries:
    """Test handling of multilingual queries."""
    
    @pytest.mark.asyncio
    async def test_non_english_query(self, edge_case_config):
        """Test query in non-English language."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=edge_case_config
        )
        
        multilingual_queries = [
            "¿Qué es Python?",              # Spanish
            "Was ist Python?",               # German
            "Qu'est-ce que Python?",        # French
            "Python とは何ですか？",          # Japanese
            "Python是什么？",                 # Chinese
        ]
        
        for query in multilingual_queries:
            try:
                sanitized = service._sanitize_query(query)
                assert len(sanitized) >= 3
            except Exception as e:
                pytest.fail(f"Multilingual query failed: {query} - {e}")


@pytest.mark.unit
class TestBoundaryConditions:
    """Test boundary conditions."""
    
    @pytest.mark.asyncio
    async def test_minimum_valid_query_length(self, edge_case_config):
        """Test minimum valid query length."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=edge_case_config
        )
        
        # Minimum is 3 characters
        min_query = "abc"
        sanitized = service._sanitize_query(min_query)
        assert sanitized == min_query
    
    @pytest.mark.asyncio
    async def test_below_minimum_query_length(self, edge_case_config):
        """Test query below minimum length."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=edge_case_config
        )
        
        with pytest.raises(ValueError, match="too short"):
            service._sanitize_query("ab")  # 2 characters
    
    @pytest.mark.asyncio
    async def test_maximum_context_chunks(self, edge_case_config):
        """Test with maximum number of context chunks."""
        mock_vector_repo = AsyncMock()
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding.return_value = Embedding(vector=[0.1] * 1536)
        
        # Maximum chunks
        max_chunks = 50
        large_chunk_set = [
            (Mock(
                chunk_id=Mock(value=f"chunk-{i}"),
                conversation_id=Mock(value="conv-1"),
                text=Mock(value=f"Content {i}"),
                author_info=Mock(name="User", author_type="human"),
                metadata=Mock(order_index=i)
            ), Mock(value=0.9 - i*0.01))
            for i in range(max_chunks)
        ]
        
        mock_vector_repo.similarity_search.return_value = large_chunk_set
        
        service = RAGService(
            vector_search_repository=mock_vector_repo,
            embedding_service=mock_embedding_service,
            config=edge_case_config
        )
        
        with patch.object(service, '_get_llm') as mock_get_llm:
            mock_llm = AsyncMock()
            mock_chain = AsyncMock()
            mock_chain.ainvoke.return_value = "Answer"
            mock_get_llm.return_value = mock_llm
            
            with patch('app.application.rag_service.RunnablePassthrough'), \
                 patch('app.application.rag_service.PromptTemplate'), \
                 patch('app.application.rag_service.StrOutputParser'):
                
                result = await service.ask("Query")
                
                # Should handle large number of chunks
                assert result["metadata"]["chunks_retrieved"] == max_chunks
