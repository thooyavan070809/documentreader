"""Application-side validation for model-provided citation IDs."""

from __future__ import annotations

import re

from rag.models import GroundedAnswer, SourceEvidence

_INLINE_CITATION = re.compile(r"\[(S\d+)]")


class CitationValidationError(ValueError):
    pass


def validate_citations(
    answer: GroundedAnswer, evidence: list[SourceEvidence]
) -> GroundedAnswer:
    available = {source.source_id for source in evidence}
    declared = set(answer.citation_ids)
    inline = set(_INLINE_CITATION.findall(answer.answer))
    claim_citations = {
        citation_id for claim in answer.claims for citation_id in claim.citation_ids
    }
    referenced = declared | inline | claim_citations

    unknown = referenced - available
    if unknown:
        raise CitationValidationError("The model returned citation IDs outside the evidence set.")
    if answer.insufficient_context:
        if answer.claims or referenced:
            raise CitationValidationError(
                "An insufficient-context answer cannot contain factual claims or citations."
            )
        return answer
    if not answer.claims or not declared:
        raise CitationValidationError("A grounded answer must contain cited claims.")
    if any(not claim.citation_ids for claim in answer.claims):
        raise CitationValidationError("Every material claim must contain a citation.")
    if not claim_citations.issubset(declared):
        raise CitationValidationError("Claim citations must be declared at answer level.")
    return answer
