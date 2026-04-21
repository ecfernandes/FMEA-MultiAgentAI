"""
ChromaDB Manager - Vector Store management.
Responsible for initializing, persisting, and managing ChromaDB collections.
"""

import chromadb
from chromadb.config import Settings
from typing import List, Dict, Optional
import os
from datetime import datetime


class ChromaManager:
    """ChromaDB manager for vector document storage."""
    
    def __init__(self, persist_directory: str = "./data/vector_store"):
        """
        Initialize ChromaDB with local persistence.
        
        Args:
            persist_directory: Directory used to persist ChromaDB data.
        """
        self.persist_directory = persist_directory
        
        # Create directory if it doesn't exist
        os.makedirs(persist_directory, exist_ok=True)
        
        # Configure persistent ChromaDB client
        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )
        
        # Default collection name
        self.collection_name = "risk_documents"
        
    def get_or_create_collection(self, collection_name: Optional[str] = None):
        """
        Get or create a ChromaDB collection.
        
        Args:
            collection_name: Collection name (uses default if None).
            
        Returns:
            Collection object
        """
        name = collection_name or self.collection_name
        
        try:
            collection = self.client.get_or_create_collection(
                name=name,
                metadata={"description": "Risk analysis documents and results"}
            )
            return collection
        except Exception as e:
            print(f"Error getting/creating collection: {e}")
            raise
    
    def add_document(
        self,
        document_text: str,
        embedding: List[float],
        metadata: Dict,
        doc_id: Optional[str] = None
    ):
        """
        Add a document to the vector store.
        
        Args:
            document_text: Full document text.
            embedding: Document embedding vector.
            metadata: Metadata (date, identified risks, etc.).
            doc_id: Unique document ID (auto-generated when None).
        """
        collection = self.get_or_create_collection()
        
        # Generate ID if not provided
        if doc_id is None:
            doc_id = f"doc_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"
        
        # Add timestamp to metadata
        metadata['timestamp'] = datetime.now().isoformat()
        
        try:
            collection.add(
                ids=[doc_id],
                embeddings=[embedding],
                documents=[document_text],
                metadatas=[metadata]
            )
            return doc_id
        except Exception as e:
            print(f"Error adding document: {e}")
            raise
    
    def query_similar(
        self,
        query_embedding: List[float],
        n_results: int = 3,
        filter_metadata: Optional[Dict] = None
    ):
        """
        Search similar documents using embeddings.
        
        Args:
            query_embedding: Query embedding vector.
            n_results: Number of results to return.
            filter_metadata: Optional metadata filters.
            
        Returns:
            Dictionary with search results.
        """
        collection = self.get_or_create_collection()
        
        try:
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=n_results,
                where=filter_metadata
            )
            return results
        except Exception as e:
            print(f"Search error: {e}")
            raise
    
    def get_all_documents(self):
        """Return all documents in collection."""
        collection = self.get_or_create_collection()
        
        try:
            # Retrieve all documents
            results = collection.get()
            return results
        except Exception as e:
            print(f"Error retrieving documents: {e}")
            return None
    
    def delete_document(self, doc_id: str):
        """Remove a document by ID."""
        collection = self.get_or_create_collection()
        
        try:
            collection.delete(ids=[doc_id])
            return True
        except Exception as e:
            print(f"Error deleting document: {e}")
            return False
    
    def count_documents(self):
        """Return total document count."""
        collection = self.get_or_create_collection()
        return collection.count()
    
    def reset_collection(self):
        """Reset collection (WARNING: removes all data!)."""
        try:
            self.client.delete_collection(name=self.collection_name)
            print(f"Collection '{self.collection_name}' reset successfully.")
            return True
        except Exception as e:
            print(f"Error resetting collection: {e}")
            return False
