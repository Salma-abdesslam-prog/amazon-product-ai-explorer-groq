"""
Amazone Product AI Explorer — Streamlit UI
Sidebar navigation + product grid + RAG chat + dataset upload.
Everything (product search + RAG + LLM) runs in-process — no separate
backend server needed, so this deploys as a single app on Streamlit
Community Cloud.
Run: streamlit run streamlit_app.py
"""

import os
import sys
from pathlib import Path
from typing import Generator

import streamlit as st

_ROOT = Path(__file__).parent
sys.path.insert(0, str(_ROOT / "backend"))

from products import ProductLoader, parse_jsonl_bytes  # noqa: E402
from rag import RAGEngine  # noqa: E402

LIMIT = 20

# Gradient palette for products without images
_GRAD = [
    ("#1a1612", "#2a2118"), ("#101820", "#192030"), ("#0f1a15", "#172a20"),
    ("#1a1510", "#28201a"), ("#14101a", "#211828"), ("#0e1a1a", "#162828"),
]

NAV = ["browse", "chat", "upload"]
NAV_LABEL = {
    "browse": "🛍️  Browse catalogue",
    "chat":   "💬  AI Chat",
    "upload": "📤  Upload dataset",
}

# ─── Page config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Product AI Explorer",
    page_icon="◉",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Minimal CSS — only things the theme engine can't handle
st.markdown("""
<style>
/* Streamlit chrome */
#MainMenu, footer, [data-testid="stToolbar"],
[data-testid="stDecoration"], [data-testid="stStatusWidget"]
  { display:none !important; }

/* Content starts right below header */
.block-container { padding-top:1.8rem !important; padding-bottom:0 !important; }

/* Sidebar width */
[data-testid="stSidebar"] { min-width:270px !important; max-width:290px !important; }
[data-testid="stSidebar"] .block-container { padding-top:1.4rem !important; }

/* Nav radio — bigger hit targets, no radio dot */
[data-testid="stRadio"] > label { display:none !important; }
[data-testid="stRadio"] > div { gap:2px !important; }
[data-testid="stRadio"] > div > label {
    padding:0.55rem 0.85rem !important;
    border-radius:8px !important;
    font-size:0.92rem !important;
    cursor:pointer !important;
    transition:background 0.15s !important;
    width:100% !important;
}
[data-testid="stRadio"] > div > label:hover
  { background:rgba(255,255,255,0.07) !important; }
[data-testid="stRadio"] > div > label[data-baseweb="radio"] > div:first-child
  { display:none !important; }

/* Product card images */
.pimg { width:100%; height:155px; object-fit:cover; border-radius:8px;
        display:block; margin-bottom:0.5rem; }
.pimg-ph { width:100%; height:155px; border-radius:8px; margin-bottom:0.5rem;
           display:flex; align-items:center; justify-content:center;
           font-family:Georgia,serif; font-size:52px; font-weight:700;
           font-style:italic; color:rgba(255,255,255,0.12); }

/* Sidebar product thumbnail */
.simg { width:100%; height:90px; object-fit:cover;
        border-radius:6px; display:block; margin-bottom:0.4rem; }

/* Chat messages */
[data-testid="stChatMessage"] { border-radius:10px !important; }

/* Thin scrollbar */
::-webkit-scrollbar { width:4px; height:4px; }
::-webkit-scrollbar-thumb { background:rgba(255,255,255,0.12); border-radius:3px; }
</style>
""", unsafe_allow_html=True)

# ─── Session state ─────────────────────────────────────────────────────────────
for _k, _v in {
    "nav":              "browse",
    "selected_product": None,
    "messages":         [],
    "search":           "",
    "category":         "",
    "page":             1,
}.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v

# ─── Helpers ──────────────────────────────────────────────────────────────────
def _hash(s: str) -> int:
    h = 0
    for c in s:
        h = (h * 31 + ord(c)) & 0xFFFFFFFF
    return abs(h)

def _stars(r: float) -> str:
    r = round(min(max(r, 0), 5))
    return "★" * r + "☆" * (5 - r)

def _fmt_rc(n: int) -> str:
    return f"{n/1000:.1f}k" if n >= 1000 else str(n) if n > 0 else ""

def _go(page: str, product: dict | None = None):
    """Navigate to a page, optionally selecting a product."""
    st.session_state.nav = page
    if product is not None:
        st.session_state.selected_product = product
        st.session_state.messages = []
    st.rerun()

# ─── In-process backend (ProductLoader + RAGEngine) ────────────────────────────
def _groq_api_key() -> str:
    try:
        key = st.secrets.get("GROQ_API_KEY", "")
    except Exception:
        # st.secrets raises if no secrets.toml exists at all (e.g. local dev without one)
        key = ""
    return key or os.environ.get("GROQ_API_KEY", "")

