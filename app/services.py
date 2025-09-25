from typing import List, Dict, Any
from openai import AsyncOpenAI
import json
import logging
import re
import os
import asyncio
from typing import List, Optional
from app.logging_config import get_logger
from app.config import settings

logger = get_logger(__name__)

# Local model loader (cached)
try:
    from sentence_transformers import SentenceTransformer  # requires numpy
except Exception:
    SentenceTransformer = None

_local_model = None

def _get_local_model(model_name: Optional[str] = None):
    global _local_model
    name = model_name or getattr(settings, "embedding_model", "all-MiniLM-L6-v2")
    if _local_model is None:
        if not SentenceTransformer:
            raise RuntimeError("sentence-transformers is not installed")
        _local_model = SentenceTransformer(name)
        logger.info(f"Loaded local embedding model: {name}")
    return _local_model

def generate_embedding_local(texts: List[str]) -> List[List[float]]:
    """
    Synchronous local embedding generation using sentence-transformers.
    Returns a Python list of lists (floats).
    """
    model = _get_local_model(getattr(settings, "embedding_model", "all-MiniLM-L6-v2"))
    embeddings = model.encode(texts, normalize_embeddings=False)
    # Fix: return the actual embeddings, not an undefined 'vecs'
    try:
        return embeddings.tolist()
    except AttributeError:
        # Already a list-like
        return [list(v) for v in embeddings]

def _resize(vec: List[float], target: int) -> List[float]:
    n = len(vec)
    if n == target:
        return vec
    if n < target:
        return vec + [0.0] * (target - n)
    return vec[:target]

class EmbeddingService:
    def __init__(self):
        # Safe defaults
        self.provider = (getattr(settings, "embedding_provider", "local") or "local").lower()
        self.model = getattr(settings, "embedding_model", "all-MiniLM-L6-v2")
        self.dimension = int(getattr(settings, "embedding_dimension", 1536))
        self.client = None

        # OpenAI optional
        try:
            from openai import AsyncOpenAI  # type: ignore
            self._AsyncOpenAI = AsyncOpenAI
        except Exception:
            self._AsyncOpenAI = None

        if self.provider == "openai" and self._AsyncOpenAI:
            import os
            api_key = getattr(settings, "openai_api_key", None) or os.getenv("OPENAI_API_KEY")
            if api_key:
                self.client = self._AsyncOpenAI(api_key=api_key)
            else:
                logger.warning("OPENAI_API_KEY not set; using local embeddings instead")
                self.provider = "local"

        logger.info(f"EmbeddingService provider={self.provider} model={self.model} target_dim={self.dimension}")

    async def generate_embedding(self, text: str) -> List[float]:
        if self.provider == "local":
            try:
                vec = (await asyncio.to_thread(generate_embedding_local, [text]))[0]
                return _resize(vec, self.dimension)
            except Exception as e:
                logger.error(f"Local embedding error: {e}")
                return [0.0] * self.dimension

        # OpenAI path
        try:
            resp = await self.client.embeddings.create(model=self.model, input=text)
            return _resize(resp.data[0].embedding, self.dimension)
        except Exception as e:
            logger.error(f"OpenAI embedding error: {e}")
            return [0.0] * self.dimension

    async def generate_embeddings_batch(self, texts: List[str]) -> List[List[float]]:
        if self.provider == "local":
            try:
                vectors = await asyncio.to_thread(generate_embedding_local, texts)
                resized = [_resize(v, self.dimension) for v in vectors]
                logger.info(f"Generated {len(resized)} local embeddings (dim={self.dimension})")
                return resized
            except Exception as e:
                logger.error(f"Local batch embedding error: {e}")
                return [[0.0] * self.dimension for _ in texts]

        # OpenAI path
        try:
            resp = await self.client.embeddings.create(model=self.model, input=texts)
            vectors = [d.embedding for d in resp.data]
            return [_resize(v, self.dimension) for v in vectors]
        except Exception as e:
            logger.error(f"OpenAI batch embedding error: {e}")
            return [[0.0] * self.dimension for _ in texts]

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
        last_author = None
        
        for i, message in enumerate(messages):
            message_text = f"{message.get('author_name', 'Unknown')}: {message.get('content', '')}"
            
            # Split if speaker changes or max_chunk_size exceeded
            if (last_author is not None and message.get('author_name') != last_author) or \
                (len(current_chunk + message_text) > max_chunk_size and current_chunk):
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
            last_author = message.get('author_name')
        
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
        logger.info("Preparing chunks for ingestion")
        
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
        logger.info(f"Prepared {len(chunks)} chunks")
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
