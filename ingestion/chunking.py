"""Deterministic, provenance-preserving text chunk construction."""

from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from uuid import NAMESPACE_URL, uuid5

from langchain_text_splitters import RecursiveCharacterTextSplitter

from ingestion.models import DocumentChunk, ParsedDocument, ValidatedUpload

CHUNKING_VERSION = "recursive-word-v1"


def _word_count(text: str) -> int:
    return len(text.split())


def build_chunks(
    *,
    document: ParsedDocument,
    upload: ValidatedUpload,
    tenant_id: str,
    workspace_id: str,
    document_id: str,
    document_version_id: str,
    document_version_number: int,
    uploaded_by: str,
    embedding_model: str,
    chunk_size_tokens: int,
    chunk_overlap_tokens: int,
    created_at: datetime | None = None,
) -> list[DocumentChunk]:
    if chunk_size_tokens <= 0:
        raise ValueError("chunk_size_tokens must be positive")
    if not 0 <= chunk_overlap_tokens < chunk_size_tokens:
        raise ValueError("chunk_overlap_tokens must be smaller than chunk_size_tokens")

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size_tokens,
        chunk_overlap=chunk_overlap_tokens,
        length_function=_word_count,
        separators=["\n\n", "\n", ". ", " ", ""],
        keep_separator=True,
        strip_whitespace=True,
    )
    timestamp = (created_at or datetime.now(UTC)).isoformat()
    chunks: list[DocumentChunk] = []

    for section in document.sections:
        for text in splitter.split_text(section.text):
            normalized = text.strip()
            if not normalized:
                continue
            index = len(chunks)
            content_hash = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
            identity = f"{tenant_id}:{document_version_id}:{index}:{content_hash}"
            chunk_id = str(uuid5(NAMESPACE_URL, identity))
            payload: dict[str, object] = {
                "tenant_id": tenant_id,
                "workspace_id": workspace_id,
                "document_id": document_id,
                "document_version_id": document_version_id,
                "document_version_number": document_version_number,
                "chunk_id": chunk_id,
                "filename": upload.display_name,
                "file_type": upload.file_extension.removeprefix("."),
                "title": document.title,
                "section_path": list(section.section_path),
                "page_start": section.page_number,
                "page_end": section.page_number,
                "chunk_index": index,
                "text": normalized,
                "content_hash": content_hash,
                "uploaded_by": uploaded_by,
                "created_at": timestamp,
                "embedding_model": embedding_model,
                "parser_version": document.parser_version,
                "chunking_version": CHUNKING_VERSION,
            }
            chunks.append(
                DocumentChunk(
                    chunk_id=chunk_id,
                    text=normalized,
                    content_hash=content_hash,
                    chunk_index=index,
                    page_start=section.page_number,
                    page_end=section.page_number,
                    section_path=section.section_path,
                    payload=payload,
                )
            )
    return chunks
