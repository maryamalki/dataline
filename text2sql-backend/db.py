import sqlite3
from datetime import datetime
from typing import Any, List, Optional
from uuid import uuid4

from postgrest.exceptions import APIError

from auth import Client
from errors import DuplicateError, InsertError, NotFoundError, UpdateError
from models import (Connection, Conversation,
                    ConversationWithMessagesWithResults, MessageWithResults,
                    Result, TableSchema, TableSchemaField, UnsavedResult)


def create_connection(
    supabase: Client,
    dsn: str,
    database: str,
    name: str = "",
    dialect: str = "",
) -> Connection:
    # Check if already exists
    data = (
        supabase.table(Connection.Config.table_name)
        .select("id")
        .eq("dsn", dsn)
        .execute()
    )
    if len(data.data) > 0:
        raise DuplicateError("Connection already exists")

    # Create new connection
    connection_id = str(uuid4())
    connection = Connection(
        name=name, database=database, id=connection_id, dsn=dsn, dialect=dialect
    )
    try:
        serialized_session = dict(connection)
        (
            supabase.table(Connection.Config.table_name)
            .insert(serialized_session)
            .execute()
        )
    except APIError as e:
        raise InsertError(e)
    return connection


def get_session(supabase: Client, session_id: str):
    data = supabase.table(Connection.__tablename__).select("*").execute()
    if len(data.data) > 0:
        return Connection(data.data[0])

    raise NotFoundError("session not found")


def update_connection(
    supabase: Client, connection_id: str, name: str, dsn: str, database: str, dialect: str
) -> None:
    """Updates a session. Raises APIError if update fails."""
    try:
        (
            supabase.table(Connection.Config.table_name)
            .update(dict(name=name, dsn=dsn, database=database, dialect=dialect))
            .eq("id", connection_id)
            .execute()
        )
    except APIError as e:
        raise UpdateError(e.message)


def get_connection_from_dsn(supabase: Client, dsn: str) -> Optional[str]:
    """Returns a connection_id from a dsn"""
    data = supabase.table(Connection.Config.table_name).select("id").eq("dsn", dsn).execute()
    if len(data.data) > 0:
        return str(data.data[0]["id"])
    return None


def get_connections(supabase: Client) -> List[Connection]:
    data = supabase.table(Connection.Config.table_name).select("*").execute()
    return [Connection(**connection) for connection in data.data]


def exists_schema_table(supabase: Client, session_id: str):
    data = (
        supabase.table("schema_tables")
        .select("*")
        .eq("session_id", session_id)
        .execute()
    )
    if len(data.data) > 0:
        return True
    return False


def create_schema_table(supabase: Client, session_id: str, table_name: str):
    """Creates a table schema for a session"""
    # Check if table already exists
    # if conn.execute(
    #     "SELECT * FROM schema_tables WHERE session_id = ? AND name = ?",
    #     (session_id, table_name),
    # ).fetchone():
    #     raise DuplicateError("Table already exists")
    data = (
        supabase.table("schema_tables")
        .select("*")
        .eq("session_id", session_id)
        .eq("name", table_name)
        .execute()
    )

    # Insert table with UUID for ID
    table_id = uuid4().hex
    conn.execute(
        "INSERT INTO schema_tables (id, session_id, name, description) VALUES (?, ?, ?, ?)",
        (table_id, session_id, table_name, ""),
    )
    return table_id


def create_schema_field(
    conn: sqlite3.Connection,
    table_id: str,
    field_name: str,
    field_type: str,
    field_description: str = "",
    is_primary_key: bool = False,
    is_foreign_key: bool = False,
    foreign_table: str = "",
):
    """Creates a field schema for a table"""
    # Check if field already exists
    if conn.execute(
        "SELECT * FROM schema_fields WHERE table_id = ? AND name = ?",
        (table_id, field_name),
    ).fetchone():
        raise DuplicateError("Field already exists")

    # Insert field and return ID of row
    field_id = uuid4().hex
    conn.execute(
        "INSERT INTO schema_fields (id, table_id, name, type, description, is_primary_key, is_foreign_key, foreign_table) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
        (
            field_id,
            table_id,
            field_name,
            field_type,
            field_description,
            is_primary_key,
            is_foreign_key,
            foreign_table,
        ),
    )

    return field_id


