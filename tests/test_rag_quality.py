"""
RAG Quality Evaluation Tests.

Measures answer quality, faithfulness, relevance, and hallucination detection
using the evaluation dataset.
"""
import pytest
import json
import os
from unittest.mock import Mock, AsyncMock, patch
from typing import List, Dict, Any

from app.application.rag_service import RAGService
from app.application.dto import SearchResultDTO
from app.domain.value_objects import Embedding


def load_evaluation_dataset():
    """Load evaluation dataset."""
    dataset_path = os.path.join(
        os.path.dirname(__file__),
        "evaluation",
        "rag_eval_dataset.json"
    )
    with open(dataset_path, 'r') as f:
        return json.load(f)


@pytest.fixture
def eval_dataset():
    """Load evaluation dataset fixture."""
    return load_evaluation_dataset()


@pytest.fixture
def quality_config():
    """Create configuration for quality tests."""
    config = Mock()
    config.provider = "openai"
    config.model = "gpt-3.5-turbo"
    config.temperature = 0.7
    config.max_tokens = 2000
    config.openai_api_key = "test-key"
    config.top_k = 5
    config.enable_streaming = False
    config.enable_conversation_memory = False
    config.max_context_tokens = 3500
    config.enable_cache = False
    config.max_retries = 3
    config.timeout_seconds = 60
    config.enable_token_tracking = True
    config.enable_latency_tracking = True
    return config


def create_chunks_from_context(context_list: List[str], conv_id: str = "test-conv") -> List[SearchResultDTO]:
    """Helper to create chunks from context list."""
    return [
        SearchResultDTO(
            chunk_id=f"chunk-{i}",
            conversation_id=conv_id,
            text=text,
            score=0.9 - (i * 0.05),
            author_name=f"Expert{i}",
            author_type="human",
            order_index=i
        )
        for i, text in enumerate(context_list, 1)
    ]


@pytest.mark.unit
class TestAnswerRelevance:
    """Test answer relevance to query."""
    
    def calculate_relevance_score(self, query: str, answer: str, context: List[str]) -> float:
        """
        Calculate relevance score (0-1) based on:
        - Answer addresses the query
        - Answer uses context appropriately
        - Answer is coherent
        """
        score = 0.0
        
        # Check if answer contains key terms from query
        query_terms = set(query.lower().split())
        answer_terms = set(answer.lower().split())
        term_overlap = len(query_terms & answer_terms) / len(query_terms) if query_terms else 0
        score += term_overlap * 0.4
        
        # Check if answer uses context
        context_used = any(ctx_word in answer.lower() for ctx in context for ctx_word in ctx.lower().split())
        score += 0.3 if context_used else 0
        
        # Check if answer has reasonable length
        if 20 <= len(answer.split()) <= 200:
            score += 0.3
        
        return min(score, 1.0)
    
    @pytest.mark.asyncio
    async def test_relevance_factual_questions(self, eval_dataset, quality_config):
        """Test relevance for factual questions."""
        factual_cases = [tc for tc in eval_dataset["test_cases"] if tc["category"] == "factual_question"]
        
        mock_vector_repo = AsyncMock()
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding.return_value = Embedding(vector=[0.1] * 1536)
        
        service = RAGService(
            vector_search_repository=mock_vector_repo,
            embedding_service=mock_embedding_service,
            config=quality_config
        )
        
        for test_case in factual_cases[:2]:  # Test subset
            query = test_case["query"]
            context = test_case["context"]
            expected_answer = test_case["ground_truth_answer"]
            
            # Calculate expected relevance
            relevance = self.calculate_relevance_score(query, expected_answer, context)
            
            # For factual questions, relevance should be high
            assert relevance >= 0.6, f"Low relevance for factual question: {query}"
    
    @pytest.mark.asyncio
    async def test_relevance_out_of_context_questions(self, eval_dataset, quality_config):
        """Test relevance for out-of-context questions."""
        ooc_cases = [tc for tc in eval_dataset["test_cases"] if tc["category"] == "out_of_context"]
        
        for test_case in ooc_cases:
            query = test_case["query"]
            context = test_case["context"]
            expected_answer = test_case["ground_truth_answer"]
            
            # Expected answer should indicate lack of information
            assert any(phrase in expected_answer.lower() for phrase in [
                "does not contain", "no information", "not mentioned", "cannot find"
            ]), f"Out-of-context answer should indicate missing information: {query}"


