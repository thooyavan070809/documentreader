# Enterprise Knowledge Assistant

A grounded document question-answering application built with Python, Streamlit, LangChain, Qdrant Cloud, Sentence Transformers, and Groq.

The approved design is documented in [`docs/TECHNICAL_ARCHITECTURE.md`](docs/TECHNICAL_ARCHITECTURE.md).

## Local setup

```powershell
py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
Copy-Item .env.example .env
```

Add the Groq and Qdrant Cloud credentials to `.env`. Never commit that file.

Run the application:

```powershell
streamlit run streamlit_app.py
```

Open `http://localhost:8502`. The project configures port `8502` in
`.streamlit/config.toml`.

Run the Vercel web experience locally:

```powershell
uvicorn server:app --reload --port 8503
```

Open `http://localhost:8503`. Deployment requirements are documented in
[`docs/VERCEL_DEPLOYMENT.md`](docs/VERCEL_DEPLOYMENT.md).

Run quality checks:

```powershell
pytest
ruff check .
mypy app domain ingestion rag storage ui
```

The application starts without provider credentials. Provider-backed operations remain unavailable until valid keys are configured.

## Current implementation

- Typed configuration with placeholder-safe Groq and Qdrant readiness checks.
- SQLite metadata schema, tenant/workspace scoping, document versioning, and audit events.
- PDF/TXT file validation, signature inspection, parsing, hashing, and deterministic chunk IDs.
- Application-owned original-file storage paths that never use a user-provided filename.
- A visible Streamlit upload workflow with durable ingestion status and duplicate detection.
- Lazy, normalized Sentence Transformer document/query embeddings.
- Idempotent Qdrant indexing and dense retrieval with tenant, workspace, and active-version filters.
- Groq structured answer generation, explicit abstention, and application-validated citations.
- Source cards containing the exact retrieved passage and document/page provenance.

The first upload downloads the configured embedding model, so it can take longer than later uploads.
DOCX/Markdown/HTML support, document deletion/retry controls, persistent conversations, and hybrid
retrieval remain planned follow-up work.
