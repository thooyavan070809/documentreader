"""Grounded answer citation-validation tests."""

import pytest

from rag.citations import CitationValidationError, validate_citations
from rag.models import AnswerClaim, GroundedAnswer, SourceEvidence


def _source(source_id: str) -> SourceEvidence:
    return SourceEvidence(
        source_id=source_id,
        chunk_id=f"chunk-{source_id}",
        document_version_id="version-1",
        filename="policy.txt",
        title="Policy",
        document_version_number=1,
        page_start=None,
        page_end=None,
        section_path=(),
        text="Remote work is available three days per week.",
        score=0.9,
    )


def test_valid_citations_are_accepted() -> None:
    answer = GroundedAnswer(
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

    assert validate_citations(answer, [_source("S1")]) is answer


def test_fabricated_citation_is_rejected() -> None:
    answer = GroundedAnswer(
        answer="Unsupported claim [S9].",
        claims=[AnswerClaim(text="Unsupported claim.", citation_ids=["S9"])],
        citation_ids=["S9"],
        insufficient_context=False,
    )

    with pytest.raises(CitationValidationError):
        validate_citations(answer, [_source("S1")])


def test_clean_abstention_is_accepted() -> None:
    answer = GroundedAnswer(
        answer="The documents do not contain enough information.",
        claims=[],
        citation_ids=[],
        insufficient_context=True,
    )

    assert validate_citations(answer, [_source("S1")]) is answer