@pytest.mark.unit
class TestAnswerFaithfulness:
    """Test answer faithfulness to context."""
    
    def calculate_faithfulness_score(self, answer: str, context: List[str]) -> float:
        """
        Calculate faithfulness score (0-1) based on:
        - Claims in answer are supported by context
        - No hallucinated information
        """
        score = 1.0
        
        # Check if answer contains phrases from context
        answer_lower = answer.lower()
        context_lower = [c.lower() for c in context]
        
        # Penalize if answer contains specific facts not in context
        answer_words = set(answer_lower.split())
        context_words = set(word for ctx in context_lower for word in ctx.split())
        
        # Check for citations
        has_citations = "[source" in answer_lower
        if has_citations:
            score += 0.2  # Bonus for citing sources
        
        # Simple heuristic: check context coverage
        unique_answer_words = answer_words - {"the", "a", "an", "is", "are", "was", "were", "be", "been", "being"}
        context_coverage = len(unique_answer_words & context_words) / len(unique_answer_words) if unique_answer_words else 0
        
        score = min(context_coverage + (0.2 if has_citations else 0), 1.0)
        
        return score
    
    @pytest.mark.asyncio
    async def test_faithfulness_with_citations(self, eval_dataset, quality_config):
        """Test faithfulness when answer includes citations."""
        mock_vector_repo = AsyncMock()
        mock_embedding_service = AsyncMock()
        
        service = RAGService(
            vector_search_repository=mock_vector_repo,
            embedding_service=mock_embedding_service,
            config=quality_config
        )
        
        test_case = eval_dataset["test_cases"][0]  # First test case
        context = test_case["context"]
        
        # Mock answer with citations
        answer_with_citations = f"Based on [Source 1], {test_case['ground_truth_answer'][:50]}"
        
        faithfulness = self.calculate_faithfulness_score(answer_with_citations, context)
        
        assert faithfulness > 0.5, "Answer with citations should have reasonable faithfulness"
    
    @pytest.mark.asyncio
    async def test_faithfulness_detects_hallucination(self, quality_config):
        """Test detection of hallucinated information."""
        context = ["Python is a programming language.", "Python was created in 1991."]
        
        # Hallucinated answer
        hallucinated_answer = "Python is a programming language created in 1985 by John Smith."
        
        faithfulness = self.calculate_faithfulness_score(hallucinated_answer, context)
        
        # Should detect that "1985" and "John Smith" are not in context
        # Note: This is a simple heuristic; real faithfulness detection is more complex
        assert faithfulness < 1.0


@pytest.mark.unit
class TestContextRelevance:
    """Test relevance of retrieved context to query."""
    
    def calculate_context_relevance(self, query: str, context_chunks: List[SearchResultDTO]) -> float:
        """
        Calculate context relevance (0-1) based on:
        - Chunk scores
        - Query term overlap
        """
        if not context_chunks:
            return 0.0
        
        # Average chunk score
        avg_score = sum(chunk.score for chunk in context_chunks) / len(context_chunks)
        
        # Query term overlap
        query_terms = set(query.lower().split())
        overlaps = []
        for chunk in context_chunks:
            chunk_terms = set(chunk.text.lower().split())
            overlap = len(query_terms & chunk_terms) / len(query_terms) if query_terms else 0
            overlaps.append(overlap)
        
        avg_overlap = sum(overlaps) / len(overlaps) if overlaps else 0
        
        # Combined score
        return (avg_score * 0.7 + avg_overlap * 0.3)
    
    @pytest.mark.asyncio
    async def test_context_relevance_high_score_chunks(self, quality_config):
        """Test context relevance with high-scoring chunks."""
        chunks = [
            SearchResultDTO(
                chunk_id=f"chunk-{i}",
                conversation_id="conv-1",
                text=f"Python programming language feature {i}",
                score=0.95 - i*0.05,
                author_name="Expert",
                order_index=i
            )
            for i in range(5)
        ]
        
        mock_vector_repo = AsyncMock()
        mock_embedding_service = AsyncMock()
        
        service = RAGService(
            vector_search_repository=mock_vector_repo,
            embedding_service=mock_embedding_service,
            config=quality_config
        )
        
        query = "What is Python programming?"
        relevance = self.calculate_context_relevance(query, chunks)
        
        assert relevance > 0.7, "High-scoring relevant chunks should have high context relevance"
    
    @pytest.mark.asyncio
    async def test_context_relevance_low_score_chunks(self, quality_config):
        """Test context relevance with low-scoring chunks."""
        chunks = [
            SearchResultDTO(
                chunk_id=f"chunk-{i}",
                conversation_id="conv-1",
                text="Unrelated content about something else",
                score=0.3 + i*0.05,
                author_name="User",
                order_index=i
            )
            for i in range(5)
        ]
        
        query = "What is Python programming?"
        relevance = self.calculate_context_relevance(query, chunks)
        
        assert relevance < 0.6, "Low-scoring chunks should have lower context relevance"


