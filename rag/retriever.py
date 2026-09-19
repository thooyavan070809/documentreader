"""Dense retrieval using mandatory authorization filters."""

from __future__ import annotations

from collections.abc import Sequence

from domain.retrieval import RetrievedChunk
from ingestion.embeddings import EmbeddingProvider
from storage.qdrant import QdrantGateway


class DenseRetriever:
    def __init__(
        self,
        *,
        embedder: EmbeddingProvider,
        qdrant: QdrantGateway,
        candidate_limit: int,
        score_threshold: float,
    ) -> None:
        self.embedder = embedder
        self.qdrant = qdrant
        self.candidate_limit = candidate_limit
        self.score_threshold = score_threshold

    def retrieve(
        self,
        *,
        question: str,
        tenant_id: str,
        workspace_id: str,
        document_version_ids: Sequence[str],
    ) -> list[RetrievedChunk]:
        query_vector = self.embedder.embed_query(question)
        return self.qdrant.search_dense(
            query_vector=query_vector,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            document_version_ids=document_version_ids,
            limit=self.candidate_limit,
            score_threshold=self.score_threshold,
        )
