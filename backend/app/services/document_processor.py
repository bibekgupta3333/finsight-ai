"""
Document Processing Service.

Handles document ingestion, text extraction, chunking, and vector embedding
for the creation of semantic memory from documents (PDF, Text).
"""

import logging
import uuid
import re
from typing import List, Dict, Any, Optional
from datetime import datetime

from app.services.llm_client import get_llm_client
from app.core.config import get_settings

logger = logging.getLogger(__name__)
settings = get_settings()


class DocumentProcessor:
    """
    Process documents for semantic search retrieval.
    """

    def __init__(self):
        self.chunk_size = 500  # Characters (approx)
        self.chunk_overlap = 50

    async def process_document(
        self, content: str, filename: str, doc_type: str = "text"
    ) -> List[Dict[str, Any]]:
        """
        Process a document text into embedded chunks.

        Args:
            content: Raw text content
            filename: Source filename
            doc_type: 'text' or 'pdf' (metadata)

        Returns:
            List of chunks with embeddings and metadata
        """
        # 1. Chunking
        chunks = self._chunk_text(content)
        logger.info(f"Split {filename} into {len(chunks)} chunks")

        # 2. Embedding
        llm_client = await get_llm_client()
        processed_chunks = []

        for i, chunk_text in enumerate(chunks):
            try:
                embedding = await llm_client.embeddings(prompt=chunk_text)

                processed_chunks.append(
                    {
                        "id": str(uuid.uuid4()),
                        "content": chunk_text,
                        "embedding": embedding,
                        "metadata": {
                            "source": filename,
                            "type": doc_type,
                            "chunk_index": i,
                            "total_chunks": len(chunks),
                            "created_at": datetime.utcnow().isoformat(),
                        },
                    }
                )
            except Exception as e:
                logger.error(f"Failed to embed chunk {i} of {filename}: {e}")

        return processed_chunks

    def _chunk_text(self, text: str) -> List[str]:
        """Simple text chunking with overlap."""
        text = re.sub(r"\s+", " ", text).strip()
        chunks = []
        start = 0
        text_len = len(text)

        while start < text_len:
            end = start + self.chunk_size

            # Adjust end to nearest space to avoid splitting words
            if end < text_len:
                # Look for last space within the chunk constraint
                last_space = text.rfind(" ", start, end)
                if last_space != -1 and last_space > start + (self.chunk_size // 2):
                    end = last_space

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - self.chunk_overlap

        return chunks


# Global instance
_document_processor = None


def get_document_processor() -> DocumentProcessor:
    global _document_processor
    if _document_processor is None:
        _document_processor = DocumentProcessor()
    return _document_processor
