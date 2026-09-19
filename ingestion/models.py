"""Immutable values passed through the ingestion pipeline."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class ValidatedUpload:
    display_name: str
    file_extension: str
    media_type: str
    content_hash: str
    byte_size: int


@dataclass(frozen=True, slots=True)
class ParsedSection:
    text: str
    page_number: int | None = None
    section_path: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ParsedDocument:
    title: str
    sections: tuple[ParsedSection, ...]
    page_count: int | None
    parser_version: str


@dataclass(frozen=True, slots=True)
class DocumentChunk:
    chunk_id: str
    text: str
    content_hash: str
    chunk_index: int
    page_start: int | None
    page_end: int | None
    section_path: tuple[str, ...]
    payload: dict[str, object]
