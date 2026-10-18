"""Section 5 — RAG retriever.

Public interface for querying the ChromaDB knowledge base:

  retrieve(query, top_k=5) -> list[dict]
      Embed the query and return the top-k matching chunks.

  build_rag_context(query, top_k=5) -> str
      Human-readable context string for injecting into an LLM prompt.

Usage:
    from rag_retriever import retrieve, build_rag_context
    results = retrieve("legal fees for briefs")
    context = build_rag_context("legal fees for briefs")
"""

import importlib.util
import os
from pathlib import Path

import chromadb
import httpx
from dotenv import load_dotenv

load_dotenv()

_embed_mod_path = Path(__file__).parent / "03_embed.py"
_spec = importlib.util.spec_from_file_location("embed_mod", _embed_mod_path)
_embed_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_embed_mod)
get_embedding = _embed_mod.get_embedding

HERE = Path(__file__).parent
DB_DIR = HERE / "chroma_db"
API_KEY = os.getenv("API_KEY")
COLLECTION_NAME = os.getenv("COLLECTION", "ghana_judicial")

_client: httpx.Client | None = None
_collection = None


def _get_embed_client() -> httpx.Client:
    global _client
    if _client is None:
        if not API_KEY:
            raise RuntimeError("API_KEY is not set. Add it to .env (OpenRouter).")
        _client = httpx.Client()
    return _client


def _get_collection():
    global _collection
    if _collection is None:
        if not DB_DIR.exists():
            raise RuntimeError("chroma_db not found. Run 04_store.py first.")
        client = chromadb.PersistentClient(path=str(DB_DIR))
        _collection = client.get_collection(COLLECTION_NAME)
    return _collection


def retrieve(query: str, top_k: int = 5) -> list[dict]:
    """Embed `query` and return the top_k most relevant chunks."""
    q_embedding = get_embedding(_get_embed_client(), query)
    res = _get_collection().query(query_embeddings=[q_embedding], n_results=top_k)

    out: list[dict] = []
    for doc, meta, dist in zip(
        res["documents"][0], res["metadatas"][0], res["distances"][0]
    ):
        out.append(
            {
                "text": doc,
                "section": meta.get("section", ""),
                "subsection": meta.get("subsection", ""),
                "source": meta.get("source", ""),
                "distance": dist,
            }
        )
    return out


def build_rag_context(query: str, top_k: int = 5) -> str:
    """Format retrieved chunks into a prompt-ready context block."""
    results = retrieve(query, top_k=top_k)
    if not results:
        return ""

    parts = ["<retrieved_knowledge>"]
    for i, r in enumerate(results, 1):
        header = f"[{i}] "
        source_bits = [b for b in [r["section"], r["subsection"]] if b]
        if source_bits:
            header += f"({', '.join(source_bits)}) "
        header += f"— source: {r['source']}"
        parts.append(header)
        parts.append(r["text"])
        parts.append("")
    parts.append("</retrieved_knowledge>")
    return "\n".join(parts).strip()


if __name__ == "__main__":
    import sys

    query = " ".join(sys.argv[1:]) or "What are the legal fees for briefs in Ghana?"
    print(f"Query: {query}\n")
    for r in retrieve(query, top_k=5):
        print(f"• [{r['section']} | {r['source']}] (d={r['distance']:.4f})")
        print(f"  {r['text'][:120].replace(chr(10), ' ')}")
        print()