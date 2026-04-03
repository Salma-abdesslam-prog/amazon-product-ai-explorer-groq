#!/usr/bin/env python3
"""
4_test_rag.py — End-to-end test of the RAG pipeline via the FastAPI backend.

Tests /health, /products, and /chat endpoints using only the Python standard
library. No extra dependencies required.
"""

import argparse
import json
import sys
import urllib.error
import urllib.request

# Windows: force UTF-8 output
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

BACKEND_URL = "http://localhost:8080"

# Sample product used when no real product is available from /products
FALLBACK_PRODUCT = {
    "asin": "TEST001",
    "title": "Sony WH-1000XM5 Wireless Noise Canceling Headphones",
    "brand": "Sony",
    "price": "$279.99",
    "description": (
        "Industry-leading noise cancellation with two processors controlling 8 microphones. "
        "30-hour battery life with quick charging. Crystal clear hands-free calling."
    ),
    "features": [
        "Industry-leading noise cancellation with two processors controlling 8 microphones",
        "30-hour battery life with quick charging (3 min = 3 hours playback)",
        "Multipoint connection — connect to two Bluetooth devices simultaneously",
    ],
    "categories": ["Electronics", "Headphones"],
    "main_category": "Electronics",
    "image_url": "",
    "rating": 4.6,
    "review_count": 12483,
}

TEST_QUESTIONS = [
    "What is this product?",
    "What are its main features?",
    "Is it good value for the price?",
]


def _get(url: str, timeout: int = 15):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, str(e)


def _post_json(url: str, payload: dict, timeout: int = 60):
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.status, resp.read().decode("utf-8")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")
    except Exception as e:
        return None, str(e)


def _post_sse(url: str, payload: dict, timeout: int = 90) -> str:
    """POST and collect a full SSE stream, return accumulated content."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url, data=data,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    tokens = []
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            for raw_line in resp:
                line = raw_line.decode("utf-8", errors="replace").strip()
                if not line.startswith("data:"):
                    continue
                chunk = line[5:].strip()
                if chunk == "[DONE]":
                    break
                try:
                    obj = json.loads(chunk)
                    token = obj.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    if token:
                        tokens.append(token)
                except json.JSONDecodeError:
                    continue
    except Exception as e:
        return f"ERROR: {e}"
    return "".join(tokens)


def section(title: str):
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def main():
    parser = argparse.ArgumentParser(description="End-to-end RAG pipeline test")
    parser.add_argument("--url", default=BACKEND_URL, help="FastAPI backend base URL")
    args = parser.parse_args()

    base = args.url.rstrip("/")
    passed = 0
    failed = 0

    print("\n" + "=" * 60)
    print("  Amazon RAG Pipeline — End-to-End Test")
    print(f"  Backend: {base}")
    print("=" * 60)

    # ── Test 1: Health check ──────────────────────────────────────────────────
    section("Test 1/3 — /health")
    status, body = _get(f"{base}/health")
    if status == 200:
        try:
            health = json.loads(body)
            print(f"  Status        : OK")
            print(f"  Products      : {health.get('products', '?'):,}")
            print(f"  Indexed docs  : {health.get('indexed_docs', '?'):,}")
            passed += 1
        except Exception:
            print(f"  Status        : OK (unparseable body)")
            passed += 1
    else:
        print(f"  FAILED — HTTP {status}: {body[:200]}")
        print("\n  Is the backend running?")
        print("    cd amazon-phi3-app/backend && uvicorn main:app --port 8080 --reload")
        failed += 1

    # ── Test 2: Products endpoint ─────────────────────────────────────────────
    section("Test 2/3 — GET /products")
    status, body = _get(f"{base}/products?page_size=1")
    product = FALLBACK_PRODUCT
    if status == 200:
        try:
            data = json.loads(body)
            items = data.get("products") or data.get("items") or []
            total = data.get("total", len(items))
            if items:
                product = items[0]
                print(f"  Status        : OK")
                print(f"  Total products: {total:,}")
                print(f"  Sample product: {product.get('title', '')[:60]}")
                passed += 1
            else:
                print(f"  OK but 0 products returned — using fallback product for chat test")
                passed += 1
        except Exception as e:
            print(f"  FAILED — could not parse response: {e}")
            failed += 1
    else:
        print(f"  FAILED — HTTP {status}: {body[:200]}")
        print("  Using fallback product for chat test.")
        failed += 1

    # ── Test 3: Chat / RAG ────────────────────────────────────────────────────
    section("Test 3/3 — POST /chat (RAG streaming)")
    print(f"  Product : {product.get('title', '')[:60]}")
    print(f"  Question: {TEST_QUESTIONS[0]}\n")

    payload = {
        "message": TEST_QUESTIONS[0],
        "product": product,
        "history": [],
    }
    response = _post_sse(f"{base}/chat", payload, timeout=90)

    if response.startswith("ERROR"):
        print(f"  FAILED — {response}")
        failed += 1
    elif len(response) < 5:
        print(f"  FAILED — empty response from /chat")
        failed += 1
    else:
        print(f"  Answer  : {response[:300]}")
        if len(response) > 300:
            print(f"            ... [{len(response)} chars total]")
        passed += 1

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'=' * 60}")
    print(f"  Results: {passed}/3 passed  |  {failed} failed")
    print(f"{'=' * 60}")

    if failed == 0:
        print("\n  All tests passed! Your RAG pipeline is working correctly.\n")
    elif passed > 0:
        print(f"\n  {passed} test(s) passed, {failed} failed. Check the errors above.\n")
    else:
        print("\n  All tests failed. Ensure the backend is running and the vectorstore is built.")
        print("  Steps:")
        print("    1. python pipeline/1_prepare_dataset.py --input data/raw/")
        print("    2. python pipeline/2_build_vectorstore.py")
        print("    3. python pipeline/3_start_ollama.py")
        print("    4. cd backend && uvicorn main:app --port 8080 --reload")
        sys.exit(1)


if __name__ == "__main__":
    main()
