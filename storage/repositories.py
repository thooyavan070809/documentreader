"""Repository interfaces that keep domain operations independent from SQLite."""

from __future__ import annotations

from datetime import UTC, datetime

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from domain.documents import DocumentStatus
from storage.models import AuditEvent, Document, DocumentVersion, IngestionJob


class DocumentRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(
        self,
        *,
        tenant_id: str,
        workspace_id: str,
        display_name: str,
        created_by: str,
    ) -> Document:
        document = Document(
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            display_name=display_name,
            created_by=created_by,
            status=DocumentStatus.UPLOADED,
        )
        self.session.add(document)
        self.session.flush()
        return document

    def get_authorized(
        self, *, document_id: str, tenant_id: str, workspace_id: str
    ) -> Document | None:
        statement = select(Document).where(
            Document.id == document_id,
            Document.tenant_id == tenant_id,
            Document.workspace_id == workspace_id,
            Document.deleted_at.is_(None),
        )
        return self.session.scalar(statement)

    def list_active(self, *, tenant_id: str, workspace_id: str) -> list[Document]:
        statement = (
            select(Document)
            .where(
                Document.tenant_id == tenant_id,
                Document.workspace_id == workspace_id,
                Document.deleted_at.is_(None),
            )
            .order_by(Document.created_at.desc())
        )
        return list(self.session.scalars(statement))

    def find_duplicate_version(
        self, *, tenant_id: str, workspace_id: str, content_hash: str
    ) -> DocumentVersion | None:
        statement = (
            select(DocumentVersion)
            .join(Document, Document.id == DocumentVersion.document_id)
            .where(
                Document.tenant_id == tenant_id,
                Document.workspace_id == workspace_id,
                Document.deleted_at.is_(None),
                DocumentVersion.content_hash == content_hash,
            )
            .order_by(DocumentVersion.created_at.desc())
        )
        return self.session.scalar(statement)

    def list_active_version_ids(self, *, tenant_id: str, workspace_id: str) -> list[str]:
        statement = select(Document.active_version_id).where(
            Document.tenant_id == tenant_id,
            Document.workspace_id == workspace_id,
            Document.deleted_at.is_(None),
            Document.active_version_id.is_not(None),
            Document.status == DocumentStatus.READY,
        )
        return [version_id for version_id in self.session.scalars(statement) if version_id]

    def add_version(
        self,
        *,
        document: Document,
        content_hash: str,
        storage_key: str,
        media_type: str,
        byte_size: int,
        parser_version: str,
        chunking_version: str,
        embedding_model: str,
    ) -> DocumentVersion:
        latest = self.session.scalar(
            select(func.max(DocumentVersion.version_number)).where(
                DocumentVersion.document_id == document.id
            )
        )
        version = DocumentVersion(
            document_id=document.id,
            version_number=(latest or 0) + 1,
            content_hash=content_hash,
            storage_key=storage_key,
            media_type=media_type,
            byte_size=byte_size,
            parser_version=parser_version,
            chunking_version=chunking_version,
            embedding_model=embedding_model,
            status=DocumentStatus.UPLOADED,
        )
        self.session.add(version)
        self.session.flush()
        return version

    def soft_delete(self, *, document: Document, actor_id: str) -> None:
        document.status = DocumentStatus.DELETED
        document.deleted_at = datetime.now(UTC)
        self.session.add(
            AuditEvent(
                tenant_id=document.tenant_id,
                actor_id=actor_id,
                action="document.deleted",
                resource_type="document",
                resource_id=document.id,
                details={"workspace_id": document.workspace_id},
            )
        )


class IngestionJobRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def create(self, *, document_version_id: str) -> IngestionJob:
        job = IngestionJob(
            document_version_id=document_version_id,
            status="pending",
            progress=0,
        )
        self.session.add(job)
        self.session.flush()
        return job
