# Amazone-Product-AI-Explorer

A RAG-powered product chatbot built on real Amazon catalogue data. Browse thousands of products, click any item, and get instant AI answers streamed token-by-token from Llama 3.3 (via the Groq API) with full semantic context retrieval.

![Architecture](https://img.shields.io/badge/stack-Streamlit%20%2B%20ChromaDB%20%2B%20Groq-E8A320?style=flat-square)
![Python](https://img.shields.io/badge/Python-3.10%2B-blue?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-white?style=flat-square)

---

## What it does

- **Browse** a grid of real Amazon products, populated from a bundled demo dataset out of the box
- **Click any product** to open an AI chat session for that item
- **Ask anything** — "Is this waterproof?", "How does it compare to similar products?", "What are the main complaints?"
- **Get streamed answers** grounded in actual product data via RAG (no hallucinated specs)

---

## Architecture

Everything runs **in a single Streamlit process** — no separate backend server, no local model runtime. This is what makes it deployable to Streamlit Community Cloud, which only runs one `streamlit run` command.

```
UCSD Amazon Dataset (.jsonl.gz)
          │
          ▼
┌───────────────────────────────────────────────────────┐
│              Streamlit App (streamlit_app.py)          │
│                                                         │
│  ProductLoader              RAGEngine                  │
│  ┌─────────────┐            ┌───────────────────────┐  │
│  │ products[]  │            │ fastembed             │  │
│  │ in-memory   │            │ all-MiniLM-L6-v2      │  │
│  │ text search │            │ ChromaDB (cosine)     │  │
│  └─────────────┘            └───────────────────────┘  │
│         │                            │                 │
│         └──────────────┬─────────────┘                 │
│                        ▼                                │
│              product ctx + top-3 related                │
│                        │                                │
│                        ▼                                │
│                  Groq API (cloud)                       │
│                  Llama 3.3 70B                           │
│                        │ token stream                   │
│                        ▼                                │
│              Sidebar nav · Browse grid                  │
│              AI Chat · Dataset Upload                   │
└───────────────────────────────────────────────────────┘
```

An optional standalone FastAPI backend (`backend/main.py`) is kept for local API access / the legacy React frontend — see [Optional: standalone backend](#optional-standalone-fastapi-backend). It shares the same `ProductLoader` / `RAGEngine` code as the Streamlit app.

---

## Tech Stack

| Layer | Technology |
|---|---|
| App | Streamlit ≥ 1.32, dark amber theme |
| LLM | Llama 3.3 70B via the [Groq API](https://console.groq.com) (cloud, free tier available) |
| Embeddings | `sentence-transformers/all-MiniLM-L6-v2` via `fastembed` (ONNX runtime, no torch) |
| Vector DB | ChromaDB (persistent, cosine similarity) |
| Data | UCSD Amazon Review Dataset 2023 |

> Node.js is **not required** — the app is pure Python (Streamlit). The `frontend/` React app and `backend/` FastAPI service are legacy/optional — see below.

---

## Quick Start (local)

### 1. Clone the repo

```bash
git clone https://github.com/Salma-abdesslam-prog/Amazone-Product-AI-Explorer.git
cd Amazone-Product-AI-Explorer
```

### 2. Get a free Groq API key

Sign up and create a key at **https://console.groq.com/keys**.

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure the API key

```bash
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# then edit .streamlit/secrets.toml and paste your key
```

(Alternatively, set the `GROQ_API_KEY` environment variable instead.)

### 5. Run it

```bash
streamlit run streamlit_app.py
```

Open **http://localhost:8501**

---

## Deploying to Streamlit Community Cloud

1. Push this repo to GitHub.
2. Go to **[share.streamlit.io](https://share.streamlit.io)** → **New app**.
3. Pick the repo/branch and set **Main file path** to `streamlit_app.py`. Streamlit Cloud auto-detects the root `requirements.txt`.
4. In **Advanced settings → Secrets**, paste:
   ```toml
   GROQ_API_KEY = "gsk_your_key_here"
   ```
5. Deploy.

### Things to know about the Cloud environment

- **Storage is ephemeral, but that's fine here.** The catalogue always comes from `data/processed/products.jsonl`, which is committed to the repo and reloaded on every startup — so the app never comes up empty, and there's nothing dynamic that could be lost on a redeploy or a sleep/wake cycle.
- **Memory.** The free tier has limited RAM. `fastembed` (ONNX-based, no PyTorch) was chosen specifically to keep the embedding step lightweight; if you load a very large dataset (100k+ products) on the free tier, watch for OOM and consider a smaller category file first.
- **Cold start.** The first request after a sleep/redeploy re-downloads the ~90 MB embedding model and re-initializes ChromaDB — expect a slower first load.

---

## Loading Product Data

The app ships with a small **demo dataset built in** — 300 products from the UCSD "Luxury Beauty" category (`data/processed/products.jsonl`, committed to the repo) — so browsing and chat work immediately with no setup, and there's no in-app upload UI.

To swap in a different/larger dataset, regenerate that file locally and redeploy:

### 1. Download a dataset file

Go to the [UCSD Amazon Reviews 2023](https://amazon-reviews-2023.github.io/) page and download any `meta_*.jsonl.gz` file. Good starting points:

| File | Size | Products |
|---|---|---|
| `meta_Musical_Instruments.jsonl.gz` | ~30 MB | ~11k |
| `meta_All_Beauty.jsonl.gz` | ~60 MB | ~33k |
| `meta_AMAZON_FASHION.jsonl.gz` | ~150 MB | ~186k |

### 2. Normalise it into `data/processed/products.jsonl`

```bash
python pipeline/1_prepare_dataset.py --input path/to/meta_Whatever.jsonl.gz --max_products 300
```
`--max_products` caps how many end up in the file — keep it small if you want this committed to the repo (Streamlit Cloud storage is ephemeral, so whatever ships in the repo is what a fresh deploy starts with).

### 3. Commit and push

```bash
git add data/processed/products.jsonl
git commit -m "Update demo dataset"
git push
```
Streamlit Cloud redeploys automatically and picks up the new file on startup.

---

## How the RAG Pipeline Works

1. **Ingestion** — Each product is serialised as a text document (title + brand + price + category + description + features + rating) and embedded using `all-MiniLM-L6-v2` (via `fastembed`). Embeddings are stored in ChromaDB with ASIN as the document ID.

2. **Query** — When a user asks a question about a product:
   - The selected product's full record is fetched by ASIN
   - ChromaDB retrieves the top-3 semantically similar related products
   - All context is assembled into the system prompt

3. **Generation** — Llama 3.3 70B streams a grounded answer via the Groq API. Tokens are rendered in real-time with `st.write_stream`.

---

## Project Structure

```
Amazone-Product-AI-Explorer/
├── streamlit_app.py             # The app — UI + in-process RAG (browse, chat, upload)
├── requirements.txt              # Dependencies for the Streamlit app (used by Streamlit Cloud)
├── .streamlit/
│   ├── config.toml               # Dark amber theme
│   └── secrets.toml.example      # Copy to secrets.toml and add your GROQ_API_KEY
├── backend/                      # Optional standalone FastAPI backend (local dev only)
│   ├── main.py                   # FastAPI app — REST endpoints over the same logic
│   ├── products.py               # ProductLoader: in-memory search + normalisation
│   ├── rag.py                    # RAGEngine: ChromaDB + Groq streaming
│   └── requirements.txt
├── pipeline/
│   ├── 1_prepare_dataset.py      # Normalise raw UCSD data
│   ├── 2_build_vectorstore.py    # Pre-build ChromaDB index
│   ├── 3_check_groq.py           # Verify GROQ_API_KEY + API connectivity
│   ├── 4_test_rag.py             # End-to-end test of the optional FastAPI backend
│   └── download_all.py           # Bulk dataset downloader
├── data/
│   ├── raw/                      # Place .jsonl.gz files here (gitignored)
│   ├── processed/
│   │   └── products.jsonl        # Committed demo dataset (300 products) — replaced/appended via Upload
│   └── chroma/                   # ChromaDB persistent store (gitignored, rebuilt at startup)
└── README.md
```

> The `frontend/` directory (legacy React app) is kept for reference but is no longer used — it required the FastAPI backend, which the Streamlit app no longer depends on.

---

## Optional: standalone FastAPI backend

`backend/main.py` still exists as a REST API over the same `ProductLoader`/`RAGEngine` code, for local development or integrating with something other than the Streamlit UI. It's independent of the Streamlit app — not needed to run or deploy it.

```bash
export GROQ_API_KEY=gsk_...          # or set it however your shell prefers
pip install -r backend/requirements.txt
cd backend
uvicorn main:app --host 0.0.0.0 --port 8080 --reload
```

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
| **No products in grid** | Shouldn't happen — the demo dataset ships in the repo. If it does, check `data/processed/products.jsonl` exists and isn't empty |
| **Sidebar shows "No GROQ_API_KEY configured"** | Add the key to `.streamlit/secrets.toml` (local) or the app's Secrets panel (Streamlit Cloud) |
| **Chat shows a Groq error** | Check your key is valid at https://console.groq.com/keys and that you haven't hit a rate limit |
| **App is slow / crashes after a big upload (Cloud)** | Free tier RAM is limited — try a smaller category file, or upgrade the app's resources |
| **Data disappeared after redeploy (Cloud)** | Expected — Cloud storage is ephemeral. Re-upload your dataset file |
| **Slow first response** | Normal — first query loads the embedding model into memory (~2–5 s locally, longer on a cold Cloud start) |
| **Embedding errors** | First run downloads the MiniLM ONNX model (~90 MB) — needs internet access |

---

## License

MIT — do whatever you want with it.
