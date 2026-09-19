"""Chunk indexing orchestration tests."""

from collections.abc import Sequence
from typing import Any, cast

import pytest

from ingestion.indexing import ChunkIndexer
from ingestion.models import DocumentChunk
from storage.qdrant import QdrantGateway


class FakeEmbedder:
    model_id = "test-model"
    dimension = 2

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        return [[float(index), 1.0] for index, _text in enumerate(texts)]

    def embed_query(self, text: str) -> list[float]:
        return [0.0, 1.0]


class FakeGateway:
    def __init__(self) -> None:
        self.received: tuple[Sequence[DocumentChunk], Sequence[Sequence[float]]] | None = None

    def upsert_chunks(
        self,
        *,
        chunks: Sequence[DocumentChunk],
        vectors: Sequence[Sequence[float]],
        batch_size: int = 64,
    ) -> int:
        self.received = chunks, vectors
        return len(chunks)


def _chunk(model_id: str = "test-model") -> DocumentChunk:
    return DocumentChunk(
        chunk_id="00000000-0000-0000-0000-000000000001",
        text="evidence",
        content_hash="hash",
        chunk_index=0,
        page_start=1,
        page_end=1,
        section_path=(),
        payload={"embedding_model": model_id},
    )


def test_indexer_embeds_and_upserts_chunks() -> None:
    gateway = FakeGateway()
    indexer = ChunkIndexer(
        embedder=FakeEmbedder(),
        qdrant=cast(QdrantGateway, gateway),
    )

    assert indexer.index([_chunk()]) == 1
    assert gateway.received is not None


def test_indexer_rejects_embedding_model_mismatch() -> None:
    indexer = ChunkIndexer(
        embedder=FakeEmbedder(),
        qdrant=cast(QdrantGateway, cast(Any, FakeGateway())),
    )

    with pytest.raises(ValueError):
        indexer.index([_chunk("other-model")])