@st.cache_resource(show_spinner="Loading product catalogue…")
def get_loader() -> ProductLoader:
    loader = ProductLoader()
    loader.load(
        processed_path=str(_ROOT / "data" / "processed" / "products.jsonl"),
        raw_dir=str(_ROOT / "data" / "raw"),
    )
    return loader

@st.cache_resource(show_spinner="Loading embedding model + vector index…")
def get_rag(_loader: ProductLoader) -> RAGEngine:
    rag = RAGEngine(chroma_dir=str(_ROOT / "data" / "chroma"), groq_api_key=_groq_api_key())
    if rag.doc_count != len(_loader.products) and _loader.products:
        rag.ingest(_loader.products)
    return rag

def api_products(query: str, category: str, page: int):
    try:
        loader = get_loader()
        result = loader.search(query=query, category=category, page=page, limit=LIMIT)
        return result["products"], result["total"], result["pages"], None
    except Exception as e:
        return [], 0, 1, str(e)

def api_categories():
    try:
        return get_loader().get_categories()
    except Exception:
        return []

def api_health():
    try:
        loader = get_loader()
        rag = get_rag(loader)
        return {"products": len(loader.products), "indexed_docs": rag.doc_count}
    except Exception:
        return None

def ingest_upload(file_bytes: bytes, append: bool) -> dict:
    """Parse an uploaded dataset file and merge/replace it into the loader + vector index."""
    products = parse_jsonl_bytes(file_bytes)
    if not products:
        raise ValueError("No valid products found in the uploaded file.")

    loader = get_loader()
    rag = get_rag(loader)

    if append:
        existing_asins = set(loader.by_asin.keys())
        new_products = [p for p in products if p.get("asin") not in existing_asins or not p.get("asin")]
        loader.load_from_list(loader.products + new_products)
        rag.ingest(new_products, append=True)
        return {
            "products": len(loader.products),
            "new_products": len(new_products),
            "indexed_docs": rag.doc_count,
        }
    else:
        loader.load_from_list(products)
        n = rag.ingest(products, append=False)
        return {"products": len(products), "new_products": len(products), "indexed_docs": n}

def chat_stream(user_text: str, product: dict, history: list) -> Generator[str, None, None]:
    try:
        rag = get_rag(get_loader())
        yield from rag.stream_chat(user_text, product, history)
    except Exception as e:
        yield f"\n\n⚠️ {e}"

# ─── Product card ──────────────────────────────────────────────────────────────
def product_card(prod: dict, sel_asin: str):
    asin    = prod.get("asin") or prod.get("title", "")[:20]
    title   = prod.get("title") or "No title"
    brand   = prod.get("brand") or ""
    price   = prod.get("price") or ""
    rating  = float(prod.get("rating") or 0)
    rc      = int(prod.get("review_count") or 0)
    img_url = prod.get("image_url") or ""
    is_sel  = bool(sel_asin and prod.get("asin") == sel_asin)
    g1, g2  = _GRAD[_hash(asin) % len(_GRAD)]
    initial = (title or "P")[0].upper()

    with st.container(border=True):
        # ── Image ──────────────────────────────────────────────────────────
        if img_url:
            st.markdown(
                f'<img class="pimg" src="{img_url}"'
                f' onerror="this.outerHTML=\'<div class=&quot;pimg-ph&quot; style=&quot;'
                f'background:linear-gradient(135deg,{g1},{g2});&quot;>{initial}</div>\'">',
                unsafe_allow_html=True,
            )
        else:
            st.markdown(
                f'<div class="pimg-ph" style="background:linear-gradient(135deg,{g1},{g2});">'
                f"{initial}</div>",
                unsafe_allow_html=True,
            )

        # ── Text ───────────────────────────────────────────────────────────
        if brand:
            st.caption(brand.upper())

        disp = (title[:52] + "…") if len(title) > 52 else title
        st.markdown(f"**{disp}**")

        c_price, c_stars = st.columns(2)
        with c_price:
            if price:
                st.markdown(f":orange[**{price}**]")
        with c_stars:
            if rating > 0:
                rc_str = f" {_fmt_rc(rc)}" if rc else ""
                st.caption(f"{_stars(rating)}{rc_str}")

        # ── CTA ────────────────────────────────────────────────────────────
        if is_sel:
            st.success("✓ In chat", icon="💬")
        else:
            key = f"ask_{asin}_{_hash(title) % 99991}"
            if st.button("💬 Ask AI", key=key, use_container_width=True, type="primary"):
                _go("chat", prod)


