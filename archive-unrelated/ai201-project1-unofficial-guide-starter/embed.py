"""
Embedding + retrieval for The Unofficial Guide (OU campus survival).

Milestone 4: take the chunks produced by ingest.py, embed them with
all-MiniLM-L6-v2, store them in a persistent ChromaDB collection with
source metadata, and expose a retrieval function for testing.

See planning.md "Retrieval Approach" for the spec this implements.

Run `python embed.py` to (re)build the index and run the evaluation-query
retrieval test described in the Milestone 4 checkpoint.
"""

from pathlib import Path

import chromadb
from sentence_transformers import SentenceTransformer

from ingest import chunk_documents, load_documents

EMBED_MODEL = "all-MiniLM-L6-v2"
CHROMA_PATH = str(Path(__file__).parent.parent / "chroma_data")
COLLECTION_NAME = "unofficial_guide"

# Lazily loaded so importing this module (e.g. from app.py) doesn't pay the
# model-load cost until something actually needs to embed.
_model = None


def _embedder():
    """Return the all-MiniLM-L6-v2 model, loading it once on first use.

    We use the SAME model to embed chunks at index time and queries at search
    time — retrieval only works if both live in the same vector space.
    """
    global _model
    if _model is None:
        _model = SentenceTransformer(EMBED_MODEL)
    return _model


def _embed(texts):
    """Embed a list of strings into a list of plain Python float lists.

    normalize_embeddings=True gives unit-length vectors, which makes cosine
    distance (the collection's metric) behave well and bounded in [0, 2].
    """
    vecs = _embedder().encode(list(texts), normalize_embeddings=True)
    return vecs.tolist()


def _collection(client):
    """Get-or-create the guide collection configured for cosine distance.

    ChromaDB defaults to squared-L2 distance; we set hnsw:space=cosine so the
    distances match the semantic-similarity framing in planning.md and the
    "below 0.5" target in the Milestone 4 checkpoint.
    """
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )


def build_index(chroma_path=CHROMA_PATH):
    """Load -> chunk -> embed -> upsert every chunk into ChromaDB.

    Each chunk is stored with its embedding, the chunk text (so retrieval can
    return it directly), and metadata: source, url, date, filename, and
    chunk_index (the chunk's position within its source document). source +
    chunk_index are what attribution in Milestone 5 will rely on.

    Returns the populated collection.
    """
    records = chunk_documents(load_documents())

    # Rebuild cleanly: drop any prior version of the collection so a re-run
    # never leaves stale chunks behind (e.g. after editing the chunker).
    client = chromadb.PersistentClient(path=chroma_path)
    try:
        client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass  # Collection didn't exist yet — fine on a first run.
    collection = _collection(client)

    ids = [f"{r['filename']}::chunk{r['chunk_index']}" for r in records]
    documents = [r["text"] for r in records]
    metadatas = [
        {
            "source": r["source"],
            "url": r["url"],
            "date": r["date"],
            "filename": r["filename"],
            "chunk_index": r["chunk_index"],
        }
        for r in records
    ]
    embeddings = _embed(documents)

    collection.upsert(
        ids=ids,
        documents=documents,
        metadatas=metadatas,
        embeddings=embeddings,
    )

    print(f"Indexed {collection.count()} chunks into "
          f"'{COLLECTION_NAME}' at {chroma_path}")
    return collection


def retrieve(query, k=4, chroma_path=CHROMA_PATH):
    """Return the top-k chunks most relevant to `query`.

    Embeds the query with the same MiniLM model, then asks ChromaDB for the k
    nearest chunks by cosine distance. Returns a list of dicts:
    {"text", "distance", "source", "url", "date", "filename", "chunk_index"},
    nearest first (lower distance = more similar).
    """
    client = chromadb.PersistentClient(path=chroma_path)
    collection = _collection(client)

    results = collection.query(
        query_embeddings=_embed([query]),
        n_results=k,
    )

    hits = []
    for doc, dist, meta in zip(
        results["documents"][0],
        results["distances"][0],
        results["metadatas"][0],
    ):
        hits.append({
            "text": doc,
            "distance": dist,
            "source": meta.get("source", ""),
            "url": meta.get("url", ""),
            "date": meta.get("date", ""),
            "filename": meta.get("filename", ""),
            "chunk_index": meta.get("chunk_index"),
        })
    return hits


# Three of the five planning.md evaluation questions, used for the Milestone 4
# retrieval sanity check.
_TEST_QUERIES = [
    "What study spots do OU students recommend, including quieter ones for finals week?",
    "Where can students park for free near campus and how do they get to main campus?",
    "What do students honestly say about living in the Adams, Couch, and Walker tower dorms?",
]


def _test_retrieval(k=4):
    """Milestone 4 checkpoint: print top-k chunks + distances per test query."""
    for q in _TEST_QUERIES:
        print("=" * 78)
        print(f"QUERY: {q}")
        print("=" * 78)
        for rank, hit in enumerate(retrieve(q, k=k), 1):
            preview = hit["text"].replace("\n", " ")
            if len(preview) > 280:
                preview = preview[:280] + "…"
            print(f"  {rank}. distance={hit['distance']:.4f}  "
                  f"[{hit['filename']} #chunk{hit['chunk_index']}]")
            print(f"     {preview}")
        print()


if __name__ == "__main__":
    build_index()
    print()
    _test_retrieval()
