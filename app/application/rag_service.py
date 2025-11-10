"""
RAG (Retrieval-Augmented Generation) Service

Full LangChain integration for question answering with retrieval-augmented generation.

Features:
- Multiple LLM providers (OpenAI, Anthropic, local)
- Streaming responses for real-time answers
- Conversation memory for multi-turn dialogues
- Query processing and validation
- Answer generation with source citations
- Response caching for performance
- Comprehensive error handling
- Token tracking and latency monitoring
"""
import logging
import time
import hashlib
import re
from typing import List, Optional, Dict, Any, AsyncIterator, Tuple
from datetime import datetime, timedelta

try:
    import tiktoken
except ImportError:
    tiktoken = None

from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.runnables import RunnablePassthrough

from .dto import SearchResultDTO
from app.domain.repositories import IVectorSearchRepository, IEmbeddingService


logger = logging.getLogger(__name__)


# Simple in-memory cache for responses
_response_cache: Dict[str, Tuple[Dict[str, Any], datetime]] = {}


def _get_cache_key(query: str, context_hash: str) -> str:
    """Generate cache key from query and context."""
    combined = f"{query}:{context_hash}"
    return hashlib.blake2b(combined.encode(), digest_size=16).hexdigest()


def _clean_cache(max_age_seconds: int = 3600):
    """Remove old entries from cache."""
    global _response_cache
    cutoff = datetime.now() - timedelta(seconds=max_age_seconds)
    _response_cache = {
        k: v for k, v in _response_cache.items()
        if v[1] > cutoff
    }


class RAGService:
    """
    Service for Retrieval-Augmented Generation operations using LangChain.
    
    Integrates with existing vector search and provides question answering
    with multiple LLM providers, streaming support, and conversation memory.
    """
    
    # Default prompt templates
    DEFAULT_QA_TEMPLATE = """You are a helpful AI assistant that answers questions based on the provided context.
Use the following pieces of context to answer the question at the end. 
If you cannot find the answer in the context, say so - do not make up information.
Always cite which source(s) you used by referencing [Source N] where N is the chunk number.

Context:
{context}

Question: {question}

Answer (with source citations):"""

