"""Persistent ingestion workflow tests with provider calls replaced by a fake."""

from pathlib import Path
from typing import cast

import pytest

from app.config import Settings
from domain.documents import DocumentStatus, IngestionStatus
from ingestion.indexing import ChunkIndexer
from ingestion.models import DocumentChunk
from ingestion.pipeline import DuplicateUploadError, IngestionService
from storage.files import LocalFileStore
from storage.metadata import DEMO_TENANT_ID, DEMO_WORKSPACE_ID, Database
from storage.models import Document, IngestionJob


class FakeIndexer:
    def __init__(self) -> None:
        self.chunks: list[DocumentChunk] = []

    def index(self, chunks: list[DocumentChunk]) -> int:
        self.chunks = list(chunks)
        return len(chunks)


def test_ingestion_persists_ready_document_and_rejects_duplicate(
    database: Database, test_settings: Settings, tmp_path: Path
) -> None:
    indexer = FakeIndexer()
    service = IngestionService(
        settings=test_settings,
        database=database,
        file_store=LocalFileStore(tmp_path / "uploads"),
        indexer=cast(ChunkIndexer, indexer),
    )
    content = b"Remote work is available three days per week."

    result = service.ingest(
        filename="policy.txt",
        content=content,
        claimed_media_type="text/plain",
        tenant_id=DEMO_TENANT_ID,
        workspace_id=DEMO_WORKSPACE_ID,
        uploaded_by="demo-user",
    )

    assert result.chunk_count == 1
    assert indexer.chunks[0].payload["tenant_id"] == DEMO_TENANT_ID
    with database.session() as session:
        document = session.get(Document, result.document_id)
        job = session.get(IngestionJob, result.ingestion_job_id)
        assert document is not None
        assert document.status == DocumentStatus.READY
        assert document.active_version_id == result.document_version_id
        assert job is not None
        assert job.status == IngestionStatus.COMPLETED
        assert job.indexed_chunks == 1

    with pytest.raises(DuplicateUploadError):
        service.ingest(
            filename="policy-copy.txt",
            content=content,
            claimed_media_type="text/plain",
            tenant_id=DEMO_TENANT_ID,
            workspace_id=DEMO_WORKSPACE_ID,
            uploaded_by="demo-user",
        )
