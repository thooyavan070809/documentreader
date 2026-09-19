from sqlalchemy import inspect

from storage.metadata import DEMO_TENANT_ID, DEMO_WORKSPACE_ID, Database
from storage.models import Tenant, Workspace


def test_database_initialization_creates_schema_and_demo_scope(database: Database) -> None:
    table_names = set(inspect(database.engine).get_table_names())

    assert {"tenants", "workspaces", "documents", "document_versions"} <= table_names
    with database.session() as session:
        assert session.get(Tenant, DEMO_TENANT_ID) is not None
        assert session.get(Workspace, DEMO_WORKSPACE_ID) is not None
