"""Ingestion: corpus markdown -> chunks -> embeddings -> pgvector.

Run as a module:  python -m app.ingest

This is the "Ingestion & Embeddings" component from the chapter's six-part RAG
anatomy. It walks the corpus, parses each file's metadata header, splits the
body into overlapping chunks, embeds them, and writes them to the store.
"""
from __future__ import annotations

import sys
from pathlib import Path

from .embeddings import get_embedder
from .settings import settings
from . import store


def parse_frontmatter(text: str) -> tuple[dict, str]:
    """Parse a leading `--- ... ---` YAML-ish block. Returns (metadata, body).

    Intentionally tiny — we only need flat `key: value` pairs, so we avoid a
    YAML dependency.
    """
    meta: dict[str, str] = {}
    if not text.startswith("---"):
        return meta, text
    end = text.find("\n---", 3)
    if end == -1:
        return meta, text
    block = text[3:end].strip()
    body = text[end + 4 :].lstrip("\n")
    for line in block.splitlines():
        if ":" in line:
            key, _, value = line.partition(":")
            meta[key.strip()] = value.strip()
    return meta, body


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """Split on blank lines into paragraphs, then pack paragraphs into chunks
    of roughly `size` characters with `overlap` characters of carry-over."""
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if current and len(current) + len(para) + 2 > size:
            chunks.append(current)
            current = current[-overlap:] + "\n\n" + para if overlap else para
        else:
            current = f"{current}\n\n{para}" if current else para
    if current:
        chunks.append(current)
    return chunks


def load_corpus(corpus_dir: Path) -> list[dict]:
    """Return one record per chunk, with metadata and content (no embeddings yet)."""
    records: list[dict] = []
    files = sorted(corpus_dir.rglob("*.md"))
    if not files:
        raise SystemExit(f"No .md files found under {corpus_dir}")
    for path in files:
        meta, body = parse_frontmatter(path.read_text(encoding="utf-8"))
        rel = path.relative_to(corpus_dir).as_posix()
        for i, chunk in enumerate(chunk_text(body, settings.chunk_chars, settings.chunk_overlap)):
            records.append(
                {
                    "source": rel,
                    "doc_type": meta.get("type", "unknown"),
                    "title": meta.get("title", path.stem),
                    "owner": meta.get("owner", "unknown"),
                    "chunk_index": i,
                    "content": chunk,
                }
            )
    return records


def main() -> None:
    corpus_dir = Path(settings.corpus_dir)
    print(f"Loading corpus from {corpus_dir} ...")
    records = load_corpus(corpus_dir)
    print(f"  {len(records)} chunks from {len(set(r['source'] for r in records))} documents")

    print(f"Embedding with provider='{settings.embeddings_provider}' ...")
    embedder = get_embedder(settings)
    vectors = embedder.embed([r["content"] for r in records])
    for record, vector in zip(records, vectors):
        record["embedding"] = vector
    print(f"  embedding dimension: {embedder.dimension}")

    print("Writing to pgvector ...")
    conn = store.connect(settings)
    store.reset(conn)
    store.init_schema(conn, embedder.dimension)
    store.add_chunks(conn, records)
    total = store.count(conn)
    conn.close()
    print(f"Done. {total} chunks stored. Re-run any time to refresh.")


if __name__ == "__main__":
    sys.exit(main())
