#!/usr/bin/env python3
"""
2_build_vectorstore.py — Embed products and ingest them into ChromaDB.

Reads products.jsonl produced by step 1, encodes each product as a text
document using fastembed (all-MiniLM-L6-v2), and upserts into
ChromaDB so the backend RAG engine can retrieve them at query time.
"""

import argparse
import json
import sys
from pathlib import Path

# Windows: force UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _product_to_doc(p: dict) -> str:
    """
    Flatten a product dict into a single text document for embedding.
    Must match the same function in backend/rag.py exactly.
    """
    lines = [f"Title: {p.get('title', '')}"]
    if p.get("brand"):
        lines.append(f"Brand: {p['brand']}")
    if p.get("price"):
        lines.append(f"Price: {p['price']}")
    if p.get("main_category"):
        lines.append(f"Category: {p['main_category']}")
    cats = p.get("categories", [])
    if cats:
        lines.append(f"All categories: {', '.join(cats)}")
    desc = p.get("description", "")
    if desc:
        lines.append(f"Description: {desc}")
    features = p.get("features", [])
    if features:
        lines.append("Features: " + " | ".join(features))
    if p.get("rating"):
        lines.append(f"Rating: {p['rating']}/5 stars ({p.get('review_count', 0)} reviews)")
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Ingest products.jsonl into ChromaDB for RAG")
    parser.add_argument("--input", default="data/processed/products.jsonl", help="Products JSONL from step 1")
    parser.add_argument("--chroma_dir", default="data/chroma", help="ChromaDB persistence directory")
    parser.add_argument("--batch_size", type=int, default=64, help="Embedding batch size")
    parser.add_argument("--append", action="store_true", help="Append to existing collection (default: replace)")
    args = parser.parse_args()

    # ── Validate input ────────────────────────────────────────────────────────
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"ERROR: {args.input} not found.", file=sys.stderr)
        print("Run pipeline/1_prepare_dataset.py first.", file=sys.stderr)
        sys.exit(1)

    # ── Load products ─────────────────────────────────────────────────────────
    print(f"Loading products from {args.input}...")
    products = []
    with open(input_path, "r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    products.append(json.loads(line))
                except json.JSONDecodeError:
                    continue

    if not products:
        print("ERROR: No products found in input file.", file=sys.stderr)
        sys.exit(1)

    print(f"Loaded {len(products):,} products.")

    # ── Lazy imports (so missing deps give a clear error) ─────────────────────
    try:
        import chromadb
        from chromadb.config import Settings
    except ImportError:
        print("ERROR: chromadb not installed. Run: pip install -r pipeline/requirements_pipeline.txt", file=sys.stderr)
        sys.exit(1)

    try:
        from fastembed import TextEmbedding
    except ImportError:
        print("ERROR: fastembed not installed. Run: pip install -r pipeline/requirements_pipeline.txt", file=sys.stderr)
        sys.exit(1)

    # ── Init ChromaDB ─────────────────────────────────────────────────────────
    chroma_dir = Path(args.chroma_dir)
    chroma_dir.mkdir(parents=True, exist_ok=True)
    print(f"\nOpening ChromaDB at {chroma_dir}...")

    client = chromadb.PersistentClient(
        path=str(chroma_dir),
        settings=Settings(anonymized_telemetry=False),
    )

    collection_name = "amazon_products"
    if not args.append:
        try:
            client.delete_collection(collection_name)
            print("Existing collection deleted (use --append to keep it).")
        except Exception:
            pass
        collection = client.create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )
    else:
        collection = client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    # ── Load embedding model ──────────────────────────────────────────────────
    print("\nLoading embedding model (all-MiniLM-L6-v2)...")
    embedder = TextEmbedding(model_name="sentence-transformers/all-MiniLM-L6-v2")
    print("Model loaded.")

    # ── Ingest in batches ─────────────────────────────────────────────────────
    print(f"\nIngesting {len(products):,} products (batch size {args.batch_size})...\n")
    total_ingested = 0

    for i in range(0, len(products), args.batch_size):
        batch = products[i: i + args.batch_size]
        docs = [_product_to_doc(p) for p in batch]
        ids = [p.get("asin") or f"p_{i + j}" for j, p in enumerate(batch)]
        metas = [
            {
                "asin": p.get("asin", ""),
                "title": p.get("title", "")[:200],
                "price": p.get("price", ""),
                "category": p.get("main_category", ""),
            }
            for p in batch
        ]
        embeds = [e.tolist() for e in embedder.embed(docs)]
        collection.upsert(documents=docs, embeddings=embeds, ids=ids, metadatas=metas)
        total_ingested += len(batch)
        pct = 100 * total_ingested / len(products)
        print(f"  [{pct:5.1f}%] {total_ingested:,} / {len(products):,} ingested", end="\r")

    print(f"\n\nDone. {total_ingested:,} products indexed in ChromaDB.")
    print(f"Collection '{collection_name}' now contains {collection.count():,} documents.")
    print(f"\nNext step:")
    print(f"  python pipeline/3_check_groq.py")


if __name__ == "__main__":
    main()
