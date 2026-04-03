"""
rag.py — RAG engine using ChromaDB for vector storage,
sentence-transformers for embeddings, and Ollama for generation.
"""

import json
import logging
from typing import Iterator

import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer
import httpx

logger = logging.getLogger(__name__)

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "phi3:latest"
COLLECTION_NAME = "amazon_products"


def _product_to_doc(p: dict) -> str:
    """
    Flatten a product dict into a complete text document for embedding.
    No truncation — we want the full content indexed for accurate retrieval.
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


class RAGEngine:
    def __init__(self, chroma_dir: str):
        logger.info("Loading embedding model (all-MiniLM-L6-v2)…")
        self._embedder = SentenceTransformer("all-MiniLM-L6-v2")
        self._chroma = chromadb.PersistentClient(
            path=chroma_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        self._col = self._chroma.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )
        logger.info("RAG engine ready — %d docs indexed", self._col.count())

    @property
    def doc_count(self) -> int:
        return self._col.count()

    # ── Ingestion ─────────────────────────────────────────────────────────────

    def ingest(self, products: list[dict], append: bool = False) -> int:
        """
        Embed and store products in ChromaDB.
        append=False  → wipe the collection first (default, for single-file loads)
        append=True   → upsert into existing collection (for loading multiple categories)
        """
        if not products:
            return 0

        if not append:
            self._chroma.delete_collection(COLLECTION_NAME)
            self._col = self._chroma.create_collection(
                name=COLLECTION_NAME,
                metadata={"hnsw:space": "cosine"},
            )

        batch_size = 64
        total = 0
        for i in range(0, len(products), batch_size):
            batch = products[i : i + batch_size]
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
            embeds = self._embedder.encode(docs, show_progress_bar=False).tolist()
            # upsert handles both insert and update, safe for both modes
            self._col.upsert(documents=docs, embeddings=embeds, ids=ids, metadatas=metas)
            total += len(batch)
            logger.info("Ingested %d / %d products", total, len(products))

        return total

    # ── Retrieval ─────────────────────────────────────────────────────────────

    def get_by_asin(self, asin: str) -> str | None:
        """Return the full indexed document for a specific product ASIN."""
        if not asin:
            return None
        try:
            result = self._col.get(ids=[asin], include=["documents"])
            if result["ids"]:
                return result["documents"][0]
        except Exception:
            pass
        return None

    def retrieve(self, query: str, k: int = 3, exclude_asin: str = "") -> list[dict]:
        """Return top-k semantically similar products, optionally excluding one ASIN."""
        count = self._col.count()
        if count == 0:
            return []
        emb = self._embedder.encode([query]).tolist()
        # fetch k+1 so we can drop the selected product itself from related results
        n = min(k + 1, count)
        res = self._col.query(
            query_embeddings=emb,
            n_results=n,
            include=["documents", "metadatas"],
        )
        results = []
        for doc, meta in zip(res["documents"][0], res["metadatas"][0]):
            if exclude_asin and meta.get("asin") == exclude_asin:
                continue
            results.append({"text": doc, "meta": meta})
            if len(results) >= k:
                break
        return results

    # ── Generation ────────────────────────────────────────────────────────────

    def stream_chat(
        self, message: str, product: dict, history: list[dict]
    ) -> Iterator[str]:
        """
        Build a full-data RAG prompt and stream tokens from Ollama.

        Uses:
        1. The complete product record (all fields, no truncation)
        2. The exact indexed document for this product from ChromaDB
        3. Semantically similar related products for broader context
        """
        asin = product.get("asin", "")

        # ── Build primary product context (complete, no truncation) ──────────
        ctx_lines = ["=== Selected Product ==="]
        ctx_lines.append(f"Title: {product.get('title', 'N/A')}")
        if product.get("brand"):
            ctx_lines.append(f"Brand: {product['brand']}")
        if product.get("price"):
            ctx_lines.append(f"Price: {product['price']}")
        if product.get("main_category"):
            ctx_lines.append(f"Category: {product['main_category']}")
        if product.get("categories"):
            ctx_lines.append(f"All categories: {', '.join(product['categories'])}")
        if product.get("description"):
            ctx_lines.append(f"Description: {product['description']}")
        features = product.get("features", [])
        if features:
            ctx_lines.append("Features:")
            for f in features:
                ctx_lines.append(f"  • {f}")
        if product.get("rating"):
            ctx_lines.append(
                f"Rating: {product['rating']}/5 stars "
                f"({product.get('review_count', 0)} customer reviews)"
            )

        # ── Pull the full indexed document from ChromaDB by ASIN ─────────────
        indexed_doc = self.get_by_asin(asin)
        if indexed_doc:
            ctx_lines.append("\n=== Full Indexed Product Record ===")
            ctx_lines.append(indexed_doc)

        # ── Retrieve semantically related products ────────────────────────────
        query = f"{product.get('title', '')} {message}"
        related = self.retrieve(query, k=3, exclude_asin=asin)
        if related:
            ctx_lines.append("\n=== Related Products in Database ===")
            for r in related:
                ctx_lines.append(f"• {r['text'][:300]}")

        context_block = "\n".join(ctx_lines)

        # ── Build Ollama message list ─────────────────────────────────────────
        ollama_messages = [
            {
                "role": "system",
                "content": (
                    "You are a knowledgeable Amazon product assistant. "
                    "You have access to the complete product data from the Amazon dataset. "
                    "Answer questions accurately using the provided product information. "
                    "Be helpful and specific. If a detail is not in the data, say so."
                ),
            }
        ]
        for h in history[-6:]:
            if h.get("content"):
                ollama_messages.append({"role": h["role"], "content": h["content"]})
        ollama_messages.append(
            {"role": "user", "content": f"{context_block}\n\nQuestion: {message}"}
        )

        # ── Stream from Ollama ────────────────────────────────────────────────
        try:
            with httpx.stream(
                "POST",
                f"{OLLAMA_URL}/api/chat",
                json={"model": OLLAMA_MODEL, "messages": ollama_messages, "stream": True},
                timeout=120,
            ) as resp:
                resp.raise_for_status()
                for line in resp.iter_lines():
                    if not line:
                        continue
                    try:
                        data = json.loads(line)
                        token = data.get("message", {}).get("content", "")
                        if token:
                            yield token
                        if data.get("done"):
                            break
                    except json.JSONDecodeError:
                        continue
        except httpx.ConnectError:
            yield (
                "\n\n⚠️ Cannot reach Ollama. "
                "Please make sure Ollama is running: https://ollama.com"
            )
        except httpx.HTTPStatusError as e:
            yield f"\n\n⚠️ Ollama error {e.response.status_code}: {e.response.text[:200]}"
        except Exception as e:
            yield f"\n\n⚠️ Unexpected error: {str(e)}"
