#!/usr/bin/env python3
"""
download_all.py — Download all Amazon v2 metadata categories and build
the full product database (products.jsonl + ChromaDB vector index).

Usage:
    # Download and index everything (default 5000 products per category)
    python pipeline/download_all.py

    # Custom limit per category
    python pipeline/download_all.py --limit 10000

    # Only specific categories
    python pipeline/download_all.py --categories Electronics,Books,Toys_and_Games

    # Resume interrupted run (skips already-downloaded files)
    python pipeline/download_all.py --resume

NOTE: Stop the backend server before running this script.
      Restart it after the script finishes to load the new data.
"""

import argparse
import gzip
import json
import sys
import time
import urllib.request
import urllib.error
from pathlib import Path

# ── Paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR   = Path(__file__).parent
PROJECT_ROOT = SCRIPT_DIR.parent
DATA_RAW     = PROJECT_ROOT / "data" / "raw"
DATA_PROC    = PROJECT_ROOT / "data" / "processed"
CHROMA_DIR   = PROJECT_ROOT / "data" / "chroma"
BACKEND_DIR  = PROJECT_ROOT / "backend"

sys.path.insert(0, str(BACKEND_DIR))

# ── Category download URLs ────────────────────────────────────────────────────
BASE = "https://mcauleylab.ucsd.edu/public_datasets/data/amazon_v2/metaFiles2"

CATEGORIES = {
    "AMAZON_FASHION":             f"{BASE}/meta_AMAZON_FASHION.json.gz",
    "All_Beauty":                 f"{BASE}/meta_All_Beauty.json.gz",
    "Appliances":                 f"{BASE}/meta_Appliances.json.gz",
    "Arts_Crafts_and_Sewing":     f"{BASE}/meta_Arts_Crafts_and_Sewing.json.gz",
    "Automotive":                 f"{BASE}/meta_Automotive.json.gz",
    "Books":                      f"{BASE}/meta_Books.json.gz",
    "CDs_and_Vinyl":              f"{BASE}/meta_CDs_and_Vinyl.json.gz",
    "Cell_Phones_and_Accessories":f"{BASE}/meta_Cell_Phones_and_Accessories.json.gz",
    "Clothing_Shoes_and_Jewelry": f"{BASE}/meta_Clothing_Shoes_and_Jewelry.json.gz",
    "Digital_Music":              f"{BASE}/meta_Digital_Music.json.gz",
    "Electronics":                f"{BASE}/meta_Electronics.json.gz",
    "Gift_Cards":                 f"{BASE}/meta_Gift_Cards.json.gz",
    "Grocery_and_Gourmet_Food":   f"{BASE}/meta_Grocery_and_Gourmet_Food.json.gz",
    "Home_and_Kitchen":           f"{BASE}/meta_Home_and_Kitchen.json.gz",
    "Industrial_and_Scientific":  f"{BASE}/meta_Industrial_and_Scientific.json.gz",
    "Kindle_Store":               f"{BASE}/meta_Kindle_Store.json.gz",
    "Luxury_Beauty":              f"{BASE}/meta_Luxury_Beauty.json.gz",
    "Magazine_Subscriptions":     f"{BASE}/meta_Magazine_Subscriptions.json.gz",
    "Movies_and_TV":              f"{BASE}/meta_Movies_and_TV.json.gz",
    "Musical_Instruments":        f"{BASE}/meta_Musical_Instruments.json.gz",
    "Office_Products":            f"{BASE}/meta_Office_Products.json.gz",
    "Patio_Lawn_and_Garden":      f"{BASE}/meta_Patio_Lawn_and_Garden.json.gz",
    "Pet_Supplies":               f"{BASE}/meta_Pet_Supplies.json.gz",
    "Prime_Pantry":               f"{BASE}/meta_Prime_Pantry.json.gz",
    "Software":                   f"{BASE}/meta_Software.json.gz",
    "Sports_and_Outdoors":        f"{BASE}/meta_Sports_and_Outdoors.json.gz",
    "Tools_and_Home_Improvement": f"{BASE}/meta_Tools_and_Home_Improvement.json.gz",
    "Toys_and_Games":             f"{BASE}/meta_Toys_and_Games.json.gz",
    "Video_Games":                f"{BASE}/meta_Video_Games.json.gz",
}


# ── Helpers ───────────────────────────────────────────────────────────────────

def _fmt_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if n < 1024:
            return f"{n:.1f} {unit}"
        n /= 1024
    return f"{n:.1f} TB"


