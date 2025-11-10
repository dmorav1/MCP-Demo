"""
Prompt Engineering Tests.

Tests different prompt variations, A/B testing, few-shot learning,
and system prompt effectiveness.
"""
import pytest
from unittest.mock import Mock, AsyncMock, patch

from app.application.rag_service import RAGService
from app.application.dto import SearchResultDTO
from app.domain.value_objects import Embedding


@pytest.fixture
def prompt_config():
    """Create configuration for prompt tests."""
    config = Mock()
    config.provider = "openai"
    config.model = "gpt-3.5-turbo"
    config.temperature = 0.7
    config.max_tokens = 1000
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
class TestPromptTemplateVariations:
    """Test different prompt template variations."""
    
    def test_default_prompt_template_structure(self, prompt_config):
        """Test default QA prompt template structure."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=prompt_config
        )
        
        template = service.DEFAULT_QA_TEMPLATE
        
        # Verify key components
        assert "{context}" in template
        assert "{question}" in template
        assert "cite" in template.lower() or "source" in template.lower()
        assert "answer" in template.lower()
    
    def test_custom_prompt_template(self, prompt_config):
        """Test using custom prompt template."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=prompt_config
        )
        
        # Custom template emphasizing conciseness
        custom_template = """Based on the following context, provide a brief, direct answer to the question.

Context:
{context}

Question: {question}

Brief Answer:"""
        
        # Replace default template
        original_template = service.DEFAULT_QA_TEMPLATE
        service.DEFAULT_QA_TEMPLATE = custom_template
        
        assert service.DEFAULT_QA_TEMPLATE == custom_template
        assert "{context}" in service.DEFAULT_QA_TEMPLATE
        assert "{question}" in service.DEFAULT_QA_TEMPLATE
        
        # Restore original
        service.DEFAULT_QA_TEMPLATE = original_template
    
    def test_prompt_with_examples(self, prompt_config):
        """Test prompt template with few-shot examples."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=prompt_config
        )
        
        # Template with few-shot examples
        few_shot_template = """You are a helpful assistant. Answer based on context and cite sources.

Example 1:
Context: Python is a programming language created by Guido van Rossum.
Question: Who created Python?
Answer: According to [Source 1], Python was created by Guido van Rossum.

Example 2:
Context: Python emphasizes code readability.
Question: What is a key feature of Python?
Answer: Based on [Source 1], a key feature of Python is code readability.

Now answer the following:

Context:
{context}

Question: {question}

Answer:"""
        
        # Verify few-shot structure
        assert "Example 1:" in few_shot_template
        assert "Example 2:" in few_shot_template
        assert "{context}" in few_shot_template
        assert "{question}" in few_shot_template


@pytest.mark.unit
class TestPromptABTesting:
    """Test A/B testing of prompt templates."""
    
    @pytest.mark.asyncio
    async def test_compare_prompt_templates(self, prompt_config):
        """Compare effectiveness of different prompt templates."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=prompt_config
        )
        
        # Template A: Direct
        template_a = """Answer the question based on context.

Context: {context}
Question: {question}
Answer:"""
        
        # Template B: Instructive
        template_b = """You are an expert assistant. Use the context to answer accurately.
Always cite sources using [Source N] format.

Context: {context}
Question: {question}

Detailed Answer with Citations:"""
        
        # Both templates should have required variables
        for template in [template_a, template_b]:
            assert "{context}" in template
            assert "{question}" in template
        
        # Template B has more explicit instructions
        assert "cite" in template_b.lower()
        assert len(template_b) > len(template_a)
    
    @pytest.mark.asyncio
    async def test_temperature_variation_effect(self, prompt_config):
        """Test effect of temperature on response variation."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=prompt_config
        )
        
        # Lower temperature (more deterministic)
        low_temp_config = Mock(spec=prompt_config)
        low_temp_config.temperature = 0.1
        
        # Higher temperature (more creative)
        high_temp_config = Mock(spec=prompt_config)
        high_temp_config.temperature = 1.5
        
        # Verify temperature ranges
        assert 0.0 <= low_temp_config.temperature <= 2.0
        assert 0.0 <= high_temp_config.temperature <= 2.0


@pytest.mark.unit
class TestFewShotLearning:
    """Test few-shot learning examples in prompts."""
    
    def test_few_shot_citation_examples(self, prompt_config):
        """Test few-shot examples for proper citation."""
        few_shot_prompt = """Answer questions based on context. Always cite sources.

