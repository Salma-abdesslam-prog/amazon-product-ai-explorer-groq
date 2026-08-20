"""
products.py — ProductLoader class for reading and searching Amazon product data.
"""

import gzip
import json
import logging
import re
from pathlib import Path

logger = logging.getLogger(__name__)


def _clean_str(val) -> str:
    if val is None:
        return ""
    if isinstance(val, list):
        return " ".join(str(v).strip() for v in val if v).strip()
    return str(val).strip()


def _flatten_categories(cats) -> list:
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


def _looks_like_price(s: str) -> bool:
    """Reject raw CSS/HTML scraping artifacts that sometimes land in the price field."""
    return len(s) <= 40 and not any(c in s for c in "{};<>")


def _parse_price(raw: dict) -> str:
    for field in ("price", "Price"):
        val = raw.get(field)
        if val is None:
            continue
        if isinstance(val, (int, float)):
            return f"${val:.2f}"
        s = str(val).strip()
        if s and s.lower() not in ("n/a", "na", "none", "") and _looks_like_price(s):
            return s
    return "Price not listed"


def normalise_raw(raw: dict) -> dict:
    """Normalise a raw JSONL product to the canonical schema."""
    desc_raw = raw.get("description", [])
    if isinstance(desc_raw, list):
        description = " ".join(_clean_str(d) for d in desc_raw if _clean_str(d))
    else:
        description = _clean_str(desc_raw)

    feat_raw = raw.get("feature") or raw.get("features") or []
    if isinstance(feat_raw, str):
        feat_raw = [feat_raw]
    features = [_clean_str(f) for f in feat_raw if _clean_str(f)]

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
        "asin": _clean_str(raw.get("asin") or raw.get("parent_asin", "")),
        "title": _clean_str(raw.get("title", "")),
        "brand": _clean_str(raw.get("brand") or raw.get("store", "")),
        "price": _parse_price(raw),
        "description": description,
        "features": features,
        "categories": cats,
        "main_category": main_cat,
        "image_url": _first_image(raw),
        "rating": rating,
        "review_count": review_count,
    }


def parse_jsonl_bytes(data: bytes) -> list:
    """Parse JSONL bytes (plain or gzip-compressed) into a list of normalised product dicts."""
    try:
        text = gzip.decompress(data).decode("utf-8", errors="replace")
    except (gzip.BadGzipFile, OSError):
        text = data.decode("utf-8", errors="replace")

    products = []
    seen = set()
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError:
            continue
        # If already normalised (has 'title' key at top level), use as-is
        if "title" in raw and len(raw.get("title", "")) >= 5:
            p = raw
        else:
            p = normalise_raw(raw)
        if not p.get("title") or len(p["title"]) < 5:
            continue
        asin = p.get("asin", "")
        if asin and asin in seen:
            continue
        if asin:
            seen.add(asin)
        products.append(p)
    return products


class ProductLoader:
    """Loads, normalises, and serves Amazon product data."""

    def __init__(self):
        self.products: list[dict] = []
        self.by_asin: dict[str, dict] = {}

    # ── Loading ───────────────────────────────────────────────────────────────

    def load(self, processed_path: str = "data/processed/products.jsonl",
             raw_dir: str = "data/raw", raw_limit: int = 5000):
        """
        Try to load from products.jsonl first.
        Fall back to raw data/raw/*.jsonl.gz if the processed file is missing.
        """
        processed = Path(processed_path)
        if processed.exists():
            logger.info("Loading products from %s", processed)
            self._load_jsonl(processed)
        else:
            logger.warning(
                "Processed file '%s' not found — falling back to raw data (max %d products). "
                "Run pipeline/1_prepare_dataset.py to generate the full dataset.",
                processed_path, raw_limit,
            )
            self._load_raw(Path(raw_dir), raw_limit)

        logger.info("Loaded %d products (%d with ASIN)", len(self.products), len(self.by_asin))

    def _load_jsonl(self, path: Path):
        with open(path, "r", encoding="utf-8", errors="replace") as fh:
            for line in fh:
                line = line.strip()
                if not line:
                    continue
                try:
                    product = json.loads(line)
                    # If it came from the pipeline it's already normalised
                    if "title" not in product:
                        product = normalise_raw(product)
                    if not product.get("title"):
                        continue
                    self.products.append(product)
                    asin = product.get("asin", "")
                    if asin:
                        self.by_asin[asin] = product
                except json.JSONDecodeError:
                    continue

    def _load_raw(self, raw_dir: Path, limit: int):
        files = list(raw_dir.glob("meta_*.jsonl.gz")) + list(raw_dir.glob("meta_*.jsonl"))
        if not files:
            logger.warning("No meta_*.jsonl.gz files found in %s", raw_dir)
            return

        count = 0
        for file_path in sorted(files):
            opener = gzip.open if file_path.suffix == ".gz" else open
            with opener(file_path, "rt", encoding="utf-8", errors="replace") as fh:
                for line in fh:
                    if count >= limit:
                        return
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        raw = json.loads(line)
                        product = normalise_raw(raw)
                        if not product.get("title"):
                            continue
                        self.products.append(product)
                        asin = product.get("asin", "")
                        if asin:
                            self.by_asin[asin] = product
                        count += 1
                    except json.JSONDecodeError:
                        continue

    # ── Querying ──────────────────────────────────────────────────────────────

    def get_categories(self) -> list[str]:
        """Return sorted unique main categories."""
        cats = set()
        for p in self.products:
            mc = p.get("main_category", "")
            if mc:
                cats.add(mc)
        return sorted(cats)

    def search(self, query: str = "", category: str = "",
               page: int = 1, limit: int = 20) -> dict:
        """
        Case-insensitive substring search over title + brand + description.
        Optional category filter. Paginates results.
        """
        query_lower = query.lower().strip() if query else ""
        category_lower = category.lower().strip() if category else ""

        results = []
        for p in self.products:
            # Category filter
            if category_lower:
                mc = p.get("main_category", "").lower()
                cats = [c.lower() for c in p.get("categories", [])]
                if category_lower not in mc and not any(category_lower in c for c in cats):
                    continue

            # Text search
            if query_lower:
                haystack = " ".join([
                    p.get("title", ""),
                    p.get("brand", ""),
                    p.get("description", ""),
                ]).lower()
                if query_lower not in haystack:
                    continue

            results.append(p)

        total = len(results)
        pages = max(1, (total + limit - 1) // limit)
        page = max(1, min(page, pages))
        start = (page - 1) * limit
        end = start + limit

        return {
            "products": results[start:end],
            "total": total,
            "page": page,
            "pages": pages,
        }

    def load_from_list(self, products: list[dict]):
        """Replace current products with a pre-parsed list."""
        self.products = []
        self.by_asin = {}
        for p in products:
            if not p.get("title"):
                continue
            self.products.append(p)
            asin = p.get("asin", "")
            if asin:
                self.by_asin[asin] = p
        logger.info("Loaded %d products from list", len(self.products))

    def get_by_asin(self, asin: str) -> dict | None:
        return self.by_asin.get(asin)
