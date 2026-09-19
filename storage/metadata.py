"""Metadata database lifecycle and transaction boundaries."""

from __future__ import annotations

from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session, sessionmaker

from storage.models import Base, Tenant, Workspace

DEMO_TENANT_ID = "00000000-0000-0000-0000-000000000001"
DEMO_WORKSPACE_ID = "00000000-0000-0000-0000-000000000002"


def _ensure_sqlite_parent(database_url: str) -> None:
    prefix = "sqlite:///"
    if not database_url.startswith(prefix) or database_url.endswith(":memory:"):
        return
    database_path = Path(database_url.removeprefix(prefix))
    database_path.parent.mkdir(parents=True, exist_ok=True)


class Database:
    """Own the SQLAlchemy engine and short-lived session transactions."""

    def __init__(self, database_url: str) -> None:
        _ensure_sqlite_parent(database_url)
        if database_url.startswith("postgresql://"):
            database_url = database_url.replace(
                "postgresql://", "postgresql+psycopg://", 1
            )
        connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
        self.engine: Engine = create_engine(database_url, connect_args=connect_args)
        self._session_factory = sessionmaker(bind=self.engine, expire_on_commit=False)

    def initialize(self) -> None:
        Base.metadata.create_all(self.engine)
        self.ensure_demo_scope()

    def ensure_demo_scope(self) -> None:
        with self.session() as session:
            if session.get(Tenant, DEMO_TENANT_ID) is None:
                session.add(Tenant(id=DEMO_TENANT_ID, name="Demo Tenant"))
            if session.get(Workspace, DEMO_WORKSPACE_ID) is None:
                session.add(
                    Workspace(
                        id=DEMO_WORKSPACE_ID,
                        tenant_id=DEMO_TENANT_ID,
                        name="Default Workspace",
                    )
                )

    @contextmanager
    def session(self) -> Iterator[Session]:
        session = self._session_factory()
        try:
            yield session
            session.commit()
        except Exception:
            session.rollback()
            raise
        finally:
            session.close()

    def ping(self) -> None:
        with self.engine.connect() as connection:
            connection.execute(text("SELECT 1"))

    def dispose(self) -> None:
        self.engine.dispose()