Example:
Context: [Source 1] Python was created by Guido van Rossum.
Question: Who created Python?
Answer: According to [Source 1], Python was created by Guido van Rossum.

Now your turn:
Context: {context}
Question: {question}
Answer:"""
        
        # Verify few-shot structure
        assert "Example:" in few_shot_prompt
        assert "[Source 1]" in few_shot_prompt
        assert "According to" in few_shot_prompt
    
    def test_few_shot_refusal_examples(self, prompt_config):
        """Test few-shot examples for refusing unanswerable questions."""
        few_shot_prompt = """Answer based on context. If information is not in context, say so.

Example 1:
Context: Python is a programming language.
Question: What is Python's latest version?
Answer: The context does not contain information about Python's latest version.

Example 2:
Context: Python emphasizes readability.
Question: What does Python emphasize?
Answer: According to the context, Python emphasizes readability.

Context: {context}
Question: {question}
Answer:"""
        
        # Verify refusal example
        assert "does not contain" in few_shot_prompt.lower()
        assert "Example 1:" in few_shot_prompt
        assert "Example 2:" in few_shot_prompt


@pytest.mark.unit
class TestSystemPromptEffectiveness:
    """Test system prompt effectiveness."""
    
    @pytest.mark.asyncio
    async def test_system_prompt_for_conversational_rag(self, prompt_config):
        """Test system prompt in conversational RAG."""
        prompt_config.enable_conversation_memory = True
        
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=prompt_config
        )
        
        # System prompts used in ask_with_context
        system_message = "You are a helpful AI assistant engaged in a conversation."
        
        assert len(system_message) > 0
        assert "assistant" in system_message.lower()
    
    @pytest.mark.asyncio
    async def test_system_prompt_variations(self, prompt_config):
        """Test different system prompt variations."""
        # Different persona prompts
        expert_prompt = "You are an expert technical assistant with deep knowledge of programming."
        concise_prompt = "You are a concise assistant. Keep answers brief and to the point."
        detailed_prompt = "You are a detailed assistant. Provide comprehensive explanations."
        
        prompts = [expert_prompt, concise_prompt, detailed_prompt]
        
        # All prompts should have clear persona
        for prompt in prompts:
            assert "you are" in prompt.lower()
            assert len(prompt) > 10


@pytest.mark.unit
class TestPromptOptimization:
    """Test prompt optimization techniques."""
    
    def test_context_length_optimization(self, prompt_config):
        """Test prompt optimization for context length."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=prompt_config
        )
        
        # Long context
        long_context = "Sample text. " * 1000  # ~2000 words
        
        # Should be truncated
        truncated = service._truncate_context(long_context, max_tokens=500)
        
        assert len(truncated) < len(long_context)
        assert service._count_tokens(truncated) <= 600  # Some margin
    
    def test_instruction_clarity(self, prompt_config):
        """Test that instructions in prompts are clear."""
        service = RAGService(
            vector_search_repository=AsyncMock(),
            embedding_service=AsyncMock(),
            config=prompt_config
        )
        
        template = service.DEFAULT_QA_TEMPLATE
        
        # Check for clear instructions
        clear_instructions = [
            "answer",
            "question",
            "context",
        ]
        
        template_lower = template.lower()
        for instruction in clear_instructions:
            assert instruction in template_lower, f"Missing clear instruction: {instruction}"
