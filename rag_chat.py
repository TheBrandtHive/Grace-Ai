"""Standalone RAG chat — retrieve from the ChromaDB knowledge base and answer
with citations via the OpenRouter LLM.

Usage:
    python rag_chat.py                       # interactive CLI
    python rag_chat.py "your question"       # one-shot answer
"""

import importlib.util
import os
from pathlib import Path

import httpx
from dotenv import load_dotenv

from rag_retriever import build_rag_context, retrieve

load_dotenv()

HERE = Path(__file__).parent

API_KEY = os.getenv("API_KEY")
BASE_URL = os.getenv("BASE_URL", "https://openrouter.ai/api/v1")
MODEL = os.getenv("MODEL", "openai/gpt-4o-mini")
TEMPERATURE = float(os.getenv("TEMPERATURE", "0.3"))
MAX_TOKENS = int(os.getenv("MAX_TOKENS", "1024"))

SYSTEM_PROMPT = (
    "You are Grace, an expert assistant on the Ghana judicial system. "
    "Answer the user's question using ONLY the <retrieved_knowledge> context "
    "provided. If the answer is not in the context, say you don't have that "
    "information rather than guessing. Where relevant, cite the data source "
    "and (if present) flag known data gaps."
)


def answer(question: str, top_k: int = 5) -> tuple[str, list[dict]]:
    if not API_KEY:
        raise RuntimeError("API_KEY is not set. Add it to .env (OpenRouter).")

    context = build_rag_context(question, top_k=top_k)
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {
            "role": "user",
            "content": (
                f"<retrieved_knowledge>\n{context}\n</retrieved_knowledge>\n\n"
                f"Question: {question}"
            ),
        },
    ]
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": MODEL,
        "messages": messages,
        "temperature": TEMPERATURE,
        "max_tokens": MAX_TOKENS,
    }
    resp = httpx.post(
        f"{BASE_URL}/chat/completions", json=payload, headers=headers, timeout=60.0
    )
    resp.raise_for_status()
    reply = resp.json()["choices"][0]["message"]["content"]
    return reply, retrieve(question, top_k=top_k)


def chat() -> None:
    print("Grace (Ghana Judicial RAG) ready. Type 'exit' or 'quit' to stop.\n")
    while True:
        try:
            question = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if question.lower() in {"exit", "quit"}:
            break
        if not question:
            continue
        try:
            reply, _ = answer(question)
            print(f"\nGrace: {reply}\n")
        except Exception as e:
            print(f"\nGrace: request failed: {e}\n")


if __name__ == "__main__":
    import sys

    args = sys.argv[1:]
    if args:
        reply, results = answer(" ".join(args))
        print(reply)
        print("\n— Sources —")
        for r in results:
            print(f"  • {r['section']} | {r['source']}")
    else:
        chat()