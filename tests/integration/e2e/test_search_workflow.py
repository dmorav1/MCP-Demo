"""End-to-end integration tests for conversation search workflow."""
import pytest
from datetime import datetime

from app.application.search_conversations import SearchConversationsUseCase
from app.application.dto import SearchQueryDTO, ConversationDTO, MessageDTO
from app.application.ingest_conversation import IngestConversationUseCase
from app.adapters.outbound.embeddings.local_embedding_service import LocalEmbeddingService
from app.domain.value_objects import STANDARD_EMBEDDING_DIMENSION


@pytest.mark.integration
@pytest.mark.slow
class TestSearchWorkflowE2E:
    """End-to-end tests for complete search workflow."""
    
    @pytest.fixture
    def embedding_service(self):
        """Create real embedding service."""
        return LocalEmbeddingService(
            model_name="all-MiniLM-L6-v2",
            device="cpu",
            target_dimension=STANDARD_EMBEDDING_DIMENSION
        )
    
    @pytest.fixture
    def ingest_use_case(
        self, conversation_repository, chunk_repository, embedding_service
    ):
        """Create ingestion use case."""
        return IngestConversationUseCase(
            conversation_repository=conversation_repository,
            chunk_repository=chunk_repository,
            embedding_service=embedding_service,
        )
    
    @pytest.fixture
    def search_use_case(
        self, vector_search_repository, chunk_repository, embedding_service
    ):
        """Create search use case."""
        return SearchConversationsUseCase(
            vector_search_repository=vector_search_repository,
            chunk_repository=chunk_repository,
            embedding_service=embedding_service,
        )
    
    @pytest.mark.asyncio
    async def test_complete_search_workflow(
        self, ingest_use_case, search_use_case
    ):
        """Test complete search workflow from ingestion to retrieval."""
        # Step 1: Ingest conversations
        conversations = [
            ConversationDTO(
                scenario_title="Python Programming Help",
                original_title="How to use loops",
                url="https://test.com/1",
                messages=[
                    MessageDTO(
                        author_name="Student",
                        author_type="human",
                        content="Can you help me understand how to use for loops in Python?",
                        timestamp=datetime.now().isoformat(),
                    ),
                    MessageDTO(
                        author_name="Tutor",
                        author_type="human",
                        content="Sure! A for loop in Python iterates over a sequence like a list or range.",
                        timestamp=datetime.now().isoformat(),
                    ),
                ],
            ),
            ConversationDTO(
                scenario_title="Mobile App Support",
                original_title="App crashes",
                url="https://test.com/2",
                messages=[
                    MessageDTO(
                        author_name="User",
                        author_type="human",
                        content="My mobile app keeps crashing when I open settings.",
                        timestamp=datetime.now().isoformat(),
                    ),
                    MessageDTO(
                        author_name="Support",
                        author_type="human",
                        content="Let's try reinstalling the app to fix the crash issue.",
                        timestamp=datetime.now().isoformat(),
                    ),
                ],
            ),
        ]
        
        for conv_dto in conversations:
            result = await ingest_use_case.execute(conv_dto)
            assert result.success is True
        
        # Step 2: Search for Python-related content
        search_query = SearchQueryDTO(
            query="Python programming loops",
            top_k=5,
        )
        
        search_results = await search_use_case.execute(search_query)
        
        # Verify search results
        assert len(search_results.results) > 0
        
        # Top result should be from Python conversation
        top_result = search_results.results[0]
        assert "Python" in top_result.chunk_text or "loop" in top_result.chunk_text.lower()
    
    @pytest.mark.asyncio
    async def test_search_semantic_matching(
        self, ingest_use_case, search_use_case
    ):
        """Test that search finds semantically similar content."""
        # Ingest conversation about product issues
        conv_dto = ConversationDTO(
            scenario_title="Product Defect Report",
            original_title="Broken item",
            url="https://test.com/defect",
            messages=[
                MessageDTO(
                    author_name="Customer",
                    author_type="human",
                    content="I received a damaged product. The screen is cracked.",
                    timestamp=datetime.now().isoformat(),
                ),
                MessageDTO(
                    author_name="Support",
                    author_type="human",
                    content="I apologize for the defective item. We'll send a replacement immediately.",
                    timestamp=datetime.now().isoformat(),
                ),
            ],
        )
        
        result = await ingest_use_case.execute(conv_dto)
        assert result.success is True
        
        # Search with semantically similar query (different words, same meaning)
        search_query = SearchQueryDTO(
            query="broken merchandise with screen issues",
            top_k=5,
        )
        
        search_results = await search_use_case.execute(search_query)
        
        # Should find the conversation despite different wording
        assert len(search_results.results) > 0
        # Top result should contain relevant content
        top_result = search_results.results[0]
        assert any(
            word in top_result.chunk_text.lower()
            for word in ["damaged", "cracked", "defective", "screen"]
        )
    
    @pytest.mark.asyncio
    async def test_search_ranking(
        self, ingest_use_case, search_use_case
    ):
        """Test that search results are ranked by relevance."""
        # Ingest multiple conversations with varying relevance
        conversations = [
            ConversationDTO(
                scenario_title="Highly Relevant",
                original_title="Test",
                url="https://test.com/1",
                messages=[
                    MessageDTO(
                        author_name="User",
                        author_type="human",
                        content="How do I reset my password for my account?",
                        timestamp=datetime.now().isoformat(),
                    ),
                ],
            ),
            ConversationDTO(
                scenario_title="Somewhat Relevant",
                original_title="Test",
                url="https://test.com/2",
                messages=[
                    MessageDTO(
                        author_name="User",
                        author_type="human",
                        content="I need to update my account settings.",
                        timestamp=datetime.now().isoformat(),
                    ),
                ],
            ),
            ConversationDTO(
                scenario_title="Not Relevant",
                original_title="Test",
                url="https://test.com/3",
                messages=[
                    MessageDTO(
                        author_name="User",
                        author_type="human",
                        content="What are your business hours?",
                        timestamp=datetime.now().isoformat(),
                    ),
                ],
            ),
        ]
        
        for conv_dto in conversations:
            await ingest_use_case.execute(conv_dto)
        
        # Search for password reset
        search_query = SearchQueryDTO(
            query="reset password account",
            top_k=5,
        )
        
        search_results = await search_use_case.execute(search_query)
        
        # Top result should be most relevant
        assert len(search_results.results) > 0
        top_result = search_results.results[0]
        assert "password" in top_result.chunk_text.lower()
        
        # Results should be ordered by distance (ascending)
        distances = [r.distance for r in search_results.results]
        assert distances == sorted(distances)
    
    @pytest.mark.asyncio
    async def test_search_with_limit(
        self, ingest_use_case, search_use_case
    ):
        """Test that search respects top_k limit."""
        # Ingest multiple conversations
        for i in range(5):
            conv_dto = ConversationDTO(
                scenario_title=f"Conversation {i}",
                original_title="Test",
                url=f"https://test.com/{i}",
                messages=[
                    MessageDTO(
                        author_name="User",
                        author_type="human",
                        content=f"This is test message number {i} about support.",
                        timestamp=datetime.now().isoformat(),
                    ),
                ],
            )
            await ingest_use_case.execute(conv_dto)
        
        # Search with small limit
        search_query = SearchQueryDTO(
            query="test support message",
            top_k=3,
        )
        
        search_results = await search_use_case.execute(search_query)
        
        # Should return exactly top_k results
        assert len(search_results.results) == 3
    
    @pytest.mark.asyncio
    async def test_search_empty_database(self, search_use_case):
        """Test search on empty database returns empty results."""
        search_query = SearchQueryDTO(
            query="test query",
            top_k=5,
        )
        
        search_results = await search_use_case.execute(search_query)
        
        # Should return empty results, not error
        assert search_results.results == []
        assert search_results.total_results == 0
    
    @pytest.mark.asyncio
    async def test_search_with_special_characters(
        self, ingest_use_case, search_use_case
    ):
        """Test search handles special characters correctly."""
        # Ingest with special characters
        conv_dto = ConversationDTO(
            scenario_title="Special Test",
            original_title="Test",
            url="https://test.com/special",
            messages=[
                MessageDTO(
                    author_name="User",
                    author_type="human",
                    content="Test with émojis 🎉🎊 and special chars: <>&",
                    timestamp=datetime.now().isoformat(),
                ),
            ],
        )
        
        await ingest_use_case.execute(conv_dto)
        
        # Search with special characters
        search_query = SearchQueryDTO(
            query="émojis special test",
            top_k=5,
        )
        
        search_results = await search_use_case.execute(search_query)
        
        # Should find results
        assert len(search_results.results) > 0


