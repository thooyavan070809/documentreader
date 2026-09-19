"""PDF and plain-text loaders that retain provenance boundaries."""

from __future__ import annotations

from pathlib import PurePath

from ingestion.models import ParsedDocument, ParsedSection, ValidatedUpload
from ingestion.validation import UploadValidationError, detect_text_encoding

PARSER_VERSION = "extractable-text-v1"


def _normalize_text(text: str) -> str:
    lines = (line.rstrip() for line in text.replace("\r\n", "\n").replace("\r", "\n").split("\n"))
    return "\n".join(lines).strip()


def _load_pdf(content: bytes, title: str) -> ParsedDocument:
    import pymupdf

    try:
        pdf = pymupdf.open(stream=content, filetype="pdf")
    except Exception as error:
        raise UploadValidationError("pdf_parse_failed", "The PDF could not be opened.") from error

    try:
        if pdf.needs_pass:
            raise UploadValidationError(
                "encrypted_pdf", "Password-protected PDFs are not supported."
            )
        page_count = pdf.page_count
        extracted_sections: list[ParsedSection] = []
        for page_index in range(page_count):
            page: pymupdf.Page = pdf.load_page(page_index)
            text = _normalize_text(page.get_text("text"))
            if text:
                extracted_sections.append(
                    ParsedSection(text=text, page_number=page_index + 1)
                )
        sections = tuple(extracted_sections)
    finally:
        pdf.close()

    if not sections:
        raise UploadValidationError(
            "no_extractable_text",
            "No extractable text was found. Scanned-PDF OCR is planned for a later phase.",
        )
    return ParsedDocument(
        title=title,
        sections=sections,
        page_count=page_count,
        parser_version=PARSER_VERSION,
    )


def _load_text(content: bytes, title: str) -> ParsedDocument:
    encoding = detect_text_encoding(content)
    text = _normalize_text(content.decode(encoding))
    if not text:
        raise UploadValidationError("no_extractable_text", "The text file contains no text.")
    return ParsedDocument(
        title=title,
        sections=(ParsedSection(text=text),),
        page_count=None,
        parser_version=PARSER_VERSION,
    )


def load_document(upload: ValidatedUpload, content: bytes) -> ParsedDocument:
    """Load validated bytes without depending on UI or storage concerns."""
    title = PurePath(upload.display_name).stem
    if upload.file_extension == ".pdf":
        return _load_pdf(content, title)
    if upload.file_extension == ".txt":
        return _load_text(content, title)
    raise UploadValidationError("unsupported_type", "No loader is available for this file type.")
