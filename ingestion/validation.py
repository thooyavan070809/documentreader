"""Upload validation based on size, extension, MIME type, and file signature."""

from __future__ import annotations

import hashlib
import re
from pathlib import PurePath

from ingestion.models import ValidatedUpload

_ALLOWED_MEDIA_TYPES = {
    ".pdf": {"application/pdf", "application/octet-stream"},
    ".txt": {"text/plain", "application/octet-stream"},
}
_CONTROL_CHARACTERS = re.compile(r"[\x00-\x1f\x7f]")


class UploadValidationError(ValueError):
    """A safe, actionable upload error suitable for presentation to a user."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(message)
        self.code = code


def sanitize_display_name(filename: str) -> str:
    leaf_name = re.split(r"[\\/]", filename)[-1]
    cleaned = _CONTROL_CHARACTERS.sub("", leaf_name).strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if not cleaned:
        raise UploadValidationError("invalid_filename", "The file name is empty or invalid.")
    return cleaned[:255]


def detect_text_encoding(content: bytes) -> str:
    if content.startswith(b"\xef\xbb\xbf"):
        return "utf-8-sig"
    if content.startswith((b"\xff\xfe", b"\xfe\xff")):
        return "utf-16"
    if b"\x00" in content:
        raise UploadValidationError("invalid_signature", "The text file appears to be binary.")
    try:
        content.decode("utf-8")
    except UnicodeDecodeError as error:
        raise UploadValidationError(
            "unsupported_encoding",
            "Text files must use UTF-8 or include a UTF-16 byte-order mark.",
        ) from error
    return "utf-8"


def validate_upload(
    *,
    filename: str,
    content: bytes,
    claimed_media_type: str | None,
    max_bytes: int,
) -> ValidatedUpload:
    if not content:
        raise UploadValidationError("empty_file", "The uploaded file is empty.")
    if len(content) > max_bytes:
        raise UploadValidationError(
            "file_too_large",
            f"The file exceeds the configured {max_bytes // (1024 * 1024)} MB limit.",
        )

    display_name = sanitize_display_name(filename)
    extension = PurePath(display_name).suffix.lower()
    if extension not in _ALLOWED_MEDIA_TYPES:
        raise UploadValidationError(
            "unsupported_type", "This phase supports PDF and TXT files only."
        )

    media_type = (claimed_media_type or "application/octet-stream").lower().split(";", 1)[0]
    if media_type not in _ALLOWED_MEDIA_TYPES[extension]:
        raise UploadValidationError(
            "mime_mismatch", "The file's reported type does not match its extension."
        )

    if extension == ".pdf":
        if not content.lstrip().startswith(b"%PDF-"):
            raise UploadValidationError(
                "invalid_signature", "The file does not have a valid PDF signature."
            )
    else:
        detect_text_encoding(content)

    return ValidatedUpload(
        display_name=display_name,
        file_extension=extension,
        media_type="application/pdf" if extension == ".pdf" else "text/plain",
        content_hash=hashlib.sha256(content).hexdigest(),
        byte_size=len(content),
    )
