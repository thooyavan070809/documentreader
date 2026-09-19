"""Local original-document storage tests."""

from pathlib import Path

import pytest

from storage.files import LocalFileStore


def test_original_is_stored_under_generated_identifiers(tmp_path: Path) -> None:
    store = LocalFileStore(tmp_path)

    key = store.store_original(
        tenant_id="tenant-1",
        document_id="document-1",
        document_version_id="version-1",
        content=b"source bytes",
    )

    assert key == "tenant-1/document-1/version-1/original"
    assert store.read_original(key) == b"source bytes"


def test_storage_rejects_path_traversal_identifiers(tmp_path: Path) -> None:
    store = LocalFileStore(tmp_path)

    with pytest.raises(ValueError):
        store.store_original(
            tenant_id="../other",
            document_id="document-1",
            document_version_id="version-1",
            content=b"source bytes",
        )
