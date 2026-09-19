"""Evidence assembly and source-label tests."""

from domain.retrieval import RetrievedChunk
from rag.context import assemble_evidence, render_context


def test_evidence_is_deduplicated_and_application_labelled() -> None:
    payload = {
        "document_version_id": "version-1",
        "filename": "policy.txt",
        "title": "Policy",
        "document_version_number": 1,
        "page_start": 2,
        "page_end": 2,
        "section_path": ["Remote work"],
        "text": "Three remote days are allowed.",
        "content_hash": "same-hash",
    }
    matches = [
        RetrievedChunk("chunk-1", 0.9, payload),
        RetrievedChunk("chunk-2", 0.8, payload),
    ]

    evidence = assemble_evidence(matches, limit=8)

    assert len(evidence) == 1
    assert evidence[0].source_id == "S1"
    assert "[S1]" in render_context(evidence)
