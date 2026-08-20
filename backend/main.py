"""
main.py — FastAPI backend for Amazon RAG Chatbot.

Serves product data + handles file ingestion into ChromaDB + streams
RAG-powered chat responses via the Groq API.

Optional: the Streamlit app (streamlit_app.py) no longer needs this backend —
it calls ProductLoader/RAGEngine in-process. Kept for local dev / API access.

Run with:
    uvicorn main:app --reload --port 8080
"""

import json
import logging
import sys
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, UploadFile, File
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

sys.path.insert(0, str(Path(__file__).parent))

from products import ProductLoader, normalise_raw, parse_jsonl_bytes
from rag import RAGEngine

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ─────────────────────────────────────────────────────────────────────────────
# App
# ─────────────────────────────────────────────────────────────────────────────

app = FastAPI(
    title="Amazon RAG API",
    description="RAG-powered Amazon product chatbot backend.",
    version="2.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://localhost:3001", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─────────────────────────────────────────────────────────────────────────────
# Startup
# ─────────────────────────────────────────────────────────────────────────────

@app.on_event("startup")
async def startup_event():
    backend_dir = Path(__file__).parent
    project_root = backend_dir.parent

    processed_path = project_root / "data" / "processed" / "products.jsonl"
    raw_dir = project_root / "data" / "raw"
    chroma_dir = str(project_root / "data" / "chroma")

    # Load products
    loader = ProductLoader()
    loader.load(processed_path=str(processed_path), raw_dir=str(raw_dir))
    app.state.loader = loader
    logger.info("Product loader ready — %d products", len(loader.products))

    # Init RAG engine
    rag = RAGEngine(chroma_dir=chroma_dir)
    app.state.rag = rag

    # Auto-ingest if ChromaDB is out of sync with loaded products
    if rag.doc_count != len(loader.products) and loader.products:
        logger.info(
            "ChromaDB has %d docs but %d products — re-indexing…",
            rag.doc_count, len(loader.products),
        )
        rag.ingest(loader.products)
        logger.info("Auto-ingest complete — %d docs indexed", rag.doc_count)


# ─────────────────────────────────────────────────────────────────────────────
# Request models
# ─────────────────────────────────────────────────────────────────────────────

class ChatRequest(BaseModel):
    message: str
    product: dict
    history: list[dict] = []


# ─────────────────────────────────────────────────────────────────────────────
# Helpers
# ─────────────────────────────────────────────────────────────────────────────

# ─────────────────────────────────────────────────────────────────────────────
# Endpoints
# ─────────────────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    loader: ProductLoader = app.state.loader
    rag: RAGEngine = app.state.rag
    return {
        "status": "ok",
        "products": len(loader.products),
        "indexed_docs": rag.doc_count,
    }


@app.get("/categories")
def get_categories():
    return {"categories": app.state.loader.get_categories()}


@app.get("/products")
def list_products(
    search: str = Query(default=""),
    category: str = Query(default=""),
    page: int = Query(default=1, ge=1),
    limit: int = Query(default=20, ge=1, le=100),
):
    return app.state.loader.search(query=search, category=category, page=page, limit=limit)


@app.get("/products/{asin}")
def get_product(asin: str):
    product = app.state.loader.get_by_asin(asin)
    if product is None:
        raise HTTPException(status_code=404, detail=f"Product '{asin}' not found.")
    return product


@app.post("/ingest")
async def ingest_file(
    file: UploadFile = File(...),
    append: bool = Query(default=False, description="Add to existing database instead of replacing it"),
):
    """
    Upload a JSONL or JSONL.GZ product file.
    append=false (default) → replaces all existing data
    append=true            → adds to existing data (use for loading multiple categories)
    """
    raw_bytes = await file.read()
    logger.info("Received file '%s' (%d bytes), append=%s", file.filename, len(raw_bytes), append)

    products = parse_jsonl_bytes(raw_bytes)
    if not products:
        raise HTTPException(status_code=422, detail="No valid products found in the uploaded file.")

    loader: ProductLoader = app.state.loader
    rag: RAGEngine = app.state.rag

    if append:
        # Merge new products into existing loader, skip duplicates by ASIN
        existing_asins = set(loader.by_asin.keys())
        new_products = [p for p in products if p.get("asin") not in existing_asins or not p.get("asin")]
        merged = loader.products + new_products
        loader.load_from_list(merged)
        n = rag.ingest(new_products, append=True)
        logger.info("Append complete — added %d new products, total %d, %d docs indexed",
                    len(new_products), len(loader.products), rag.doc_count)
        return {"status": "ok", "products": len(loader.products), "new_products": len(new_products), "indexed_docs": rag.doc_count}
    else:
        loader.load_from_list(products)
        n = rag.ingest(products, append=False)
        logger.info("Replace complete — %d products loaded, %d docs indexed", len(products), n)
        return {"status": "ok", "products": len(products), "indexed_docs": n}


@app.post("/chat")
async def chat(req: ChatRequest):
    """
    RAG chat endpoint.
    Looks up the complete product record by ASIN from the in-memory loader,
    then retrieves related context from ChromaDB and streams a Groq response.
    """
    rag: RAGEngine = app.state.rag
    loader: ProductLoader = app.state.loader

    # Always use the authoritative full record from the loader, not what the frontend sends
    asin = req.product.get("asin", "")
    full_product = loader.get_by_asin(asin) if asin else None
    product = full_product or req.product  # fallback to frontend payload if ASIN not found

    def event_stream():
        for token in rag.stream_chat(req.message, product, req.history):
            payload = json.dumps({"choices": [{"delta": {"content": token}}]})
            yield f"data: {payload}\n\n"
        yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
