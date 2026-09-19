"""Lazy Qdrant Cloud client boundary."""

from __future__ import annotations

from collections.abc import Sequence
from typing import TYPE_CHECKING

from qdrant_client import models

from app.config import Settings
from domain.retrieval import RetrievedChunk
from ingestion.models import DocumentChunk

if TYPE_CHECKING:
    from qdrant_client import QdrantClient


class QdrantNotConfiguredError(RuntimeError):
    pass


class QdrantGateway:
    def __init__(self, settings: Settings, *, client: QdrantClient | None = None) -> None:
        self.settings = settings
        self._client = client

    @property
    def client(self) -> QdrantClient:
        if not self.settings.qdrant_configured:
            raise QdrantNotConfiguredError(
                "Set QDRANT_URL and QDRANT_API_KEY in .env before using Qdrant Cloud."
            )
        if self._client is None:
            from qdrant_client import QdrantClient

            self._client = QdrantClient(
                url=self.settings.qdrant_url,
                api_key=self.settings.qdrant_api_key.get_secret_value(),
                timeout=10,
            )
        return self._client

    def ping(self) -> None:
        self.client.get_collections()

    def ensure_collection(self, *, vector_size: int) -> None:
        """Create the collection and authorization indexes if they do not exist."""
        collection_name = self.settings.qdrant_collection
        if self.client.collection_exists(collection_name):
            info = self.client.get_collection(collection_name)
            vector_config = info.config.params.vectors
            if not isinstance(vector_config, models.VectorParams):
                raise RuntimeError("The configured collection must use one unnamed dense vector.")
            if vector_config.size != vector_size:
                raise RuntimeError(
                    "The Qdrant collection vector size does not match the embedding model."
                )
            return

        self.client.create_collection(
            collection_name=collection_name,
            vectors_config=models.VectorParams(size=vector_size, distance=models.Distance.COSINE),
        )
        for field_name in (
            "tenant_id",
            "workspace_id",
            "document_id",
            "document_version_id",
        ):
            self.client.create_payload_index(
                collection_name=collection_name,
                field_name=field_name,
                field_schema=models.PayloadSchemaType.KEYWORD,
                wait=True,
            )

    def upsert_chunks(
        self,
        *,
        chunks: Sequence[DocumentChunk],
        vectors: Sequence[Sequence[float]],
        batch_size: int = 64,
    ) -> int:
        if len(chunks) != len(vectors):
            raise ValueError("Each chunk must have exactly one embedding vector.")
        if not chunks:
            return 0
        vector_size = len(vectors[0])
        if vector_size == 0 or any(len(vector) != vector_size for vector in vectors):
            raise ValueError("Embedding vectors must be non-empty and have equal dimensions.")

        self.ensure_collection(vector_size=vector_size)
        indexed = 0
        for start in range(0, len(chunks), batch_size):
            points = [
                models.PointStruct(
                    id=chunk.chunk_id,
                    vector=list(vector),
                    payload=chunk.payload,
                )
                for chunk, vector in zip(
                    chunks[start : start + batch_size],
                    vectors[start : start + batch_size],
                    strict=True,
                )
            ]
            self.client.upsert(
                collection_name=self.settings.qdrant_collection,
                points=points,
                wait=True,
            )
            indexed += len(points)
        return indexed

    def search_dense(
        self,
        *,
        query_vector: Sequence[float],
        tenant_id: str,
        workspace_id: str,
        document_version_ids: Sequence[str],
        limit: int,
        score_threshold: float,
    ) -> list[RetrievedChunk]:
        if not document_version_ids:
            return []
        response = self.client.query_points(
            collection_name=self.settings.qdrant_collection,
            query=list(query_vector),
            query_filter=build_scope_filter(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                document_version_ids=document_version_ids,
            ),
            limit=limit,
            score_threshold=score_threshold,
            with_payload=True,
            with_vectors=False,
        )
        return [
            RetrievedChunk(
                chunk_id=str(point.id),
                score=float(point.score),
                payload=dict(point.payload or {}),
            )
            for point in response.points
        ]


def build_scope_filter(
    *,
    tenant_id: str,
    workspace_id: str,
    document_ids: Sequence[str] | None = None,
    document_version_ids: Sequence[str] | None = None,
) -> models.Filter:
    """Build mandatory authorization filters before any similarity search."""
    conditions: list[models.Condition] = [
        models.FieldCondition(key="tenant_id", match=models.MatchValue(value=tenant_id)),
        models.FieldCondition(key="workspace_id", match=models.MatchValue(value=workspace_id)),
    ]
    if document_ids:
        conditions.append(
            models.FieldCondition(
                key="document_id",
                match=models.MatchAny(any=list(document_ids)),
            )
        )
    if document_version_ids:
        conditions.append(
            models.FieldCondition(
                key="document_version_id",
                match=models.MatchAny(any=list(document_version_ids)),
            )
        )
    return models.Filter(must=conditions)
