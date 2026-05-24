"""
ChromaDB vector overlay for holographic memory.
Provides unlimited-capacity semantic search alongside the existing SQLite fact_store.

Usage:
  python vector_store.py index              # index all facts from holographic store
  python vector_store.py search "query"     # semantic search
  python vector_store.py stats              # show collection stats
"""

import json
import os
import sqlite3
import sys
from pathlib import Path

HOME = Path(os.environ.get("HERMES_HOME", str(Path.home() / ".hermes")))
HOLO_DB = HOME / "memory_store.db"
CHROMA_DIR = HOME / "chroma_db"
COLLECTION_NAME = "holographic_facts"


def get_chroma_client():
    """Lazy-init ChromaDB persistent client."""
    import chromadb
    CHROMA_DIR.mkdir(parents=True, exist_ok=True)
    client = chromadb.PersistentClient(path=str(CHROMA_DIR))
    return client


def get_collection(client=None):
    """Get or create the facts collection."""
    if client is None:
        client = get_chroma_client()
    collection = client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"hnsw:space": "cosine"},
    )
    return collection


def fetch_all_facts():
    """Fetch all facts from the holographic SQLite store."""
    if not HOLO_DB.exists():
        return []
    conn = sqlite3.connect(str(HOLO_DB))
    conn.row_factory = sqlite3.Row
    rows = conn.execute("""
        SELECT f.fact_id, f.content, f.category, f.tags,
               f.trust_score, f.retrieval_count, f.helpful_count,
               f.created_at, f.updated_at,
               GROUP_CONCAT(e.name, ', ') AS entities
        FROM facts f
        LEFT JOIN fact_entities fe ON fe.fact_id = f.fact_id
        LEFT JOIN entities e ON e.entity_id = fe.entity_id
        GROUP BY f.fact_id
        ORDER BY f.trust_score DESC
    """).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def index_facts(verbose=True):
    """Index all facts from holographic store into ChromaDB."""
    facts = fetch_all_facts()
    if not facts:
        print("No facts found in holographic store.")
        return 0

    client = get_chroma_client()

    # Check what's already indexed
    try:
        existing_col = client.get_collection(COLLECTION_NAME)
        existing_count = existing_col.count()
        if existing_count > 0:
            if verbose:
                print(f"Collection has {existing_count} entries. Re-indexing...")
            client.delete_collection(COLLECTION_NAME)
    except Exception:
        pass

    collection = get_collection(client)

    ids = []
    documents = []
    metadatas = []

    for f in facts:
        fid = str(f["fact_id"])
        parts = [f["content"]]
        if f.get("entities"):
            parts.append(f"entities: {f['entities']}")
        if f.get("tags"):
            parts.append(f"tags: {f['tags']}")
        if f.get("category"):
            parts.append(f"category: {f['category']}")
        doc = " | ".join(parts)

        ids.append(fid)
        documents.append(doc)
        # ChromaDB metadata values must be str, int, float, or bool — no None
        metadatas.append({
            "fact_id": str(f["fact_id"]),
            "category": str(f.get("category", "general")),
            "tags": str(f.get("tags", "")),
            "trust_score": float(f.get("trust_score", 0.5)),
            "entities": str(f.get("entities", "")),
            "content_preview": str(f["content"][:200]),
        })

    collection.add(ids=ids, documents=documents, metadatas=metadatas)

    if verbose:
        print(f"Indexed {len(facts)} facts into ChromaDB (collection: {COLLECTION_NAME})")
        print(f"Collection now has {collection.count()} entries")
        print(f"ChromaDB storage: {CHROMA_DIR}")
    return len(facts)


def search(query: str, n_results: int = 10, category: str = None):
    """Semantic search over the vector store. Returns list of result dicts."""
    collection = get_collection()

    kwargs = {
        "query_texts": [query],
        "n_results": n_results,
    }
    if category:
        kwargs["where"] = {"category": category}

    results = collection.query(**kwargs)

    output = []
    ids_list = results.get("ids", [[]])
    metas_list = results.get("metadatas", [[]])
    dists_list = results.get("distances", [[]])

    if ids_list and ids_list[0]:
        for i, doc_id in enumerate(ids_list[0]):
            meta = metas_list[0][i] if metas_list and metas_list[0] else {}
            dist = dists_list[0][i] if dists_list and dists_list[0] else None
            output.append({
                "fact_id": int(meta.get("fact_id", doc_id)) if meta.get("fact_id") else 0,
                "content_preview": str(meta.get("content_preview", "")),
                "category": str(meta.get("category", "general")),
                "trust_score": float(meta.get("trust_score", 0.5)),
                "distance": round(dist, 4) if dist is not None else None,
            })
    return output


def get_stats():
    """Show stats about both stores."""
    facts = fetch_all_facts()
    collection = get_collection()
    chroma_count = collection.count()

    print(f"=== Holographic Store ===")
    print(f"  Facts: {len(facts)}")
    print(f"  DB path: {HOLO_DB}")
    if HOLO_DB.exists():
        print(f"  DB size: {HOLO_DB.stat().st_size / 1024:.1f} KB")
    print(f"\n=== ChromaDB Vector Store ===")
    print(f"  Indexed: {chroma_count}")
    print(f"  Storage: {CHROMA_DIR}")
    if CHROMA_DIR.exists():
        total_size = sum(f.stat().st_size for f in CHROMA_DIR.rglob("*") if f.is_file())
        print(f"  Size: {total_size / 1024:.1f} KB")
    if facts:
        categories = set(f.get("category", "general") for f in facts)
        print(f"\n  Categories: {categories}")
        print(f"  Avg trust: {sum(f.get('trust_score', 0) for f in facts) / len(facts):.2f}")


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "index"

    if cmd == "index":
        index_facts()
    elif cmd == "search":
        query = " ".join(sys.argv[2:]) if len(sys.argv) > 2 else "user preferences"
        results = search(query)
        if not results:
            print("No results found.")
        for r in results:
            print(f"  [{r['fact_id']}] (trust={r['trust_score']}, dist={r['distance']}) {r['content_preview'][:100]}")
    elif cmd == "stats":
        get_stats()
    else:
        print(f"Unknown command: {cmd}")
        print("Usage: python vector_store.py <index|search <query>|stats>")
