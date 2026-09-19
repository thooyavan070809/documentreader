"""Application service composition independent of Streamlit pages."""

from functools import lru_cache

from langchain_core.language_models import BaseChatModel

from app.config import Settings, get_settings
from ingestion.embeddings import SentenceTransformerEmbedder
from ingestion.indexing import ChunkIndexer
from ingestion.pipeline import IngestionService
from rag.generation import GroqGroundedGenerator
from rag.retriever import DenseRetriever
from rag.service import GroundedChatService
from storage.files import LocalFileStore
from storage.metadata import Database
from storage.qdrant import QdrantGateway


@lru_cache(maxsize=1)
def get_database() -> Database:
    settings = get_settings()
    database = Database(settings.metadata_database_url)
    database.initialize()
    return database


@lru_cache(maxsize=1)
def get_qdrant_gateway() -> QdrantGateway:
    return QdrantGateway(get_settings())


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformerEmbedder:
    settings = get_settings()
    return SentenceTransformerEmbedder(
        model_name=settings.embedding_model,
        device=settings.embedding_device,
    )


@lru_cache(maxsize=1)
def get_chunk_indexer() -> ChunkIndexer:
    return ChunkIndexer(embedder=get_embedder(), qdrant=get_qdrant_gateway())


@lru_cache(maxsize=1)
def get_file_store() -> LocalFileStore:
    return LocalFileStore(get_settings().upload_root)


@lru_cache(maxsize=1)
def get_ingestion_service() -> IngestionService:
    return IngestionService(
        settings=get_settings(),
        database=get_database(),
        file_store=get_file_store(),
        indexer=get_chunk_indexer(),
    )


def create_groq_chat_model(settings: Settings | None = None) -> BaseChatModel:
    active_settings = settings or get_settings()
    if not active_settings.groq_configured:
        raise RuntimeError("Set GROQ_API_KEY in .env before using Groq.")

    from langchain_groq import ChatGroq

    return ChatGroq(
        api_key=active_settings.groq_api_key,
        model=active_settings.groq_model,
        temperature=0,
    )


@lru_cache(maxsize=1)
def get_chat_service() -> GroundedChatService:
    settings = get_settings()
    retriever = DenseRetriever(
        embedder=get_embedder(),
        qdrant=get_qdrant_gateway(),
        candidate_limit=settings.dense_candidate_limit,
        score_threshold=settings.min_retrieval_score,
    )
    return GroundedChatService(
        settings=settings,
        database=get_database(),
        retriever=retriever,
        generator=GroqGroundedGenerator(create_groq_chat_model(settings)),
    )
