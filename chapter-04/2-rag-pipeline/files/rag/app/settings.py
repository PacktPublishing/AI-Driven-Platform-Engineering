"""Configuration for the RAG pipeline, read from environment variables.

Everything has a sensible default so the lab runs out of the box against the
local kind cluster with local embeddings. Override via env vars as documented
in the lab README.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


def _default_corpus_dir() -> str:
    # The corpus lives in Lab 1, one directory up from this lab.
    here = Path(__file__).resolve()
    # .../chapter-04/2-rag-pipeline/files/rag/app/settings.py
    #   parents[0]=app [1]=rag [2]=files [3]=2-rag-pipeline [4]=chapter-04
    chapter_root = here.parents[4]
    return str(chapter_root / "1-knowledge-corpus" / "corpus")


@dataclass(frozen=True)
class Settings:
    # --- Postgres / pgvector -------------------------------------------------
    pg_host: str = os.getenv("PG_HOST", "localhost")
    pg_port: int = int(os.getenv("PG_PORT", "30900"))
    pg_db: str = os.getenv("PG_DB", "ragdb")
    pg_user: str = os.getenv("PG_USER", "rag")
    pg_password: str = os.getenv("PG_PASSWORD", "ragpassword")

    # --- Embeddings ----------------------------------------------------------
    # "local"  -> fastembed, CPU, no credentials (default)
    # "bedrock"-> Amazon Titan embeddings
    embeddings_provider: str = os.getenv("EMBEDDINGS_PROVIDER", "local")
    local_embed_model: str = os.getenv("LOCAL_EMBED_MODEL", "BAAI/bge-small-en-v1.5")
    bedrock_embed_model: str = os.getenv("BEDROCK_EMBED_MODEL", "amazon.titan-embed-text-v2:0")

    # --- Generation LLM ------------------------------------------------------
    # "auto" picks bedrock if AWS creds look present, else anthropic if a key is
    # set, else "none" (retrieval-only). Force with LLM_PROVIDER=bedrock|anthropic|none.
    llm_provider: str = os.getenv("LLM_PROVIDER", "auto")
    bedrock_model_id: str = os.getenv("BEDROCK_MODEL_ID", "us.anthropic.claude-sonnet-4-5-20250929-v1:0")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
    aws_region: str = os.getenv("AWS_REGION", "us-east-1")
    max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "1024"))

    # --- Retrieval / chunking ------------------------------------------------
    top_k: int = int(os.getenv("TOP_K", "4"))
    chunk_chars: int = int(os.getenv("CHUNK_CHARS", "900"))
    chunk_overlap: int = int(os.getenv("CHUNK_OVERLAP", "150"))

    corpus_dir: str = os.getenv("CORPUS_DIR", _default_corpus_dir())

    @property
    def conninfo(self) -> str:
        return (
            f"host={self.pg_host} port={self.pg_port} dbname={self.pg_db} "
            f"user={self.pg_user} password={self.pg_password}"
        )


settings = Settings()
