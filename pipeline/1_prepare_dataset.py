#!/usr/bin/env python3
"""
1_prepare_dataset.py — Prepare UCSD Amazon dataset for RAG ingestion.

Reads meta_*.jsonl.gz files, normalises schema, deduplicates by ASIN,
and exports products.jsonl for ChromaDB ingestion (step 2).
"""

import argparse
import gzip
import json
import sys
from pathlib import Path

# Windows: force UTF-8 output so box-drawing characters don't crash
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# ─────────────────────────────────────────────────────────────────────────────
# Schema normalisation
# ─────────────────────────────────────────────────────────────────────────────

GENERIC_FALLBACKS = {
    "n/a", "na", "none", "not available", "not specified", "unknown",
    "no description available", "no features listed", "see product details",
    "see description", "please see the product description",
}


def _clean_str(val) -> str:
    """Coerce a value to a clean string."""
    if val is None:
        return ""
    if isinstance(val, list):
        parts = [_clean_str(v) for v in val if v]
        return " ".join(parts).strip()
    return str(val).strip()


def _is_fallback(text: str) -> bool:
    return text.lower() in GENERIC_FALLBACKS or len(text) < 3


def _flatten_categories(cats) -> list:
    """Flatten nested category lists into a flat list of strings."""
    result = []
    if isinstance(cats, list):
        for item in cats:
            if isinstance(item, list):
                result.extend(_flatten_categories(item))
            elif item:
                result.append(str(item).strip())
    elif cats:
        result.append(str(cats).strip())
    return [c for c in result if c]


def _first_image(raw: dict) -> str:
    """Extract the first image URL from various schema fields."""
    for field in ("imageURLHighRes", "imageUrlHighRes", "images", "image", "imageURL"):
        val = raw.get(field)
        if not val:
            continue
        if isinstance(val, list) and val:
            first = val[0]
            if isinstance(first, dict):
                for k in ("large", "hi_res", "url", "thumb"):
                    if first.get(k):
                        return str(first[k])
                return str(next(iter(first.values()), ""))
            return str(first)
        if isinstance(val, str):
            return val
    return ""


def _parse_price(raw: dict) -> str:
    for field in ("price", "Price"):
        val = raw.get(field)
        if val is None:
            continue
        if isinstance(val, (int, float)):
            return f"${val:.2f}"
        s = str(val).strip()
        if s and not _is_fallback(s):
            return s
    return "Price not listed"


def normalise_product(raw: dict) -> dict | None:
    """Normalise a raw JSONL record to the canonical product schema."""
    asin = _clean_str(raw.get("asin") or raw.get("parent_asin", ""))
    title = _clean_str(raw.get("title", ""))

    if not title or len(title) < 5:
        return None

    brand = _clean_str(raw.get("brand") or raw.get("store", ""))
    price = _parse_price(raw)

    # Description — 2018 schema uses list, 2023 uses string
    desc_raw = raw.get("description", [])
    if isinstance(desc_raw, list):
        desc_parts = [_clean_str(d) for d in desc_raw if _clean_str(d)]
        description = " ".join(desc_parts)
    else:
        description = _clean_str(desc_raw)

    # Features
    feat_raw = raw.get("feature") or raw.get("features") or []
    if isinstance(feat_raw, str):
        feat_raw = [feat_raw]
    features = [_clean_str(f) for f in feat_raw if _clean_str(f) and not _is_fallback(_clean_str(f))]

    cats = _flatten_categories(raw.get("categories") or raw.get("category") or [])
    main_cat = _clean_str(raw.get("main_category") or raw.get("main_cat") or (cats[0] if cats else ""))

    rating_raw = raw.get("average_rating") or raw.get("overall") or 0.0
    try:
        rating = float(rating_raw)
    except (TypeError, ValueError):
        rating = 0.0

    rc_raw = raw.get("rating_number") or raw.get("reviewCount") or 0
    try:
        review_count = int(rc_raw)
    except (TypeError, ValueError):
        review_count = 0

    return {
        "asin": asin,
        "title": title,
        "brand": brand,
        "price": price,
        "description": description,
        "features": features,
        "categories": cats,
        "main_category": main_cat,
        "image_url": _first_image(raw),
        "rating": rating,
        "review_count": review_count,
    }


# ─────────────────────────────────────────────────────────────────────────────
# Reading JSONL / JSONL.GZ
# ─────────────────────────────────────────────────────────────────────────────

def iter_records(path: Path):
    """Yield raw dicts from a .jsonl or .jsonl.gz file."""
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


# ─────────────────────────────────────────────────────────────────────────────
# Main
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Prepare UCSD Amazon dataset for RAG ingestion")
    parser.add_argument("--input", required=True, help="Path to meta_*.jsonl.gz file(s), or a directory")
    parser.add_argument("--output", default="data/processed/products.jsonl", help="Output products JSONL for RAG")
    parser.add_argument("--max_products", type=int, default=0, help="Maximum number of products to export (0 = unlimited)")
    args = parser.parse_args()

    # Collect input files
    input_path = Path(args.input)
    if input_path.is_dir():
        files = (
            sorted(input_path.glob("meta_*.jsonl.gz"))
            + sorted(input_path.glob("meta_*.jsonl"))
            + sorted(input_path.glob("meta_*.json"))
            + sorted(input_path.glob("*/meta_*.jsonl.gz"))
            + sorted(input_path.glob("*/meta_*.jsonl"))
            + sorted(input_path.glob("*/meta_*.json"))
        )
        seen = set()
        unique = []
        for f in files:
            if f not in seen and f.is_file():
                seen.add(f)
                unique.append(f)
        files = unique
    else:
        files = [input_path]

    if not files:
        print(f"ERROR: No input files found at {args.input}", file=sys.stderr)
        sys.exit(1)

    print(f"Input files: {[str(f) for f in files]}")

    Path(args.output).parent.mkdir(parents=True, exist_ok=True)

    all_products = []
    seen_asins = set()
    total_raw = 0
    skipped_no_title = 0
    skipped_duplicate = 0

    for file_path in files:
        print(f"\nReading: {file_path}")
        for raw in iter_records(file_path):
            total_raw += 1

            if total_raw % 5000 == 0:
                print(f"  Processed {total_raw} raw records | {len(all_products)} products kept")

            product = normalise_product(raw)
            if product is None:
                skipped_no_title += 1
                continue

            asin = product["asin"]
            if asin and asin in seen_asins:
                skipped_duplicate += 1
                continue
            if asin:
                seen_asins.add(asin)

            all_products.append(product)

            if args.max_products and len(all_products) >= args.max_products:
                print(f"  Reached max_products={args.max_products}, stopping.")
                break
        else:
            continue
        break

    print(f"\n{'─'*50}")
    print(f"Raw records read      : {total_raw:>10,}")
    print(f"Skipped (no title)    : {skipped_no_title:>10,}")
    print(f"Skipped (duplicate)   : {skipped_duplicate:>10,}")
    print(f"Products exported     : {len(all_products):>10,}")
    print(f"{'─'*50}")

    with open(args.output, "w", encoding="utf-8") as fh:
        for p in all_products:
            fh.write(json.dumps(p) + "\n")

    print(f"\nProducts written -> {args.output}  ({len(all_products):,} products)")
    print("\nNext step:")
    print(f"  python pipeline/2_build_vectorstore.py --input {args.output}")
    print("\nDone!")


if __name__ == "__main__":
    main()
