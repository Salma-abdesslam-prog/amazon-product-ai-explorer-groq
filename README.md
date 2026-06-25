# Amazone-Product-AI-Explorer

A RAG-powered product chatbot built on real Amazon catalogue data. Browse thousands of products, click any item, and get instant AI answers streamed token-by-token from a local Phi-3 model with full semantic context retrieval.

![Architecture](https://img.shields.io/badge/stack-Streamlit%20%2B%20FastAPI%20%2B%20ChromaDB%20%2B%20Phi--3-E8A320?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-white?style=flat-square)

---

## What it does

- **Browse** a searchable, filterable grid of real Amazon products across multiple categories
- **Click any product** to open an AI chat session for that item
- **Ask anything** — "Is this waterproof?", "How does it compare to similar products?", "What are the main complaints?"
- **Get streamed answers** grounded in actual product data via RAG (no hallucinated specs)
- **Upload new categories** at any time through the built-in dataset panel

---

## Architecture

```
UCSD Amazon Dataset (.jsonl.gz)
          │
          ▼
┌─────────────────────────────────────────────────────┐
│                  FastAPI Backend (:8080)             │
│                                                     │
│  ProductLoader          RAGEngine                   │
│  ┌─────────────┐        ┌──────────────────────┐    │
│  │ products[]  │        │ sentence-transformers │    │
│  │ in-memory   │        │ all-MiniLM-L6-v2     │    │
│  │ text search │        │ ChromaDB (cosine)     │    │
│  └─────────────┘        └──────────────────────┘    │
│         │                        │                  │
│         └──────────┬─────────────┘                  │
│                    ▼                                 │
│              /chat endpoint                         │
│         (product ctx + top-3 related)               │
└──────────────────────┬──────────────────────────────┘
                       │ SSE stream
                       ▼
              Ollama (:11434)
              Phi-3-mini-4k
                       │ token stream
                       ▼
┌─────────────────────────────────────────────────────┐
│           Streamlit Frontend (:8501)                │
│                                                     │
│  Sidebar nav     Browse (4-col product grid)        │
│  AI Chat (SSE)   Dataset Upload                     │
└─────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | Streamlit ≥ 1.32, dark amber theme |
| Backend | FastAPI, Uvicorn (async) |
| LLM | Phi-3-mini via Ollama (local, no API key) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector DB | ChromaDB (persistent, cosine similarity) |
| Streaming | Server-Sent Events (SSE) end-to-end |
| Data | UCSD Amazon Review Dataset 2023 |

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Backend + embeddings + frontend |
| [Ollama](https://ollama.com/download) | latest | Local LLM runtime |

> Node.js is **not required** — the frontend is pure Python (Streamlit).

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/Salma-abdesslam-prog/Amazone-Product-AI-Explorer.git
cd Amazone-Product-AI-Explorer
```

### 2. Install Ollama and pull Phi-3

```bash
# Install from https://ollama.com/download, then:
ollama pull phi3
```

### 3. Install backend dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Install Streamlit dependencies

```bash
cd ..
pip install -r requirements-streamlit.txt
```

### 5. Run everything

Three separate terminals:

```bash
# Terminal 1 — Ollama (if not already running as a service)
ollama serve

# Terminal 2 — FastAPI backend
cd backend
uvicorn main:app --host 0.0.0.0 --port 8080

# Terminal 3 — Streamlit frontend
cd ..
streamlit run streamlit_app.py
```

Open **http://localhost:8501**

---

## Loading Product Data

The app ships without product data. On first launch, go to **Upload Dataset** in the sidebar and upload one of the UCSD Amazon dataset files.

### Download a dataset file

Go to the [UCSD Amazon Reviews 2023](https://amazon-reviews-2023.github.io/) page and download any `meta_*.jsonl.gz` file. Good starting points:

| File | Size | Products |
|---|---|---|
| `meta_Musical_Instruments.jsonl.gz` | ~30 MB | ~11k |
| `meta_All_Beauty.jsonl.gz` | ~60 MB | ~33k |
| `meta_AMAZON_FASHION.jsonl.gz` | ~150 MB | ~186k |

### Loading multiple categories

Upload the first file with **Replace** mode, then upload additional files with **Append** mode to merge them into the same vector store.

---

## How the RAG Pipeline Works

1. **Ingestion** — Each product is serialised as a text document (title + brand + price + category + description + features + rating) and embedded using `all-MiniLM-L6-v2`. Embeddings are stored in ChromaDB with ASIN as the document ID.

2. **Query** — When a user asks a question about a product:
   - The selected product's full record is fetched by ASIN
   - ChromaDB retrieves the top-3 semantically similar related products
   - All context is assembled into the system prompt

3. **Generation** — Phi-3 streams a grounded answer via Ollama's `/api/chat` endpoint. Tokens are forwarded to Streamlit as SSE and rendered in real-time with `st.write_stream`.

---

## Project Structure

```
Amazone-Product-AI-Explorer/
├── streamlit_app.py             # Streamlit UI — browse, chat, upload
├── requirements-streamlit.txt   # Streamlit dependencies
├── .streamlit/
│   └── config.toml              # Dark amber theme
├── backend/
│   ├── main.py                  # FastAPI app — all API endpoints
│   ├── products.py              # ProductLoader: in-memory search + normalisation
│   ├── rag.py                   # RAGEngine: ChromaDB + Ollama SSE streaming
│   └── requirements.txt
├── pipeline/
│   ├── 1_prepare_dataset.py     # Normalise raw UCSD data
│   ├── 2_build_vectorstore.py   # Pre-build ChromaDB index
│   ├── 3_start_ollama.py        # Check + start Ollama
│   ├── 4_test_rag.py            # End-to-end RAG test
│   └── download_all.py          # Bulk dataset downloader
├── data/
│   ├── raw/                     # Place .jsonl.gz files here
│   ├── processed/               # Normalised products.jsonl
│   └── chroma/                  # ChromaDB persistent store
└── README.md
```

> The `frontend/` directory (legacy React app) is kept for reference but is no longer used.

---

## API Reference

| Endpoint | Method | Description |
|---|---|---|
| `/health` | GET | DB stats: product count + indexed docs |
| `/categories` | GET | All available product categories |
| `/products` | GET | Search + filter + paginate products |
| `/products/{asin}` | GET | Get single product by ASIN |
| `/ingest?append=bool` | POST | Upload + embed a product file |
| `/chat` | POST | Stream RAG answer (SSE) |

---

## Troubleshooting

| Problem | Fix |
|---|---|
| **No products in grid** | Upload a dataset file via the Upload Dataset page in the sidebar |
| **Chat shows no response** | Check Ollama is running: `ollama list` — make sure `phi3` appears |
| **"model requires more system memory"** | Phi-3 needs ~2.2 GB free RAM. Close other apps, or reduce the context window in `rag.py` (`num_ctx`) |
| **Backend won't start** | `pip install -r backend/requirements.txt` — ChromaDB needs Python 3.10+ |
| **Slow first response** | Normal — first query loads the embedding model into memory (~2–5 s) |
| **Embedding errors** | First run downloads the MiniLM model (~90 MB) — needs internet access |

---

## License

MIT — do whatever you want with it.
