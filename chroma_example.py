"""Minimal Chroma example: add data to a collection and query it.

Uses a local PersistentClient so the data is saved to ./chroma_data and
persists between runs. Nothing is deleted at the end.
"""

import chromadb

# Persistent local client — data is written to ./chroma_data on disk.
client = chromadb.PersistentClient(path="./chroma_data")

# get_or_create so re-running the script doesn't error on an existing collection.
collection = client.get_or_create_collection(name="getting_started")

# --- Data to ingest -------------------------------------------------------
documents = [
    "Chroma is an open-source embedding database for AI applications.",
    "The Eiffel Tower is located in Paris, France.",
    "Python is a popular programming language for data science.",
    "Espresso is a concentrated form of coffee brewed under pressure.",
    "Mount Everest is the highest mountain above sea level.",
]
ids = [f"doc{i}" for i in range(1, len(documents) + 1)]

# upsert avoids duplicate-id errors when the script is run more than once.
collection.upsert(documents=documents, ids=ids)

print("=" * 70)
print("INGESTED DATA")
print("=" * 70)
for doc_id, doc in zip(ids, documents):
    print(f"  {doc_id}: {doc}")
print(f"\nCollection '{collection.name}' now holds {collection.count()} documents.")

# --- Query ----------------------------------------------------------------
query_text = "Tell me about a database for AI"
print("\n" + "=" * 70)
print("QUERY")
print("=" * 70)
print(f"  {query_text!r}")

results = collection.query(query_texts=[query_text], n_results=3)

print("\n" + "=" * 70)
print("RESULTS (top 3, nearest first)")
print("=" * 70)
result_ids = results["ids"][0]
result_docs = results["documents"][0]
result_dists = results["distances"][0]
for rank, (rid, rdoc, rdist) in enumerate(zip(result_ids, result_docs, result_dists), 1):
    print(f"  {rank}. [{rid}] (distance={rdist:.4f})")
    print(f"     {rdoc}")
