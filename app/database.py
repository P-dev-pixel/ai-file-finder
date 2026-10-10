import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "file_index.db"


def get_connection():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row

    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                path TEXT NOT NULL UNIQUE,
                extension TEXT NOT NULL,
                size_bytes INTEGER NOT NULL,
                modified_at REAL NOT NULL,
                content TEXT NOT NULL DEFAULT ''
            )
        """)
        columns = connection.execute(
            "PRAGMA table_info(files)"
        ).fetchall()
        
        column_names = {column["name"] for column in columns}
        
        if "content" not in column_names:
            connection.execute(
                "ALTER TABLE files ADD COLUMN content TEXT NOT NULL DEFAULT ''"
            )

        connection.execute("""
            CREATE TABLE IF NOT EXISTS search_roots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                path TEXT NOT NULL UNIQUE
            )
        """)


# Check whether the existing FTS5 table has the content column.
        fts_columns = connection.execute(
             "PRAGMA table_info(file_search)"
).fetchall()

        fts_column_names = {
    column["name"] for column in fts_columns
}

        if "content" not in fts_column_names:
    # Remove the old search index, not the files table.
            connection.execute("DROP TABLE IF EXISTS file_search")

            connection.execute("""
        CREATE VIRTUAL TABLE file_search
        USING fts5(
            name,
            path,
            content,
            content='files',
            content_rowid='id'
        )
    """)

    # Populate the new index from existing file records.
            connection.execute("""
        INSERT INTO file_search(file_search)
        VALUES ('rebuild')
    """)

    print(f"Database ready: {DB_PATH}")
    
    
def search_files(query: str, limit: int = 20, extension: str | None = None):
    fts_query = query.strip()

    if fts_query and " " not in fts_query:
        fts_query = f"{fts_query}*"

    sql = """
        SELECT
            files.id,
            files.name,
            files.path,
            files.extension,
            files.size_bytes,
            files.modified_at,
            bm25(file_search) AS relevance

        FROM file_search

        JOIN files
            ON files.id = file_search.rowid

        WHERE file_search MATCH ?
    """

    parameters = [fts_query]

    if extension:
        sql += " AND files.extension = ?"
        parameters.append(extension.lower())

    sql += """
        ORDER BY relevance
        LIMIT ?
    """

    parameters.append(limit)

    with get_connection() as connection:
        rows = connection.execute(
            sql,
            parameters,
        ).fetchall()

    return rows

def add_search_root(path: str):
    with get_connection() as connection:
        connection.execute(
            """
            INSERT OR IGNORE INTO search_roots (path)
            VALUES (?)
            """,
            (path,),
        )


def get_search_roots():
    with get_connection() as connection:
        rows = connection.execute(
            """
            SELECT id, path 
            FROM search_roots
            ORDER BY path
            """
            
        ).fetchall()
    return rows