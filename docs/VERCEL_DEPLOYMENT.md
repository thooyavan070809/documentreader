# Vercel deployment

The public application is a single-origin FastAPI service:

- `/` serves the responsive web interface from `web/`.
- `/api/documents` validates and indexes uploaded PDF/TXT files.
- `/api/chat` runs authorized retrieval, grounded Groq generation, and citation validation.
- `Dockerfile.vercel` packages the API, static frontend, and Sentence Transformers model.

The existing Streamlit application remains available for local development.

## Required Vercel configuration

Create a Vercel project from the GitHub repository. Vercel detects `Dockerfile.vercel` automatically.
Configure these encrypted environment variables for Production and Preview as appropriate:

```text
APP_ENV=production
APP_SECRET_KEY=<long-random-secret>
GROQ_API_KEY=<secret>
GROQ_MODEL=openai/gpt-oss-120b
QDRANT_URL=<cluster-https-url>
QDRANT_API_KEY=<secret>
QDRANT_COLLECTION=enterprise_knowledge
EMBEDDING_MODEL=BAAI/bge-base-en-v1.5
METADATA_DATABASE_URL=<managed-postgresql-url>
```

Do not upload `.env` or paste credentials into GitHub.

## Persistence requirement

The container defaults to SQLite and uploads under `/tmp` only so a disposable preview can start.
Vercel container instances are stateless; this storage is not durable. Before accepting real user data:

1. Provision managed PostgreSQL and set `METADATA_DATABASE_URL`.
2. Add S3-compatible original-document storage and signed browser uploads.
3. Add authentication and map identities to tenant/workspace permissions.
4. Replace the shared demo identity used by the initial public preview.

Until those controls are complete, use non-sensitive demonstration documents only.

## Deployment workflow

1. Commit the repository and push it to GitHub.
2. In Vercel, select **Add New → Project** and import the repository.
3. Add the environment variables above.
4. Enable Fluid Compute. New Vercel projects support larger functions; if the image-size check requests it, add `VERCEL_SUPPORT_LARGE_FUNCTIONS=1` and redeploy.
5. Deploy a Preview first and verify `/api/health`, upload, chat, and source cards.
6. Promote the verified deployment to Production and attach the desired domain.

The first Vercel build is slower because the embedding model is downloaded into the container image.
