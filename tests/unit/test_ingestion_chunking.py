"""Parsing and deterministic chunk construction tests."""

from datetime import UTC, datetime

from ingestion.chunking import build_chunks
from ingestion.loaders import load_document
from ingestion.models import ParsedDocument, ParsedSection
from ingestion.validation import validate_upload


def test_text_loading_and_chunking_is_deterministic() -> None:
    content = ("Evidence must remain traceable to its source. " * 12).encode()
    upload = validate_upload(
        filename="policy.txt",
        content=content,
        claimed_media_type="text/plain",
        max_bytes=10_000,
    )
    document = load_document(upload, content)
    arguments = {
        "document": document,
        "upload": upload,
        "tenant_id": "tenant-1",
        "workspace_id": "workspace-1",
        "document_id": "document-1",
        "document_version_id": "version-1",
        "document_version_number": 1,
        "uploaded_by": "user@example.com",
        "embedding_model": "BAAI/bge-base-en-v1.5",
        "chunk_size_tokens": 20,
        "chunk_overlap_tokens": 5,
        "created_at": datetime(2026, 1, 1, tzinfo=UTC),
    }

    first = build_chunks(**arguments)
    second = build_chunks(**arguments)

    assert len(first) > 1
    assert [chunk.chunk_id for chunk in first] == [chunk.chunk_id for chunk in second]
    assert [chunk.chunk_index for chunk in first] == list(range(len(first)))
    assert all(chunk.payload["tenant_id"] == "tenant-1" for chunk in first)


def test_chunks_never_cross_page_boundaries() -> None:
    upload = validate_upload(
        filename="source.txt",
        content=b"placeholder",
        claimed_media_type="text/plain",
        max_bytes=1024,
    )
    document = ParsedDocument(
        title="Source",
        sections=(
            ParsedSection(text="first page evidence " * 10, page_number=1),
            ParsedSection(text="second page evidence " * 10, page_number=2),
        ),
        page_count=2,
        parser_version="test-v1",
    )

    chunks = build_chunks(
        document=document,
        upload=upload,
        tenant_id="tenant-1",
        workspace_id="workspace-1",
        document_id="document-1",
        document_version_id="version-1",
        document_version_number=1,
        uploaded_by="user@example.com",
        embedding_model="test-model",
        chunk_size_tokens=8,
        chunk_overlap_tokens=2,
    )

    assert {chunk.page_start for chunk in chunks} == {1, 2}
    assert all(chunk.page_start == chunk.page_end for chunk in chunks)
    assert all(not ("first" in chunk.text and "second" in chunk.text) for chunk in chunks)
