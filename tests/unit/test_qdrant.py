"""Qdrant indexing and authorization-filter tests with an in-memory fake client."""

from types import SimpleNamespace
from typing import Any, cast

from pydantic import SecretStr
from qdrant_client import QdrantClient, models

from app.config import Settings
from ingestion.models import DocumentChunk
from storage.qdrant import QdrantGateway, build_scope_filter


class FakeQdrantClient:
    def __init__(self) -> None:
        self.exists = False
        self.vector_size: int | None = None
        self.payload_indexes: list[str] = []
        self.upserted_ids: list[list[str]] = []
        self.query_kwargs: dict[str, Any] | None = None

    def collection_exists(self, _collection_name: str) -> bool:
        return self.exists

    def create_collection(self, **kwargs: Any) -> bool:
        vector_config = kwargs["vectors_config"]
        self.vector_size = vector_config.size
        self.exists = True
        return True

    def get_collection(self, _collection_name: str) -> Any:
        vector_config = models.VectorParams(
            size=self.vector_size or 0,
            distance=models.Distance.COSINE,
        )
        return SimpleNamespace(
            config=SimpleNamespace(params=SimpleNamespace(vectors=vector_config))
        )

    def create_payload_index(self, **kwargs: Any) -> None:
        self.payload_indexes.append(kwargs["field_name"])

    def upsert(self, **kwargs: Any) -> None:
        self.upserted_ids.append([str(point.id) for point in kwargs["points"]])

    def query_points(self, **kwargs: Any) -> Any:
        self.query_kwargs = kwargs
        return SimpleNamespace(
            points=[
                SimpleNamespace(
                    id="00000000-0000-0000-0000-000000000001",
                    score=0.91,
                    payload={"text": "Authorized evidence"},
                )
            ]
        )


def _chunk(index: int) -> DocumentChunk:
    chunk_id = f"00000000-0000-0000-0000-{index:012d}"
    return DocumentChunk(
        chunk_id=chunk_id,
        text=f"chunk {index}",
        content_hash=f"hash-{index}",
        chunk_index=index,
        page_start=1,
        page_end=1,
        section_path=(),
        payload={
            "tenant_id": "tenant-1",
            "workspace_id": "workspace-1",
            "document_id": "document-1",
            "document_version_id": "version-1",
            "embedding_model": "test-model",
        },
    )


def test_chunk_upsert_is_idempotent_and_creates_authorization_indexes() -> None:
    settings = Settings(
        _env_file=None,
        qdrant_url="https://example.qdrant.io",
        qdrant_api_key=SecretStr("test-key"),
        qdrant_collection="test-collection",
    )
    fake_client = FakeQdrantClient()
    gateway = QdrantGateway(settings, client=cast(QdrantClient, fake_client))
    chunks = [_chunk(1), _chunk(2)]
    vectors = [[1.0, 0.0], [0.0, 1.0]]

    assert gateway.upsert_chunks(chunks=chunks, vectors=vectors) == 2
    assert gateway.upsert_chunks(chunks=chunks, vectors=vectors) == 2

    assert fake_client.vector_size == 2
    assert fake_client.payload_indexes == [
        "tenant_id",
        "workspace_id",
        "document_id",
        "document_version_id",
    ]
    assert fake_client.upserted_ids[0] == fake_client.upserted_ids[1]


def test_scope_filter_always_contains_tenant_and_workspace() -> None:
    scope = build_scope_filter(
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        document_ids=["document-1"],
    )
    conditions = cast(list[models.FieldCondition], scope.must)

    assert [condition.key for condition in conditions] == [
        "tenant_id",
        "workspace_id",
        "document_id",
    ]


def test_dense_search_applies_scope_and_active_version_filters() -> None:
    settings = Settings(
        _env_file=None,
        qdrant_url="https://example.qdrant.io",
        qdrant_api_key=SecretStr("test-key"),
        qdrant_collection="test-collection",
    )
    fake_client = FakeQdrantClient()
    gateway = QdrantGateway(settings, client=cast(QdrantClient, fake_client))

    matches = gateway.search_dense(
        query_vector=[1.0, 0.0],
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        document_version_ids=["version-1"],
        limit=8,
        score_threshold=0.35,
    )

    assert matches[0].payload["text"] == "Authorized evidence"
    assert fake_client.query_kwargs is not None
    query_filter = fake_client.query_kwargs["query_filter"]
    conditions = cast(list[models.FieldCondition], query_filter.must)
    assert [condition.key for condition in conditions] == [
        "tenant_id",
        "workspace_id",
        "document_version_id",
    ]
