# -*- coding: utf-8 -*-
"""
Vector Service - ChromaDB integration for knowledge base vectorization
"""
import logging
import os
from pathlib import Path
from typing import List, Dict, Any, Optional
import chromadb
from chromadb.config import Settings
from openai import OpenAI

from runtime.modules.agent.llm_service import LLMConfigService
from runtime.shared.llm_endpoints import normalize_openai_base_url

logger = logging.getLogger(__name__)


class VectorService:
    """Service for vectorizing and searching documents using ChromaDB and OpenAI"""

    def __init__(self, persist_directory: str = "km/chroma_db"):
        """Initialize ChromaDB client"""
        self.persist_directory = persist_directory
        os.makedirs(persist_directory, exist_ok=True)

        self.client = chromadb.PersistentClient(
            path=persist_directory,
            settings=Settings(anonymized_telemetry=False)
        )

        # Initialize OpenAI client from the default LLM config in DB, with env overrides.
        api_key = os.environ.get('OPENAI_API_KEY')
        api_base = os.environ.get('OPENAI_API_BASE')
        self.embedding_model = 'text-embedding-3-small'

        if not api_key:
            try:
                default_cfg = LLMConfigService().get_default_config()
                if default_cfg:
                    api_key = default_cfg.get('api_key') or api_key
                    raw_endpoint = default_cfg.get('api_endpoint') or ''
                    if raw_endpoint:
                        api_base = api_base or normalize_openai_base_url(raw_endpoint)
            except Exception as e:
                logger.warning(f"Failed to load default LLM config for embedding: {e}")

        if api_key and api_base:
            self.openai_client = OpenAI(api_key=api_key, base_url=api_base)
        elif api_key:
            self.openai_client = OpenAI(api_key=api_key)
        else:
            self.openai_client = OpenAI()

    def get_or_create_collection(self, km_id: str):
        """Get or create a collection for a knowledge base"""
        collection_name = f"kb_{km_id}"
        return self.client.get_or_create_collection(
            name=collection_name,
            metadata={"km_id": km_id, "hnsw:space": "cosine"}
        )

    def get_embedding(self, text: str, model: Optional[str] = None) -> List[float]:
        """Get embedding from OpenAI"""
        try:
            response = self.openai_client.embeddings.create(
                input=text,
                model=model or self.embedding_model
            )
            return response.data[0].embedding
        except Exception as e:
            logger.error(f"Error getting embedding: {e}")
            raise

    def upsert_note(
        self,
        km_id: str,
        note_id: int,
        title: str,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 100
    ) -> int:
        try:
            collection = self.get_or_create_collection(km_id)

            try:
                collection.delete(where={"note_id": str(note_id)})
            except Exception:
                pass

            chunks = self.chunk_text(text, chunk_size, overlap)
            if not chunks:
                logger.warning(f"No chunks generated for note {note_id}")
                return 0

            ids = []
            embeddings = []
            documents = []
            metadatas = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"note_{note_id}_chunk_{i}"
                embedding = self.get_embedding(chunk)
                ids.append(chunk_id)
                embeddings.append(embedding)
                documents.append(chunk)
                metadatas.append({
                    "note_id": str(note_id),
                    "title": title or "",
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                })

            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )

            logger.info(f"Added {len(chunks)} chunks for note {note_id} to collection {km_id}")
            return len(chunks)

        except Exception as e:
            logger.error(f"Error upserting note to vector DB: {e}")
            raise

    def chunk_text(self, text: str, chunk_size: int = 1000, overlap: int = 100) -> List[str]:
        """Split text into chunks with overlap"""
        if not text:
            return []

        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + chunk_size
            chunk = text[start:end]

            # Try to break at sentence boundary
            if end < text_len:
                last_period = chunk.rfind('.')
                last_newline = chunk.rfind('\n')
                break_point = max(last_period, last_newline)

                if break_point > chunk_size * 0.5:  # Only break if we're past halfway
                    chunk = chunk[:break_point + 1]
                    end = start + break_point + 1

            chunks.append(chunk.strip())
            start = end - overlap

        return [c for c in chunks if c]  # Filter empty chunks

    def add_document(
        self,
        km_id: str,
        file_id: int,
        filename: str,
        text: str,
        chunk_size: int = 1000,
        overlap: int = 100
    ) -> int:
        """Add a document to the vector database"""
        try:
            collection = self.get_or_create_collection(km_id)

            # Chunk the text
            chunks = self.chunk_text(text, chunk_size, overlap)

            if not chunks:
                logger.warning(f"No chunks generated for file {filename}")
                return 0

            # Generate embeddings and add to collection
            ids = []
            embeddings = []
            documents = []
            metadatas = []

            for i, chunk in enumerate(chunks):
                chunk_id = f"file_{file_id}_chunk_{i}"
                embedding = self.get_embedding(chunk)

                ids.append(chunk_id)
                embeddings.append(embedding)
                documents.append(chunk)
                metadatas.append({
                    "file_id": str(file_id),
                    "filename": filename,
                    "chunk_index": i,
                    "total_chunks": len(chunks)
                })

            collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=documents,
                metadatas=metadatas
            )

            logger.info(f"Added {len(chunks)} chunks for file {filename} to collection {km_id}")
            return len(chunks)

        except Exception as e:
            logger.error(f"Error adding document to vector DB: {e}")
            raise

    def search(
        self,
        km_id: str,
        query: str,
        top_k: int = 5
    ) -> List[Dict[str, Any]]:
        """Search for similar documents"""
        try:
            collection = self.get_or_create_collection(km_id)

            # Get query embedding
            query_embedding = self.get_embedding(query)

            # Search
            results = collection.query(
                query_embeddings=[query_embedding],
                n_results=top_k
            )

            formatted_results = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    distance = float(results['distances'][0][i])
                    score = max(0.0, min(1.0, 1.0 - distance))
                    formatted_results.append({
                        "content": results['documents'][0][i],
                        "score": score,
                        "distance": distance,
                        "metadata": results['metadatas'][0][i]
                    })

            return formatted_results

        except Exception as e:
            logger.error(f"Error searching vector DB: {e}")
            raise

    def delete_document(self, km_id: str, file_id: int):
        """Delete all chunks of a document from the vector database"""
        try:
            collection = self.get_or_create_collection(km_id)

            # Get all IDs for this file
            results = collection.get(
                where={"file_id": str(file_id)}
            )

            if results['ids']:
                collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for file_id {file_id}")

        except Exception as e:
            logger.error(f"Error deleting document from vector DB: {e}")
            raise

    def delete_note(self, km_id: str, note_id: int):
        """Delete all chunks of a note from the vector database"""
        try:
            collection = self.get_or_create_collection(km_id)
            results = collection.get(where={"note_id": str(note_id)})
            if results.get('ids'):
                collection.delete(ids=results['ids'])
                logger.info(f"Deleted {len(results['ids'])} chunks for note_id {note_id}")
        except Exception as e:
            logger.error(f"Error deleting note from vector DB: {e}")
            raise

    def delete_collection(self, km_id: str):
        """Delete an entire collection"""
        try:
            collection_name = f"kb_{km_id}"
            self.client.delete_collection(name=collection_name)
            logger.info(f"Deleted collection {collection_name}")
        except Exception as e:
            logger.error(f"Error deleting collection: {e}")
            raise


# Global instance
_vector_service = None


def get_vector_service() -> VectorService:
    """Get or create global vector service instance"""
    global _vector_service
    if _vector_service is None:
        _vector_service = VectorService()
    return _vector_service
