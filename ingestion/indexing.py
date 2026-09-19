"""Application service for embedding and idempotently indexing chunks."""

from __future__ import annotations

from collections.abc import Sequence

from ingestion.embeddings import EmbeddingProvider
from ingestion.models import DocumentChunk
from storage.qdrant import QdrantGateway


class ChunkIndexer:
    def __init__(self, *, embedder: EmbeddingProvider, qdrant: QdrantGateway) -> None:
        self.embedder = embedder
        self.qdrant = qdrant

    def index(self, chunks: Sequence[DocumentChunk]) -> int:
        if not chunks:
            return 0
        if any(
            chunk.payload.get("embedding_model") != self.embedder.model_id
            for chunk in chunks
        ):
            raise ValueError("Chunk metadata does not match the configured embedding model.")
        vectors = self.embedder.embed_documents([chunk.text for chunk in chunks])
        return self.qdrant.upsert_chunks(chunks=chunks, vectors=vectors)
