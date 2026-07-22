"""
Ingestion + chunking for The Unofficial Guide (OU campus survival).

Milestone 3: load documents from documents/ and split them into chunks the
embedding model (all-MiniLM-L6-v2, 256-token ceiling) can handle.

Each .txt file in documents/ starts with a small metadata header:

    source: <human-readable source name>
    url: <original url>
    date: <YYYY or YYYY-MM, or "unknown">
    ---
    <body text...>

See planning.md "Chunking Strategy" for the spec this implements.
"""

import re
from pathlib import Path

DOCUMENTS_DIR = Path(__file__).parent / "documents"
EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"

# Lazily loaded so importing this module stays cheap (and load_documents works
# even before the heavy ML deps are installed).
_tokenizer = None


def _tok():
    """Return the all-MiniLM-L6-v2 tokenizer, loading it once on first use.

    We count tokens with the *same* tokenizer the embedding model uses, so the
    256-token ceiling we enforce matches exactly what the model truncates at.
    """
    global _tokenizer
    if _tokenizer is None:
        from transformers import AutoTokenizer
        _tokenizer = AutoTokenizer.from_pretrained(EMBED_MODEL)
    return _tokenizer


def n_tokens(text):
    """Token count under the embedding model's tokenizer (no special tokens)."""
    return len(_tok().encode(text, add_special_tokens=False))


def load_documents(directory=DOCUMENTS_DIR):
    """Read every .txt file in `directory` into a list of document records.

    Returns a list of dicts: {"text", "source", "url", "date", "filename"}.
    The metadata header (everything before the first line that is exactly
    "---") is parsed into the source/url/date fields; the rest is the body.
    """
    directory = Path(directory)
    docs = []

    for path in sorted(directory.glob("*.txt")):
        raw = path.read_text(encoding="utf-8")

        # Split header from body on the first standalone "---" line.
        if "\n---\n" in raw:
            header, body = raw.split("\n---\n", 1)
        else:
            # No header present: treat the whole file as body, no metadata.
            header, body = "", raw

        meta = {"source": "", "url": "", "date": ""}
        for line in header.splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                key = key.strip().lower()
                if key in meta:
                    meta[key] = value.strip()

        docs.append({
            "text": body.strip(),
            "source": meta["source"],
            "url": meta["url"],
            "date": meta["date"],
            "filename": path.name,
        })

    return docs


# --------------------------------------------------------------------------- #
# Chunking (Milestone 3, "Chunking Strategy" in planning.md)
# --------------------------------------------------------------------------- #

# Sentence boundary: end punctuation followed by whitespace. Good enough for
# news prose / FAQ answers; we are not parsing abbreviations exhaustively.
_SENTENCE_END = re.compile(r"(?<=[.!?])\s+")


def _split_sentences(paragraph):
    return [s.strip() for s in _SENTENCE_END.split(paragraph) if s.strip()]


def _hard_split(text, max_tokens, overlap):
    """Last resort: split a single over-long unit into token windows.

    Only reached when one sentence alone exceeds max_tokens. Windows step by
    (max_tokens - overlap) so consecutive pieces share `overlap` tokens and a
    thought isn't severed mid-clause.
    """
    tok = _tok()
    ids = tok.encode(text, add_special_tokens=False)
    pieces, step = [], max_tokens - overlap
    for start in range(0, len(ids), step):
        window = ids[start:start + max_tokens]
        pieces.append(tok.decode(window).strip())
        if start + max_tokens >= len(ids):
            break
    return pieces


def _is_heading(para, max_heading_tokens=15):
    """A short line that introduces the block after it (title, "4. Foo", etc.).

    Headings don't end in sentence punctuation and are short. We detect them so
    we can keep a heading glued to the content it describes instead of letting a
    chunk boundary strand it (e.g. "4. Swinging pendulum room" away from its
    description).
    """
    if "\n" in para or para.endswith((".", "!", "?")):
        return False
    return n_tokens(para) <= max_heading_tokens


def _merge_headings(paragraphs, max_tokens):
    """Attach each heading paragraph to the following paragraph when they fit."""
    merged = []
    i = 0
    while i < len(paragraphs):
        para = paragraphs[i]
        if (_is_heading(para) and i + 1 < len(paragraphs)
                and n_tokens(para + "\n\n" + paragraphs[i + 1]) <= max_tokens):
            merged.append(para + "\n\n" + paragraphs[i + 1])
            i += 2
        else:
            merged.append(para)
            i += 1
    return merged


