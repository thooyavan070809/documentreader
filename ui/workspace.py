"""Visible document and chat workflows shared by Streamlit pages."""

from __future__ import annotations

from typing import Any

import streamlit as st

from ingestion.pipeline import DuplicateUploadError, IngestionProcessingError
from ingestion.validation import UploadValidationError
from storage.metadata import DEMO_TENANT_ID, DEMO_WORKSPACE_ID
from storage.repositories import DocumentRepository
from ui.runtime import Runtime

DEMO_USER_ID = "demo-user"


def render_document_panel(runtime: Runtime) -> None:
    st.subheader("Upload and index")
    st.caption("Supported now: text-based PDF and UTF-8/UTF-16 TXT files.")
    uploaded_file = st.file_uploader(
        "Choose a document",
        type=["pdf", "txt"],
        key="document_upload",
    )
    start_indexing = st.button(
        "Upload and index",
        type="primary",
        disabled=uploaded_file is None,
        use_container_width=True,
    )
    if start_indexing and uploaded_file is not None:
        progress = st.progress(0, text="Starting ingestion")

        def report(message: str, percentage: int) -> None:
            progress.progress(percentage, text=message)

        try:
            result = runtime.ingestion_service().ingest(
                filename=uploaded_file.name,
                content=uploaded_file.getvalue(),
                claimed_media_type=uploaded_file.type,
                tenant_id=DEMO_TENANT_ID,
                workspace_id=DEMO_WORKSPACE_ID,
                uploaded_by=DEMO_USER_ID,
                progress_callback=report,
            )
        except (UploadValidationError, DuplicateUploadError, IngestionProcessingError) as error:
            progress.empty()
            st.error(str(error))
        else:
            progress.progress(100, text="Document is ready")
            st.success(f"Indexed {result.chunk_count} searchable chunks.")

    st.divider()
    st.subheader("Indexed documents")
    with runtime.database.session() as session:
        documents = DocumentRepository(session).list_active(
            tenant_id=DEMO_TENANT_ID,
            workspace_id=DEMO_WORKSPACE_ID,
        )
    if not documents:
        st.info("Upload a document to begin.")
        return
    st.dataframe(
        [
            {
                "Name": document.display_name,
                "Status": document.status,
                "Created": document.created_at,
            }
            for document in documents
        ],
        use_container_width=True,
        hide_index=True,
    )


def _render_source(source: dict[str, Any]) -> None:
    page = source.get("page_start") or "N/A"
    label = f"[{source['source_id']}] {source['filename']} — page {page}"
    with st.expander(label):
        st.caption(f"Retrieval score: {source['score']:.3f}")
        st.text(source["text"])


def render_chat_panel(runtime: Runtime) -> None:
    st.subheader("Ask your documents")
    st.caption("Answers are limited to indexed evidence and include validated sources.")

    with st.form("grounded_question_form", clear_on_submit=True):
        question = st.text_area(
            "Question",
            placeholder="What does the uploaded document say about ...?",
            height=100,
        )
        submitted = st.form_submit_button(
            "Ask",
            type="primary",
            use_container_width=True,
        )

    messages = st.session_state.setdefault("grounded_messages", [])
    if submitted:
        if not question.strip():
            st.warning("Enter a question first.")
        else:
            with st.spinner("Retrieving evidence and generating a grounded answer..."):
                try:
                    result = runtime.chat_service().ask(
                        question=question,
                        tenant_id=DEMO_TENANT_ID,
                        workspace_id=DEMO_WORKSPACE_ID,
                    )
                except Exception:
                    st.error("The question could not be processed. Check provider connectivity.")
                else:
                    messages.append(
                        {
                            "question": question,
                            "answer": result.answer,
                            "sources": [
                                {
                                    "source_id": source.source_id,
                                    "filename": source.filename,
                                    "page_start": source.page_start,
                                    "text": source.text,
                                    "score": source.score,
                                }
                                for source in result.sources
                            ],
                        }
                    )

    if not messages:
        st.info("Index at least one document, then ask a question here.")
        return
    for message in reversed(messages):
        with st.chat_message("user"):
            st.write(message["question"])
        with st.chat_message("assistant"):
            st.write(message["answer"])
            for source in message["sources"]:
                _render_source(source)
