import openai
from typing import List, Dict, Any
import json
import re
from app.database import settings

class EmbeddingService:
    def __init__(self):
        openai.api_key = settings.openai_api_key
        self.model = settings.embedding_model
        self.dimension = settings.embedding_dimension

    async def generate_embedding(self, text: str) -> List[float]:
        """Generate embedding for a given text using OpenAI API"""
        try:
            response = await openai.embeddings.acreate(
                model=self.model,
                input=text
            )
            return response.data[0].embedding
        except Exception as e:
            print(f"Error generating embedding: {str(e)}")
            # Return zero vector as fallback
            return [0.0] * self.dimension

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        """Generate embeddings for multiple texts"""
        try:
            response = await openai.embeddings.acreate(
                model=self.model,
                input=texts
            )
            return [data.embedding for data in response.data]
        except Exception as e:
            print(f"Error generating batch embeddings: {str(e)}")
            # Return zero vectors as fallback
            return [[0.0] * self.dimension for _ in texts]

class ConversationProcessor:
    def __init__(self):
        self.embedding_service = EmbeddingService()

    def chunk_conversation(self, messages: List[Dict[str, Any]], max_chunk_size: int = 1000) -> List[Dict[str, Any]]:
        """
        Chunk conversation messages into smaller pieces suitable for embedding
        """
        chunks = []
        current_chunk = ""
        current_messages = []
        
        for i, message in enumerate(messages):
            message_text = f"{message.get('author_name', 'Unknown')}: {message.get('content', '')}"
            
            # If adding this message would exceed max_chunk_size, save current chunk
            if len(current_chunk + message_text) > max_chunk_size and current_chunk:
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
            chunks.append({
                "order_index": len(chunks),
                "chunk_text": current_chunk.strip(),
                "author_name": current_messages[-1].get('author_name'),
                "author_type": current_messages[-1].get('author_type'),
                "timestamp": current_messages[-1].get('timestamp')
            })
        
        return chunks

    async def process_conversation_for_ingestion(self, conversation_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Process a conversation for ingestion, including chunking and embedding generation
        """
        messages = conversation_data.get('messages', [])
        chunks = self.chunk_conversation(messages)
        
        # Generate embeddings for all chunks
        chunk_texts = [chunk['chunk_text'] for chunk in chunks]
        embeddings = await self.embedding_service.generate_embeddings_batch(chunk_texts)
        
        # Add embeddings to chunks
        for chunk, embedding in zip(chunks, embeddings):
            chunk['embedding'] = embedding
        
        return {
            'scenario_title': conversation_data.get('scenario_title'),
            'original_title': conversation_data.get('original_title'),
            'url': conversation_data.get('url'),
            'chunks': chunks
        }

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
