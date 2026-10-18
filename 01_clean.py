"""Section 1 — Cleaning.

Reads raw data files from raw_data/ and produces a normalized, cleaned
single document per source file in clean_data/.

Cleaning operations:
  1. Drop leading header comment block (SOURCE / FORMAT / NOTE lines).
  2. Drop trailing shell artifacts (EOF / echo / wc junk lines).
  3. Collapse blank-line runs and strip whitespace-only lines.
  4. Strip trailing whitespace from each line.
  5. Preserve markdown structure: headers, tables, lists, bracketed flags.
Output is written to clean_data/<stem>-clean.md.
"""

from pathlib import Path

HERE = Path(__file__).parent
RAW_DIR = HERE / "raw_data"
CLEAN_DIR = HERE / "clean_data"

# Fallback locations searched when raw_data/ is empty.
FALLBACK_DIRS = [HERE]

# Leading comment lines to strip once a "clear" content start is found.
# We stop stripping at the first line that does NOT match the header pattern.
HEADER_LINE = "# "  # all top metadata lines are single-hash comments

# Trailing junk: leftover shell command output / EOF markers.
TRAILING_STRIP = {"EOF", 'echo "Lines:"'}


def clean_raw(raw_lines: list[str]) -> tuple[list[str], dict]:
    """Clean raw lines. Returns (cleaned_lines, report)."""
    report: dict = {}
    lines = list(raw_lines)

    # 1. Strip leading header/metadata block.
    start = 0
    for i, line in enumerate(lines):
        if line.startswith(HEADER_LINE):
            start = i + 1
        else:
            break
    removed_header = start
    lines = lines[start:]
    report["header_lines_removed"] = removed_header

    # 2. Strip trailing shell artifacts and trailing blank lines.
    while lines and not lines[-1].strip():
        lines.pop()
    trailing_shell = 0
    while lines:
        last = lines[-1].rstrip()
        if last in TRAILING_STRIP or last.startswith("wc -l ") or last.startswith("echo "):
            trailing_shell += 1
            lines.pop()
        else:
            break
    report["trailing_artifact_lines_removed"] = trailing_shell

    # 3. Normalize: strip trailing whitespace; collapse blank-run (>1 blank) to one.
    out: list[str] = []
    prev_blank = False
    for line in lines:
        stripped = line.rstrip()
        if not stripped.strip():
            if not prev_blank and out:  # keep at most one blank between content
                out.append("")
            prev_blank = True
            continue
        out.append(stripped)
        prev_blank = False
    # Trim any leading/longing leftover blanks.
    while out and not out[0].strip():
        out.pop(0)
    while out and not out[-1].strip():
        out.pop()

    report["blank_lines_collapsed"] = sum(1 for l in out if not l.strip())
    report["content_lines"] = sum(1 for l in out if l.strip())
    return out, report


def main() -> None:
    CLEAN_DIR.mkdir(exist_ok=True)
    candidates = list(RAW_DIR.glob("*.md"))
    origin = RAW_DIR
    if not candidates:
        for d in FALLBACK_DIRS:
            candidates = [
                p for p in d.glob("*.md")
                if "raw" in p.name and "-clean" not in p.name
            ]
            if candidates:
                origin = d
                break
    if not candidates:
        print("No .md files found. Drop raw data into raw_data/ (or the project root).")
        return
    print(f"Source directory: {origin}")
    for src in candidates:
        cleaned, report = clean_raw(src.read_text(encoding="utf-8").splitlines())
        dest = CLEAN_DIR / f"{src.stem}-clean.md"
        dest.write_text("\n".join(cleaned) + "\n", encoding="utf-8")
        print(f"✅ {src.name} -> {dest.name}")
        for k, v in report.items():
            print(f"   {k}: {v}")


if __name__ == "__main__":
    main()