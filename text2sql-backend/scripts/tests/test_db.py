import os
from typing import Generator, List

import pytest
from postgrest import SyncRequestBuilder
from supabase.client import Client

from db import create_connection, get_connection_from_dsn, get_connections
from models import Connection


class TestClient(Client):
    _tables: List[str] = []

    def table(self, table_name: str) -> SyncRequestBuilder:  # type: ignore
        self._tables.append(table_name)
        # Call parent method
        return super().table(table_name)


@pytest.fixture(scope="function")
def supabase() -> Generator[TestClient, None, None]:
    # Load env vars and initialize client
    url = os.getenv("SUPABASE_URL", "")
    public_key = os.getenv("SUPABASE_PUBLIC_KEY", "")
    client = TestClient(url, public_key)

    # Yield client
    yield client

    # Teardown - delete all tables
    table_set_for_deletion = set(client._tables)
    for table_name in table_set_for_deletion:
        client.table(table_name).delete().neq(
            "id", "00000000-0000-0000-0000-000000000000"
        ).execute()


def test_create_session(supabase: TestClient) -> None:
    # Arrange
    dsn = "postgresql://postgres:postgres@localhost:5432/customdb"
    database = "postgres"

    # Act
    session = create_connection(supabase, dsn, database)

    # Assert
    assert session is not None
    data = (
        supabase.table(Connection.Config.table_name)
        .select("*")
        .eq("id", session.id)
        .execute()
    )
    assert len(data.data) == 1
    assert data.data[0] == dict(session)


def test_get_connection_from_dsn(supabase: TestClient) -> None:
    # Arrange
    dsn = "postgresql://postgres:postgres@localhost:5432/customdb"
    database = "postgres"
    session = create_connection(supabase, dsn, database)

    # Act
    result = get_connection_from_dsn(supabase, dsn)

    # Assert
    assert result is not None
    assert result == session.id


def test_get_connections(supabase: TestClient) -> None:
    # Arrange
    dsn = "postgresql://postgres:postgres@localhost:5432/customdb"
    database = "postgres"
    session = create_connection(supabase, dsn, database)

    # Act
    result = get_connections(supabase)

    # Assert
    assert result is not None
    assert len(result) == 1
    assert result[0] == session

