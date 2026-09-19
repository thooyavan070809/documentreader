from storage.metadata import DEMO_TENANT_ID, DEMO_WORKSPACE_ID, Database
from storage.models import AuditEvent
from storage.repositories import DocumentRepository


def test_document_repository_scopes_versions_and_soft_deletion(database: Database) -> None:
    with database.session() as session:
        repository = DocumentRepository(session)
        document = repository.create(
            tenant_id=DEMO_TENANT_ID,
            workspace_id=DEMO_WORKSPACE_ID,
            display_name="Policy.pdf",
            created_by="developer@example.com",
        )
        version = repository.add_version(
            document=document,
            content_hash="a" * 64,
            storage_key="demo/document/version/original",
            media_type="application/pdf",
            byte_size=1024,
            parser_version="pymupdf-v1",
            chunking_version="structure-v1",
            embedding_model="BAAI/bge-base-en-v1.5",
        )
        document_id = document.id

        assert version.version_number == 1
        assert repository.get_authorized(
            document_id=document_id,
            tenant_id=DEMO_TENANT_ID,
            workspace_id=DEMO_WORKSPACE_ID,
        ) is document

        repository.soft_delete(document=document, actor_id="developer@example.com")

    with database.session() as session:
        repository = DocumentRepository(session)
        assert repository.list_active(
            tenant_id=DEMO_TENANT_ID,
            workspace_id=DEMO_WORKSPACE_ID,
        ) == []
        assert session.query(AuditEvent).count() == 1
