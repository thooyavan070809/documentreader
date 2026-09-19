"""Convert retrieved chunks into bounded, application-labelled evidence."""

from __future__ import annotations

from domain.retrieval import RetrievedChunk
from rag.models import SourceEvidence


def _optional_int(value: object) -> int | None:
    return value if isinstance(value, int) else None


def _string(value: object, default: str = "") -> str:
    return value if isinstance(value, str) else default


def assemble_evidence(
    matches: list[RetrievedChunk], *, limit: int
) -> list[SourceEvidence]:
    evidence: list[SourceEvidence] = []
    seen_hashes: set[str] = set()
    for match in matches:
        payload = match.payload
        text = _string(payload.get("text")).strip()
        content_hash = _string(payload.get("content_hash"), match.chunk_id)
        if not text or content_hash in seen_hashes:
            continue
        seen_hashes.add(content_hash)
        raw_section_path = payload.get("section_path")
        section_path = (
            tuple(str(item) for item in raw_section_path)
            if isinstance(raw_section_path, list)
            else ()
        )
        version_number = payload.get("document_version_number")
        evidence.append(
            SourceEvidence(
                source_id=f"S{len(evidence) + 1}",
                chunk_id=match.chunk_id,
                document_version_id=_string(payload.get("document_version_id")),
                filename=_string(payload.get("filename"), "Unknown document"),
                title=_string(payload.get("title"), "Untitled"),
                document_version_number=(
                    version_number if isinstance(version_number, int) else 1
                ),
                page_start=_optional_int(payload.get("page_start")),
                page_end=_optional_int(payload.get("page_end")),
                section_path=section_path,
                text=text,
                score=match.score,
            )
        )
        if len(evidence) >= limit:
            break
    return evidence


def render_context(evidence: list[SourceEvidence]) -> str:
    blocks: list[str] = []
    for source in evidence:
        page = str(source.page_start) if source.page_start is not None else "Not available"
        section = " > ".join(source.section_path) or "Not available"
        blocks.append(
            "\n".join(
                (
                    f"[{source.source_id}]",
                    f"Document: {source.filename}",
                    f"Version: {source.document_version_number}",
                    f"Page: {page}",
                    f"Section: {section}",
                    f"Content: {source.text}",
                )
            )
        )
    return "\n\n".join(blocks)
