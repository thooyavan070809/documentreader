"""Structured evidence and answer contracts."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import BaseModel, Field


@dataclass(frozen=True, slots=True)
class SourceEvidence:
    source_id: str
    chunk_id: str
    document_version_id: str
    filename: str
    title: str
    document_version_number: int
    page_start: int | None
    page_end: int | None
    section_path: tuple[str, ...]
    text: str
    score: float


class AnswerClaim(BaseModel):
    text: str = Field(min_length=1)
    citation_ids: list[str]


class GroundedAnswer(BaseModel):
    answer: str = Field(min_length=1)
    claims: list[AnswerClaim]
    citation_ids: list[str]
    insufficient_context: bool


@dataclass(frozen=True, slots=True)
class AnswerResult:
    answer: str
    sources: tuple[SourceEvidence, ...]
    insufficient_context: bool
