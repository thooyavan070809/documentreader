"""Application-owned local file storage for original documents."""

from __future__ import annotations

import re
from pathlib import Path

_SAFE_IDENTIFIER = re.compile(r"^[A-Za-z0-9_-]{1,128}$")


class LocalFileStore:
    def __init__(self, root: Path) -> None:
        self.root = root.resolve()

    @staticmethod
    def _check_identifier(value: str) -> str:
        if not _SAFE_IDENTIFIER.fullmatch(value):
            raise ValueError(
                "Storage identifiers may contain letters, numbers, hyphens, and underscores."
            )
        return value

    def _original_path(
        self, *, tenant_id: str, document_id: str, document_version_id: str
    ) -> Path:
        parts = (
            self._check_identifier(tenant_id),
            self._check_identifier(document_id),
            self._check_identifier(document_version_id),
        )
        path = self.root.joinpath(*parts, "original").resolve()
        path.relative_to(self.root)
        return path

    def store_original(
        self,
        *,
        tenant_id: str,
        document_id: str,
        document_version_id: str,
        content: bytes,
    ) -> str:
        target = self._original_path(
            tenant_id=tenant_id,
            document_id=document_id,
            document_version_id=document_version_id,
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        temporary = target.with_name("original.uploading")
        temporary.write_bytes(content)
        temporary.replace(target)
        return target.relative_to(self.root).as_posix()

    def read_original(self, storage_key: str) -> bytes:
        path = (self.root / storage_key).resolve()
        path.relative_to(self.root)
        return path.read_bytes()
