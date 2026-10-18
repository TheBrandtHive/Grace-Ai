"""Section 2 — Chunking.

Reads cleaned documents from clean_data/ and produces semantic chunks in
chunk_data/. Each chunk:

  * is scoped to a `###` subsection (falling back to the `##` section when a
    `###` does not exist);
  * carries the parent `## SECTION` heading as prepended context so each chunk
    is self-contained;
  * fits within CHAR_BUDGET characters (paragraphs are split if a subsection is
    too large);
  * records metadata: source, section (##), subsection (###), index.

Output format: one JSON line per chunk (JSONL) for easy downstream loading.
"""

import json
from pathlib import Path
import re

HERE = Path(__file__).parent
CLEAN_DIR = HERE / "clean_data"
CHUNK_DIR = HERE / "chunk_data"

CHAR_BUDGET = 1200
MIN_CHARS = 40
OVERLAP_CHARS = 120


def parse_headers(lines: list[str]) -> list[dict]:
    """Split lines into blocks bounded by ## / ### headers."""
    blocks: list[dict] = []
    current = None
    for raw in lines:
        line = raw.strip()
        if line.startswith("### "):
            current = {"h3": line[4:].strip(), "h2": "", "lines": []}
            blocks.append(current)
        elif line.startswith("## "):
            current = {"h3": None, "h2": line[3:].strip(), "lines": []}
            blocks.append(current)
        elif current is not None:
            current["lines"].append(raw)
    return blocks


def assign_section(blocks: list[dict]) -> None:
    last_h2 = None
    for b in blocks:
        if b["h2"]:
            last_h2 = b["h2"]
        b["section"] = last_h2


def split_long(text: str) -> list[str]:
    """Split over-budget text into ~CHAR_BUDGET pieces with overlap."""
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    pieces: list[str] = []
    buf = ""
    for p in paragraphs:
        # if this paragraph alone is over budget, hard-split it by sentences
        if len(p) > CHAR_BUDGET:
            if buf:
                pieces.append(buf)
                buf = ""
            sentences = re.split(r"(?<=[.!?])\s+", p)
            tmp = ""
            for s in sentences:
                if len(tmp) + len(s) + 1 > CHAR_BUDGET and tmp:
                    pieces.append(tmp)
                    tail = tmp[-OVERLAP_CHARS:] if len(tmp) > OVERLAP_CHARS else tmp
                    tmp = tail + " " + s
                else:
                    tmp = tmp + " " + s if tmp else s
            if tmp:
                pieces.append(tmp)
            continue
        if len(buf) + len(p) + 4 > CHAR_BUDGET and buf:
            pieces.append(buf)
            tail = buf[-OVERLAP_CHARS:] if len(buf) > OVERLAP_CHARS else buf
            buf = tail + "\n\n" + p
        else:
            buf = buf + "\n\n" + p if buf else p
    if buf:
        pieces.append(buf)
    return [p for p in pieces if len(p.strip()) >= MIN_CHARS]


def chunk_document(source: Path) -> list[dict]:
    text = source.read_text(encoding="utf-8")
    lines = text.splitlines()
    blocks = parse_headers(lines)
    assign_section(blocks)

    chunks: list[dict] = []
    for b in blocks:
        if not b["lines"]:
            continue
        body = "\n".join(b["lines"]).strip()
        if b["h3"]:
            header = f"{b['section']} — {b['h3']}"
        else:
            header = b["section"] or ""
        full_text = f"{header}\n\n{body}" if header else body

        pieces = split_long(full_text) if len(full_text) > CHAR_BUDGET else [full_text]
        for piece in pieces:
            piece = piece.strip()
            if len(piece) < MIN_CHARS:
                continue
            chunks.append(
                {
                    "id": f"{source.stem}::{b['section']}::{b['h3'] or ''}::{len(chunks)}",
                    "text": piece,
                    "section": b["section"] or (b["h3"] or ""),
                    "subsection": b["h3"] or "",
                    "source": source.name,
                }
            )
    return chunks


def main() -> None:
    CHUNK_DIR.mkdir(exist_ok=True)
    files = sorted(CLEAN_DIR.glob("*-clean.md"))
    if not files:
        print(f"No cleaned files found in {CLEAN_DIR}. Run 01_clean.py first.")
        return
    total = 0
    for src in files:
        chunks = chunk_document(src)
        dest = CHUNK_DIR / f"{src.stem}-chunks.jsonl"
        with dest.open("w", encoding="utf-8") as f:
            for c in chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        skipped = max(0, 0)
        print(f"✅ {src.name} -> {dest.name} ({len(chunks)} chunks) [{skipped} ignored]")
        total += len(chunks)
    print(f"\nTotal chunks written: {total}")


if __name__ == "__main__":
    main()