def get_table_schemas_with_descriptions(session_id: str):
    # Select all table schemas for a session and then join with schema_descriptions to get the field descriptions
    descriptions = conn.execute(
        """
    SELECT
        schema_tables.id,
        schema_tables.session_id,
        schema_tables.name,
        schema_tables.description,
        schema_fields.id,
        schema_fields.name,
        schema_fields.type,
        schema_fields.description,
        schema_fields.is_primary_key,
        schema_fields.is_foreign_key,
        schema_fields.foreign_table
    FROM schema_tables
    INNER JOIN schema_fields ON schema_tables.id = schema_fields.table_id
    WHERE schema_tables.session_id = ?""",
        (session_id,),
    ).fetchall()

    # Join all the field descriptions for each table into a list of table schemas
    schemas = {}
    for description in descriptions:
        if description[0] not in schemas:
            schemas[description[0]] = []
        schemas[description[0]].append(description)

    # Return a list of TableSchema objects
    return [
        TableSchema(
            session_id=session_id,
            id=table[0][0],
            name=table[0][2],
            description=table[0][3],
            field_descriptions=[
                TableSchemaField(
                    id=field[4],
                    schema_id=field[0],
                    name=field[5],
                    type=field[6],
                    description=field[7],
                    is_primary_key=field[8],
                    is_foreign_key=field[9],
                    linked_table=field[10],
                )
                for field in table
            ],
        )
        for table in schemas.values()
    ]


# def get_schema_table(table_id: str):
#     schema_table = conn.execute(
#         """SELECT id, name, description FROM schema_tables WHERE id = ?""", (table_id,)
#     ).fetchone()

#     return TableSchema(id=schema_table[0])


def update_schema_table_description(
    conn: sqlite3.Connection, table_id: str, description: str
):
    return conn.execute(
        """UPDATE schema_tables SET description = ? WHERE id = ?""",
        (description, table_id),
    )


def update_schema_table_field_description(
    conn: sqlite3.Connection, field_id: str, description: str
):
    # Check
    return conn.execute(
        """UPDATE schema_fields SET description = ? WHERE id = ?""",
        (description, field_id),
    )


def session_is_indexed(session_id):
    return conn.execute(
        "SELECT * FROM schema_indexes WHERE session_id = ?", (session_id,)
    ).fetchone()


def insert_schema_index(session_id, index_file):
    conn.execute("INSERT INTO schema_indexes VALUES (?, ?)", (session_id, index_file))
    conn.commit()


def get_schema_index(session_id):
    return conn.execute(
        "SELECT index_file FROM schema_indexes WHERE session_id = ?", (session_id,)
    ).fetchone()[0]


# Conversation logic
def get_conversation(conversation_id: str) -> Conversation:
    conversation = conn.execute(
        "SELECT conversation_id, session_id, name, created_at FROM conversations WHERE conversation_id = ?",
        (conversation_id,),
    ).fetchone()
    return Conversation(
        conversation_id=str(conversation[0]),
        session_id=conversation[1],
        name=conversation[2],
        created_at=conversation[3],
    )


def get_conversations():
    conversations = conn.execute(
        "SELECT conversation_id, session_id, name, created_at FROM conversations"
    ).fetchall()
    return [
        Conversation(
            conversation_id=conversation[0],
            session_id=conversation[1],
            name=conversation[2],
            created_at=conversation[3],
        )
        for conversation in conversations
    ]


