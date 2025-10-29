import os
import logging
import time
from typing import List, Optional
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

class EmbeddingService:
    def __init__(self):
        self.client = None
        self.model = "text-embedding-ada-002"
        self.max_retries = 3
        self.retry_delay = 1.0
        self._initialize_client()

    def _initialize_client(self):
        """Initialize OpenAI client"""
        try:
            api_key = os.getenv('OPENAI_API_KEY')
            if not api_key:
                raise ValueError("OPENAI_API_KEY environment variable not set")

            # Add timeout to prevent indefinite hangs
            self.client = OpenAI(api_key=api_key, timeout=30.0, max_retries=3)
            logger.info("OpenAI client initialized successfully")
            
        except Exception as e:
            logger.error(f"Failed to initialize OpenAI client: {e}")
            raise
    
    async def create_embedding_async(self, text: str) -> Optional[List[float]]:
        """Create embedding for text with retry logic (async)"""
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None
        
        # Clean and prepare text
        text = text.strip()
        if len(text) > 8000:  # OpenAI's limit is ~8192 tokens
            text = text[:8000]
            logger.warning("Text truncated to 8000 characters for embedding")
        
        for attempt in range(self.max_retries):
            try:
                import asyncio
                loop = asyncio.get_event_loop()
                response = await loop.run_in_executor(
                    None, 
                    lambda: self.client.embeddings.create(
                        model=self.model,
                        input=text
                    )
                )
                
                embedding = response.data[0].embedding
                logger.debug(f"Created embedding for text: {text[:50]}...")
                return embedding
                
            except Exception as e:
                logger.warning(f"Embedding attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    await asyncio.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(f"Failed to create embedding after {self.max_retries} attempts")
                    return None

    def create_embedding(self, text: str) -> Optional[List[float]]:
        """Create embedding for text with retry logic"""
        if not text or not text.strip():
            logger.warning("Empty text provided for embedding")
            return None
        
        # Clean and prepare text
        text = text.strip()
        if len(text) > 8000:  # OpenAI's limit is ~8192 tokens
            text = text[:8000]
            logger.warning("Text truncated to 8000 characters for embedding")
        
        for attempt in range(self.max_retries):
            try:
                response = self.client.embeddings.create(
                    model=self.model,
                    input=text
                )
                
                embedding = response.data[0].embedding
                logger.debug(f"Created embedding for text: {text[:50]}...")
                return embedding
                
            except Exception as e:
                logger.warning(f"Embedding attempt {attempt + 1} failed: {e}")
                
                if attempt < self.max_retries - 1:
                    time.sleep(self.retry_delay * (2 ** attempt))  # Exponential backoff
                else:
                    logger.error(f"Failed to create embedding after {self.max_retries} attempts")
                    return None
    
    def create_embeddings_batch(self, texts: List[str]) -> List[Optional[List[float]]]:
        """Create embeddings for multiple texts"""
        embeddings = []
        
        for text in texts:
            embedding = self.create_embedding(text)
            embeddings.append(embedding)
            
            # Small delay to avoid rate limiting
            time.sleep(0.1)
        
        return embeddings
    
    def get_embedding_dimension(self) -> int:
        """Get the dimension of embeddings for this model"""
        return 1536  # ada-002 dimension
    
    def calculate_similarity(self, embedding1: List[float], embedding2: List[float]) -> float:
        """Calculate cosine similarity between two embeddings"""
        try:
            import numpy as np
            
            # Convert to numpy arrays
            vec1 = np.array(embedding1)
            vec2 = np.array(embedding2)
            
            # Calculate cosine similarity
            dot_product = np.dot(vec1, vec2)
            magnitude1 = np.linalg.norm(vec1)
            magnitude2 = np.linalg.norm(vec2)
            
            if magnitude1 == 0 or magnitude2 == 0:
                return 0.0
            
            similarity = dot_product / (magnitude1 * magnitude2)
            return float(similarity)
            
        except Exception as e:
            logger.error(f"Error calculating similarity: {e}")
            return 0.0
    
    def test_connection(self) -> bool:
        """Test if the OpenAI API connection is working"""
        try:
            test_embedding = self.create_embedding("test connection")
            return test_embedding is not None
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

# Global instance
embedding_service = EmbeddingService()