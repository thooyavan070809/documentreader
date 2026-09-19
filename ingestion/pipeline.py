"""Synchronous MVP ingestion workflow with durable state transitions."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from app.config import Settings
from domain.documents import DocumentStatus, IngestionStatus
from ingestion.chunking import CHUNKING_VERSION, build_chunks
from ingestion.indexing import ChunkIndexer
from ingestion.loaders import PARSER_VERSION, load_document
from ingestion.validation import UploadValidationError, validate_upload
from storage.files import LocalFileStore
from storage.metadata import Database
from storage.models import Document, DocumentVersion, IngestionJob
from storage.repositories import DocumentRepository, IngestionJobRepository

ProgressCallback = Callable[[str, int], None]


class DuplicateUploadError(ValueError):
    pass


class IngestionProcessingError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class IngestionResult:
    document_id: str
    document_version_id: str
    ingestion_job_id: str
    chunk_count: int


class IngestionService:
    def __init__(
        self,
        *,
        settings: Settings,
        database: Database,
        file_store: LocalFileStore,
        indexer: ChunkIndexer,
    ) -> None:
        self.settings = settings
        self.database = database
        self.file_store = file_store
        self.indexer = indexer

    @staticmethod
    def _notify(callback: ProgressCallback | None, message: str, progress: int) -> None:
        if callback is not None:
            callback(message, progress)

    @staticmethod
    def _set_processing_state(
        session: Session,
        *,
        document_id: str,
        version_id: str,
        job_id: str,
        status: DocumentStatus,
        job_status: IngestionStatus,
        progress: int,
        page_count: int | None = None,
        expected_chunks: int | None = None,
    ) -> None:
        document = session.get(Document, document_id)
        version = session.get(DocumentVersion, version_id)
        job = session.get(IngestionJob, job_id)
        if document is None or version is None or job is None:
            raise RuntimeError("Ingestion metadata disappeared during processing.")
        document.status = status
        version.status = status
        job.status = job_status
        job.progress = progress
        if job.started_at is None:
            job.started_at = datetime.now(UTC)
        if page_count is not None:
            version.page_count = page_count
        if expected_chunks is not None:
            job.expected_chunks = expected_chunks

    def _mark_failed(
        self, *, document_id: str, version_id: str, job_id: str, error: Exception
    ) -> None:
        with self.database.session() as session:
            document = session.get(Document, document_id)
            version = session.get(DocumentVersion, version_id)
            job = session.get(IngestionJob, job_id)
            if document is not None:
                document.status = DocumentStatus.FAILED
            if version is not None:
                version.status = DocumentStatus.FAILED
            if job is not None:
                job.status = IngestionStatus.FAILED
                job.error_code = type(error).__name__
                job.error_message = str(error)[:1000]
                job.completed_at = datetime.now(UTC)

    def ingest(
        self,
        *,
        filename: str,
        content: bytes,
        claimed_media_type: str | None,
        tenant_id: str,
        workspace_id: str,
        uploaded_by: str,
        progress_callback: ProgressCallback | None = None,
    ) -> IngestionResult:
        self._notify(progress_callback, "Validating upload", 5)
        upload = validate_upload(
            filename=filename,
            content=content,
            claimed_media_type=claimed_media_type,
            max_bytes=self.settings.max_upload_mb * 1024 * 1024,
        )

        with self.database.session() as session:
            documents = DocumentRepository(session)
            duplicate = documents.find_duplicate_version(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                content_hash=upload.content_hash,
            )
            if duplicate is not None:
                raise DuplicateUploadError(
                    "This exact file has already been uploaded to the workspace."
                )
            document = documents.create(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                display_name=upload.display_name,
                created_by=uploaded_by,
            )
            version = documents.add_version(
                document=document,
                content_hash=upload.content_hash,
                storage_key="pending",
                media_type=upload.media_type,
                byte_size=upload.byte_size,
                parser_version=PARSER_VERSION,
                chunking_version=CHUNKING_VERSION,
                embedding_model=self.settings.embedding_model,
            )
            job = IngestionJobRepository(session).create(document_version_id=version.id)
            document_id = document.id
            version_id = version.id
            version_number = version.version_number
            job_id = job.id
            version.storage_key = self.file_store.store_original(
                tenant_id=tenant_id,
                document_id=document_id,
                document_version_id=version_id,
                content=content,
            )

        try:
            self._notify(progress_callback, "Extracting document text", 20)
            with self.database.session() as session:
                self._set_processing_state(
                    session,
                    document_id=document_id,
                    version_id=version_id,
                    job_id=job_id,
                    status=DocumentStatus.PARSING,
                    job_status=IngestionStatus.PARSING,
                    progress=20,
                )
            parsed = load_document(upload, content)

            self._notify(progress_callback, "Creating searchable chunks", 40)
            chunks = build_chunks(
                document=parsed,
                upload=upload,
                tenant_id=tenant_id,
                workspace_id=workspace_id,
                document_id=document_id,
                document_version_id=version_id,
                document_version_number=version_number,
                uploaded_by=uploaded_by,
                embedding_model=self.settings.embedding_model,
                chunk_size_tokens=self.settings.chunk_size_tokens,
                chunk_overlap_tokens=self.settings.chunk_overlap_tokens,
            )
            if not chunks:
                raise UploadValidationError(
                    "no_extractable_text", "No searchable text chunks were produced."
                )
            with self.database.session() as session:
                self._set_processing_state(
                    session,
                    document_id=document_id,
                    version_id=version_id,
                    job_id=job_id,
                    status=DocumentStatus.EMBEDDING,
                    job_status=IngestionStatus.EMBEDDING,
                    progress=55,
                    page_count=parsed.page_count,
                    expected_chunks=len(chunks),
                )

            self._notify(progress_callback, "Embedding and indexing chunks", 60)
            indexed_count = self.indexer.index(chunks)
            if indexed_count != len(chunks):
                raise RuntimeError("Qdrant did not confirm every expected chunk.")

            self._notify(progress_callback, "Finalizing document", 95)
            with self.database.session() as session:
                final_document = session.get(Document, document_id)
                final_version = session.get(DocumentVersion, version_id)
                final_job = session.get(IngestionJob, job_id)
                if final_document is None or final_version is None or final_job is None:
                    raise RuntimeError("Ingestion metadata disappeared during finalization.")
                final_document.status = DocumentStatus.READY
                final_document.active_version_id = version_id
                final_version.status = DocumentStatus.READY
                final_job.status = IngestionStatus.COMPLETED
                final_job.progress = 100
                final_job.indexed_chunks = indexed_count
                final_job.completed_at = datetime.now(UTC)
        except Exception as error:
            self._mark_failed(
                document_id=document_id,
                version_id=version_id,
                job_id=job_id,
                error=error,
            )
            if isinstance(error, UploadValidationError):
                raise
            raise IngestionProcessingError(
                "Document processing failed. Check the document and provider configuration."
            ) from error

        self._notify(progress_callback, "Document is ready", 100)
        return IngestionResult(
            document_id=document_id,
            document_version_id=version_id,
            ingestion_job_id=job_id,
            chunk_count=indexed_count,
        )
