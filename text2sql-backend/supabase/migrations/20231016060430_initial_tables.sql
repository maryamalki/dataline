-- CONNECTIONS: Create table to store connections with unique constraint on id and dsn and not null
CREATE TABLE IF NOT EXISTS connections (
    id uuid PRIMARY KEY,
    dsn text UNIQUE NOT NULL,
    database text NOT NULL,
    name text,
    dialect text,
    UNIQUE (id, dsn)
);
-- SCHEMA TABLE: Create table to store table names in the schema with a reference to a session
CREATE TABLE IF NOT EXISTS schema_tables (
    id uuid PRIMARY KEY,
    connection_id uuid NOT NULL,
    name text NOT NULL,
    description text NOT NULL,
    FOREIGN KEY(connection_id) REFERENCES connections(id)
);
-- SCHEMA FIELDS: Create table to store a reference to a table schema, table reference, field name, field type ('table' or 'field'), and a field description (text) with a reference to a session
CREATE TABLE IF NOT EXISTS schema_fields (
    id uuid PRIMARY KEY,
    table_id uuid NOT NULL,
    name text NOT NULL,
    type text NOT NULL,
    description text NOT NULL,
    is_primary_key boolean NOT NULL DEFAULT false,
    is_foreign_key boolean NOT NULL DEFAULT false,
    foreign_table text NOT NULL DEFAULT '',
    FOREIGN KEY(table_id) REFERENCES schema_tables(id)
);
-- MESSAGES: Create table to store messages with text, role, and session_id
CREATE TABLE IF NOT EXISTS messages (
    id uuid PRIMARY KEY,
    content text NOT NULL,
    role text NOT NULL,
    created_at text,
    selected_tables text NOT NULL DEFAULT ''
);
-- RESULTS: Create table to store results with a result text field with a reference to a session
CREATE TABLE IF NOT EXISTS results (
    id uuid PRIMARY KEY,
    content text NOT NULL,
    type text NOT NULL,
    created_at text
);
-- SAVED_QUERIES: Create many to many table to store saved queries with a reference to a result
CREATE TABLE IF NOT EXISTS saved_queries (
    result_id uuid NOT NULL,
    name text,
    description text,
    FOREIGN KEY(result_id) REFERENCES results(id)
);
-- MESSAGE_RESULTS: Create many to many table to store message with multiple results
CREATE TABLE IF NOT EXISTS message_results (
    message_id uuid NOT NULL,
    result_id uuid NOT NULL,
    FOREIGN KEY(message_id) REFERENCES messages(id),
    FOREIGN KEY(result_id) REFERENCES results(id)
);
-- CONVERSATIONS: Create table to store conversations with a reference to a session, and many results, and a datetime field
CREATE TABLE IF NOT EXISTS conversations (
    id uuid PRIMARY KEY,
    connection_id uuid NOT NULL,
    name text NOT NULL,
    created_at text,
    FOREIGN KEY(connection_id) REFERENCES connections(id)
);
-- CONVERSATION_MESSAGES: Create many to many table to store conversation with multiple messages with order
CREATE TABLE IF NOT EXISTS conversation_messages (
    conversation_id uuid NOT NULL,
    message_id uuid NOT NULL,
    FOREIGN KEY(conversation_id) REFERENCES conversations(id),
    FOREIGN KEY(message_id) REFERENCES messages(id)
);