def _to_units(text, max_tokens, overlap):
    """Break text into atomic units, each guaranteed <= max_tokens.

    Boundaries are respected in order of preference: paragraph, then sentence,
    then (rarely) a hard token-window split. Headings are first glued to the
    block they introduce so a chunk boundary can't orphan them.
    """
    paragraphs = [p.strip() for p in text.split("\n\n") if p.strip()]
    units = []
    for para in _merge_headings(paragraphs, max_tokens):
        if n_tokens(para) <= max_tokens:
            units.append(para)
            continue
        for sent in _split_sentences(para):
            if n_tokens(sent) <= max_tokens:
                units.append(sent)
            else:
                units.extend(_hard_split(sent, max_tokens, overlap))
    return units


def chunk_text(text, target=200, max_tokens=256, overlap=40, min_tokens=30):
    """Structure-aware chunking per planning.md.

    1. Split into atomic units on natural boundaries (paragraph -> sentence),
       hard-splitting with overlap only when a single unit exceeds max_tokens.
    2. Greedily group adjacent units up to the ~target token size.
    3. Merge a trailing fragment under min_tokens into the previous chunk so we
       don't embed a near-empty chunk.

    Returns a list of chunk strings.
    """
    units = _to_units(text, max_tokens, overlap)

    chunks, cur, cur_tok = [], [], 0
    for unit in units:
        ut = n_tokens(unit)
        # Flush when the current group is non-empty and adding this unit would
        # push it past target. A lone unit between target and max stays whole.
        if cur and cur_tok + ut > target:
            chunks.append("\n\n".join(cur))
            cur, cur_tok = [unit], ut
        else:
            cur.append(unit)
            cur_tok += ut
    if cur:
        chunks.append("\n\n".join(cur))

    # Merge a too-small final chunk back into its neighbor.
    if len(chunks) >= 2 and n_tokens(chunks[-1]) < min_tokens:
        chunks[-2] = chunks[-2] + "\n\n" + chunks[-1]
        chunks.pop()

    return chunks


def chunk_documents(docs):
    """Chunk every document, carrying source/url/date metadata onto each chunk.

    Returns a list of dicts: {"text", "source", "url", "date", "filename",
    "chunk_index"} ready for embedding in Milestone 4.
    """
    records = []
    for d in docs:
        for i, chunk in enumerate(chunk_text(d["text"])):
            records.append({
                "text": chunk,
                "source": d["source"],
                "url": d["url"],
                "date": d["date"],
                "filename": d["filename"],
                "chunk_index": i,
            })
    return records


def _inspect():
    """Stage 2 + Stage 4 inspection report. Run: python ingest.py"""
    docs = load_documents()
    print(f"Loaded {len(docs)} documents from {DOCUMENTS_DIR}\n")

    MAX_TOKENS, MIN_TOKENS = 256, 30
    all_records = chunk_documents(docs)
    over_max, tiny, all_tok = [], [], []

    print(f"{'file':32} {'doc_tok':>7} {'chunks':>6}   chunk token sizes")
    print("-" * 78)
    for d in docs:
        chunks = chunk_text(d["text"])
        sizes = [n_tokens(c) for c in chunks]
        all_tok += sizes
        print(f"{d['filename']:32} {n_tokens(d['text']):>7} {len(chunks):>6}   {sizes}")
        for c, s in zip(chunks, sizes):
            if s > MAX_TOKENS:
                over_max.append((d["filename"], s))
            if s < MIN_TOKENS:
                tiny.append((d["filename"], s, c[:50]))

    print("-" * 78)
    print(f"TOTAL: {len(all_records)} chunks across {len(docs)} documents")
    print(f"token sizes -> min {min(all_tok)}, max {max(all_tok)}, "
          f"mean {sum(all_tok)//len(all_tok)}")

    # Hard validation: the 256 ceiling is the embedding model's, so any breach
    # means silent truncation at index time. This MUST be empty.
    print("\nVALIDATION")
    print(f"  chunks over {MAX_TOKENS} tokens (must be 0): {len(over_max)} {over_max}")
    print(f"  chunks under {MIN_TOKENS} tokens: {len(tiny)} "
          f"{[(f, s) for f, s, _ in tiny]}")
    assert not over_max, "FAIL: a chunk exceeds the 256-token embedding ceiling"
    print("  OK: no chunk exceeds the embedding model's 256-token ceiling.")


if __name__ == "__main__":
    _inspect()
