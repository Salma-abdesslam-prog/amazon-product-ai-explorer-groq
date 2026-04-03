#!/usr/bin/env python3
"""
3_start_ollama.py — Verify Ollama is running and the phi3 model is available.

Checks the Ollama API, pulls phi3:latest if missing, reports ChromaDB status,
and prints instructions for starting the FastAPI backend.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

# Windows: force UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OLLAMA_URL = "http://localhost:11434"
OLLAMA_MODEL = "phi3:latest"


def _get(url: str, timeout: int = 10):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, str(e)


def _post(url: str, payload: dict, timeout: int = 300):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"Content-Type": "application/json"}, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, str(e)


def check_ollama_running() -> bool:
    status, body = _get(f"{OLLAMA_URL}/api/tags")
    return status == 200


def list_models() -> list:
    status, body = _get(f"{OLLAMA_URL}/api/tags")
    if status != 200:
        return []
    try:
        return [m["name"] for m in json.loads(body).get("models", [])]
    except Exception:
        return []


def pull_model(model: str) -> bool:
    print(f"  Pulling {model} from Ollama registry (this may take a few minutes)...")
    status, body = _post(f"{OLLAMA_URL}/api/pull", {"name": model})
    return status == 200


def chroma_doc_count(chroma_dir: str) -> int:
    try:
        import chromadb
        from chromadb.config import Settings
        client = chromadb.PersistentClient(
            path=chroma_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        col = client.get_collection("amazon_products")
        return col.count()
    except Exception:
        return -1


def main():
    parser = argparse.ArgumentParser(description="Verify Ollama and phi3 model are ready for RAG")
    parser.add_argument("--model", default=OLLAMA_MODEL, help="Ollama model to verify/pull")
    parser.add_argument("--ollama_url", default=OLLAMA_URL, help="Ollama base URL")
    parser.add_argument("--chroma_dir", default="data/chroma", help="ChromaDB directory to report stats")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  RAG Stack — Ollama Setup Check")
    print("=" * 60)

    # ── Step 1: Ollama running? ───────────────────────────────────────────────
    print(f"\n[1/3] Checking Ollama at {args.ollama_url}...", end=" ")
    if not check_ollama_running():
        print("NOT RUNNING")
        print("\n  Ollama is not running. Start it with:")
        print("    ollama serve")
        print("\n  Or download Ollama from: https://ollama.com")
        sys.exit(1)
    print("OK")

    # ── Step 2: Model available? ──────────────────────────────────────────────
    models = list_models()
    model_name = args.model.split(":")[0]
    model_present = any(model_name in m for m in models)

    print(f"\n[2/3] Checking model '{args.model}'...", end=" ")
    if model_present:
        print("already pulled")
    else:
        print("not found, pulling now...")
        ok = pull_model(args.model)
        if not ok:
            print(f"\n  ERROR: Failed to pull {args.model}.")
            print("  Try manually: ollama pull phi3")
            sys.exit(1)
        print(f"  Model {args.model} pulled successfully.")

    # ── Step 3: ChromaDB stats ────────────────────────────────────────────────
    print(f"\n[3/3] Checking ChromaDB at '{args.chroma_dir}'...", end=" ")
    count = chroma_doc_count(args.chroma_dir)
    if count == -1:
        print("collection not found")
        print("  Run pipeline/2_build_vectorstore.py to index your products first.")
    else:
        print(f"{count:,} documents indexed")

    # ── Summary ───────────────────────────────────────────────────────────────
    print("\n" + "=" * 60)
    print("  Setup complete. Start the backend with:")
    print()
    print("    cd amazon-phi3-app/backend")
    print("    uvicorn main:app --host 0.0.0.0 --port 8080 --reload")
    print()
    print("  Then open the frontend:")
    print("    cd amazon-phi3-app/frontend")
    print("    npm start")
    print("=" * 60 + "\n")

    print("Next step:")
    print("  python pipeline/4_test_rag.py")


if __name__ == "__main__":
    main()