# ═══════════════════════════════════════════════════════════════════════════════
# SIDEBAR
# ═══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("## ◉ Product AI")
    st.caption("RAG-powered Amazon catalogue · Llama 3.3 (Groq)")
    st.divider()

    # ── Navigation ────────────────────────────────────────────────────────────
    nav_choice = st.radio(
        "nav",
        options=NAV,
        format_func=lambda x: NAV_LABEL[x],
        index=NAV.index(st.session_state.nav),
        label_visibility="collapsed",
    )
    # Sync nav (handles user clicking radio directly)
    if nav_choice != st.session_state.nav:
        st.session_state.nav = nav_choice
        st.rerun()

    st.divider()

    # ── Filters (relevant for browse) ─────────────────────────────────────────
    new_search = st.text_input(
        "🔍 Search",
        value=st.session_state.search,
        placeholder="headphones, laptops, shoes…",
    )
    if new_search != st.session_state.search:
        st.session_state.search   = new_search
        st.session_state.page     = 1
        st.session_state.nav      = "browse"
        st.rerun()

    cats   = api_categories()
    opts   = ["All categories"] + cats
    cur_ci = 0
    if st.session_state.category:
        try:
            cur_ci = opts.index(st.session_state.category)
        except ValueError:
            cur_ci = 0
    cat_pick = st.selectbox("📂 Category", opts, index=cur_ci)
    new_cat  = "" if cat_pick == "All categories" else cat_pick
    if new_cat != st.session_state.category:
        st.session_state.category = new_cat
        st.session_state.page     = 1
        st.session_state.nav      = "browse"
        st.rerun()

    # ── DB stats ──────────────────────────────────────────────────────────────
    st.divider()
    health = api_health()
    if health:
        sc1, sc2 = st.columns(2)
        sc1.metric("Products",  f"{health.get('products', 0):,}")
        sc2.metric("Indexed",   f"{health.get('indexed_docs', 0):,}")
    else:
        st.warning("Could not load the catalogue.", icon="⚠️")

    if not _groq_api_key():
        st.warning("No **GROQ_API_KEY** configured — chat is disabled.", icon="🔑")

    # ── Selected product info ─────────────────────────────────────────────────
    sel = st.session_state.selected_product
    if sel:
        st.divider()
        st.caption("CHATTING ABOUT")
        with st.container(border=True):
            img_url = sel.get("image_url", "")
            if img_url:
                st.markdown(
                    f'<img class="simg" src="{img_url}"'
                    f' onerror="this.style.display=\'none\'">',
                    unsafe_allow_html=True,
                )
            t = sel.get("title", "")
            st.markdown(f"**{(t[:42]+'…') if len(t)>42 else t}**")
            meta = " · ".join(filter(None, [sel.get("brand"), sel.get("price")]))
            if meta:
                st.caption(meta)
            r = float(sel.get("rating") or 0)
            if r > 0:
                st.progress(r / 5, text=f"{_stars(r)} {r:.1f}")
            n_msgs = sum(1 for m in st.session_state.messages if m["role"] == "user")
            if n_msgs:
                st.caption(f"{n_msgs} message{'s' if n_msgs > 1 else ''} in history")

            if st.button("Open Chat →", use_container_width=True, type="primary"):
                _go("chat")
            if st.button("✕ Deselect", use_container_width=True):
                st.session_state.selected_product = None
                st.session_state.messages = []
                if st.session_state.nav == "chat":
                    st.session_state.nav = "browse"
                st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — BROWSE
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.nav == "browse":

    # Header row
    h_left, h_right = st.columns([5, 2])
    with h_left:
        st.markdown("## 🛍️ Browse Catalogue")

    # Fetch
    products, total, pages, err = api_products(
        st.session_state.search, st.session_state.category, st.session_state.page
    )

    # Active filter pills + count
    pill_parts = []
    if st.session_state.search:
        pill_parts.append(f"🔍 **{st.session_state.search}**")
    if st.session_state.category:
        pill_parts.append(f"📂 **{st.session_state.category}**")

    info_cols = st.columns([6, 1]) if pill_parts else [st.container()]
    with info_cols[0]:
        if not err:
            if pill_parts:
                st.markdown(
                    f"{' · '.join(pill_parts)} · "
                    f"<span style='color:gray'>{total:,} results · page {st.session_state.page}/{pages}</span>",
                    unsafe_allow_html=True,
                )
            else:
                st.caption(f"{total:,} products · page {st.session_state.page} of {pages}")

    if pill_parts and len(info_cols) > 1:
        with info_cols[1]:
            if st.button("✕ Clear", use_container_width=True):
                st.session_state.search   = ""
                st.session_state.category = ""
                st.session_state.page     = 1
                st.rerun()

    st.divider()

    # Error state
    if err:
        st.error(f"**Error loading products:** {err}", icon="⚠️")
        if st.button("🔄 Retry"):
            st.rerun()

    # Empty state
    elif not products:
        ec1, ec2, ec3 = st.columns([1, 2, 1])
        with ec2:
            st.markdown(
                "<br><div style='text-align:center;padding:2rem 0;'>"
                "<p style='font-size:3rem'>🔍</p>"
                "<p style='font-size:1.1rem;font-weight:600;'>No products found</p>"
                "<p style='color:gray;'>Try different keywords or clear the filters.</p>"
                "</div>",
                unsafe_allow_html=True,
            )

    # Product grid
    else:
        sel_asin = (st.session_state.selected_product or {}).get("asin", "")
        N = 4
        for row_start in range(0, len(products), N):
            row  = products[row_start : row_start + N]
            cols = st.columns(N, gap="medium")
            for col, prod in zip(cols, row):
                with col:
                    product_card(prod, sel_asin)

        # Pagination
        if pages > 1:
            st.divider()
            pg1, pg2, pg3 = st.columns([1, 2, 1])
            with pg1:
                st.button(
                    "← Previous",
                    disabled=st.session_state.page <= 1,
                    use_container_width=True,
                    on_click=lambda: st.session_state.update(page=st.session_state.page - 1),
                )
            with pg2:
                st.markdown(
                    f"<p style='text-align:center;color:gray;padding:0.4rem 0;'>"
                    f"Page {st.session_state.page} of {pages}</p>",
                    unsafe_allow_html=True,
                )
            with pg3:
                st.button(
                    "Next →",
                    disabled=st.session_state.page >= pages,
                    use_container_width=True,
                    on_click=lambda: st.session_state.update(page=st.session_state.page + 1),
                )


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — CHAT
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.nav == "chat":

    if not st.session_state.selected_product:
        # ── No product selected ───────────────────────────────────────────────
        st.markdown("## 💬 AI Chat")
        st.divider()

        cc1, cc2, cc3 = st.columns([1, 3, 1])
        with cc2:
            with st.container(border=True):
                st.markdown(
                    "<div style='text-align:center;padding:2rem 1rem;'>"
                    "<p style='font-size:3rem'>🛍️</p>"
                    "<h3>Select a product first</h3>"
                    "<p style='color:gray;'>Browse the catalogue and click "
                    "<strong>💬 Ask AI</strong> on any product to start chatting.</p>"
                    "</div>",
                    unsafe_allow_html=True,
                )
                if st.button("Go to Browse →", use_container_width=True, type="primary"):
                    _go("browse")

    else:
        # ── Chat session ──────────────────────────────────────────────────────
        prod    = st.session_state.selected_product
        title   = prod.get("title", "")
        brand   = prod.get("brand", "")
        price   = prod.get("price", "")
        rating  = float(prod.get("rating") or 0)
        img_url = prod.get("image_url", "")
        asin    = prod.get("asin") or title[:15]
        g1, g2  = _GRAD[_hash(asin) % len(_GRAD)]
        initial = (title or "P")[0].upper()

        # ── Product context banner ────────────────────────────────────────────
        with st.container(border=True):
            bc1, bc2, bc3 = st.columns([1, 7, 2])

            with bc1:
                if img_url:
                    st.markdown(
                        f'<img src="{img_url}" style="width:58px;height:58px;'
                        f'object-fit:cover;border-radius:8px;"'
                        f' onerror="this.style.display=\'none\'">',
                        unsafe_allow_html=True,
                    )
                else:
                    st.markdown(
                        f'<div style="width:58px;height:58px;border-radius:8px;'
                        f'background:linear-gradient(135deg,{g1},{g2});'
                        f'display:flex;align-items:center;justify-content:center;'
                        f'font-size:22px;font-style:italic;color:rgba(255,255,255,.2);">'
                        f"{initial}</div>",
                        unsafe_allow_html=True,
                    )

            with bc2:
                disp_t = (title[:80] + "…") if len(title) > 80 else title
                st.markdown(f"**{disp_t}**")
                meta_parts = [p for p in [brand, price] if p]
                if rating > 0:
                    meta_parts.append(f"{_stars(rating)} {rating:.1f}")
                meta_parts.append("🟢 Llama 3.3 · RAG")
                st.caption("  ·  ".join(meta_parts))

            with bc3:
                if st.button("← Browse", use_container_width=True):
                    _go("browse")
                if st.session_state.messages:
                    if st.button("🗑 Clear chat", use_container_width=True):
                        st.session_state.messages = []
                        st.rerun()

        # ── Message history ───────────────────────────────────────────────────
        if not st.session_state.messages:
            st.markdown("<br>", unsafe_allow_html=True)
            ic1, ic2, ic3 = st.columns([1, 3, 1])
            with ic2:
                st.markdown(
                    "<div style='text-align:center;padding:2.5rem 0;color:gray;'>"
                    "<p style='font-size:2.5rem'>💬</p>"
                    "<p>Ask anything — specs, comparisons, tips, alternatives…</p>"
                    "</div>",
                    unsafe_allow_html=True,
                )
        else:
            for msg in st.session_state.messages:
                with st.chat_message(msg["role"]):
                    st.markdown(msg["content"])

        # ── Chat input (pins to bottom of viewport) ───────────────────────────
        prompt_label = (
            f"Ask about {(title[:45]+'…') if len(title)>45 else title}…"
        )
        if prompt := st.chat_input(prompt_label):
            st.session_state.messages.append({"role": "user", "content": prompt})

            with st.chat_message("user"):
                st.markdown(prompt)

            history = [
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages[:-1]
                if m.get("content")
            ]

            with st.chat_message("assistant"):
                response = st.write_stream(
                    chat_stream(prompt, st.session_state.selected_product, history)
                )

            st.session_state.messages.append(
                {"role": "assistant", "content": response}
            )


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN — UPLOAD
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.nav == "upload":

    st.markdown("## 📤 Upload Dataset")
    st.caption("Import Amazon product data from UCSD dataset files.")
    st.divider()

    # ── DB stats ──────────────────────────────────────────────────────────────
    health = api_health()
    if health:
        mc1, mc2, mc3 = st.columns(3)
        products_n  = health.get("products", 0)
        indexed_n   = health.get("indexed_docs", 0)
        coverage    = indexed_n / max(products_n, 1)
        mc1.metric("Products in database", f"{products_n:,}")
        mc2.metric("Indexed documents",    f"{indexed_n:,}")
        mc3.metric("Index coverage",       f"{coverage:.0%}",
                   delta="fully indexed" if coverage >= 0.99 else "partial",
                   delta_color="normal" if coverage >= 0.99 else "inverse")
    else:
        st.error("Cannot reach backend to show database stats.", icon="🔌")

    st.divider()

    # ── Upload form ───────────────────────────────────────────────────────────
    with st.container(border=True):
        st.subheader("Import file")
        st.caption("Accepts **.json**, **.jsonl**, and **.jsonl.gz** files (UCSD Amazon dataset format)")

        uploaded = st.file_uploader(
            "Dataset file",
            type=["json", "jsonl", "gz"],
            label_visibility="collapsed",
        )

        if uploaded:
            sz_mb = uploaded.size / 1024 / 1024
            st.info(f"📄 **{uploaded.name}** — {sz_mb:.2f} MB", icon="✅")

        st.markdown("---")
        st.markdown("**Import mode**")

        mode = st.radio(
            "mode",
            options=["replace", "append"],
            format_func=lambda x: (
                "🔄  Replace — wipe all existing products and load this file"
                if x == "replace" else
                "➕  Append — merge new products with existing ones (deduplicates by ASIN)"
            ),
            label_visibility="collapsed",
        )
        append = mode == "append"

        if mode == "replace" and uploaded:
            st.warning(
                "This will **permanently delete** all existing products and replace them.",
                icon="⚠️",
            )

        st.markdown("---")
        submit = st.button(
            "Append & Index" if append else "Upload & Replace",
            disabled=not uploaded,
            type="primary",
            use_container_width=True,
        )

    # ── Upload processing ──────────────────────────────────────────────────────
    if submit and uploaded:
        with st.status("Processing dataset…", expanded=True) as status:
            st.write("📖 Parsing file…")
            try:
                d = ingest_upload(uploaded.getvalue(), append=append)
                st.write("🔧 Indexing into vector database…")

                status.update(
                    label="✅ Dataset processed successfully!",
                    state="complete",
                    expanded=True,
                )
                added = d.get("new_products", d.get("products", 0))
                total = d.get("products", 0)
                idx   = d.get("indexed_docs", 0)

                st.divider()
                rc1, rc2, rc3 = st.columns(3)
                rc1.metric("New products added", f"+{added:,}")
                rc2.metric("Total in database",  f"{total:,}")
                rc3.metric("Documents indexed",  f"{idx:,}")
                st.balloons()

            except Exception as e:
                status.update(label="❌ Upload failed", state="error")
                st.error(str(e))
