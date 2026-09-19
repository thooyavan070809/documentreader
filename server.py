"""Single-origin FastAPI entrypoint for the Vercel web experience."""

from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from app.config import get_settings
from app.dependencies import get_chat_service, get_database, get_ingestion_service
from ingestion.pipeline import DuplicateUploadError, IngestionProcessingError
from ingestion.validation import UploadValidationError
from storage.metadata import DEMO_TENANT_ID, DEMO_WORKSPACE_ID
from storage.repositories import DocumentRepository

WEB_ROOT = Path(__file__).parent / "web"
PUBLIC_UPLOAD_LIMIT_BYTES = 4 * 1024 * 1024

app = FastAPI(
    title="Enterprise Knowledge Assistant API",
    version="0.2.0",
    docs_url="/api/docs",
    openapi_url="/api/openapi.json",
)


class QuestionRequest(BaseModel):
    question: str = Field(min_length=1, max_length=4000)


@app.get("/api/health")
def health() -> dict[str, object]:
    settings = get_settings()
    return {
        "status": (
            "ready"
            if settings.groq_configured and settings.qdrant_configured
            else "configuration_required"
        ),
        "groq_configured": settings.groq_configured,
        "qdrant_configured": settings.qdrant_configured,
        "embedding_model": settings.embedding_model,
    }


@app.get("/api/documents")
def list_documents() -> dict[str, object]:
    with get_database().session() as session:
        documents = DocumentRepository(session).list_active(
            tenant_id=DEMO_TENANT_ID,
            workspace_id=DEMO_WORKSPACE_ID,
        )
        items = [
            {
                "id": document.id,
                "name": document.display_name,
                "status": document.status,
                "created_at": document.created_at.isoformat(),
            }
            for document in documents
        ]
    return {"documents": items}


@app.post("/api/documents", status_code=201)
async def upload_document(file: Annotated[UploadFile, File()]) -> dict[str, object]:
    content = await file.read(PUBLIC_UPLOAD_LIMIT_BYTES + 1)
    if len(content) > PUBLIC_UPLOAD_LIMIT_BYTES:
        raise HTTPException(
            status_code=413,
            detail="Public web uploads are limited to 4 MB.",
        )
    try:
        result = get_ingestion_service().ingest(
            filename=file.filename or "document",
            content=content,
            claimed_media_type=file.content_type,
            tenant_id=DEMO_TENANT_ID,
            workspace_id=DEMO_WORKSPACE_ID,
            uploaded_by="public-demo-user",
        )
    except (UploadValidationError, DuplicateUploadError) as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except IngestionProcessingError as error:
        raise HTTPException(status_code=502, detail=str(error)) from error
    return {
        "document_id": result.document_id,
        "status": "ready",
        "chunk_count": result.chunk_count,
    }


@app.post("/api/chat")
def ask_documents(request: QuestionRequest) -> dict[str, object]:
    try:
        result = get_chat_service().ask(
            question=request.question,
            tenant_id=DEMO_TENANT_ID,
            workspace_id=DEMO_WORKSPACE_ID,
        )
    except ValueError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    except Exception as error:
        raise HTTPException(
            status_code=502,
            detail="The grounded answer service is temporarily unavailable.",
        ) from error
    return {
        "answer": result.answer,
        "insufficient_context": result.insufficient_context,
        "sources": [
            {
                "source_id": source.source_id,
                "filename": source.filename,
                "title": source.title,
                "page_start": source.page_start,
                "section_path": list(source.section_path),
                "text": source.text,
                "score": source.score,
            }
            for source in result.sources
        ],
    }


@app.get("/")
def index() -> FileResponse:
    return FileResponse(WEB_ROOT / "index.html")


app.mount("/static", StaticFiles(directory=WEB_ROOT), name="static")
