#!/usr/bin/env python3
"""
3_check_groq.py — Verify a GROQ_API_KEY is set and the API is reachable.

Checks the Groq API with a minimal request, reports ChromaDB status,
and prints instructions for starting the backend / Streamlit app.
"""

import argparse
import json
import os
import sys
import urllib.error
import urllib.request

# Windows: force UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
GROQ_MODEL = "openai/gpt-oss-120b"


def check_groq(api_key: str, model: str) -> tuple[bool, str]:
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "Say OK."}],
        "max_tokens": 5,
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        GROQ_URL, data=data,
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return True, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return False, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return False, str(e)


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
    parser = argparse.ArgumentParser(description="Verify a Groq API key is set and reachable")
    parser.add_argument("--model", default=GROQ_MODEL, help="Groq model to test")
    parser.add_argument("--chroma_dir", default="data/chroma", help="ChromaDB directory to report stats")
    args = parser.parse_args()

    print("\n" + "=" * 60)
    print("  RAG Stack — Groq Setup Check")
    print("=" * 60)

    # ── Step 1: API key present? ──────────────────────────────────────────────
    api_key = os.environ.get("GROQ_API_KEY", "")
    print(f"\n[1/3] Checking GROQ_API_KEY environment variable...", end=" ")
    if not api_key:
        print("NOT SET")
        print("\n  No GROQ_API_KEY found in the environment.")
        print("  Get a free key at: https://console.groq.com/keys")
        print("  Then set it, e.g.:")
        print("    export GROQ_API_KEY=gsk_...        (macOS/Linux)")
        print("    $env:GROQ_API_KEY='gsk_...'         (PowerShell)")
        print("\n  For the Streamlit app, put it in .streamlit/secrets.toml instead")
        print("  (see .streamlit/secrets.toml.example).")
        sys.exit(1)
    print("OK")

    # ── Step 2: API reachable? ────────────────────────────────────────────────
    print(f"\n[2/3] Calling Groq with model '{args.model}'...", end=" ")
    ok, body = check_groq(api_key, args.model)
    if not ok:
        print("FAILED")
        print(f"\n  ERROR: {body[:300]}")
        sys.exit(1)
    print("OK")

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
    print("  Setup complete. Start the app with:")
    print()
    print("    streamlit run streamlit_app.py")
    print()
    print("  (or the optional standalone FastAPI backend:")
    print("    cd backend && uvicorn main:app --host 0.0.0.0 --port 8080 --reload)")
    print("=" * 60 + "\n")


if __name__ == "__main__":
    main()
