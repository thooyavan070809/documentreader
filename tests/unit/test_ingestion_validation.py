"""Upload validation tests."""

import pytest

from ingestion.validation import UploadValidationError, validate_upload


def test_valid_text_upload_is_hashed_and_name_is_sanitized() -> None:
    upload = validate_upload(
        filename="../Quarterly  Report.txt",
        content=b"Grounded enterprise knowledge.",
        claimed_media_type="text/plain; charset=utf-8",
        max_bytes=1024,
    )

    assert upload.display_name == "Quarterly Report.txt"
    assert upload.file_extension == ".txt"
    assert len(upload.content_hash) == 64


@pytest.mark.parametrize(
    ("filename", "content", "media_type", "expected_code"),
    [
        ("empty.txt", b"", "text/plain", "empty_file"),
        ("fake.pdf", b"not a pdf", "application/pdf", "invalid_signature"),
        ("binary.txt", b"hello\x00world", "text/plain", "invalid_signature"),
        ("notes.exe", b"hello", "application/octet-stream", "unsupported_type"),
    ],
)
def test_invalid_uploads_are_rejected(
    filename: str, content: bytes, media_type: str, expected_code: str
) -> None:
    with pytest.raises(UploadValidationError) as error:
        validate_upload(
            filename=filename,
            content=content,
            claimed_media_type=media_type,
            max_bytes=1024,
        )

    assert error.value.code == expected_code