@pytest.mark.integration
@pytest.mark.slow
class TestSearchWorkflowPerformance:
    """Performance tests for search workflow."""
    
    @pytest.fixture
    def embedding_service(self):
        """Create embedding service."""
        return LocalEmbeddingService(
            model_name="all-MiniLM-L6-v2",
            device="cpu",
            target_dimension=STANDARD_EMBEDDING_DIMENSION
        )
    
    @pytest.fixture
    def search_use_case(
        self, vector_search_repository, chunk_repository, embedding_service
    ):
        """Create search use case."""
        return SearchConversationsUseCase(
            vector_search_repository=vector_search_repository,
            chunk_repository=chunk_repository,
            embedding_service=embedding_service,
        )
    
    @pytest.fixture
    def ingest_use_case(
        self, conversation_repository, chunk_repository, embedding_service
    ):
        """Create ingestion use case."""
        return IngestConversationUseCase(
            conversation_repository=conversation_repository,
            chunk_repository=chunk_repository,
            embedding_service=embedding_service,
        )
    
    @pytest.mark.asyncio
    async def test_search_performance(
        self, ingest_use_case, search_use_case
    ):
        """Test search performance with multiple conversations."""
        import time
        
        # Ingest 10 conversations
        for i in range(10):
            conv_dto = ConversationDTO(
                scenario_title=f"Conversation {i}",
                original_title="Test",
                url=f"https://test.com/{i}",
                messages=[
                    MessageDTO(
                        author_name="User",
                        author_type="human",
                        content=f"Message {j} in conversation {i} with test content."
                        for j in range(3)
                    )[0],  # Just use first message for speed
                    timestamp=datetime.now().isoformat(),
                ],
            )
            await ingest_use_case.execute(conv_dto)
        
        # Measure search time
        search_query = SearchQueryDTO(
            query="test content message",
            top_k=5,
        )
        
        start_time = time.time()
        search_results = await search_use_case.execute(search_query)
        elapsed = time.time() - start_time
        
        # Should complete quickly (< 2 seconds)
        assert elapsed < 2.0
        assert len(search_results.results) > 0
        
        print(f"\n⏱️  Search completed in {elapsed:.3f}s")
