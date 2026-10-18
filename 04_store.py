"""Section 4 — Store embeddings in ChromaDB.

Loads embedded records from embeddings_data/*.jsonl and upserts them into a
persistent ChromaDB collection. Re-running is idempotent: ids already present
in the collection are skipped.

Collection: default "ghana_judicial"  (override with COLLECTION env var)
Persistence: ./chroma_db
"""

import json
import os
from pathlib import Path

import chromadb
from dotenv import load_dotenv

load_dotenv()

HERE = Path(__file__).parent
EMBED_DIR = HERE / "embeddings_data"
DB_DIR = HERE / "chroma_db"

COLLECTION_NAME = os.getenv("COLLECTION", "ghana_judicial")


def load_records() -> list[dict]:
    records: list[dict] = []
    files = sorted(EMBED_DIR.glob("*.jsonl"))
    if not files:
        raise SystemExit(f"No embedding files found in {EMBED_DIR}. Run 03_embed.py first.")
    for p in files:
        with p.open(encoding="utf-8") as f:
            for line in f:
                if line.strip():
                    records.append(json.loads(line))
    return records


def main() -> None:
    DB_DIR.mkdir(exist_ok=True)
    records = load_records()
    print(f"Loaded {len(records)} embedded records.")

    client = chromadb.PersistentClient(path=str(DB_DIR))
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )

    existing = set(collection.get(include=[]).get("ids", []))
    to_add = [r for r in records if r["id"] not in existing]
    print(f"Collection '{COLLECTION_NAME}' currently has {len(existing)} ids; adding {len(to_add)}.")

    if to_add:
        ids = [r["id"] for r in to_add]
        embeds = [r["embedding"] for r in to_add]
        docs = [r["text"] for r in to_add]
        metadatas = [
            {
                "section": r.get("section", ""),
                "subsection": r.get("subsection", ""),
                "source": r.get("source", ""),
            }
            for r in to_add
        ]
        collection.add(ids=ids, embeddings=embeds, documents=docs, metadatas=metadatas)

    final = collection.count()
    print(f"✅ Stored. Collection '{COLLECTION_NAME}' now has {final} records in {DB_DIR}.")


if __name__ == "__main__":
    main()