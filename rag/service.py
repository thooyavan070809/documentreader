"""Deterministic retrieve, generate, and validate application service."""

from __future__ import annotations

from dataclasses import dataclass

from app.config import Settings
from rag.citations import CitationValidationError, validate_citations
from rag.context import assemble_evidence, render_context
from rag.generation import AnswerGenerator
from rag.models import AnswerResult
from rag.retriever import DenseRetriever
from storage.metadata import Database
from storage.repositories import DocumentRepository

_NO_EVIDENCE = "I couldn't find sufficient information in the indexed documents."
_INVALID_RESPONSE = "I found relevant passages but could not produce a safely cited answer."


@dataclass(frozen=True, slots=True)
class GroundedChatService:
    settings: Settings
    database: Database
    retriever: DenseRetriever
    generator: AnswerGenerator

    def ask(
        self, *, question: str, tenant_id: str, workspace_id: str
    ) -> AnswerResult:
        normalized_question = question.strip()
        if not normalized_question:
            raise ValueError("Enter a question before submitting.")
        with self.database.session() as session:
            version_ids = DocumentRepository(session).list_active_version_ids(
                tenant_id=tenant_id,
                workspace_id=workspace_id,
            )
        if not version_ids:
            return AnswerResult(_NO_EVIDENCE, (), True)

        matches = self.retriever.retrieve(
            question=normalized_question,
            tenant_id=tenant_id,
            workspace_id=workspace_id,
            document_version_ids=version_ids,
        )
        evidence = assemble_evidence(matches, limit=self.settings.final_context_limit)
        if not evidence:
            return AnswerResult(_NO_EVIDENCE, (), True)

        generated = self.generator.generate(
            question=normalized_question,
            context=render_context(evidence),
        )
        try:
            validated = validate_citations(generated, evidence)
        except CitationValidationError:
            return AnswerResult(_INVALID_RESPONSE, (), True)
        cited_ids = set(validated.citation_ids)
        sources = tuple(source for source in evidence if source.source_id in cited_ids)
        return AnswerResult(
            answer=validated.answer,
            sources=sources,
            insufficient_context=validated.insufficient_context,
        )
