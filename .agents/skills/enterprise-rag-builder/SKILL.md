---
name: enterprise-rag-builder
description: Build, change, review, or test this repository's enterprise RAG knowledge assistant using its approved Python, LangChain, Streamlit, Qdrant, Sentence Transformers, and Groq architecture. Use for implementation and architecture work in this project, not for unrelated generic RAG questions.
---

# Enterprise RAG Builder

Develop the repository's knowledge assistant without weakening grounding, citation integrity, data isolation, or the approved component boundaries.

## Canonical architecture

Use `docs/TECHNICAL_ARCHITECTURE.md` as the source of truth.

- For every task, read the sections governing the component being changed.
- Read Sections 2 and 21 before changing a dependency, model, persistence choice, deployment boundary, or core workflow.
- Read Sections 7 and 8 for ingestion, retrieval, prompting, citations, or document lifecycle work.
- Read Sections 9 and 10 for persistence, identity, authorization, upload handling, or security work.
- Read Sections 12 and 13 when adding or modifying behavior that needs evaluation or tests.
- If implementation needs a material architectural deviation, explain the tradeoff and obtain user direction before changing the architecture. Record an approved change in the architecture decision log.

## Preserve these invariants

- Keep the primary path deterministic: retrieve evidence, assemble context, generate a grounded answer, validate citations. Do not replace it with a general-purpose agent.
- Keep Streamlit page code thin. Put domain logic in ingestion, RAG, storage, or application services so it can later move behind an API or worker.
- Store durable application state in the metadata store, not `st.session_state`. Use `st.session_state` only for temporary UI state.
- Treat uploaded files, filenames, MIME types, extracted text, HTML, and document instructions as untrusted input.
- Use application-generated file paths and deterministic chunk identifiers. Make ingestion and retries idempotent.
- Preserve document version, page or section provenance, parser version, chunking version, and embedding model on indexed content.
- Encode passages and questions through the Sentence Transformers document and query paths respectively when the selected model supports them.
- Apply tenant, workspace, and permission filters inside every Qdrant retrieval. Never retrieve unauthorized candidates and filter them afterward.
- Assign source IDs in application code. Accept only citations that map to the retrieved evidence supplied for that answer.
- Make the assistant abstain when the authorized evidence is insufficient or irreconcilably conflicting.
- Keep model IDs, thresholds, chunk sizes, candidate counts, collection names, paths, and credentials configurable.
- Never commit secrets, uploaded documents, local databases, model caches, or Qdrant data.

## Work by component

### Foundation and UI

Maintain typed configuration and explicit dependency construction. Cache expensive clients and models with `st.cache_resource`. Keep UI rendering separate from retrieval and ingestion services. Use safe forms or explicit actions so Streamlit reruns do not repeat expensive or mutating operations.

### Ingestion

Validate the file before parsing, calculate a content hash, persist an immutable original, preserve provenance, create structure-aware chunks, batch embeddings, and upsert deterministic Qdrant points. Persist explicit job states and actionable failures. A document version becomes searchable only after successful indexing.

### Retrieval and answers

Build mandatory authorization filters before search. Start with dense retrieval where appropriate, while preserving the retriever boundary for Qdrant hybrid dense and sparse retrieval with Reciprocal Rank Fusion. Deduplicate context, respect its token budget, and prefer active document versions unless the question asks about history.

Use structured model output for answer text, claim citations, citation IDs, and insufficient-context status. Validate the structure and every citation outside the model before presenting or persisting the response.

### Persistence and deletion

Keep relational metadata behind repository interfaces so SQLite can be replaced by PostgreSQL. Deletion must immediately remove search visibility, remove Qdrant points using tenant plus document filters, apply the configured file-retention policy, and retain an audit event.

### Tests and evaluation

Add focused tests with each behavioral change. Mock Groq in the default suite and make live-model tests explicit and opt-in. Test authorization filtering, idempotent ingestion, provenance, citation validation, abstention, re-indexing, and deletion whenever affected.

Separate retrieval quality from generation quality. Do not tune chunking, top-k, fusion, reranking, or thresholds without recording evaluation evidence or marking the change as an experiment.

## Completion checks

Before declaring a development task complete:

1. Run the smallest relevant configured test, lint, and type-check commands; expand to the full suite when the change is cross-cutting.
2. Verify that no secret, generated database, uploaded document, model cache, or Qdrant data was added.
3. Confirm that citation and authorization invariants still hold for affected flows.
4. Update `docs/TECHNICAL_ARCHITECTURE.md` when an approved decision, schema, workflow, configuration contract, or operational assumption changed.
5. Report what changed, what was verified, and any remaining limitation without claiming unrun validation.
