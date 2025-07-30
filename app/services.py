from typing import List, Dict, Any
from openai import AsyncOpenAI
import json
import logging
import re
from app.database import settings
from app.logging_config import get_logger

# Get logger for this module
logger = get_logger(__name__)


class EmbeddingService:
    def __init__(self):
        # Use the settings to get the API key
        api_key = settings.openai_api_key
        logger.info(f"🔧 Initializing EmbeddingService with model: {settings.embedding_model}")
        logger.info(f"📏 Embedding dimension: {settings.embedding_dimension}")
        
        if api_key:
            self.client = AsyncOpenAI(api_key=api_key)
            logger.info("✅ Using API key from settings")
        else:
            self.client = AsyncOpenAI()  # Will use OPENAI_API_KEY env var automatically
            logger.info("🔑 Using API key from environment variable")
            
        self.model = settings.embedding_model
        self.dimension = settings.embedding_dimension

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a given text using OpenAI API"""
        logger.debug(f"🔄 Generating embedding for text: {text[:50]}...")
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=text
            )
            embedding = response.data[0].embedding
            logger.info(f"✅ Generated embedding with dimension: {len(embedding)}")
            return embedding
        except Exception as e:
            logger.error(f"❌ Error generating embedding: {str(e)}")
            # Return zero vector as fallback
            fallback_vector = [0.0] * self.dimension
            logger.warning(f"⚠️ Returning zero vector fallback with dimension: {len(fallback_vector)}")
            return fallback_vector

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        logger.info(f"🔄 Generating batch embeddings for {len(texts)} texts")
        try:
            response = await self.client.embeddings.create(
                model=self.model,
                input=texts
            )
            logger.info(f"✅ Generated {len(response.data)} embeddings successfully")
            return [data.embedding for data in response.data]
        except Exception as e:
            logger.error(f"❌ Error generating batch embeddings: {str(e)}")
            # Return zero vectors as fallback
            fallback_vectors = [[0.0] * self.dimension for _ in texts]
            logger.warning(f"⚠️ Returning {len(fallback_vectors)} zero vector fallbacks")
            return fallback_vectors

class ConversationProcessor:
    def __init__(self):
        self.embedding_service = EmbeddingService()
        logger.info("🎯 ConversationProcessor initialized")

    def chunk_conversation(self, messages: List[Dict[str, Any]], max_chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """
        Chunk conversation messages into smaller pieces suitable for embedding
        """
        logger.info(f"📝 Starting to chunk {len(messages)} messages with max_chunk_size: {max_chunk_size}")
        chunks = []
        current_chunk = ""
        current_messages = []
        
        for i, message in enumerate(messages):
            message_text = f"{message.get('author_name', 'Unknown')}: {message.get('content', '')}"
            
            # If adding this message would exceed max_chunk_size, save current chunk
            if len(current_chunk + message_text) > max_chunk_size and current_chunk:
                logger.debug(f"🔄 Creating chunk {len(chunks)} with {len(current_messages)} messages")
                chunks.append({
                    "order_index": len(chunks),
                    "chunk_text": current_chunk.strip(),
                    "author_name": current_messages[-1].get('author_name'),
                    "author_type": current_messages[-1].get('author_type'),
                    "timestamp": current_messages[-1].get('timestamp')
                })
                current_chunk = ""
                current_messages = []
            
            current_chunk += message_text + "\n"
            current_messages.append(message)
        
        # Add the last chunk if it exists
        if current_chunk.strip():
            logger.debug(f"🔄 Creating final chunk {len(chunks)} with {len(current_messages)} messages")
            chunks.append({
                "order_index": len(chunks),
                "chunk_text": current_chunk.strip(),
                "author_name": current_messages[-1].get('author_name'),
                "author_type": current_messages[-1].get('author_type'),
                "timestamp": current_messages[-1].get('timestamp')
            })
        
        logger.info(f"✅ Created {len(chunks)} chunks from {len(messages)} messages")
        return chunks

    async def process_conversation_for_ingestion(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a conversation for ingestion, including chunking and embedding generation
        """
        logger.info(f"🚀 Starting conversation processing for: {conversation_data.get('scenario_title', 'Unknown scenario')}")
        messages = conversation_data.get('messages', [])
        logger.debug(f"📋 Processing {len(messages)} messages")
        
        chunks = self.chunk_conversation(messages)
        
        # Generate embeddings for all chunks
        chunk_texts = [chunk['chunk_text'] for chunk in chunks]
        logger.info(f"🔄 Generating embeddings for {len(chunk_texts)} chunks")
        embeddings = await self.embedding_service.generate_embeddings_batch(chunk_texts)
        
        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding
        
        result = {
            'scenario_title': conversation_data.get('scenario_title'),
            'original_title': conversation_data.get('original_title'),
            'url': conversation_data.get('url'),
            'chunks': chunks
        }
        
        logger.info(f"✅ Conversation processing completed: {len(chunks)} chunks with embeddings")
        return result

class ContextFormatter:
    @staticmethod
    def format_search_results(results: List[Dict[str, Any]], query: str) -> Dict[str, Any]:
        """
        Format search results for consumption by an LLM
        """
        formatted_results = []
        
        for result in results:
            formatted_result = {
                'conversation_id': result['conversation_id'],
                'scenario_title': result['scenario_title'],
                'original_title': result['original_title'],
                'url': result['url'],
                'relevance_score': result['relevance_score'],
                'matched_content': result['chunk_text'],
                'author_info': {
                    'name': result['author_name'],
                    'type': result['author_type']
                },
                'timestamp': result['timestamp']
            }
            formatted_results.append(formatted_result)
        
        return {
            'query': query,
            'total_results': len(formatted_results),
            'results': formatted_results,
            'context_summary': f"Found {len(formatted_results)} relevant conversation segments for query: '{query}'"
        }