# (Removed unused DEFAULT_CONVERSATIONAL_TEMPLATE)
    
    def __init__(
        self,
        vector_search_repository: IVectorSearchRepository,
        embedding_service: IEmbeddingService,
        config: Optional[Any] = None
    ):
        """
        Initialize RAG service.
        
        Args:
            vector_search_repository: Repository for vector similarity search
            embedding_service: Service for generating embeddings
            config: RAG configuration (from infrastructure.config.RAGConfig)
        """
        self.vector_search_repo = vector_search_repository
        self.embedding_service = embedding_service
        self.config = config
        
        # Conversation memory (conversation_id -> messages)
        self._conversation_memory: Dict[str, List[Dict[str, str]]] = {}
        
        # Token tracking
        self._token_usage: Dict[str, int] = {"prompt_tokens": 0, "completion_tokens": 0}
        
        logger.info(f"RAGService initialized with provider: {getattr(config, 'provider', 'not configured')}")
    
    def _get_llm(self, **kwargs):
        """
        Get LLM instance based on configuration.
        
        Returns:
            LangChain LLM instance
        """
        if not self.config:
            raise ValueError("RAG configuration is required")
        
        provider = kwargs.get('provider', self.config.provider)
        model = kwargs.get('model', self.config.model)
        temperature = kwargs.get('temperature', self.config.temperature)
        max_tokens = kwargs.get('max_tokens', self.config.max_tokens)
        
        try:
            if provider == "openai":
                from langchain_openai import ChatOpenAI
                api_key = kwargs.get('openai_api_key', self.config.openai_api_key)
                if not api_key:
                    raise ValueError("OpenAI API key is required for OpenAI provider")
                
                return ChatOpenAI(
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    api_key=api_key,
                    timeout=self.config.timeout_seconds,
                    max_retries=self.config.max_retries
                )
            
            elif provider == "anthropic":
                from langchain_anthropic import ChatAnthropic
                api_key = kwargs.get('anthropic_api_key', self.config.anthropic_api_key)
                if not api_key:
                    raise ValueError("Anthropic API key is required for Anthropic provider")
                
                return ChatAnthropic(
                    model=model,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    anthropic_api_key=api_key,
                    timeout=self.config.timeout_seconds,
                    max_retries=self.config.max_retries
                )
            
            elif provider == "local":
                # For local models, we'd typically use Ollama or similar
                # This is a placeholder - actual implementation would depend on local setup
                logger.warning("Local LLM provider not fully implemented - using mock")
                from langchain_community.llms import FakeListLLM
                return FakeListLLM(
                    responses=["This is a mock response from a local LLM. Please configure a real local model."]
                )
            
            else:
                raise ValueError(f"Unsupported LLM provider: {provider}")
        
        except Exception as e:
            logger.error(f"Failed to initialize LLM: {e}")
            raise
    
    def _format_context(self, chunks: List[SearchResultDTO]) -> str:
        """
        Format search results into context string.
        
        Args:
            chunks: List of search result chunks
            
        Returns:
            Formatted context string with source citations
        """
        if not chunks:
            return "No relevant context found."
        
        context_parts = []
        for i, chunk in enumerate(chunks, 1):
            author = chunk.author_name or "Unknown"
            context_parts.append(f"[Source {i}] {author}: {chunk.text}")
        
        return "\n\n".join(context_parts)
    
    def _count_tokens(self, text: str, model: str = "gpt-3.5-turbo") -> int:
        """
        Count tokens in text.
        
        Args:
            text: Text to count tokens for
            model: Model name for tokenizer
            
        Returns:
            Approximate token count
        """
        if tiktoken:
            try:
                encoding = tiktoken.encoding_for_model(model)
                return len(encoding.encode(text))
            except Exception as e:
                logger.debug(f"Token counting failed: {e}, using approximation")
        
        # Fallback: rough approximation (1 token ≈ 4 characters)
        return len(text) // 4
    
    def _truncate_context(self, context: str, max_tokens: int, model: str = "gpt-3.5-turbo") -> str:
        """
        Truncate context to fit within token limit.
        
        Args:
            context: Context string to truncate
            max_tokens: Maximum number of tokens
            model: Model name for tokenizer
            
        Returns:
            Truncated context
        """
        current_tokens = self._count_tokens(context, model)
        if current_tokens <= max_tokens:
            return context
        
        logger.warning(f"Context truncated from {current_tokens} to ~{max_tokens} tokens")
        
        # Simple truncation: keep first N characters proportional to token limit
        ratio = max_tokens / current_tokens
        target_length = int(len(context) * ratio * 0.9)  # 10% safety margin
        return context[:target_length] + "\n\n[... context truncated ...]"
    
    def _sanitize_query(self, query: str) -> str:
        """
        Sanitize and validate query.
        
        Args:
            query: User query
            
        Returns:
            Sanitized query
            
        Raises:
            ValueError: If query is invalid
        """
        if not query or not query.strip():
            raise ValueError("Query cannot be empty")
        
        query = query.strip()
        
        # Remove excessive whitespace
        query = re.sub(r'\s+', ' ', query)
        
        # Check length
        if len(query) < 3:
            raise ValueError("Query is too short (minimum 3 characters)")
        
        if len(query) > 1000:
            logger.warning("Query is very long, truncating")
            query = query[:1000]
        
        return query
    
    def _extract_citations(self, answer: str) -> List[int]:
        """
        Extract source citations from answer.
        
        Args:
            answer: Generated answer
            
        Returns:
            List of cited source numbers
        """
        citations = re.findall(r'\[Source (\d+)\]', answer)
        return [int(c) for c in citations]
    
    def _calculate_confidence(
        self,
        answer: str,
        chunks: List[SearchResultDTO],
        citations: List[int]
    ) -> float:
        """
        Calculate confidence score for answer.
        
        Args:
            answer: Generated answer
            chunks: Context chunks used
            citations: Cited source numbers
            
        Returns:
            Confidence score (0.0 to 1.0)
        """
        # Simple heuristic-based confidence scoring
        confidence = 0.5  # Base confidence
        
        # Boost if citations are present
        if citations:
            confidence += 0.2
        
        # Boost based on chunk scores
        if chunks:
            avg_score = sum(chunk.score for chunk in chunks) / len(chunks)
            confidence += avg_score * 0.2
        
        # Reduce if answer is very short
        if len(answer) < 50:
            confidence -= 0.1
        
        # Check for uncertainty phrases
        uncertainty_phrases = [
            "i don't know", "i'm not sure", "cannot find", "not mentioned",
            "no information", "unclear", "ambiguous"
        ]
        if any(phrase in answer.lower() for phrase in uncertainty_phrases):
            confidence -= 0.3
        
        return max(0.0, min(1.0, confidence))
    
    async def ask(
        self,
        query: str,
        top_k: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Ask a question and get an answer with source citations.
        
        Args:
            query: User question
            top_k: Number of context chunks to retrieve (default from config)
            **kwargs: Additional parameters (temperature, max_tokens, etc.)
            
        Returns:
            Dictionary with:
                - answer: Generated answer with citations
                - sources: List of source chunks used
                - confidence: Confidence score (0.0 to 1.0)
                - metadata: Additional metadata (tokens, latency, etc.)
        """
        start_time = time.time()
        
        try:
            # Sanitize query
            query = self._sanitize_query(query)
            logger.info(f"Processing RAG query: '{query[:50]}...'")
            
            # Check cache
            if self.config and self.config.enable_cache:
                _clean_cache(self.config.cache_ttl_seconds)
                cache_key = _get_cache_key(query, "simple")
                if cache_key in _response_cache:
                    cached_response, cached_time = _response_cache[cache_key]
                    logger.info("Returning cached response")
                    cached_response["metadata"]["cached"] = True
                    cached_response["metadata"]["cache_age_seconds"] = (datetime.now() - cached_time).total_seconds()
                    return cached_response
            
            # Retrieve context
            top_k = top_k or (self.config.top_k if self.config else 5)
            
            # Generate query embedding
            query_embedding = await self.embedding_service.generate_embedding(query)
            
            # Perform vector search
            results = await self.vector_search_repo.similarity_search(
                query_embedding,
                top_k=top_k
            )
            
            # Convert to DTOs
            chunks = [
                SearchResultDTO(
                    chunk_id=str(chunk.chunk_id.value) if hasattr(chunk.chunk_id, 'value') else str(chunk.chunk_id),
                    conversation_id=str(chunk.conversation_id.value) if hasattr(chunk.conversation_id, 'value') else str(chunk.conversation_id),
                    text=chunk.text.value if hasattr(chunk.text, 'value') else str(chunk.text),
                    score=score.value if hasattr(score, 'value') else float(score),
                    author_name=chunk.author_info.name if chunk.author_info else None,
                    author_type=chunk.author_info.author_type if chunk.author_info else None,
                    order_index=chunk.metadata.order_index if chunk.metadata else 0
                )
                for chunk, score in results
            ]
            
            if not chunks:
                return {
                    "answer": "I couldn't find any relevant information to answer your question.",
                    "sources": [],
                    "confidence": 0.0,
                    "metadata": {
                        "query": query,
                        "chunks_retrieved": 0,
                        "latency_ms": (time.time() - start_time) * 1000
                    }
                }
            
            # Format context
            context = self._format_context(chunks)
            
            # Truncate context if needed
            max_context_tokens = (self.config.max_context_tokens if self.config else 3500)
            context = self._truncate_context(context, max_context_tokens, self.config.model if self.config else "gpt-3.5-turbo")
            
            # Create prompt
            prompt_template = PromptTemplate(
                template=self.DEFAULT_QA_TEMPLATE,
                input_variables=["context", "question"]
            )
            
            # Get LLM
            llm = self._get_llm(**kwargs)
            
            # Create chain
            chain = (
                {"context": lambda x: context, "question": RunnablePassthrough()}
                | prompt_template
                | llm
                | StrOutputParser()
            )
            
            # Generate answer
            answer = await chain.ainvoke(query)
            
            # Extract citations and calculate confidence
            citations = self._extract_citations(answer)
            confidence = self._calculate_confidence(answer, chunks, citations)
            
            # Track token usage
            if self.config and self.config.enable_token_tracking:
                prompt_tokens = self._count_tokens(context + query, self.config.model)
                completion_tokens = self._count_tokens(answer, self.config.model)
                self._token_usage["prompt_tokens"] += prompt_tokens
                self._token_usage["completion_tokens"] += completion_tokens
            
            latency_ms = (time.time() - start_time) * 1000
            
            result = {
                "answer": answer,
                "sources": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "text": chunk.text,
                        "score": chunk.score,
                        "author": chunk.author_name
                    }
                    for chunk in chunks
                ],
                "confidence": confidence,
                "metadata": {
                    "query": query,
                    "chunks_retrieved": len(chunks),
                    "citations": citations,
                    "latency_ms": latency_ms,
                    "provider": self.config.provider if self.config else "unknown",
                    "model": self.config.model if self.config else "unknown",
                    "cached": False
                }
            }
            
            if self.config and self.config.enable_token_tracking:
                result["metadata"]["tokens"] = {
                    "prompt": prompt_tokens,
                    "completion": completion_tokens,
                    "total": prompt_tokens + completion_tokens
                }
            
            # Cache result
            if self.config and self.config.enable_cache:
                _response_cache[cache_key] = (result, datetime.now())
            
            logger.info(f"RAG query completed in {latency_ms:.2f}ms with confidence {confidence:.2f}")
            return result
        
        except Exception as e:
            logger.error(f"RAG query failed: {e}", exc_info=True)
            return {
                "answer": f"I encountered an error while processing your question: {str(e)}",
                "sources": [],
                "confidence": 0.0,
                "metadata": {
                    "query": query,
                    "error": str(e),
                    "latency_ms": (time.time() - start_time) * 1000
                }
            }
    
    async def ask_with_context(
        self,
        query: str,
        conversation_id: Optional[str] = None,
        top_k: Optional[int] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Ask a question with conversation context for multi-turn dialogue.
        
        Args:
            query: User question
            conversation_id: Optional conversation ID for memory
            top_k: Number of context chunks to retrieve
            **kwargs: Additional parameters
            
        Returns:
            Dictionary with answer, sources, confidence, and metadata
        """
        start_time = time.time()
        
        try:
            query = self._sanitize_query(query)
            logger.info(f"Processing conversational RAG query: '{query[:50]}...'")
            
            # Get conversation history
            history = []
            if conversation_id and self.config and self.config.enable_conversation_memory:
                history = self._conversation_memory.get(conversation_id, [])
                # Limit history to max messages
                max_history = self.config.max_history_messages
                if len(history) > max_history * 2:  # Each turn = 2 messages
                    history = history[-(max_history * 2):]
            
            # Retrieve context (same as ask())
            top_k = top_k or (self.config.top_k if self.config else 5)
            query_embedding = await self.embedding_service.generate_embedding(query)
            results = await self.vector_search_repo.similarity_search(query_embedding, top_k=top_k)
            
            chunks = [
                SearchResultDTO(
                    chunk_id=str(chunk.chunk_id.value) if hasattr(chunk.chunk_id, 'value') else str(chunk.chunk_id),
                    conversation_id=str(chunk.conversation_id.value) if hasattr(chunk.conversation_id, 'value') else str(chunk.conversation_id),
                    text=chunk.text.value if hasattr(chunk.text, 'value') else str(chunk.text),
                    score=score.value if hasattr(score, 'value') else float(score),
                    author_name=chunk.author_info.name if chunk.author_info else None,
                    author_type=chunk.author_info.author_type if chunk.author_info else None,
                    order_index=chunk.metadata.order_index if chunk.metadata else 0
                )
                for chunk, score in results
            ]
            
            if not chunks:
                answer = "I couldn't find any relevant information to answer your question."
                result = {
                    "answer": answer,
                    "sources": [],
                    "confidence": 0.0,
                    "metadata": {
                        "query": query,
                        "conversation_id": conversation_id,
                        "history_length": len(history),
                        "chunks_retrieved": 0,
                        "latency_ms": (time.time() - start_time) * 1000
                    }
                }
                
                # Update conversation memory
                if conversation_id and self.config and self.config.enable_conversation_memory:
                    if conversation_id not in self._conversation_memory:
                        self._conversation_memory[conversation_id] = []
                    self._conversation_memory[conversation_id].append({"role": "user", "content": query})
                    self._conversation_memory[conversation_id].append({"role": "assistant", "content": answer})
                
                return result
            
            # Format context
            context = self._format_context(chunks)
            max_context_tokens = (self.config.max_context_tokens if self.config else 3500)
            context = self._truncate_context(context, max_context_tokens, self.config.model if self.config else "gpt-3.5-turbo")
            
            # Create conversational prompt with history
            messages = [
                SystemMessage(content="You are a helpful AI assistant engaged in a conversation.")
            ]
            
            # Add history
            for msg in history:
                if msg["role"] == "user":
                    messages.append(HumanMessage(content=msg["content"]))
                else:
                    messages.append(AIMessage(content=msg["content"]))
            
            # Add context and current question
            context_message = f"""Context from knowledge base:
{context}

Use this context to answer the following question. Always cite your sources using [Source N] format."""
            
            messages.append(HumanMessage(content=context_message))
            messages.append(HumanMessage(content=query))
            
            # Get LLM and generate answer
            llm = self._get_llm(**kwargs)
            answer = await llm.ainvoke(messages)
            answer_text = answer.content if hasattr(answer, 'content') else str(answer)
            
            # Extract citations and calculate confidence
            citations = self._extract_citations(answer_text)
            confidence = self._calculate_confidence(answer_text, chunks, citations)
            
            # Track tokens
            if self.config and self.config.enable_token_tracking:
                prompt_tokens = self._count_tokens(context + query + str(history), self.config.model)
                completion_tokens = self._count_tokens(answer_text, self.config.model)
                self._token_usage["prompt_tokens"] += prompt_tokens
                self._token_usage["completion_tokens"] += completion_tokens
            
            latency_ms = (time.time() - start_time) * 1000
            
            result = {
                "answer": answer_text,
                "sources": [
                    {
                        "chunk_id": chunk.chunk_id,
                        "text": chunk.text,
                        "score": chunk.score,
                        "author": chunk.author_name
                    }
                    for chunk in chunks
                ],
                "confidence": confidence,
                "metadata": {
                    "query": query,
                    "conversation_id": conversation_id,
                    "history_length": len(history),
                    "chunks_retrieved": len(chunks),
                    "citations": citations,
                    "latency_ms": latency_ms,
                    "provider": self.config.provider if self.config else "unknown",
                    "model": self.config.model if self.config else "unknown"
                }
            }
            
            if self.config and self.config.enable_token_tracking:
                result["metadata"]["tokens"] = {
                    "prompt": prompt_tokens,
                    "completion": completion_tokens,
                    "total": prompt_tokens + completion_tokens
                }
            
            # Update conversation memory
            if conversation_id and self.config and self.config.enable_conversation_memory:
                if conversation_id not in self._conversation_memory:
                    self._conversation_memory[conversation_id] = []
                self._conversation_memory[conversation_id].append({"role": "user", "content": query})
                self._conversation_memory[conversation_id].append({"role": "assistant", "content": answer_text})
            
            logger.info(f"Conversational RAG query completed in {latency_ms:.2f}ms with confidence {confidence:.2f}")
            return result
        
        except Exception as e:
            logger.error(f"Conversational RAG query failed: {e}", exc_info=True)
            return {
                "answer": f"I encountered an error while processing your question: {str(e)}",
                "sources": [],
                "confidence": 0.0,
                "metadata": {
                    "query": query,
                    "conversation_id": conversation_id,
                    "error": str(e),
                    "latency_ms": (time.time() - start_time) * 1000
                }
            }
    
    async def ask_streaming(
        self,
        query: str,
        top_k: Optional[int] = None,
        **kwargs
    ) -> AsyncIterator[str]:
        """
        Ask a question and stream the answer in real-time.
        
        Args:
            query: User question
            top_k: Number of context chunks to retrieve
            **kwargs: Additional parameters
            
        Yields:
            Answer chunks as they are generated
        """
        try:
            query = self._sanitize_query(query)
            logger.info(f"Processing streaming RAG query: '{query[:50]}...'")
            
            # Retrieve context
            top_k = top_k or (self.config.top_k if self.config else 5)
            query_embedding = await self.embedding_service.generate_embedding(query)
            results = await self.vector_search_repo.similarity_search(query_embedding, top_k=top_k)
            
            chunks = [
                SearchResultDTO(
                    chunk_id=str(chunk.chunk_id.value) if hasattr(chunk.chunk_id, 'value') else str(chunk.chunk_id),
                    conversation_id=str(chunk.conversation_id.value) if hasattr(chunk.conversation_id, 'value') else str(chunk.conversation_id),
                    text=chunk.text.value if hasattr(chunk.text, 'value') else str(chunk.text),
                    score=score.value if hasattr(score, 'value') else float(score),
                    author_name=chunk.author_info.name if chunk.author_info else None,
                    author_type=chunk.author_info.author_type if chunk.author_info else None,
                    order_index=chunk.metadata.order_index if chunk.metadata else 0
                )
                for chunk, score in results
            ]
            
            if not chunks:
                yield "I couldn't find any relevant information to answer your question."
                return
            
            # Format context
            context = self._format_context(chunks)
            max_context_tokens = (self.config.max_context_tokens if self.config else 3500)
            context = self._truncate_context(context, max_context_tokens, self.config.model if self.config else "gpt-3.5-turbo")
            
            # Create prompt
            prompt_template = PromptTemplate(
                template=self.DEFAULT_QA_TEMPLATE,
                input_variables=["context", "question"]
            )
            
            # Get LLM
            llm = self._get_llm(**kwargs)
            
            # Create streaming chain
            chain = (
                {"context": lambda x: context, "question": RunnablePassthrough()}
                | prompt_template
                | llm
                | StrOutputParser()
            )
            
            # Stream answer
            async for chunk in chain.astream(query):
                yield chunk
        
        except Exception as e:
            logger.error(f"Streaming RAG query failed: {e}", exc_info=True)
            yield f"Error: {str(e)}"
    
    def clear_conversation_memory(self, conversation_id: Optional[str] = None):
        """
        Clear conversation memory.
        
        Args:
            conversation_id: Specific conversation to clear, or None to clear all
        """
        if conversation_id:
            self._conversation_memory.pop(conversation_id, None)
            logger.info(f"Cleared conversation memory for: {conversation_id}")
        else:
            self._conversation_memory.clear()
            logger.info("Cleared all conversation memory")
    
    def get_token_usage(self) -> Dict[str, int]:
        """Get cumulative token usage statistics."""
        return self._token_usage.copy()
    
    def reset_token_usage(self):
        """Reset token usage counters."""
        self._token_usage = {"prompt_tokens": 0, "completion_tokens": 0}
        logger.info("Reset token usage counters")
