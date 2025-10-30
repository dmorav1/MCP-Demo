"""
Search Conversations Use Case

Orchestrates the semantic search workflow:
1. Validate search query
2. Generate query embedding
3. Perform vector similarity search
4. Apply relevance filtering and ranking
5. Return formatted results
"""
import logging
import time
from typing import List, Optional
from datetime import datetime

from app.domain.entities import ConversationChunk
from app.domain.value_objects import Embedding, RelevanceScore, SearchQuery
from app.domain.repositories import (
    IVectorSearchRepository, IEmbeddingService,
    RepositoryError, EmbeddingError, ValidationError
)
from app.domain.services import SearchRelevanceService

from .dto import (
    SearchConversationRequest, SearchConversationResponse,
    SearchResultDTO, SearchFilters
)


logger = logging.getLogger(__name__)


class SearchConversationsUseCase:
    """
    Use case for searching conversations using semantic vector search.
    
    This orchestrates the search workflow while delegating:
    - Embedding generation to the embedding service
    - Vector search to the repository
    - Relevance scoring to domain services
    
    Dependencies are injected following hexagonal architecture principles.
    """
    
    def __init__(
        self,
        vector_search_repository: IVectorSearchRepository,
        embedding_service: IEmbeddingService,
        relevance_service: SearchRelevanceService,
    ):
        self.vector_search_repo = vector_search_repository
        self.embedding_service = embedding_service
        self.relevance_service = relevance_service
        
        logger.info("SearchConversationsUseCase initialized")
    
    async def execute(
        self, 
        request: SearchConversationRequest
    ) -> SearchConversationResponse:
        """
        Execute the conversation search use case.
        
        Args:
            request: The search request with query and parameters
            
        Returns:
            Response with search results and metadata
            
        Raises:
            ValidationError: If query validation fails
            EmbeddingError: If query embedding generation fails
            RepositoryError: If search fails
        """
        start_time = time.time()
        
        try:
            logger.info(f"Starting search for query: '{request.query[:50]}...' (top_k={request.top_k})")
            
            # Step 1: Validate query
            self._validate_query(request)
            
            # Step 2: Create search query value object
            search_query = SearchQuery(
                text=request.query,
                top_k=request.top_k
            )
            
            # Step 3: Generate query embedding
            query_embedding = await self._generate_query_embedding(request.query)
            
            # Step 4: Perform vector search
            search_results = await self._perform_vector_search(
                query_embedding, 
                request.top_k
            )
            
            # Step 5: Apply filters if provided
            filtered_results = self._apply_filters(search_results, request.filters)
            
            # Step 6: Enhance relevance scores
            ranked_results = self._rank_results(filtered_results, request.query)
            
            # Step 7: Convert to DTOs
            result_dtos = self._convert_to_dtos(ranked_results)
            
            # Calculate execution time
            execution_time_ms = (time.time() - start_time) * 1000
            
            logger.info(
                f"Search completed: {len(result_dtos)} results in {execution_time_ms:.2f}ms"
            )
            
            return SearchConversationResponse(
                results=result_dtos,
                query=request.query,
                total_results=len(result_dtos),
                execution_time_ms=execution_time_ms,
                success=True,
                error_message=None
            )
            
        except ValidationError as e:
            logger.error(f"Validation error during search: {str(e)}")
            return SearchConversationResponse(
                results=[],
                query=request.query,
                total_results=0,
                execution_time_ms=0,
                success=False,
                error_message=f"Validation error: {str(e)}"
            )
        except (EmbeddingError, RepositoryError) as e:
            logger.error(f"Error during search: {str(e)}")
            execution_time_ms = (time.time() - start_time) * 1000
            return SearchConversationResponse(
                results=[],
                query=request.query,
                total_results=0,
                execution_time_ms=execution_time_ms,
                success=False,
                error_message=f"Search failed: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Unexpected error during search: {str(e)}")
            execution_time_ms = (time.time() - start_time) * 1000
            return SearchConversationResponse(
                results=[],
                query=request.query,
                total_results=0,
                execution_time_ms=execution_time_ms,
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def _validate_query(self, request: SearchConversationRequest) -> None:
        """
        Validate the search request.
        
        Args:
            request: The search request
            
        Raises:
            ValidationError: If validation fails
        """
        # Basic validation (DTO already validates some constraints)
        if len(request.query) > 10000:
            raise ValidationError("Query text exceeds maximum length of 10000 characters")
        
        # Additional business rule validations can be added here
        logger.debug(f"Search request validation passed for query: {request.query[:50]}")
    
    async def _generate_query_embedding(self, query_text: str) -> Embedding:
        """
        Generate embedding for the search query.
        
        Args:
            query_text: The query text
            
        Returns:
            The query embedding
            
        Raises:
            EmbeddingError: If embedding generation fails
        """
        try:
            embedding = await self.embedding_service.generate_embedding(query_text)
            logger.debug(f"Generated query embedding with dimension {len(embedding.values)}")
            return embedding
        except Exception as e:
            logger.error(f"Failed to generate query embedding: {str(e)}")
            raise EmbeddingError(f"Query embedding generation failed: {str(e)}")
    
    async def _perform_vector_search(
        self, 
        query_embedding: Embedding, 
        top_k: int
    ) -> List[tuple[ConversationChunk, RelevanceScore]]:
        """
        Perform vector similarity search.
        
        Args:
            query_embedding: The embedded query
            top_k: Maximum number of results
            
        Returns:
            List of (chunk, score) tuples
            
        Raises:
            RepositoryError: If search fails
        """
        try:
            results = await self.vector_search_repo.similarity_search(
                query_embedding=query_embedding,
                top_k=top_k
            )
            logger.debug(f"Vector search returned {len(results)} results")
            return results
        except Exception as e:
            logger.error(f"Vector search failed: {str(e)}")
            raise RepositoryError(f"Search operation failed: {str(e)}")
    
    def _apply_filters(
        self,
        results: List[tuple[ConversationChunk, RelevanceScore]],
        filters: Optional[SearchFilters]
    ) -> List[tuple[ConversationChunk, RelevanceScore]]:
        """
        Apply filters to search results.
        
        Args:
            results: The unfiltered results
            filters: Optional filters to apply
            
        Returns:
            Filtered results
        """
        if not filters:
            return results
        
        filtered = results
        
        # Apply minimum score filter
        if filters.min_score is not None:
            filtered = [
                (chunk, score) for chunk, score in filtered
                if score.value >= filters.min_score
            ]
            logger.debug(f"Applied min_score filter: {len(filtered)} results remain")
        
        # Apply author name filter
        if filters.author_name:
            filtered = [
                (chunk, score) for chunk, score in filtered
                if chunk.metadata.author_info and 
                   chunk.metadata.author_info.name == filters.author_name
            ]
            logger.debug(f"Applied author_name filter: {len(filtered)} results remain")
        
        # Apply author type filter
        if filters.author_type:
            filtered = [
                (chunk, score) for chunk, score in filtered
                if chunk.metadata.author_info and 
                   chunk.metadata.author_info.author_type == filters.author_type
            ]
            logger.debug(f"Applied author_type filter: {len(filtered)} results remain")
        
        # Apply timestamp filters
        if filters.date_from:
            filtered = [
                (chunk, score) for chunk, score in filtered
                if chunk.metadata.timestamp and 
                   chunk.metadata.timestamp >= filters.date_from
            ]
            logger.debug(f"Applied date_from filter: {len(filtered)} results remain")
        
        if filters.date_to:
            filtered = [
                (chunk, score) for chunk, score in filtered
                if chunk.metadata.timestamp and 
                   chunk.metadata.timestamp <= filters.date_to
            ]
            logger.debug(f"Applied date_to filter: {len(filtered)} results remain")
        
        return filtered
    
    def _rank_results(
        self,
        results: List[tuple[ConversationChunk, RelevanceScore]],
        query: str
    ) -> List[tuple[ConversationChunk, RelevanceScore]]:
        """
        Apply additional ranking using domain service.
        
        Args:
            results: The search results
            query: The original query
            
        Returns:
            Re-ranked results
        """
        # The relevance service can apply additional ranking logic
        # For now, results from vector search are already ranked by similarity
        # Future enhancements: keyword boosting, recency boosting, etc.
        
        return results
    
    def _convert_to_dtos(
        self,
        results: List[tuple[ConversationChunk, RelevanceScore]]
    ) -> List[SearchResultDTO]:
        """
        Convert domain entities to DTOs.
        
        Args:
            results: List of (chunk, score) tuples
            
        Returns:
            List of search result DTOs
        """
        dtos = []
        
        for chunk, score in results:
            dto = SearchResultDTO(
                chunk_id=chunk.id.value if chunk.id else "",
                conversation_id=chunk.conversation_id.value,
                text=chunk.text.value,
                score=score.value,
                author_name=chunk.metadata.author_info.name if chunk.metadata.author_info else None,
                author_type=chunk.metadata.author_info.author_type if chunk.metadata.author_info else None,
                timestamp=chunk.metadata.timestamp,
                order_index=chunk.metadata.order_index,
                metadata={
                    "conversation_id": chunk.conversation_id.value,
                    "chunk_id": chunk.id.value if chunk.id else "",
                }
            )
            dtos.append(dto)
        
        return dtos