def get_conversations_with_messages_with_results() -> (
    list[ConversationWithMessagesWithResults]
):
    conversations = conn.execute(
        "SELECT conversation_id, session_id, name, created_at FROM conversations ORDER BY created_at DESC"
    ).fetchall()

    conversations_with_messages_with_results = []
    for conversation in conversations:
        conversation_id = conversation[0]
        session_id = conversation[1]
        name = conversation[2]

        messages = conn.execute(
            """
        SELECT messages.message_id, content, role, created_at
        FROM messages
        INNER JOIN conversation_messages ON messages.message_id = conversation_messages.message_id
        WHERE conversation_messages.conversation_id = ?
        ORDER BY messages.created_at ASC""",
            (conversation_id,),
        ).fetchall()

        messages_with_results = []
        for message in messages:
            message_id = message[0]
            content = message[1]
            role = message[2]
            created_at = message[3]
            results = conn.execute(
                "SELECT results.result_id, content, type, created_at, CASE WHEN saved_queries.result_id IS NULL THEN 0 ELSE 1 END AS is_saved FROM results INNER JOIN message_results ON results.result_id = message_results.result_id LEFT JOIN saved_queries ON results.result_id = saved_queries.result_id WHERE message_results.message_id = ?",
                (message_id,),
            ).fetchall()
            results = [
                Result(
                    result_id=result[0],
                    content=result[1],
                    type=result[2],
                    created_at=result[3],
                    is_saved=result[4],
                )
                for result in results
            ]
            messages_with_results.append(
                MessageWithResults(
                    message_id=message_id,
                    content=content,
                    role=role,
                    results=results,
                    created_at=created_at,
                )
            )
        conversations_with_messages_with_results.append(
            ConversationWithMessagesWithResults(
                conversation_id=str(conversation_id),
                created_at=conversation[3],
                session_id=session_id,
                name=name,
                messages=messages_with_results,
            )
        )
    return conversations_with_messages_with_results


def delete_conversation(conversation_id: str):
    """Delete conversation, all associated messages, and all their results"""
    conn.execute(
        "DELETE FROM message_results WHERE message_id IN (SELECT message_id FROM conversation_messages WHERE conversation_id = ?)",
        (conversation_id,),
    )
    conn.execute(
        "DELETE FROM messages WHERE message_id IN (SELECT message_id FROM conversation_messages WHERE conversation_id = ?)",
        (conversation_id,),
    )
    conn.execute(
        "DELETE FROM conversations WHERE conversation_id = ?", (conversation_id,)
    )
    conn.execute(
        "DELETE FROM conversation_messages WHERE conversation_id = ?",
        (conversation_id,),
    )
    conn.commit()


# Create empty converstaion
def create_conversation(session_id: str, name: str) -> int:
    """Creates an empty conversation and returns its id"""
    created_at = datetime.now()
    conversation_id = conn.execute(
        "INSERT INTO conversations (session_id, name, created_at) VALUES (?, ?, ?)",
        (session_id, name, created_at),
    ).lastrowid
    conn.commit()
    return conversation_id


def update_conversation(conversation_id: str, name: str):
    conn.execute(
        "UPDATE conversations SET name = ? WHERE conversation_id = ?",
        (name, conversation_id),
    )
    conn.commit()
    return True


def toggle_save_query(result_id: str):
    # check if result_id exists in saved_queries
    exists = conn.execute(
        "SELECT * FROM saved_queries WHERE result_id = ?", (result_id,)
    ).fetchone()

    if exists:
        conn.execute("DELETE FROM saved_queries WHERE result_id = ?", (result_id,))
        conn.commit()
        return False
    else:
        conn.execute("INSERT INTO saved_queries (result_id) VALUES (?)", (result_id,))
        conn.commit()
        return True


# Add message with results to conversation
def add_message_to_conversation(
    conversation_id: str,
    content: str,
    role: str,
    results: Optional[list[Result]] = [],
    selected_tables: Optional[list[str]] = [],
):
    # Basic validation
    if results and role != "assistant":
        raise ValueError("Only assistant messages can have results")

    # Create message object
    created_at = datetime.now()
    message_id = conn.execute(
        "INSERT INTO messages (content, role, created_at, selected_tables) VALUES (?, ?, ?, ?)",
        (content, role, created_at, ",".join(selected_tables)),
    ).lastrowid

    # Create result objects and update message_results many2many
    for result in results:
        # Insert result type and content
        result_id = conn.execute(
            "INSERT INTO results (content, type, created_at) VALUES (?, ?, ?)",
            (result.content, result.type, created_at),
        ).lastrowid

        # Insert message_id and result_id into message_results table
        conn.execute(
            "INSERT INTO message_results (message_id, result_id) VALUES (?, ?)",
            (message_id, result_id),
        )

    # Insert message_id and conversation_id into conversation_messages table
    conn.execute(
        "INSERT INTO conversation_messages (conversation_id, message_id) VALUES (?, ?)",
        (
            conversation_id,
            message_id,
        ),
    )
    conn.commit()
    return MessageWithResults(
        content=content,
        role=role,
        results=results,
        message_id=message_id,
        created_at=created_at,
    )


