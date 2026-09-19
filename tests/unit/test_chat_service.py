"""Grounded chat orchestration tests without external model calls."""

from collections.abc import Sequence
from typing import cast

from app.config import Settings
from domain.documents import DocumentStatus
from domain.retrieval import RetrievedChunk
from rag.generation import AnswerGenerator
from rag.models import AnswerClaim, GroundedAnswer
from rag.retriever import DenseRetriever
from rag.service import GroundedChatService
from storage.metadata import DEMO_TENANT_ID, DEMO_WORKSPACE_ID, Database
from storage.repositories import DocumentRepository


class FakeRetriever:
    def __init__(self) -> None:
        self.version_ids: Sequence[str] = []

    def retrieve(
        self,
        *,
        question: str,
        tenant_id: str,
        workspace_id: str,
        document_version_ids: Sequence[str],
    ) -> list[RetrievedChunk]:
        self.version_ids = document_version_ids
        return [
            RetrievedChunk(
                chunk_id="chunk-1",
                score=0.92,
                payload={
                    "document_version_id": document_version_ids[0],
                    "document_version_number": 1,
                    "filename": "policy.txt",
                    "title": "Policy",
                    "page_start": None,
                    "page_end": None,
                    "section_path": [],
                    "text": "Remote work is available three days per week.",
                    "content_hash": "hash-1",
                },
            )
        ]


class FakeGenerator:
    def generate(self, *, question: str, context: str) -> GroundedAnswer:
        assert "[S1]" in context
        return GroundedAnswer(
            answer="Remote work is available three days per week [S1].",
            claims=[
                AnswerClaim(
                    text="Remote work is available three days per week.",
                    citation_ids=["S1"],
                )
            ],
            citation_ids=["S1"],
            insufficient_context=False,
        )


def test_chat_uses_only_active_versions_and_returns_validated_sources(
    database: Database, test_settings: Settings
) -> None:
    with database.session() as session:
        repository = DocumentRepository(session)
        document = repository.create(
            tenant_id=DEMO_TENANT_ID,
            workspace_id=DEMO_WORKSPACE_ID,
            display_name="policy.txt",
            created_by="demo-user",
        )
        version = repository.add_version(
            document=document,
            content_hash="a" * 64,
            storage_key="tenant/document/version/original",
            media_type="text/plain",
            byte_size=100,
            parser_version="test",
            chunking_version="test",
            embedding_model="test-model",
        )
        document.status = DocumentStatus.READY
        document.active_version_id = version.id
        version.status = DocumentStatus.READY
        active_version_id = version.id

    retriever = FakeRetriever()
    service = GroundedChatService(
        settings=test_settings,
        database=database,
        retriever=cast(DenseRetriever, retriever),
        generator=cast(AnswerGenerator, FakeGenerator()),
    )

    result = service.ask(
        question="How many remote-work days are available?",
        tenant_id=DEMO_TENANT_ID,
        workspace_id=DEMO_WORKSPACE_ID,
    )

    assert retriever.version_ids == [active_version_id]
    assert result.insufficient_context is False
    assert result.sources[0].source_id == "S1"


def test_chat_abstains_when_no_documents_are_ready(
    database: Database, test_settings: Settings
) -> None:
    service = GroundedChatService(
        settings=test_settings,
        database=database,
        retriever=cast(DenseRetriever, FakeRetriever()),
        generator=cast(AnswerGenerator, FakeGenerator()),
    )

    result = service.ask(
        question="What is the policy?",
        tenant_id=DEMO_TENANT_ID,
        workspace_id=DEMO_WORKSPACE_ID,
    )

    assert result.insufficient_context is True
    assert result.sources == ()
