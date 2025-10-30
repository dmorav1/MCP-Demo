"""
Ingest Conversation Use Case

Orchestrates the complete workflow for ingesting a new conversation:
1. Validate input data
2. Create conversation entity
3. Chunk messages into searchable units
4. Generate embeddings for chunks
5. Persist conversation and chunks with embeddings
"""
import logging
from typing import List
from datetime import datetime

from app.domain.entities import Conversation, ConversationChunk
from app.domain.value_objects import (
    ConversationId, ChunkId, ChunkText, Embedding, 
    AuthorInfo, ConversationMetadata, ChunkMetadata
)
from app.domain.repositories import (
    IConversationRepository, IChunkRepository, 
    IEmbeddingService, RepositoryError, EmbeddingError, ValidationError
)
from app.domain.services import (
    ConversationChunkingService, ConversationValidationService,
    EmbeddingValidationService
)

from .dto import (
    IngestConversationRequest, IngestConversationResponse,
    ConversationMetadataDTO, MessageDTO
)


logger = logging.getLogger(__name__)


class IngestConversationUseCase:
    """
    Use case for ingesting conversations.
    
    This orchestrates the entire ingestion workflow while delegating
    business logic to domain services and persistence to repositories.
    
    Dependencies are injected following hexagonal architecture principles:
    - Domain services for business logic
    - Repository interfaces for persistence
    - Embedding service interface for vector generation
    """
    
    def __init__(
        self,
        conversation_repository: IConversationRepository,
        chunk_repository: IChunkRepository,
        embedding_service: IEmbeddingService,
        chunking_service: ConversationChunkingService,
        validation_service: ConversationValidationService,
        embedding_validation_service: EmbeddingValidationService,
    ):
        self.conversation_repo = conversation_repository
        self.chunk_repo = chunk_repository
        self.embedding_service = embedding_service
        self.chunking_service = chunking_service
        self.validation_service = validation_service
        self.embedding_validation_service = embedding_validation_service
        
        logger.info("IngestConversationUseCase initialized")
    
    async def execute(
        self, 
        request: IngestConversationRequest
    ) -> IngestConversationResponse:
        """
        Execute the conversation ingestion use case.
        
        Args:
            request: The ingestion request with messages and metadata
            
        Returns:
            Response with conversation ID and ingestion details
            
        Raises:
            ValidationError: If input validation fails
            RepositoryError: If persistence fails
            EmbeddingError: If embedding generation fails
        """
        try:
            logger.info(f"Starting conversation ingestion with {len(request.messages)} messages")
            
            # Step 1: Validate input
            await self._validate_request(request)
            
            # Step 2: Create conversation entity
            conversation = self._create_conversation_entity(request)
            
            # Step 3: Convert DTOs to domain messages and chunk
            messages = self._convert_messages_to_domain(request.messages)
            chunks = self.chunking_service.chunk_conversation_messages(
                messages=messages,
                conversation_id=conversation.id
            )
            
            logger.info(f"Created {len(chunks)} chunks from messages")
            
            # Step 4: Generate embeddings for chunks
            chunks_with_embeddings = await self._generate_embeddings(chunks)
            
            # Step 5: Persist conversation
            saved_conversation = await self.conversation_repo.save(conversation)
            logger.info(f"Saved conversation with ID: {saved_conversation.id.value}")
            
            # Step 6: Persist chunks with embeddings
            saved_chunks = await self.chunk_repo.save_chunks(chunks_with_embeddings)
            logger.info(f"Saved {len(saved_chunks)} chunks")
            
            # Step 7: Build response
            return self._build_response(saved_conversation, saved_chunks)
            
        except ValidationError as e:
            logger.error(f"Validation error during ingestion: {str(e)}")
            return IngestConversationResponse(
                conversation_id="",
                chunks_created=0,
                metadata=self._empty_metadata(),
                success=False,
                error_message=f"Validation error: {str(e)}"
            )
        except (RepositoryError, EmbeddingError) as e:
            logger.error(f"Error during ingestion: {str(e)}")
            return IngestConversationResponse(
                conversation_id="",
                chunks_created=0,
                metadata=self._empty_metadata(),
                success=False,
                error_message=f"Ingestion failed: {str(e)}"
            )
        except Exception as e:
            logger.exception(f"Unexpected error during ingestion: {str(e)}")
            return IngestConversationResponse(
                conversation_id="",
                chunks_created=0,
                metadata=self._empty_metadata(),
                success=False,
                error_message=f"Unexpected error: {str(e)}"
            )
    
    async def _validate_request(self, request: IngestConversationRequest) -> None:
        """
        Validate the ingestion request.
        
        Args:
            request: The request to validate
            
        Raises:
            ValidationError: If validation fails
        """
        if not request.messages:
            raise ValidationError("Cannot ingest conversation with no messages")
        
        # Validate each message has text
        for idx, msg in enumerate(request.messages):
            if not msg.text or not msg.text.strip():
                raise ValidationError(f"Message at index {idx} has empty text")
        
        logger.debug(f"Request validation passed for {len(request.messages)} messages")
    
    def _create_conversation_entity(
        self, 
        request: IngestConversationRequest
    ) -> Conversation:
        """
        Create a conversation domain entity from the request.
        
        Args:
            request: The ingestion request
            
        Returns:
            A new Conversation entity
        """
        metadata = ConversationMetadata(
            scenario_title=request.scenario_title,
            original_title=request.original_title,
            url=request.url,
            created_at=datetime.utcnow()
        )
        
        conversation = Conversation(
            id=None,  # Will be assigned by repository
            metadata=metadata,
            chunks=[]
        )
        
        # Validate using domain service
        validation_result = self.validation_service.validate_conversation(conversation)
        if not validation_result.is_valid:
            error_messages = ", ".join(validation_result.errors)
            raise ValidationError(f"Conversation validation failed: {error_messages}")
        
        return conversation
    
    def _convert_messages_to_domain(
        self, 
        messages: List[MessageDTO]
    ) -> List[dict]:
        """
        Convert message DTOs to domain message format.
        
        Args:
            messages: List of message DTOs
            
        Returns:
            List of message dictionaries for domain services
        """
        domain_messages = []
        for msg in messages:
            domain_msg = {
                "text": msg.text,
                "author_name": msg.author_name,
                "author_type": msg.author_type or "user",
                "timestamp": msg.timestamp
            }
            domain_messages.append(domain_msg)
        
        return domain_messages
    
    async def _generate_embeddings(
        self, 
        chunks: List[ConversationChunk]
    ) -> List[ConversationChunk]:
        """
        Generate embeddings for all chunks.
        
        Args:
            chunks: List of chunks without embeddings
            
        Returns:
            List of chunks with embeddings attached
            
        Raises:
            EmbeddingError: If embedding generation fails
        """
        if not chunks:
            return chunks
        
        # Extract texts for batch embedding
        texts = [chunk.text.value for chunk in chunks]
        
        try:
            # Generate embeddings in batch for efficiency
            embeddings = await self.embedding_service.generate_embeddings_batch(texts)
            
            # Validate embeddings
            for embedding in embeddings:
                validation_result = self.embedding_validation_service.validate_embedding(
                    embedding
                )
                if not validation_result.is_valid:
                    raise EmbeddingError(
                        f"Invalid embedding generated: {validation_result.errors}"
                    )
            
            # Attach embeddings to chunks
            chunks_with_embeddings = []
            for chunk, embedding in zip(chunks, embeddings):
                # Create new chunk with embedding (immutable pattern)
                chunk_with_embedding = ConversationChunk(
                    id=chunk.id,
                    conversation_id=chunk.conversation_id,
                    text=chunk.text,
                    metadata=chunk.metadata,
                    embedding=embedding
                )
                chunks_with_embeddings.append(chunk_with_embedding)
            
            logger.info(f"Generated embeddings for {len(chunks)} chunks")
            return chunks_with_embeddings
            
        except Exception as e:
            logger.error(f"Failed to generate embeddings: {str(e)}")
            raise EmbeddingError(f"Embedding generation failed: {str(e)}")
    
    def _build_response(
        self,
        conversation: Conversation,
        chunks: List[ConversationChunk]
    ) -> IngestConversationResponse:
        """
        Build the ingestion response.
        
        Args:
            conversation: The saved conversation
            chunks: The saved chunks
            
        Returns:
            The ingestion response DTO
        """
        metadata_dto = ConversationMetadataDTO(
            conversation_id=str(conversation.id.value),
            scenario_title=conversation.metadata.scenario_title,
            original_title=conversation.metadata.original_title,
            url=conversation.metadata.url,
            created_at=conversation.metadata.created_at or datetime.utcnow(),
            total_chunks=len(chunks)
        )
        
        return IngestConversationResponse(
            conversation_id=str(conversation.id.value),
            chunks_created=len(chunks),
            metadata=metadata_dto,
            success=True,
            error_message=None
        )
    
    def _empty_metadata(self) -> ConversationMetadataDTO:
        """Create empty metadata for error responses."""
        return ConversationMetadataDTO(
            conversation_id="",
            scenario_title=None,
            original_title=None,
            url=None,
            created_at=datetime.utcnow(),
            total_chunks=0
        )
