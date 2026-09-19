"""Lazy Sentence Transformers embedding boundary."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any, Protocol, cast


class EmbeddingProvider(Protocol):
    @property
    def model_id(self) -> str: ...

    @property
    def dimension(self) -> int: ...

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]: ...

    def embed_query(self, text: str) -> list[float]: ...


class SentenceTransformerEmbedder:
    """Load the configured model only when an embedding is first requested."""

    def __init__(
        self,
        *,
        model_name: str,
        device: str,
        model_factory: Callable[[str, str], Any] | None = None,
    ) -> None:
        self._model_name = model_name
        self._device = device
        self._model_factory = model_factory or self._default_factory
        self._model: Any | None = None

    @staticmethod
    def _default_factory(model_name: str, device: str) -> Any:
        from sentence_transformers import SentenceTransformer

        return SentenceTransformer(model_name, device=device)

    @property
    def model_id(self) -> str:
        return self._model_name

    @property
    def model(self) -> Any:
        if self._model is None:
            self._model = self._model_factory(self._model_name, self._device)
        return self._model

    @property
    def dimension(self) -> int:
        dimension = self.model.get_sentence_embedding_dimension()
        if dimension is None or dimension <= 0:
            raise RuntimeError("The embedding model did not report a valid vector dimension.")
        return cast(int, dimension)

    @staticmethod
    def _to_rows(values: Any) -> list[list[float]]:
        raw_rows = values.tolist() if hasattr(values, "tolist") else values
        return [[float(value) for value in row] for row in raw_rows]

    def embed_documents(self, texts: Sequence[str]) -> list[list[float]]:
        if not texts:
            return []
        vectors = self.model.encode_document(
            list(texts),
            batch_size=32,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return self._to_rows(vectors)

    def embed_query(self, text: str) -> list[float]:
        if not text.strip():
            raise ValueError("A retrieval query cannot be empty.")
        vectors = self.model.encode_query(
            [text],
            batch_size=1,
            show_progress_bar=False,
            convert_to_numpy=True,
            normalize_embeddings=True,
        )
        return self._to_rows(vectors)[0]
