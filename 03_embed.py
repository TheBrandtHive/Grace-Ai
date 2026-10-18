"""Section 3 — Embedding.

Reads chunks from chunk_data/*.jsonl and embeds each chunk's text using the
OpenRouter embeddings model (EMBEDDINGS_MODEL in .env). Vectors are written to
embeddings_data/*.jsonl as records of the form:

    {"id", "text", "embedding": [...], "section", "subsection", "source"}

Handles:
  * resuming from a checkpoint (already-embedded ids are skipped);
  * batching; retries with backoff on transient failures;
  * API key / config validation up front.
"""

import json
import os
import time
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv()

HERE = Path(__file__).parent
CHUNK_DIR = HERE / "chunk_data"
EMBED_DIR = HERE / "embeddings_data"

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
EMBEDDING_MODEL = os.getenv("EMBEDDINGS_MODEL", "openai/text-embedding-3-small")

BATCH_SIZE = 32
MAX_RETRIES = 4
RETRY_BACKOFF = 2.0  # seconds, multiplied per attempt


def get_embedding(client: httpx.Client, text: str) -> list[float]:
    """Embed a single text string with retry/backoff."""
    headers = {"Authorization": f"Bearer {API_KEY}"}
    last_err = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = client.post(
                f"{BASE_URL}/embeddings",
                headers=headers,
                json={"model": EMBEDDING_MODEL, "input": text},
                timeout=60.0,
            )
            resp.raise_for_status()
            data = resp.json()["data"][0]["embedding"]
            return data
        except httpx.HTTPStatusError as e:
            if e.response.status_code in {429, 500, 502, 503, 504}:
                last_err = e
                time.sleep(RETRY_BACKOFF * attempt)
                continue
            raise
        except httpx.TransportError as e:
            last_err = e
            time.sleep(RETRY_BACKOFF * attempt)
    raise RuntimeError(f"Embedding failed after {MAX_RETRIES} retries: {last_err}")


def load_chunks(path: Path) -> list[dict]:
    with path.open(encoding="utf-8") as f:
        return [json.loads(line) for line in f if line.strip()]


def main() -> None:
    if not API_KEY:
        raise SystemExit("API_KEY is not set. Add it to .env (OpenRouter).")
    EMBED_DIR.mkdir(exist_ok=True)

    chunk_files = sorted(CHUNK_DIR.glob("*.jsonl"))
    if not chunk_files:
        raise SystemExit(f"No chunk files found in {CHUNK_DIR}. Run 02_chunk.py first.")

    client = httpx.Client()
    total_new = 0
    for src in chunk_files:
        chunks = load_chunks(src)
        dest = EMBED_DIR / f"{src.stem}-embeddings.jsonl"

        # Resume: skip ids already embedded.
        done_ids: set[str] = set()
        if dest.exists():
            with dest.open(encoding="utf-8") as f:
                for line in f:
                    if line.strip():
                        done_ids.add(json.loads(line)["id"])

        to_do = [c for c in chunks if c["id"] not in done_ids]
        print(f"📄 {src.name}: {len(chunks)} chunks, {len(to_do)} to embed")

        out_f = dest.open("a", encoding="utf-8") if dest.exists() else dest.open("w", encoding="utf-8")
        try:
            for i, chunk in enumerate(to_do, 1):
                emb = get_embedding(client, chunk["text"])
                record = {
                    "id": chunk["id"],
                    "text": chunk["text"],
                    "embedding": emb,
                    "section": chunk.get("section", ""),
                    "subsection": chunk.get("subsection", ""),
                    "source": chunk.get("source", ""),
                }
                out_f.write(json.dumps(record, ensure_ascii=False) + "\n")
                if i % 10 == 0 or i == len(to_do):
                    print(f"   embedded {i}/{len(to_do)}")
            total_new += len(to_do)
        finally:
            out_f.close()
        print(f"✅ {src.name} -> {dest.name}")

    client.close()
    print(f"\nTotal embeddings added: {total_new}")


if __name__ == "__main__":
    main()