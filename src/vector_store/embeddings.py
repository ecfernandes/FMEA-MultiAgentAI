"""
Embedding Generator - Semantic vector generation.
Uses Sentence Transformers to create document embeddings.
"""

from sentence_transformers import SentenceTransformer
from typing import List, Union
import numpy as np


class EmbeddingGenerator:
    """Generate text embeddings using pre-trained models."""
    
    def __init__(self, model_name: str = "paraphrase-multilingual-MiniLM-L12-v2"):
        """
        Initialize the embedding generator.
        
        Args:
            model_name: Sentence Transformer model name.
                       'paraphrase-multilingual-MiniLM-L12-v2' -> 384D, great for PT/FR/EN (420MB)
                       'paraphrase-multilingual-mpnet-base-v2' -> 768D, more accurate (970MB)
                       'all-MiniLM-L6-v2' -> 384D, mainly English (80MB)
        
        Recommended for UTFPR-UTC project: paraphrase-multilingual-MiniLM-L12-v2
        Supports 50+ languages including Portuguese, French, and English with high quality.
        """
        self.model_name = model_name
        
        # Load model (automatic cache) - CPU to save memory
        print(f"Loading embedding model: {model_name}...")
        self.model = SentenceTransformer(model_name, device='cpu')
        print("✓ Model loaded successfully!")
        
    def encode_text(self, text: str) -> List[float]:
        """
        Generate embedding for a single text.
        
        Args:
            text: Text to embed.
            
        Returns:
            List of floats representing embedding vector.
        """
        # Normalize text
        text = text.strip()
        
        if not text:
            raise ValueError("Empty text cannot be vectorized")
        
        # Generate embedding
        embedding = self.model.encode(text, convert_to_numpy=True)
        
        # Convert to Python list (ChromaDB expects list)
        return embedding.tolist()
    
    def encode_batch(self, texts: List[str], batch_size: int = 32) -> List[List[float]]:
        """
        Generate embeddings for multiple texts efficiently.
        
        Args:
            texts: List of texts to vectorize.
            batch_size: Batch size for processing.
            
        Returns:
            List of embeddings.
        """
        # Filter empty texts
        valid_texts = [t.strip() for t in texts if t.strip()]
        
        if not valid_texts:
            raise ValueError("No valid text provided")
        
        # Generate embeddings in batch (more efficient)
        embeddings = self.model.encode(
            valid_texts,
            batch_size=batch_size,
            show_progress_bar=True,
            convert_to_numpy=True
        )
        
        # Convert to list of lists
        return [emb.tolist() for emb in embeddings]
    
    def similarity(self, text1: str, text2: str) -> float:
        """
        Calculate cosine similarity between two texts.
        
        Args:
            text1: First text.
            text2: Second text.
            
        Returns:
            Similarity score (0 to 1, where 1 = semantically identical).
        """
        emb1 = np.array(self.encode_text(text1))
        emb2 = np.array(self.encode_text(text2))
        
        # Cosine similarity
        cosine_sim = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        
        return float(cosine_sim)
    
    def get_model_info(self) -> dict:
        """Return information about loaded model."""
        return {
            "model_name": self.model_name,
            "embedding_dimension": self.model.get_sentence_embedding_dimension(),
            "max_seq_length": self.model.max_seq_length,
            "device": str(self.model.device)
        }


# Helper function for simplified use
def create_embedding(text: str, model_name: str = "all-MiniLM-L6-v2") -> List[float]:
    """
    Utility function to create an embedding quickly.
    
    Args:
        text: Text to vectorize.
        model_name: Model to use.
        
    Returns:
        Embedding vector.
    """
    generator = EmbeddingGenerator(model_name)
    return generator.encode_text(text)
