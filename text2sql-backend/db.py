import sqlite3
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from errors import DuplicateError
from models import (
    Conversation,
    ConversationWithMessagesWithResults,
    MessageWithResults,
    Result,
    Session,
    TableSchema,
    TableSchemaField,
    UnsavedResult,
)

# Old way of using database - this is a single connection, hard to manage transactions
conn = sqlite3.connect("db.sqlite3", check_same_thread=False)


class DatabaseManager:
    def __init__(self, db_file="db.sqlite3"):
        self.db_file = db_file
        self.connection = None

    def __enter__(self):
        self.connection = sqlite3.connect(self.db_file)
        return self.connection

    def __exit__(self, exc_type, exc_value, traceback):
        if self.connection:
            self.connection.close()


# SESSIONS: Create table to store session_id and dsn with unique constraint on session_id and dsn and not null
conn.execute(
    """CREATE TABLE IF NOT EXISTS sessions (
        session_id text PRIMARY KEY,
        dsn text UNIQUE NOT NULL,
        database text NOT NULL,
        name text,
        dialect text,
        UNIQUE (session_id, dsn))"""
)

# SCHEMA TABLE: Create table to store table names in the schema with a reference to a session
conn.execute(
    """CREATE TABLE IF NOT EXISTS schema_tables (
    session_id text NOT NULL,
    id text PRIMARY KEY,
    name text NOT NULL,
    description text NOT NULL,
    FOREIGN KEY(session_id) REFERENCES sessions(session_id))"""
)

# SCHEMA FIELDS: Create table to store a reference to a table schema, table reference, field name, field type ('table' or 'field'), and a field description (text) with a reference to a session
conn.execute(
    """CREATE TABLE IF NOT EXISTS schema_fields (id text PRIMARY KEY,
    table_id text NOT NULL,
    name text NOT NULL,
    type text NOT NULL,
    description text NOT NULL,
    is_primary_key boolean NOT NULL DEFAULT 0,
    is_foreign_key boolean NOT NULL DEFAULT 0,
    foreign_table text NOT NULL DEFAULT '',
    FOREIGN KEY(table_id) REFERENCES schema_tables(table_id))"""
)

# MESSAGES: Create table to store messages with text, role, and session_id
conn.execute(
    """CREATE TABLE IF NOT EXISTS messages (message_id integer PRIMARY KEY AUTOINCREMENT, content text NOT NULL, role text NOT NULL, created_at text, selected_tables text NOT NULL DEFAULT '')"""
)

# RESULTS: Create table to store results with a result text field with a reference to a session
conn.execute(
    """CREATE TABLE IF NOT EXISTS results (result_id integer PRIMARY KEY AUTOINCREMENT, content text NOT NULL, type text NOT NULL, created_at text, is_saved BOOLEAN DEFAULT FALSE)"""
)


# MESSAGE_RESULTS: Create many to many table to store message with multiple results
conn.execute(
    """CREATE TABLE IF NOT EXISTS message_results (message_id integer NOT NULL, result_id integer NOT NULL, FOREIGN KEY(message_id) REFERENCES messages(message_id), FOREIGN KEY(result_id) REFERENCES results(result_id))"""
)

# CONVERSATIONS: Create table to store conversations with a reference to a session, and many results, and a datetime field
conn.execute(
    """CREATE TABLE IF NOT EXISTS conversations (conversation_id integer PRIMARY KEY AUTOINCREMENT, session_id text NOT NULL, name text NOT NULL, created_at text, FOREIGN KEY(session_id) REFERENCES sessions(session_id))"""
)

# CONVERSATION_MESSAGES: Create many to many table to store conversation with multiple messages with order
conn.execute(
    """CREATE TABLE IF NOT EXISTS conversation_messages (conversation_id integer NOT NULL, message_id integer NOT NULL, FOREIGN KEY(conversation_id) REFERENCES conversations(conversation_id), FOREIGN KEY(message_id) REFERENCES messages(message_id))"""
)


def create_session(
    conn: sqlite3.Connection,
    dsn: str,
    database: str,
    name: str = "",
    dialect: str = "",
) -> str:
    # Check if session_id or dsn already exist
    session_id = uuid4().hex

    conn.execute(
        "INSERT INTO sessions VALUES (?, ?, ?, ?, ?)",
        (session_id, dsn, database, name, dialect),
    )
    return session_id


def get_session(conn: sqlite3.Connection, session_id: str):
    session = conn.execute(
        "SELECT session_id, name, dsn, database, dialect FROM sessions WHERE session_id = ?",
        (session_id,),
    ).fetchone()
    if not session:
        raise Exception("Session not found")

    return Session(
        session_id=session[0],
        name=session[1],
        dsn=session[2],
        database=session[3],
        dialect=session[4],
    )


def update_session(session_id: str, name: str, dsn: str, database: str, dialect: str):
    conn.execute(
        "UPDATE sessions SET name = ?, dsn = ?, database = ?, dialect = ? WHERE session_id = ?",
        (name, dsn, database, dialect, session_id),
    )
    conn.commit()
    return True


def get_session_from_dsn(dsn: str):
    return conn.execute("SELECT * FROM sessions WHERE dsn = ?", (dsn,)).fetchone()


def get_sessions():
    return [
        Session(session_id=x[0], name=x[1], dsn=x[2], database=x[3], dialect=x[4])
        for x in conn.execute(
            "SELECT session_id, name, dsn, database, dialect FROM sessions"
        ).fetchall()
    ]


def exists_schema_table(session_id: str):
    result = conn.execute(
        "SELECT * FROM schema_tables WHERE session_id = ?", (session_id,)
    ).fetchone()
    if result:
        return True
    return False


def create_schema_table(conn: sqlite3.Connection, session_id: str, table_name: str):
    """Creates a table schema for a session"""
    # Check if table already exists
    if conn.execute(
        "SELECT * FROM schema_tables WHERE session_id = ? AND name = ?",
        (session_id, table_name),
    ).fetchone():
        raise DuplicateError("Table already exists")

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
                "SELECT results.result_id, content, type, created_at, is_saved FROM results INNER JOIN message_results ON results.result_id = message_results.result_id WHERE message_results.message_id = ?",
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
    # Get is_saved
    is_saved = conn.execute(
        "SELECT is_saved FROM results WHERE result_id = ?", (result_id,)
    ).fetchone()[0]
    # Toggle is_saved
    conn.execute(
        "UPDATE results SET is_saved = ? WHERE result_id = ?",
        (not is_saved, result_id),
    )
    conn.commit()
    return not is_saved


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
            "SELECT result_id, content, type, created_at, is_saved FROM results WHERE result_id IN (SELECT result_id FROM message_results WHERE message_id = ?)",
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