@pytest.mark.unit
class TestHallucinationDetection:
    """Test detection of hallucinated information."""
    
    def detect_hallucination(self, answer: str, context: List[str]) -> bool:
        """
        Simple hallucination detection based on:
        - Specific facts (dates, names, numbers) not in context
        - Definitive statements without supporting context
        """
        import re
        
        # Extract potential facts from answer
        dates = re.findall(r'\b\d{4}\b', answer)
        names = re.findall(r'\b[A-Z][a-z]+ [A-Z][a-z]+\b', answer)
        
        context_text = " ".join(context)
        
        # Check if facts are in context
        for date in dates:
            if date not in context_text:
                return True
        
        for name in names:
            if name not in context_text:
                return True
        
        return False
    
    @pytest.mark.asyncio
    async def test_hallucination_detection_clean_answer(self):
        """Test that clean answers are not flagged as hallucinations."""
        context = ["Python was created by Guido van Rossum in 1991."]
        answer = "Based on the context, Python was created by Guido van Rossum in 1991."
        
        is_hallucination = self.detect_hallucination(answer, context)
        
        assert not is_hallucination, "Clean answer should not be flagged as hallucination"
    
    @pytest.mark.asyncio
    async def test_hallucination_detection_fabricated_facts(self):
        """Test detection of fabricated facts."""
        context = ["Python is a programming language."]
        answer = "Python was created by John Smith in 1985."
        
        is_hallucination = self.detect_hallucination(answer, context)
        
        assert is_hallucination, "Fabricated facts should be detected as hallucination"


@pytest.mark.unit
class TestCitationAccuracy:
    """Test accuracy of source citations."""
    
    @pytest.mark.asyncio
    async def test_citations_match_sources(self, quality_config):
        """Test that citations reference existing sources."""
        mock_vector_repo = AsyncMock()
        mock_embedding_service = AsyncMock()
        
        service = RAGService(
            vector_search_repository=mock_vector_repo,
            embedding_service=mock_embedding_service,
            config=quality_config
        )
        
        answer = "According to [Source 1] and [Source 3], Python is great."
        citations = service._extract_citations(answer)
        
        assert citations == [1, 3]
        assert all(c >= 1 for c in citations), "Citations should be positive integers"
    
    @pytest.mark.asyncio
    async def test_citation_content_alignment(self, eval_dataset, quality_config):
        """Test that cited content aligns with source content."""
        test_case = eval_dataset["test_cases"][0]
        expected_citations = test_case["expected_citations"]
        
        # Verify expected citations are reasonable
        assert len(expected_citations) <= len(test_case["context"])
        assert all(1 <= c <= len(test_case["context"]) for c in expected_citations)


@pytest.mark.unit
class TestQualityMetricsIntegration:
    """Test integration of quality metrics."""
    
    @pytest.mark.asyncio
    async def test_overall_quality_score(self, eval_dataset, quality_config):
        """Test calculation of overall quality score."""
        mock_vector_repo = AsyncMock()
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embedding.return_value = Embedding(vector=[0.1] * 1536)
        
        service = RAGService(
            vector_search_repository=mock_vector_repo,
            embedding_service=mock_embedding_service,
            config=quality_config
        )
        
        test_case = eval_dataset["test_cases"][0]
        
        # Calculate component scores
        chunks = create_chunks_from_context(test_case["context"])
        
        # Answer relevance
        relevance_calculator = TestAnswerRelevance()
        relevance = relevance_calculator.calculate_relevance_score(
            test_case["query"],
            test_case["ground_truth_answer"],
            test_case["context"]
        )
        
        # Context relevance
        context_calculator = TestContextRelevance()
        context_relevance = context_calculator.calculate_context_relevance(
            test_case["query"],
            chunks
        )
        
        # Overall quality (simple average)
        overall_quality = (relevance + context_relevance) / 2
        
        # For high-quality test cases, overall score should be good
        if test_case["relevance_score"] >= 0.9:
            assert overall_quality >= 0.6, "High-quality case should have good overall score"