def get_messages_with_results(conversation_id: str) -> list[MessageWithResults]:
    # Get all message_ids for conversation
    message_ids = conn.execute(
        "SELECT cm.message_id FROM conversation_messages cm JOIN messages m ON m.message_id=cm.message_id WHERE conversation_id = ? ORDER BY m.created_at ASC",
        (conversation_id,),
    ).fetchall()

    # Get all results for each message_id
    messages = []
    for message_id in message_ids:
        message_id = message_id[0]
        message = conn.execute(
            "SELECT content, role, created_at FROM messages WHERE message_id = ?",
            (message_id,),
        ).fetchone()
        results = conn.execute(
            "SELECT results.result_id, content, type, created_at, CASE WHEN saved_queries.result_id IS NULL THEN 0 ELSE 1 END AS is_saved FROM results LEFT JOIN saved_queries ON results.result_id = saved_queries.result_id WHERE results.result_id IN (SELECT result_id FROM message_results WHERE message_id = ?)",
            (message_id,),
        ).fetchall()
        messages.append(
            MessageWithResults(
                content=message[0],
                results=[
                    Result(
                        result_id=result[0],
                        content=result[1],
                        type=result[2],
                        created_at=result[3],
                        is_saved=result[4],
                    )
                    for result in results
                ],
                role=message[1],
                created_at=message[2],
                message_id=message_id,
                conversation_id=conversation_id,
            )
        )

    return messages


def get_message_history(conversation_id: str) -> list[dict[str, Any]]:
    """Returns the message history of a conversation in OpenAI API format"""
    messages = conn.execute(
        """SELECT content, role, created_at
        FROM messages
        INNER JOIN conversation_messages ON messages.message_id = conversation_messages.message_id
        WHERE conversation_messages.conversation_id = ?
        ORDER BY messages.created_at ASC
        """,
        (conversation_id,),
    )

    return [{"role": message[1], "content": message[0]} for message in messages]


def get_message_history_with_selected_tables_with_sql(conversation_id: str):
    """Returns the message history of a conversation with selected tables as a list"""
    messages = conn.execute(
        """SELECT messages.content, messages.role, messages.created_at, results.content, messages.selected_tables
    FROM messages
    INNER JOIN conversation_messages ON messages.message_id = conversation_messages.message_id
    INNER JOIN message_results ON messages.message_id = message_results.message_id
    INNER JOIN results ON message_results.result_id = results.result_id
    WHERE conversation_messages.conversation_id = ?
    AND results.type = 'sql'
    ORDER BY messages.created_at ASC
    """,
        (conversation_id,),
    )

    return [
        {
            "role": message[1],
            "content": "Selected tables: "
            + message[4]
            + "\n"
            + message[0]
            + "\nSQL: "
            + message[3],
        }
        for message in messages
    ]


def get_message_history_with_sql(conversation_id: str) -> list[dict[str, Any]]:
    """Returns the message history of a conversation with the SQL result encoded inside content in OpenAI API format"""
    messages_with_sql = conn.execute(
        """SELECT messages.content, messages.role, messages.created_at, results.content
    FROM messages
    INNER JOIN conversation_messages ON messages.message_id = conversation_messages.message_id
    INNER JOIN message_results ON messages.message_id = message_results.message_id
    INNER JOIN results ON message_results.result_id = results.result_id
    WHERE conversation_messages.conversation_id = ?
    AND results.type = 'sql'
    ORDER BY messages.created_at ASC
    """,
        (conversation_id,),
    )

    return [
        {"role": message[1], "content": message[0] + "\nSQL: " + message[3]}
        for message in messages_with_sql
    ]


def create_result(result: UnsavedResult) -> Result:
    """Create a result and return it"""
    created_at = datetime.now()
    result_id = conn.execute(
        "INSERT INTO results (content, type, created_at) VALUES (?, ?, ?)",
        (result.content, result.type, created_at),
    ).lastrowid
    conn.commit()

    return Result(
        result_id=result_id,
        content=result.content,
        type=result.type,
        created_at=created_at,
    )
