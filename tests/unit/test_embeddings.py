"""Sentence Transformer embedding boundary tests without model downloads."""

from typing import Any

import pytest

from ingestion.embeddings import SentenceTransformerEmbedder


class FakeSentenceTransformer:
    def __init__(self) -> None:
        self.calls: list[tuple[str, list[str], dict[str, Any]]] = []

    def get_sentence_embedding_dimension(self) -> int:
        return 3

    def encode_document(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        self.calls.append(("document", texts, kwargs))
        return [[1.0, 0.0, 0.0] for _ in texts]

    def encode_query(self, texts: list[str], **kwargs: Any) -> list[list[float]]:
        self.calls.append(("query", texts, kwargs))
        return [[0.0, 1.0, 0.0] for _ in texts]


def test_embedder_uses_document_and_query_paths_with_normalization() -> None:
    fake_model = FakeSentenceTransformer()
    loads: list[tuple[str, str]] = []

    def factory(model_name: str, device: str) -> FakeSentenceTransformer:
        loads.append((model_name, device))
        return fake_model

    embedder = SentenceTransformerEmbedder(
        model_name="test-model",
        device="cpu",
        model_factory=factory,
    )

    assert loads == []
    assert embedder.dimension == 3
    assert embedder.embed_documents(["one", "two"]) == [
        [1.0, 0.0, 0.0],
        [1.0, 0.0, 0.0],
    ]
    assert embedder.embed_query("question") == [0.0, 1.0, 0.0]
    assert loads == [("test-model", "cpu")]
    assert [call[0] for call in fake_model.calls] == ["document", "query"]
    assert all(call[2]["normalize_embeddings"] is True for call in fake_model.calls)


def test_embedder_rejects_empty_query() -> None:
    embedder = SentenceTransformerEmbedder(
        model_name="test-model",
        device="cpu",
        model_factory=lambda _name, _device: FakeSentenceTransformer(),
    )

    with pytest.raises(ValueError):
        embedder.embed_query("  ")
