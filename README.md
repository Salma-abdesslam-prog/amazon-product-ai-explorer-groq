# Amazone-Product-AI-Explorer

A full-stack RAG-powered product chatbot built on real Amazon catalogue data. Browse thousands of products, click any item, and get instant AI answers about it — streamed token-by-token from a local Phi-3 model with full semantic context retrieval.

![Architecture](https://img.shields.io/badge/stack-React%20%2B%20FastAPI%20%2B%20ChromaDB%20%2B%20Phi--3-E8A320?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square)
![Node](https://img.shields.io/badge/Node.js-18%2B-green?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-white?style=flat-square)

---

## What it does

- **Browse** a searchable, filterable grid of real Amazon products across multiple categories
- **Click any product** to open an AI chat panel on the right
- **Ask anything** — "Is this waterproof?", "How does it compare to similar products?", "What are the main complaints?"
- **Get streamed answers** grounded in actual product data via RAG (no hallucinated specs)
- **Upload new categories** at any time through the built-in data panel

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
│              React Frontend (:3000)                 │
│                                                     │
│  ProductBrowser   CategoryFilter   SearchBar        │
│  ProductCard      ChatBot (SSE)    UploadPanel      │
└─────────────────────────────────────────────────────┘
```

---

## Tech Stack

| Layer | Technology |
|---|---|
| Frontend | React 18, Tailwind CSS, Lucide icons |
| Backend | FastAPI, Uvicorn (async) |
| LLM | Phi-3-mini-4k via Ollama (local, no API key) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` |
| Vector DB | ChromaDB (persistent, cosine similarity) |
| Streaming | Server-Sent Events (SSE) end-to-end |
| Data | UCSD Amazon Review Dataset 2023 |

---

## Prerequisites

| Tool | Version | Purpose |
|---|---|---|
| Python | 3.10+ | Backend + embeddings |
| Node.js | 18+ | Frontend |
| [Ollama](https://ollama.com/download) | latest | Local LLM runtime |
| npm | 9+ | Frontend deps |

---

## Quick Start

### 1. Clone the repo

```bash
git clone https://github.com/YOUR_USERNAME/Amazone-Product-AI-Explorer.git
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

### 4. Install frontend dependencies

```bash
cd ../frontend
npm install
```

### 5. Run everything

**Option A — one command (Linux / macOS / WSL):**
```bash
cd ..
chmod +x start.sh
./start.sh
```

**Option B — three separate terminals:**

```bash
# Terminal 1 — Backend
cd backend
uvicorn main:app --host 0.0.0.0 --port 8080 --reload

# Terminal 2 — Ollama (if not already running)
ollama serve

# Terminal 3 — Frontend
cd frontend
npm start
```

Open **http://localhost:3000**

---

## Loading Product Data

The app ships without product data. On first launch, click **Upload Data** in the top-right corner and drop one of the UCSD Amazon dataset files.

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

3. **Generation** — Phi-3 streams a grounded answer via Ollama's `/api/chat` endpoint. Tokens are forwarded to the browser as SSE, appearing in real-time.

---

## Project Structure

```
Amazone-Product-AI-Explorer/
├── backend/
│   ├── main.py              # FastAPI app — all API endpoints
│   ├── products.py          # ProductLoader: in-memory search + normalisation
│   ├── rag.py               # RAGEngine: ChromaDB + Ollama streaming
│   └── requirements.txt
├── frontend/
│   ├── public/
│   │   └── index.html
│   ├── src/
│   │   ├── App.jsx                      # Root layout
│   │   ├── index.css                    # Design tokens + animations
│   │   ├── components/
│   │   │   ├── ProductBrowser.jsx       # Grid + pagination
│   │   │   ├── ProductCard.jsx          # Individual product tile
│   │   │   ├── SearchBar.jsx            # Debounced search
│   │   │   ├── CategoryFilter.jsx       # Category tag filter
│   │   │   ├── ChatBot.jsx              # Streaming AI chat panel
│   │   │   └── UploadPanel.jsx          # File upload + ingestion modal
│   │   └── hooks/
│   │       ├── useProducts.js           # Product fetching + pagination
│   │       └── useChat.js               # SSE streaming chat state
│   ├── package.json
│   └── tailwind.config.js
├── pipeline/
│   ├── 1_prepare_dataset.py             # Normalise raw UCSD data
│   ├── 2_build_vectorstore.py           # Pre-build ChromaDB index
│   ├── 3_start_ollama.py                # Check + start Ollama
│   ├── 4_test_rag.py                    # End-to-end RAG test
│   └── download_all.py                  # Bulk dataset downloader
├── data/
│   ├── raw/                             # Place .jsonl.gz files here
│   ├── processed/                       # Normalised products.jsonl
│   └── chroma/                          # ChromaDB persistent store
├── start.sh                             # Launch all services
└── README.md
```

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
| **No products in grid** | Upload a dataset file via the Upload Data button |
| **Chat returns no response** | Check Ollama is running: `ollama list` — make sure `phi3` is listed |
| **Backend won't start** | `pip install -r backend/requirements.txt` — ChromaDB needs Python 3.10+ |
| **Slow first response** | Normal — first query loads the embedding model into memory (~2–5s) |
| **CORS error in browser** | Ensure backend is on port 8080, not another port |
| **Embedding errors** | First run downloads the MiniLM model (~90 MB) — needs internet access |

---

## Design

The UI follows a **Neo-Editorial Commerce** aesthetic — near-black backgrounds, warm cream typography, amber accent color, and JetBrains Mono for all metadata. Fonts: Playfair Display (display) · DM Sans (body) · JetBrains Mono (mono).

---

## License

MIT — do whatever you want with it.