def download_file(url: str, dest: Path) -> bool:
    """Download url → dest with a simple progress indicator. Returns True on success."""
    print(f"  Downloading {dest.name} …", end="", flush=True)
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60) as resp, open(dest, "wb") as fh:
            total = int(resp.headers.get("Content-Length", 0))
            downloaded = 0
            chunk = 1024 * 256  # 256 KB
            while True:
                block = resp.read(chunk)
                if not block:
                    break
                fh.write(block)
                downloaded += len(block)
                if total:
                    pct = downloaded / total * 100
                    print(f"\r  Downloading {dest.name} … {pct:.0f}% ({_fmt_bytes(downloaded)}/{_fmt_bytes(total)})   ",
                          end="", flush=True)
        print(f"\r  Downloaded  {dest.name}  ({_fmt_bytes(dest.stat().st_size)})          ")
        return True
    except urllib.error.URLError as e:
        print(f"\r  FAILED {dest.name}: {e}")
        if dest.exists():
            dest.unlink()
        return False


def find_local_file(cat_name: str) -> Path | None:
    """
    Look for an already-downloaded file for this category in data/raw/.
    Handles: .json.gz, .json, and the nested-dir structure (meta_X.json/meta_X.json).
    """
    base = DATA_RAW / f"meta_{cat_name}"
    candidates = [
        DATA_RAW / f"meta_{cat_name}.json.gz",    # standard gzip
        DATA_RAW / f"meta_{cat_name}.jsonl.gz",   # alternate extension
        DATA_RAW / f"meta_{cat_name}.json",        # plain json (if not a dir)
        base / f"meta_{cat_name}.json",            # nested dir (user's format)
        base / f"meta_{cat_name}.jsonl",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def iter_jsonl_gz(path: Path):
    """Yield raw dicts from a .json.gz or plain .json/.jsonl file line by line."""
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8", errors="replace") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                yield json.loads(line)
            except json.JSONDecodeError:
                continue


def normalise(raw: dict) -> dict | None:
    """Minimal normalisation — compatible with backend products.py schema."""
    from products import normalise_raw
    p = normalise_raw(raw)
    return p if p.get("title") and len(p["title"]) >= 5 else None


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Download and index all Amazon v2 categories")
    parser.add_argument("--limit",      type=int,   default=5000,
                        help="Max products to ingest per category (default: 5000)")
    parser.add_argument("--categories", type=str,   default="",
                        help="Comma-separated category names to process (default: all)")
    parser.add_argument("--resume",     action="store_true",
                        help="Skip categories already present in products.jsonl")
    parser.add_argument("--no-download",action="store_true",
                        help="Skip downloading — only ingest already-downloaded files in data/raw/")
    args = parser.parse_args()

    DATA_RAW.mkdir(parents=True, exist_ok=True)
    DATA_PROC.mkdir(parents=True, exist_ok=True)

    # Which categories to process
    if args.categories:
        selected = {k: v for k, v in CATEGORIES.items() if k in args.categories.split(",")}
        if not selected:
            print(f"ERROR: None of the specified categories matched. Available: {', '.join(CATEGORIES)}")
            sys.exit(1)
    else:
        selected = CATEGORIES

    # Load existing products.jsonl to know what's already indexed (for --resume)
    existing_asins: set[str] = set()
    existing_categories: set[str] = set()
    products_path = DATA_PROC / "products.jsonl"

    if args.resume and products_path.exists():
        print("Reading existing products.jsonl for resume check …")
        with open(products_path, "r", encoding="utf-8") as fh:
            for line in fh:
                try:
                    p = json.loads(line)
                    if p.get("asin"):
                        existing_asins.add(p["asin"])
                    if p.get("main_category"):
                        existing_categories.add(p["main_category"])
                except Exception:
                    continue
        print(f"  Found {len(existing_asins):,} existing products across categories: "
              f"{', '.join(sorted(existing_categories))}\n")

    # Set up RAG engine (uses CPU for embeddings to avoid VRAM conflict)
    print("Loading embedding model on CPU …")
    import chromadb
    from chromadb.config import Settings
    from sentence_transformers import SentenceTransformer

    embedder = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
    chroma = chromadb.PersistentClient(
        path=str(CHROMA_DIR),
        settings=Settings(anonymized_telemetry=False),
    )
    # If not resuming, wipe and recreate ChromaDB collection
    if not args.resume:
        try:
            chroma.delete_collection("amazon_products")
        except Exception:
            pass
        col = chroma.create_collection("amazon_products", metadata={"hnsw:space": "cosine"})
        # Also clear products.jsonl
        if products_path.exists():
            products_path.unlink()
            print("Cleared existing products.jsonl")
    else:
        col = chroma.get_or_create_collection("amazon_products", metadata={"hnsw:space": "cosine"})

    print(f"ChromaDB currently has {col.count():,} docs\n")

    # Process each category
    total_products = 0
    total_new = 0

    for i, (cat_name, url) in enumerate(selected.items(), 1):
        print(f"[{i}/{len(selected)}] {cat_name}")

        if args.resume and cat_name in existing_categories:
            print(f"  Skipping — already in database.\n")
            continue

        # Check if file already exists locally (any supported format)
        local = find_local_file(cat_name)
        dest  = DATA_RAW / f"meta_{cat_name}.json.gz"

        if local:
            print(f"  Found local file: {local.name} ({_fmt_bytes(local.stat().st_size)})")
        elif args.no_download:
            print(f"  No local file found and --no-download set — skipping.\n")
            continue
        else:
            ok = download_file(url, dest)
            if not ok:
                print(f"  Skipping {cat_name} due to download error.\n")
                continue
            local = dest

        # Parse and collect products up to limit
        products = []
        seen = set(existing_asins)
        skipped_dup = 0
        t0 = time.time()

        for raw in iter_jsonl_gz(local):
            p = normalise(raw)
            if p is None:
                continue
            asin = p.get("asin", "")
            if asin and asin in seen:
                skipped_dup += 1
                continue
            if asin:
                seen.add(asin)
            products.append(p)
            if len(products) >= args.limit:
                break

        print(f"  Parsed {len(products):,} products (skipped {skipped_dup:,} duplicates) "
              f"in {time.time()-t0:.1f}s")

        if not products:
            print(f"  No new products — skipping.\n")
            continue

        # Write to products.jsonl
        with open(products_path, "a", encoding="utf-8") as fh:
            for p in products:
                fh.write(json.dumps(p) + "\n")
        print(f"  Appended to products.jsonl")

        # Embed and store in ChromaDB in batches
        batch_size = 64
        t0 = time.time()
        for j in range(0, len(products), batch_size):
            batch = products[j : j + batch_size]
            docs, ids, metas = [], [], []
            for k, p in enumerate(batch):
                # Build full document text
                lines = [f"Title: {p.get('title', '')}"]
                if p.get("brand"):       lines.append(f"Brand: {p['brand']}")
                if p.get("price"):       lines.append(f"Price: {p['price']}")
                if p.get("main_category"): lines.append(f"Category: {p['main_category']}")
                if p.get("description"): lines.append(f"Description: {p['description']}")
                if p.get("features"):    lines.append("Features: " + " | ".join(p["features"]))
                docs.append("\n".join(lines))
                ids.append(p.get("asin") or f"{cat_name}_{j+k}")
                metas.append({
                    "asin":     p.get("asin", ""),
                    "title":    p.get("title", "")[:200],
                    "price":    p.get("price", ""),
                    "category": p.get("main_category", ""),
                })

            embeds = embedder.encode(docs, show_progress_bar=False).tolist()
            col.upsert(documents=docs, embeddings=embeds, ids=ids, metadatas=metas)

            done = min(j + batch_size, len(products))
            print(f"\r  Indexing … {done:,}/{len(products):,} "
                  f"({done/len(products)*100:.0f}%)  ", end="", flush=True)

        elapsed = time.time() - t0
        print(f"\r  Indexed {len(products):,} products in {elapsed:.0f}s              ")
        existing_asins.update(p.get("asin", "") for p in products)

        total_products += len(products)
        total_new += len(products)
        print(f"  ChromaDB total: {col.count():,} docs\n")

    # Final summary
    print("=" * 60)
    print(f"  Done!")
    print(f"  New products added this run  : {total_new:,}")
    print(f"  Total docs in ChromaDB       : {col.count():,}")
    if products_path.exists():
        lines = sum(1 for _ in open(products_path, "r", encoding="utf-8"))
        print(f"  Total lines in products.jsonl: {lines:,}")
    print("=" * 60)
    print()
    print("  Restart the backend to load the updated database:")
    print("  python -m uvicorn main:app --reload --port 8080")
    print()


if __name__ == "__main__":
    main()
