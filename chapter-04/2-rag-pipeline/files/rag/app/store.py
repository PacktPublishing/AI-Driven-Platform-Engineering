"""The vector store: Postgres + pgvector.

Deliberately thin. The schema is one table of chunks with an embedding column;
search is a single `ORDER BY embedding <=> query` (cosine distance). For a
corpus this small, exact search is instant — no index needed. At real scale
you'd add an ivfflat/hnsw index, which the chapter notes as an extension.
"""
from __future__ import annotations

from dataclasses import dataclass

import psycopg
from pgvector.psycopg import register_vector

from .settings import Settings


@dataclass
class Retrieved:
    source: str
    doc_type: str
    title: str
    owner: str
    content: str
    score: float  # cosine similarity in [0, 1], higher is closer


def connect(settings: Settings) -> psycopg.Connection:
    conn = psycopg.connect(settings.conninfo, autocommit=True)
    conn.execute("CREATE EXTENSION IF NOT EXISTS vector")
    register_vector(conn)
    return conn


def init_schema(conn: psycopg.Connection, dimension: int) -> None:
    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS chunks (
            id          SERIAL PRIMARY KEY,
            source      TEXT NOT NULL,
            doc_type    TEXT NOT NULL,
            title       TEXT NOT NULL,
            owner       TEXT NOT NULL,
            chunk_index INT  NOT NULL,
            content     TEXT NOT NULL,
            embedding   VECTOR({dimension}) NOT NULL
        )
        """
    )


def reset(conn: psycopg.Connection) -> None:
    """Drop the table so a re-ingest can't mix embedding dimensions."""
    conn.execute("DROP TABLE IF EXISTS chunks")


def add_chunks(conn: psycopg.Connection, rows: list[dict]) -> None:
    with conn.cursor() as cur:
        cur.executemany(
            """
            INSERT INTO chunks (source, doc_type, title, owner, chunk_index, content, embedding)
            VALUES (%(source)s, %(doc_type)s, %(title)s, %(owner)s, %(chunk_index)s, %(content)s, %(embedding)s)
            """,
            rows,
        )


def count(conn: psycopg.Connection) -> int:
    return conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]


def search(conn: psycopg.Connection, query_embedding: list[float], top_k: int) -> list[Retrieved]:
    # `<=>` is cosine distance (0 = identical). Similarity = 1 - distance.
    # Cast the parameter to `vector` explicitly: psycopg sends a Python list as a
    # Postgres array, and there is no `vector <=> array` operator.
    rows = conn.execute(
        """
        SELECT source, doc_type, title, owner, content,
               1 - (embedding <=> %s::vector) AS similarity
        FROM chunks
        ORDER BY embedding <=> %s::vector
        LIMIT %s
        """,
        (query_embedding, query_embedding, top_k),
    ).fetchall()
    return [
        Retrieved(source=r[0], doc_type=r[1], title=r[2], owner=r[3], content=r[4], score=float(r[5]))
        for r in rows
    ]
