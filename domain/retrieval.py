"""Retrieval results returned by vector storage."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RetrievedChunk:
    chunk_id: str
    score: float
    payload: dict[str, object]
